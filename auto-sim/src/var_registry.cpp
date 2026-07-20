#include "var_registry.h"
#include "loan_schema.h"

#include <algorithm>
#include <cmath>
#include <string>
#include <unordered_set>
#include <vector>

namespace rrm {

static const char* MONTH_NAMES[] = {
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
};

// ---------------------------------------------------------------------------
// VarRegistry core
// ---------------------------------------------------------------------------

void VarRegistry::register_var(VarDef def) {
    size_t i = vars_.size();
    if (def.kind == VarKind::TIME_VARYING && def.is_age_var && def.update_fn)
        age_idx_.push_back(i);
    else if (def.kind == VarKind::TIME_VARYING && def.update_fn)
        period_idx_.push_back(i);
    else if (def.kind == VarKind::MACRO && def.macro_fn)
        macro_idx_.push_back(i);
    else if (def.kind == VarKind::PATH_DEPENDENT && def.path_fn)
        path_idx_.push_back(i);
    vars_.push_back(std::move(def));
}

void VarRegistry::step_period(LoanDict& loan, int next_period,
                              const VarContext& ctx) const {
    // Pass 1: advance age (close current period)
    for (size_t i : age_idx_)
        vars_[i].update_fn(loan, 0);
    // Pass 2: update period context, then macros (which read r_dt etc.)
    for (size_t i : period_idx_)
        vars_[i].update_fn(loan, next_period);
    for (size_t i : macro_idx_)
        vars_[i].macro_fn(loan, ctx);
}

void VarRegistry::step_transition(LoanDict& loan, const std::string& from_status,
                                  const std::string& to_status) const {
    for (size_t i : path_idx_)
        vars_[i].path_fn(loan, from_status, to_status);
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
    // Report-anchored: tag the transition with r_dt's own month season (matches
    // training add_asof_features, which dropped the old season_shift=1).
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
    // gap from the payment day to r_dt's reporting month-end (report-anchored,
    // matching training's date.dt.days_in_month; the old +1 shift was dropped).
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
        // age fraction is over the ORIGINAL term (fraction of the loan's full life),
        // not the remaining term used for amortization.
        int t  = get_int(loan, "orig_term");
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
        // Compute inflator from raw CPI levels: CPI(t) / CPI(t - lag) - 1.
        // Freeze behavior: if either month is missing from the table
        // (e.g. past the last actual), the previous value is kept.
        const int lag_months = (field_name == "cpi_inflator_36") ? -36 : -12;
        macro_fn = [lag_months, field_name](LoanDict& loan, const VarContext& ctx) {
            if (!ctx.calendar_table) return;
            std::string r_dt = get_string(loan, "r_dt");
            int y, m;
            parse_year_month(r_dt, y, m);
            char key_now[8];
            std::snprintf(key_now, sizeof(key_now), "%04d-%02d", y, m);
            auto now_it = ctx.calendar_table->find(key_now);
            if (now_it == ctx.calendar_table->end()) return;
            auto now_col = now_it->second.find("CPIAUCNS");
            if (now_col == now_it->second.end()) return;
            int ly, lm;
            advance_month(y, m, lag_months, ly, lm);
            char key_lag[8];
            std::snprintf(key_lag, sizeof(key_lag), "%04d-%02d", ly, lm);
            auto lag_it = ctx.calendar_table->find(key_lag);
            if (lag_it == ctx.calendar_table->end()) return;
            auto lag_col = lag_it->second.find("CPIAUCNS");
            if (lag_col == lag_it->second.end() || lag_col->second <= 0) return;
            set_val(loan, field_name, now_col->second / lag_col->second - 1.0);
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

            if (loan.find("_fico_bkt") == loan.end()) return;   // absent (missing ofico) -> skip, like Python
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

// str field with a missing-key-safe fallback (empty string)
static std::string sfield(const LoanDict& d, const char* k) {
    auto it = d.find(k);
    return (it != d.end()) ? std::get<std::string>(it->second) : std::string();
}

// mask(6-bit) -> bucket lookup, built once (thread-safe magic static). bit k =
// delinquent k months ago; bucket = f(#bits) matching consolidate.py's cut
// (0->"0", 1->"1", 2-3->"2-3", 4-6->"4-6").
static const std::string* dq6_table() {
    static const std::vector<std::string> T = [] {
        std::vector<std::string> t(64);
        for (int m = 0; m < 64; ++m) {
            int c = 0; for (int b = m; b; b >>= 1) c += b & 1;
            t[m] = (c == 0) ? "0" : (c == 1) ? "1" : (c <= 3) ? "2-3" : "4-6";
        }
        return t;
    }();
    return T.data();
}

// Trailing-6-month delinquency count, bucketed 0/1/2-3/4-6 — a bounded, decaying
// delinquency memory. 6-bit rolling mask in loan["_dq6_mask"]; O(1) shift + table
// lookup. Timing mirrors consolidate.py shift(1..6): records the state the loan was
// IN this period (from_status); value read when scoring period t reflects t-1..t-6.
static void reg_dq6_bkt(VarRegistry& reg) {
    reg.register_var({
        "dq6_bkt", VarKind::PATH_DEPENDENT, false, nullptr, nullptr,
        [](LoanDict& loan, const std::string& from, const std::string& /*to*/) {
            int m = 0;
            auto it = loan.find("_dq6_mask");
            if (it != loan.end()) m = std::get<int>(it->second);
            int flag = (from == "D1M" || from == "D2M" || from == "D3M" || from == "D4M") ? 1 : 0;
            m = ((m << 1) | flag) & 63;
            set_val(loan, "_dq6_mask", m);
            set_val(loan, "dq6_bkt", dq6_table()[m]);
        }
    });
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

    // Path-dependent delinquency-history feature: bounded 6-month DQ memory used by
    // the history-aware ctd1 (PRIME_BASE_HISTORY). Superseded ever_dq_flag /
    // months_in_current_bkt (removed — they homogenized the Current pool and
    // over-suppressed C->D1M). dq6_bkt decays, so re-default risk cools off.
    reg_dq6_bkt(reg);

    // MACRO — only active when configured as "custom"
    reg_cpi_inflator(reg, "cpi_inflator_36", active_macro_vars);
    reg_cpi_inflator(reg, "cpi_inflator_12", active_macro_vars);
    reg_rate_incentive(reg, active_macro_vars);

    return reg;
}

}  // namespace rrm
