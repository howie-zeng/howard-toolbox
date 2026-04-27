#include "var_registry.h"
#include "loan_schema.h"

#include <algorithm>
#include <cmath>
#include <string>
#include <unordered_set>

namespace rrm {

static const char* MONTH_NAMES[] = {
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
};

// ---------------------------------------------------------------------------
// VarRegistry core
// ---------------------------------------------------------------------------

void VarRegistry::register_var(VarDef def) {
    vars_.push_back(std::move(def));
}

void VarRegistry::step_period(LoanDict& loan, int next_period,
                              const VarContext& ctx) const {
    // Pass 1: advance age (close current period)
    for (const auto& var : vars_) {
        if (var.is_age_var && var.update_fn)
            var.update_fn(loan, 0);
    }
    // Pass 2: update period context + macros for the upcoming period
    for (const auto& var : vars_) {
        if (var.kind == VarKind::TIME_VARYING && !var.is_age_var && var.update_fn)
            var.update_fn(loan, next_period);
        if (var.kind == VarKind::MACRO && var.macro_fn)
            var.macro_fn(loan, ctx);
    }
}

std::unordered_set<std::string> VarRegistry::dynamic_var_names() const {
    std::unordered_set<std::string> result;
    for (const auto& v : vars_)
        result.insert(v.name);
    return result;
}

// ---------------------------------------------------------------------------
// Variable registration helpers
// ---------------------------------------------------------------------------

static void reg_r_dt(VarRegistry& reg) {
    reg.register_var({
        "r_dt", VarKind::TIME_VARYING, false,
        [](LoanDict& loan, int period) {
            int sy = get_int(loan, "_start_year");
            int sm = get_int(loan, "_start_month");
            int y, m;
            advance_month(sy, sm, period, y, m);
            set_val(loan, "r_dt", end_of_month_str(y, m));
        },
        nullptr
    });
}

static void reg_month(VarRegistry& reg) {
    reg.register_var({
        "month", VarKind::TIME_VARYING, false,
        [](LoanDict& loan, int) {
            std::string r_dt = get_string(loan, "r_dt");
            int y, m;
            parse_year_month(r_dt, y, m);
            set_val(loan, "month", std::string(MONTH_NAMES[m - 1]));
        },
        nullptr
    });
}

static void reg_days_to_month_end(VarRegistry& reg) {
    reg.register_var({
        "days_to_month_end", VarKind::TIME_VARYING, false,
        [](LoanDict& loan, int) {
            std::string r_dt = get_string(loan, "r_dt");
            int y, m;
            parse_year_month(r_dt, y, m);
            int pmt_day = 15;
            auto it = loan.find("pmt_day");
            if (it != loan.end()) pmt_day = static_cast<int>(get_numeric(loan, "pmt_day"));
            int dim = days_in_month(y, m);
            int dte = dim - std::min(pmt_day, dim);
            set_val(loan, "days_to_month_end", dte);
        },
        nullptr
    });
}

static void reg_month_group(VarRegistry& reg) {
    reg.register_var({
        "month_group", VarKind::TIME_VARYING, false,
        [](LoanDict& loan, int) {
            int dte = get_int(loan, "days_to_month_end");
            set_val(loan, "month_group", std::string(dte <= 28 ? "30_Day" : "31_Day"));
        },
        nullptr
    });
}

// --- Age vars (called AFTER model eval) ---

static void reg_loan_age(VarRegistry& reg) {
    reg.register_var({
        "loan_age", VarKind::TIME_VARYING, true,
        [](LoanDict& loan, int) {
            set_val(loan, "loan_age", get_int(loan, "loan_age") + 1);
        },
        nullptr
    });
}

static void reg_age(VarRegistry& reg) {
    reg.register_var({
        "age", VarKind::TIME_VARYING, true,
        [](LoanDict& loan, int) {
            set_val(loan, "age", get_int(loan, "loan_age"));
        },
        nullptr
    });
}

static void reg_age_pct(VarRegistry& reg) {
    auto fn = [](LoanDict& loan, int) {
        int la = get_int(loan, "loan_age");
        int t  = get_int(loan, "term");
        double pct = (t > 0) ? static_cast<double>(la) / t : 0.0;
        set_val(loan, "age_pct", pct);
        set_val(loan, "c_age_pct", pct);
        set_val(loan, "age_fc", pct);
    };
    reg.register_var({"age_pct",   VarKind::TIME_VARYING, true, fn, nullptr});
    reg.register_var({"c_age_pct", VarKind::TIME_VARYING, true, nullptr, nullptr});
    reg.register_var({"age_fc",    VarKind::TIME_VARYING, true, nullptr, nullptr});
}

// --- Macro vars (only active when mode="custom") ---

static void reg_cpi_inflator(VarRegistry& reg, const std::string& field_name,
                             const std::unordered_set<std::string>& active) {
    std::function<void(LoanDict&, const VarContext&)> macro_fn = nullptr;

    if (active.count(field_name)) {
        macro_fn = [field_name](LoanDict& loan, const VarContext& ctx) {
            if (!ctx.calendar_table) return;
            std::string r_dt = get_string(loan, "r_dt");
            std::string ym = r_dt.substr(0, 7);
            auto it = ctx.calendar_table->find(ym);
            if (it != ctx.calendar_table->end()) {
                auto col = it->second.find(field_name);
                if (col != it->second.end())
                    set_val(loan, field_name, col->second);
            }
            // If not found, value stays (freeze behavior)
        };
    }

    reg.register_var({field_name, VarKind::MACRO, false, nullptr, macro_fn});
}

static void reg_rate_incentive(VarRegistry& reg,
                               const std::unordered_set<std::string>& active) {
    std::function<void(LoanDict&, const VarContext&)> macro_fn = nullptr;

    if (active.count("rate_incentive_ALL")) {
        macro_fn = [](LoanDict& loan, const VarContext& ctx) {
            if (!ctx.fico_coupon_table) return;

            std::string r_dt = get_string(loan, "r_dt");
            // YYYY-MM -> YYYYMM
            std::string ym;
            if (r_dt.size() >= 7) {
                ym = r_dt.substr(0, 4) + r_dt.substr(5, 2);
            } else {
                return;
            }

            std::string bkt = get_string(loan, "_fico_bkt");
            if (bkt.empty()) return;

            auto it = ctx.fico_coupon_table->find(ym + "|" + bkt);
            if (it != ctx.fico_coupon_table->end()) {
                auto coupon_col = it->second.find("fico_bkt_coupon");
                if (coupon_col != it->second.end()) {
                    double coupon_r = coupon_col->second;
                    try {
                        double coupon_v = get_numeric(loan, "_coupon_at_vintage");
                        set_val(loan, "rate_incentive_ALL", coupon_r - coupon_v);
                    } catch (...) {}
                }
            }
            // If not found, value stays (freeze behavior)
        };
    }

    reg.register_var({"rate_incentive_ALL", VarKind::MACRO, false, nullptr, macro_fn});
}

// ---------------------------------------------------------------------------
// build_var_registry — construct the default registry
// ---------------------------------------------------------------------------

VarRegistry build_var_registry(const std::unordered_set<std::string>& active_macro_vars) {
    VarRegistry reg;

    // TIME_VARYING — period context (before model)
    reg_r_dt(reg);
    reg_month(reg);
    reg_days_to_month_end(reg);
    reg_month_group(reg);

    // TIME_VARYING — age (after model)
    reg_loan_age(reg);
    reg_age(reg);
    reg_age_pct(reg);

    // MACRO — only active when configured as "custom"
    reg_cpi_inflator(reg, "cpi_inflator_36", active_macro_vars);
    reg_cpi_inflator(reg, "cpi_inflator_12", active_macro_vars);
    reg_rate_incentive(reg, active_macro_vars);

    return reg;
}

}  // namespace rrm
