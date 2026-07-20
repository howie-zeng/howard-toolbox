#include "cf.h"
#include "loan_schema.h"
#include "utils.h"
#include "model/model_coef.h"
#include "model/transition.h"
#include <algorithm>
#include <cmath>
#include <random>
#include <stdexcept>

namespace rrm {

static void compute_payments(
    double num_pay, double begin_bal, double pi_pmt, double r_m,
    double& int_paid_out, double& prin_paid_out, double& end_bal_out) {

    double bal = begin_bal;
    double total_int = 0.0;
    double total_prin = 0.0;

    for (int p = 0; p < static_cast<int>(num_pay); ++p) {
        double int_pmt = bal * r_m;
        double prin_pmt = pi_pmt - int_pmt;
        if (prin_pmt < 0.0) prin_pmt = 0.0;
        if (prin_pmt > bal) prin_pmt = bal;
        bal -= prin_pmt;
        total_int += int_pmt;
        total_prin += prin_pmt;
        if (bal <= 0.01) { bal = 0.0; break; }
    }

    int_paid_out = total_int;
    prin_paid_out = total_prin;
    end_bal_out = bal;
}

CfResult run_cf(LoanDict loan,
                DataMgr& dm,
                int n_per,
                int dup,
                const std::string& dial_name,
                std::mt19937& rng,
                DumpCollector* dump,
                const model::LogitCache& logit_cache) {

    CfResult result;
    CfIndices ci = extract_cf_indices(CF_DICT);

    result.loan_cf.assign(n_per, std::vector<double>(CF_COL_LEN, 0.0));
    result.prob_log.reserve(n_per);

    try {
        init_time_varying(loan);

        std::string status = get_string(loan, "status");
        double end_bal     = get_numeric(loan, "end_bal");
        int    term        = get_int(loan, "term");
        double int_rate    = get_numeric(loan, "int_rate");
        double r_m = (int_rate < 1.0) ? int_rate / 12.0 : int_rate / 1200.0;

        double z = std::pow(1.0 + r_m, term);
        double pi_pmt = (std::abs(z - 1.0) > 1e-9)
            ? end_bal * r_m * z / (z - 1.0)
            : end_bal / term;

        for (int per = 0; per < n_per; ++per) {
            if (!should_continue(loan, per, n_per, status)) break;

            double begin_bal = end_bal;
            result.loan_cf[per][ci.begin_bal] = begin_bal;

            auto roll_to_it = dm.status_to_roll.find(status);
            if (roll_to_it == dm.status_to_roll.end()) break;
            const auto& roll_to = roll_to_it->second;

            auto tl_it = dm.transition_layout.find(status);
            if (tl_it == dm.transition_layout.end()) break;
            const auto& tl = tl_it->second;

            // Snapshot loan state pre-transition for dump
            DumpRow dump_row;
            if (dump) {
                dump_row.per = per;
                dump_row.from_status = status;
                dump_row.begin_bal = begin_bal;
                dump_snap_loan(dump_row, loan);
                dump_row.note_rate = (int_rate < 1.0) ? int_rate : int_rate / 100.0;
                dump_row.pi_pmt = pi_pmt;
            }

            auto tr = model::flipcoin_logit(
                loan, status, dial_name, per,
                roll_to, tl,
                dm.model_coef, dm.roll, rng,
                logit_cache);

            {
                ProbEntry pe;
                pe.begin_bal = begin_bal;
                pe.probs.assign(dm.prob_schema.n_cols, 0.0);
                auto layout_it = dm.prob_schema.layout.find(status);
                if (layout_it != dm.prob_schema.layout.end()) {
                    const auto& col_idx = layout_it->second.col_idx;
                    for (size_t ri = 0; ri < roll_to.size(); ++ri) {
                        pe.probs[col_idx[ri]] = tr.prob_proj[ri];
                    }
                }
                result.prob_log.push_back(std::move(pe));
            }

            std::string status_to = tr.status_to;

            double num_pay = 0.0;
            auto pmt_to_it = dm.pmt_matrix.find(status_to);
            if (pmt_to_it != dm.pmt_matrix.end()) {
                auto pmt_from_it = pmt_to_it->second.find(status);
                if (pmt_from_it != pmt_to_it->second.end())
                    num_pay = pmt_from_it->second;
            }

            double int_paid = 0.0, prin_paid = 0.0;
            compute_payments(num_pay, begin_bal, pi_pmt, r_m,
                             int_paid, prin_paid, end_bal);

            if (status_to == "PIF") {
                prin_paid = begin_bal;
                int_paid = begin_bal * r_m;
                end_bal = 0.0;
                result.loan_cf[per][ci.pif_cnt] = 1.0;
                result.loan_cf[per][ci.pif_bal] = begin_bal;
            } else if (status_to == "LIQ") {
                double gross = begin_bal;
                double rr = 0.0;   // recovery rate
                int    lag = 0;    // recovery lag (months); -1 => never recovers
                if (dm.has_severity) {
                    std::string plat = get_string(loan, "platform_f");
                    auto cdf_it = dm.lag_cdf.find(plat);
                    if (cdf_it == dm.lag_cdf.end()) {
                        rr = std::max(0.0, 1.0 - dm.liq_severity);
                    } else {
                        std::uniform_real_distribution<double> u01(0.0, 1.0);
                        double u = u01(rng);
                        std::string label = cdf_it->second.back().first;
                        for (const auto& lc : cdf_it->second) { if (u <= lc.second) { label = lc.first; break; } }
                        auto lm = dm.lag_label_map.find(label);
                        lag = (lm != dm.lag_label_map.end()) ? lm->second.first : -1;
                        if (lag >= 0) {
                            set_val(loan, "platform", plat);
                            set_val(loan, "recovery_lag_bkt", lm->second.second);
                            double ob = get_numeric(loan, "orig_bal"); if (ob <= 0.0) ob = gross;
                            set_val(loan, "paydown_fraction", std::max(0.0, std::min(1.0, 1.0 - gross / ob)));
                            double md = 1.0;
                            if (!dm.manheim.empty()) {
                                std::string odt = get_string(loan, "orig_dt");
                                std::string rdt = get_string(loan, "r_dt");
                                if (odt.size() >= 7 && rdt.size() >= 7) {
                                    int oym = std::stoi(odt.substr(0,4))*12 + std::stoi(odt.substr(5,2));
                                    int rym = std::stoi(rdt.substr(0,4))*12 + std::stoi(rdt.substr(5,2));
                                    auto mo = dm.manheim.find(oym); auto mc = dm.manheim.find(rym);
                                    if (mo != dm.manheim.end() && mc != dm.manheim.end() && mo->second > 0.0)
                                        md = mc->second / mo->second;
                                }
                            }
                            set_val(loan, "manheim_drift", md);
                            double slp = dm.model_coef.severity_calc(loan, "SEV");
                            rr = 1.0 / (1.0 + std::exp(-slp));
                            if (rr < 0.0) rr = 0.0; if (rr > 1.0) rr = 1.0;
                        }
                    }
                } else {
                    rr = std::max(0.0, 1.0 - dm.liq_severity);
                }
                double recovery = gross * rr;
                end_bal = 0.0;
                prin_paid = 0.0;
                int_paid = 0.0;
                result.loan_cf[per][ci.liq_cnt] = 1.0;
                result.loan_cf[per][ci.liq_bal] = gross;
                result.loan_cf[per][CF_DICT.at("loss")] = gross;   // GROSS loss at default -> CGL
                if (recovery > 0.0 && lag >= 0) {
                    int tgt = per + lag;                            // recovery deferred to t+lag
                    if (tgt < n_per) {
                        result.loan_cf[tgt][CF_DICT.at("recov")]     += recovery;
                        result.loan_cf[tgt][CF_DICT.at("net_recov")] += recovery;
                    }
                }
            } else {
                auto dq = dq_bucket_for_status(status_to);
                if (dq.has_value()) {
                    result.loan_cf[per][CF_DICT.at(dq->first)] = 1.0;
                    result.loan_cf[per][CF_DICT.at(dq->second)] = end_bal;
                }
            }

            result.loan_cf[per][ci.end_bal]   = end_bal;
            result.loan_cf[per][ci.int_pmt]  = int_paid;
            result.loan_cf[per][ci.prin_pmt] = prin_paid;
            result.loan_cf[per][ci.cnt]      = 1.0;

            result.loan_cf[per][ci.sch_int]  = begin_bal * r_m;
            result.loan_cf[per][ci.sch_prin] = std::max(0.0, pi_pmt - result.loan_cf[per][ci.sch_int]);

            // Complete dump row with post-transition data
            if (dump) {
                dump_row.to_status = status_to;
                dump_row.num_pay = num_pay;
                dump_row.end_bal = end_bal;
                dump_row.int_pmt = int_paid;
                dump_row.prin_pmt = prin_paid;
                if (!result.prob_log.empty())
                    dump_row.probs = dm.prob_schema.to_map(result.prob_log.back().probs);
                if (status_to == "LIQ")
                    dump_row.loss = result.loan_cf[per][CF_DICT.at("loss")];
                dump->rows.push_back(std::move(dump_row));
            }

            // Update path-dependent history vars from the drawn transition, then
            // advance age + period context.
            dm.var_registry.step_transition(loan, status, status_to);
            dm.var_registry.step_period(loan, per + 1, dm.var_ctx);

            set_val(loan, "end_bal", end_bal);
            set_val(loan, "status", status_to);
            status = status_to;
        }
    } catch (const std::exception& e) {
        result.has_error = true;
        result.error_msg = e.what();
    }

    if (dup > 1) {
        double inv = 1.0 / dup;
        for (auto& row : result.loan_cf)
            for (auto& v : row) v *= inv;
    }

    return result;
}

}  // namespace rrm
