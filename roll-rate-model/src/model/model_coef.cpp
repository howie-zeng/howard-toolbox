#include "model/model_coef.h"
#include <algorithm>
#include <cmath>
#include <set>
#include <sstream>
#include <stdexcept>

namespace rrm::model {

static constexpr int SMOOTH_MIN_ROWS    = 6;  // >5 numeric rows => smooth

std::string get_model_name(const std::string& from_status,
                           const std::string& to_status) {
    return "from" + from_status + "_" + to_status;
}

double smooth_1d_calc(double x, const Smooth1dInfo& info) {
    double xc = std::min(std::max(x, info.xmin), info.xmax);
    double x_in = (xc - info.xmin) * info.step_inv;
    int x_left = static_cast<int>(x_in);
    int x_right = x_left + 1;

    if (x_right <= info.xn) {
        return (info.lookup[x_right] - info.lookup[x_left]) * (x_in - x_left) + info.lookup[x_left];
    }
    return info.lookup[info.xn];
}

double smooth_2d_calc(double x, double y, const Smooth2dInfo& info) {
    double xc = std::min(std::max(x, info.xmin), info.xmax);
    double x_in = (xc - info.xmin) * info.xstep_inv;
    int x1 = static_cast<int>(x_in);
    int x2 = x1 + 1;

    double yc = std::min(std::max(y, info.ymin), info.ymax);
    double y_in = (yc - info.ymin) * info.ystep_inv;
    int y1 = static_cast<int>(y_in);
    int y2 = y1 + 1;

    if (x2 <= info.xn && y2 <= info.yn) {
        double x_y1 = (x2 - x_in) * info.lookup[x1][y1] + (x_in - x1) * info.lookup[x2][y1];
        double x_y2 = (x2 - x_in) * info.lookup[x1][y2] + (x_in - x1) * info.lookup[x2][y2];
        return (y2 - y_in) * x_y1 + (y_in - y1) * x_y2;
    }
    if (x2 > info.xn && y2 <= info.yn) {
        return (info.lookup[info.xn][y2] - info.lookup[info.xn][y1]) * (y_in - y1) + info.lookup[info.xn][y1];
    }
    if (x2 <= info.xn && y2 > info.yn) {
        return (info.lookup[x2][info.yn] - info.lookup[x1][info.yn]) * (x_in - x1) + info.lookup[x1][info.yn];
    }
    return info.lookup[info.xn][info.yn];
}

// ─── helpers ─────────────────────────────────────────────────────────────

static bool is_numeric(const std::string& s) {
    if (s.empty()) return false;
    char* end = nullptr;
    std::strtod(s.c_str(), &end);
    return end != s.c_str() && *end == '\0';
}

static Smooth1dInfo build_smooth_auto(const std::vector<io::CoefRow>& rows) {
    struct Pt { double x; double v; };
    std::vector<Pt> pts;
    pts.reserve(rows.size());
    for (const auto& r : rows)
        pts.push_back({std::stod(r.var_val1), r.value});
    std::sort(pts.begin(), pts.end(), [](const Pt& a, const Pt& b){ return a.x < b.x; });

    Smooth1dInfo info{};
    if (pts.size() < 2) {
        info.xmin = 0; info.xmax = 1; info.step_inv = 1; info.xn = 0;
        info.lookup = {pts.empty() ? 0.0 : pts[0].v};
        return info;
    }
    info.xmin = pts.front().x;
    info.xmax = pts.back().x;
    info.xn   = static_cast<int>(pts.size()) - 1;
    double step = (info.xn > 0) ? (info.xmax - info.xmin) / info.xn : 1.0;
    info.step_inv = (step > 0) ? 1.0 / step : 1.0;
    info.lookup.resize(pts.size());
    for (size_t i = 0; i < pts.size(); ++i)
        info.lookup[i] = pts[i].v;
    return info;
}

// ─── auto-detect model building ──────────────────────────────────────────

void ModelCoef::build_model_auto(const std::string& model_name,
                                 const std::vector<io::CoefRow>& rows) {
    ModelLink link;

    // Partition rows by (var_name1) and (var_name1, var_name2)
    std::unordered_map<std::string, std::vector<io::CoefRow>> by_var1;
    std::map<std::pair<std::string, std::string>, std::vector<io::CoefRow>> by_var12;

    for (const auto& r : rows) {
        if (!r.var_name2.empty()) {
            by_var12[{r.var_name1, r.var_name2}].push_back(r);
        } else {
            by_var1[r.var_name1].push_back(r);
        }
    }

    // Intercept
    {
        auto it = by_var1.find("intercept");
        if (it != by_var1.end() && !it->second.empty())
            link.intercept = it->second[0].value;
    }

    // 1D terms: auto-detect smooth vs lookup
    for (const auto& [var_name, var_rows] : by_var1) {
        if (var_name == "intercept") continue;

        bool all_numeric = std::all_of(var_rows.begin(), var_rows.end(),
            [](const io::CoefRow& r){ return is_numeric(r.var_val1); });

        if (all_numeric && static_cast<int>(var_rows.size()) >= SMOOTH_MIN_ROWS) {
            link.terms_1d[var_name] = build_smooth_auto(var_rows);
        } else {
            Lookup1dInfo info;
            for (const auto& r : var_rows)
                info.levels.emplace_back(r.var_val1, r.value);
            link.terms_1d[var_name] = std::move(info);
        }
    }

    // 2D terms: auto-detect type
    for (const auto& [key_pair, var_rows] : by_var12) {
        const auto& [vn1, vn2] = key_pair;

        bool v1_numeric = std::all_of(var_rows.begin(), var_rows.end(),
            [](const io::CoefRow& r){ return is_numeric(r.var_val1); });

        // Collect distinct var_val2 values
        std::set<std::string> vals2;
        for (const auto& r : var_rows)
            if (!r.var_val2.empty()) vals2.insert(r.var_val2);

        if (v1_numeric && vals2.size() > 1) {
            // SmoothByFactor: smooth in var1, factor in var2
            SmoothByFctInfo info;
            std::unordered_map<std::string, std::vector<io::CoefRow>> by_factor;
            for (const auto& r : var_rows)
                by_factor[r.var_val2].push_back(r);
            for (auto& [fct, frows] : by_factor)
                info.smooth_dict[fct] = build_smooth_auto(frows);
            link.terms_2d[{vn1, vn2}] = std::move(info);

        } else if (v1_numeric) {
            // SmoothByNum: smooth in var1, numeric weight in var2
            SmoothByNumInfo info;
            info.smooth = build_smooth_auto(var_rows);
            link.terms_2d[{vn1, vn2}] = std::move(info);

        } else {
            // Lookup2D: both categorical
            Lookup2dInfo info;
            for (const auto& r : var_rows)
                info.lookup[{r.var_val1, r.var_val2}] = r.value;
            link.terms_2d[{vn1, vn2}] = std::move(info);
        }
    }

    model_link_[model_name] = std::move(link);
}

// ─── read (auto-detect, no specs required) ───────────────────────────────

void ModelCoef::read(const std::string& coef_dir, const std::string& from_model) {
    std::string path = coef_dir + "/" + from_model + ".txt";
    auto all_rows = io::read_coef_file(path);

    std::string from_status = from_model.substr(4);

    std::unordered_map<std::string, std::vector<io::CoefRow>> by_model;
    for (auto& r : all_rows) {
        std::string full_name = get_model_name(from_status, r.model);
        by_model[full_name].push_back(std::move(r));
    }

    for (auto& [model_name, model_rows] : by_model) {
        build_model_auto(model_name, model_rows);
    }
}

bool ModelCoef::has_model(const std::string& model_name) const {
    return model_link_.count(model_name) > 0;
}



// ─── calc ────────────────────────────────────────────────────────────────

static std::string loan_str(const LoanDict& loan, const std::string& key) {
    auto it = loan.find(key);
    if (it == loan.end()) return "";  // missing key => empty string (lookup returns 0)
    if (auto* s = std::get_if<std::string>(&it->second)) return *s;
    if (auto* i = std::get_if<int>(&it->second)) return std::to_string(*i);
    if (auto* d = std::get_if<double>(&it->second)) return std::to_string(static_cast<int>(*d));
    return "";
}

static double loan_num(const LoanDict& loan, const std::string& key) {
    auto it = loan.find(key);
    if (it == loan.end()) return 0.0;
    if (auto* p = std::get_if<double>(&it->second)) return *p;
    if (auto* p = std::get_if<int>(&it->second))    return static_cast<double>(*p);
    return 0.0;
}

// Variables that change each simulation period.
// Everything else is static (set once at prep, never changes).
double ModelCoef::calc(const LoanDict& loan,
                       const std::string& from_status,
                       const std::string& to_status) const {
    std::string name = get_model_name(from_status, to_status);
    auto ml_it = model_link_.find(name);
    if (ml_it == model_link_.end())
        throw std::runtime_error("missing model: " + name);

    const ModelLink& ml = ml_it->second;
    double result = ml.intercept;

    for (const auto& [var_name, term] : ml.terms_1d) {
        if (auto* info = std::get_if<Lookup1dInfo>(&term)) {
            std::string val = loan_str(loan, var_name);
            for (const auto& [level, coef] : info->levels) {
                if (level == val) { result += coef; break; }
            }
        } else if (auto* info = std::get_if<Smooth1dInfo>(&term)) {
            double val = loan_num(loan, var_name);
            result += smooth_1d_calc(val, *info);
        }
    }

    for (const auto& [key_pair, term] : ml.terms_2d) {
        const auto& [vn1, vn2] = key_pair;

        if (auto* info = std::get_if<Lookup2dInfo>(&term)) {
            std::string v1 = loan_str(loan, vn1);
            std::string v2 = loan_str(loan, vn2);
            auto it = info->lookup.find({v1, v2});
            if (it != info->lookup.end()) result += it->second;

        } else if (auto* info = std::get_if<SmoothByNumInfo>(&term)) {
            double v1 = loan_num(loan, vn1);
            double v2 = loan_num(loan, vn2);
            result += smooth_1d_calc(v1, info->smooth) * v2;

        } else if (auto* info = std::get_if<SmoothByFctInfo>(&term)) {
            std::string fct = loan_str(loan, vn2);
            double v1 = loan_num(loan, vn1);
            auto sit = info->smooth_dict.find(fct);
            if (sit != info->smooth_dict.end()) {
                result += smooth_1d_calc(v1, sit->second);
            }

        } else if (auto* info = std::get_if<Smooth2dInfo>(&term)) {
            double v1 = loan_num(loan, vn1);
            double v2 = loan_num(loan, vn2);
            result += smooth_2d_calc(v1, v2, *info);
        }
    }

    if (std::isnan(result))
        throw std::runtime_error("calc result is NaN for model: " + name);

    return result;
}

double ModelCoef::calc(const LoanDict& loan,
                       const std::string& model_name) const {
    auto ml_it = model_link_.find(model_name);
    if (ml_it == model_link_.end())
        throw std::runtime_error("missing model: " + model_name);

    const ModelLink& ml = ml_it->second;
    double result = ml.intercept;

    for (const auto& [var_name, term] : ml.terms_1d) {
        if (auto* info = std::get_if<Lookup1dInfo>(&term)) {
            std::string val = loan_str(loan, var_name);
            for (const auto& [level, coef] : info->levels) {
                if (level == val) { result += coef; break; }
            }
        } else if (auto* info = std::get_if<Smooth1dInfo>(&term)) {
            double val = loan_num(loan, var_name);
            result += smooth_1d_calc(val, *info);
        }
    }

    for (const auto& [key_pair, term] : ml.terms_2d) {
        const auto& [vn1, vn2] = key_pair;
        if (auto* info = std::get_if<Lookup2dInfo>(&term)) {
            std::string v1 = loan_str(loan, vn1);
            std::string v2 = loan_str(loan, vn2);
            auto it = info->lookup.find({v1, v2});
            if (it != info->lookup.end()) result += it->second;
        } else if (auto* info = std::get_if<SmoothByNumInfo>(&term)) {
            double v1 = loan_num(loan, vn1);
            double v2 = loan_num(loan, vn2);
            result += smooth_1d_calc(v1, info->smooth) * v2;
        } else if (auto* info = std::get_if<SmoothByFctInfo>(&term)) {
            std::string fct = loan_str(loan, vn2);
            double v1 = loan_num(loan, vn1);
            auto sit = info->smooth_dict.find(fct);
            if (sit != info->smooth_dict.end())
                result += smooth_1d_calc(v1, sit->second);
        } else if (auto* info = std::get_if<Smooth2dInfo>(&term)) {
            double v1 = loan_num(loan, vn1);
            double v2 = loan_num(loan, vn2);
            result += smooth_2d_calc(v1, v2, *info);
        }
    }

    if (std::isnan(result))
        throw std::runtime_error("calc result is NaN for model: " + model_name);
    return result;
}

// ─── classify_terms ─────────────────────────────────────────────────────

void ModelCoef::classify_terms(const std::unordered_set<std::string>& dynamic_vars) {
    for (auto& [name, ml] : model_link_) {
        ml.static_1d.clear();
        ml.dynamic_1d.clear();
        ml.static_2d.clear();
        ml.dynamic_2d.clear();

        for (auto& [var_name, term] : ml.terms_1d) {
            if (dynamic_vars.count(var_name))
                ml.dynamic_1d.emplace_back(var_name, &term);
            else
                ml.static_1d.emplace_back(var_name, &term);
        }

        for (auto& [key_pair, term] : ml.terms_2d) {
            const auto& [vn1, vn2] = key_pair;
            if (dynamic_vars.count(vn1) || dynamic_vars.count(vn2))
                ml.dynamic_2d.emplace_back(vn1, vn2, &term);
            else
                ml.static_2d.emplace_back(vn1, vn2, &term);
        }
    }
}

// ─── shared eval helpers ────────────────────────────────────────────────

double ModelCoef::eval_terms_1d(const LoanDict& loan,
    const std::vector<std::pair<std::string, const CoefTerm*>>& terms) const {
    double result = 0.0;
    for (const auto& [var_name, term_ptr] : terms) {
        if (auto* info = std::get_if<Lookup1dInfo>(term_ptr)) {
            std::string val = loan_str(loan, var_name);
            for (const auto& [level, coef] : info->levels) {
                if (level == val) { result += coef; break; }
            }
        } else if (auto* info = std::get_if<Smooth1dInfo>(term_ptr)) {
            double val = loan_num(loan, var_name);
            result += smooth_1d_calc(val, *info);
        }
    }
    return result;
}

double ModelCoef::eval_terms_2d(const LoanDict& loan,
    const std::vector<std::tuple<std::string, std::string, const CoefTerm*>>& terms) const {
    double result = 0.0;
    for (const auto& [vn1, vn2, term_ptr] : terms) {
        if (auto* info = std::get_if<Lookup2dInfo>(term_ptr)) {
            std::string v1 = loan_str(loan, vn1);
            std::string v2 = loan_str(loan, vn2);
            auto it = info->lookup.find({v1, v2});
            if (it != info->lookup.end()) result += it->second;
        } else if (auto* info = std::get_if<SmoothByNumInfo>(term_ptr)) {
            double v1 = loan_num(loan, vn1);
            double v2 = loan_num(loan, vn2);
            result += smooth_1d_calc(v1, info->smooth) * v2;
        } else if (auto* info = std::get_if<SmoothByFctInfo>(term_ptr)) {
            std::string fct = loan_str(loan, vn2);
            double v1 = loan_num(loan, vn1);
            auto sit = info->smooth_dict.find(fct);
            if (sit != info->smooth_dict.end())
                result += smooth_1d_calc(v1, sit->second);
        } else if (auto* info = std::get_if<Smooth2dInfo>(term_ptr)) {
            double v1 = loan_num(loan, vn1);
            double v2 = loan_num(loan, vn2);
            result += smooth_2d_calc(v1, v2, *info);
        }
    }
    return result;
}

// ─── calc_dynamic / build_static_cache ───────────────────────────────────

double ModelCoef::calc_dynamic(const LoanDict& loan,
                               const std::string& model_name) const {
    auto ml_it = model_link_.find(model_name);
    if (ml_it == model_link_.end())
        throw std::runtime_error("missing model: " + model_name);
    const ModelLink& ml = ml_it->second;
    return eval_terms_1d(loan, ml.dynamic_1d)
         + eval_terms_2d(loan, ml.dynamic_2d);
}

LogitCache ModelCoef::build_static_cache(const LoanDict& loan) const {
    LogitCache cache;
    for (const auto& [name, ml] : model_link_) {
        cache[name] = ml.intercept + eval_terms_1d(loan, ml.static_1d)
                                   + eval_terms_2d(loan, ml.static_2d);
    }
    return cache;
}

}  // namespace rrm::model
