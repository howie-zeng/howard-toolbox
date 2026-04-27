#include "runners/cf_parallel.h"
#include "cf.h"
#include "dump.h"
#include "utils.h"
#include <algorithm>
#include <iostream>
#include <random>

#ifdef _OPENMP
#include <omp.h>
#endif

namespace rrm::runners {

BatchResult run_batch(
    std::vector<LoanDict>& loans,
    DataMgr& dm,
    int n_per,
    int dup,
    int n_threads,
    uint32_t seed0,
    const std::string& dial_name) {

    BatchResult result;
    result.cf_sum.assign(n_per, std::vector<double>(CF_COL_LEN, 0.0));

    int n_loans = static_cast<int>(loans.size());
    int total_tasks = n_loans * dup;

    std::vector<std::string> errors;
    std::vector<std::vector<std::vector<double>>> partial_sums;

#ifdef _OPENMP
    if (n_threads > 0) omp_set_num_threads(n_threads);
    int actual_threads = omp_get_max_threads();
#else
    int actual_threads = 1;
#endif

    partial_sums.resize(actual_threads,
        std::vector<std::vector<double>>(n_per, std::vector<double>(CF_COL_LEN, 0.0)));

    #pragma omp parallel for schedule(dynamic)
    for (int task_idx = 0; task_idx < total_tasks; ++task_idx) {
        int loan_idx = task_idx / dup;
        int path = task_idx % dup;

#ifdef _OPENMP
        int tid = omp_get_thread_num();
#else
        int tid = 0;
#endif

        LoanDict loan_copy = loans[loan_idx];
        std::string loan_id = "unknown";
        {
            auto lid_it = loan_copy.find("loan_id");
            if (lid_it != loan_copy.end()) {
                if (auto* s = std::get_if<std::string>(&lid_it->second)) loan_id = *s;
                else if (auto* i = std::get_if<int>(&lid_it->second)) loan_id = std::to_string(*i);
                else if (auto* d = std::get_if<double>(&lid_it->second)) loan_id = std::to_string(static_cast<long long>(*d));
            }
        }

        uint32_t seed = stable_seed(seed0, loan_id, path);
        std::mt19937 rng(seed);

        CfResult cf = run_cf(std::move(loan_copy), dm, n_per, dup, dial_name, rng);

        if (cf.has_error) {
            #pragma omp critical
            {
                errors.push_back(loan_id + "|" + std::to_string(path) + ": " + cf.error_msg);
            }
        } else {
            auto& ps = partial_sums[tid];
            for (int p = 0; p < n_per; ++p) {
                for (int c = 0; c < CF_COL_LEN; ++c) {
                    ps[p][c] += cf.loan_cf[p][c];
                }
            }
        }
    }

    for (int t = 0; t < actual_threads; ++t) {
        for (int p = 0; p < n_per; ++p) {
            for (int c = 0; c < CF_COL_LEN; ++c) {
                result.cf_sum[p][c] += partial_sums[t][p][c];
            }
        }
    }

    result.errors = std::move(errors);
    result.n_done = total_tasks - static_cast<int>(result.errors.size());
    result.n_error = static_cast<int>(result.errors.size());

    return result;
}

// Helper: extract loan_id as string from loan dict
static std::string extract_loan_id(const LoanDict& loan) {
    auto lid_it = loan.find("loan_id");
    if (lid_it != loan.end()) {
        if (auto* s = std::get_if<std::string>(&lid_it->second)) return *s;
        if (auto* i = std::get_if<int>(&lid_it->second)) return std::to_string(*i);
        if (auto* d = std::get_if<double>(&lid_it->second)) return std::to_string(static_cast<long long>(*d));
    }
    return "unknown";
}

// Helper: extract a field as string for grouping
static std::string field_as_string(const LoanDict& loan, const std::string& key) {
    auto it = loan.find(key);
    if (it == loan.end()) return "";
    if (auto* s = std::get_if<std::string>(&it->second)) return *s;
    if (auto* i = std::get_if<int>(&it->second)) return std::to_string(*i);
    if (auto* d = std::get_if<double>(&it->second)) {
        long long iv = static_cast<long long>(*d);
        if (static_cast<double>(iv) == *d) return std::to_string(iv);
        return std::to_string(*d);
    }
    return "";
}

GroupedBatchResult run_batch_grouped(
    std::vector<LoanDict>& loans,
    DataMgr& dm,
    int n_per,
    int dup,
    int n_threads,
    uint32_t seed0,
    const std::string& dial_name,
    const std::vector<std::string>& group_by,
    const DumpConfig& dump_cfg) {

    int n_loans = static_cast<int>(loans.size());
    int total_tasks = n_loans * dup;

    // Pre-compute group keys, orig_bal, orig_age per loan
    std::vector<std::string> loan_group_keys(n_loans);
    std::vector<double> loan_orig_bal(n_loans);
    std::vector<int> loan_orig_age(n_loans);

    std::unordered_map<std::string, double> group_orig_bal;
    double total_orig_bal = 0.0;
    int max_orig_age = 0;

    for (int i = 0; i < n_loans; ++i) {
        const auto& loan = loans[i];
        std::string key;
        for (const auto& g : group_by) {
            if (!key.empty()) key += "|";
            key += g + "=" + field_as_string(loan, g);
        }
        loan_group_keys[i] = key;

        double ob = 0.0;
        auto ob_it = loan.find("orig_bal");
        if (ob_it != loan.end()) {
            if (auto* d = std::get_if<double>(&ob_it->second)) ob = *d;
            else if (auto* iv = std::get_if<int>(&ob_it->second)) ob = static_cast<double>(*iv);
        }
        if (ob <= 0) {
            auto eb_it = loan.find("end_bal");
            if (eb_it != loan.end()) {
                if (auto* d = std::get_if<double>(&eb_it->second)) ob = *d;
                else if (auto* iv = std::get_if<int>(&eb_it->second)) ob = static_cast<double>(*iv);
            }
        }
        loan_orig_bal[i] = ob;
        total_orig_bal += ob;
        group_orig_bal[key] += ob;

        int la = 0;
        auto la_it = loan.find("loan_age");
        if (la_it != loan.end()) {
            if (auto* iv = std::get_if<int>(&la_it->second)) la = *iv;
            else if (auto* d = std::get_if<double>(&la_it->second)) la = static_cast<int>(*d);
        }
        loan_orig_age[i] = la;
        if (la > max_orig_age) max_orig_age = la;
    }

    // Group CF and probs are indexed by loan_age (not period)
    int max_age = max_orig_age + n_per;

    // Initialize group CF accumulators (age-indexed)
    std::unordered_map<std::string, std::vector<std::vector<double>>> group_cf;
    for (const auto& [key, _] : group_orig_bal) {
        group_cf[key].assign(max_age, std::vector<double>(CF_COL_LEN, 0.0));
    }

    std::vector<std::string> errors;

#ifdef _OPENMP
    if (n_threads > 0) omp_set_num_threads(n_threads);
    int actual_threads = omp_get_max_threads();
#else
    int actual_threads = 1;
#endif

    // Portfolio partial sums (period-indexed, unchanged)
    std::vector<std::vector<std::vector<double>>> port_partial(actual_threads,
        std::vector<std::vector<double>>(n_per, std::vector<double>(CF_COL_LEN, 0.0)));

    // Group partial sums: thread -> group_key -> cf[max_age][CF_COL_LEN] (age-indexed)
    std::vector<std::unordered_map<std::string, std::vector<std::vector<double>>>> grp_partial(actual_threads);
    for (int t = 0; t < actual_threads; ++t) {
        for (const auto& [key, _] : group_orig_bal) {
            grp_partial[t][key].assign(max_age, std::vector<double>(CF_COL_LEN, 0.0));
        }
    }

    // Group partial sums: period-indexed (same structure, indexed by period not age)
    std::vector<std::unordered_map<std::string, std::vector<std::vector<double>>>> grp_partial_per(actual_threads);
    for (int t = 0; t < actual_threads; ++t) {
        for (const auto& [key, _] : group_orig_bal) {
            grp_partial_per[t][key].assign(n_per, std::vector<double>(CF_COL_LEN, 0.0));
        }
    }

    // Per-thread prob accumulators: flat vectors (age * n_prob_cols)
    int n_prob_cols = dm.prob_schema.n_cols;
    std::vector<std::unordered_map<std::string, std::vector<double>>> prob_partial(actual_threads);
    std::vector<std::unordered_map<std::string, std::vector<double>>> pbal_partial(actual_threads);
    // Period-indexed prob accumulators
    std::vector<std::unordered_map<std::string, std::vector<double>>> prob_partial_per(actual_threads);
    std::vector<std::unordered_map<std::string, std::vector<double>>> pbal_partial_per(actual_threads);
    for (int t = 0; t < actual_threads; ++t) {
        for (const auto& [key, _] : group_orig_bal) {
            prob_partial[t][key].assign(max_age * n_prob_cols, 0.0);
            pbal_partial[t][key].assign(max_age, 0.0);
            prob_partial_per[t][key].assign(n_per * n_prob_cols, 0.0);
            pbal_partial_per[t][key].assign(n_per, 0.0);
        }
    }

    // Dump
    std::vector<DumpEntry> dump_entries;
    int dump_loan_limit = dump_cfg.enabled ? dump_cfg.max_loans : 0;
    int dump_path_limit = dump_cfg.enabled ? dump_cfg.max_paths : 0;

    // Pre-compute static logit caches (once per loan, shared across dup paths)
    std::vector<model::LogitCache> loan_caches(n_loans);
    for (int i = 0; i < n_loans; ++i) {
        loan_caches[i] = dm.model_coef.build_static_cache(loans[i]);
    }

    #pragma omp parallel for schedule(dynamic)
    for (int task_idx = 0; task_idx < total_tasks; ++task_idx) {
        int loan_idx = task_idx / dup;
        int path = task_idx % dup;

#ifdef _OPENMP
        int tid = omp_get_thread_num();
#else
        int tid = 0;
#endif

        LoanDict loan_copy = loans[loan_idx];
        std::string loan_id = extract_loan_id(loan_copy);

        bool do_dump = dump_cfg.enabled
                       && loan_idx < dump_loan_limit
                       && path < dump_path_limit;
        DumpCollector dc;

        uint32_t seed = stable_seed(seed0, loan_id, path);
        std::mt19937 rng(seed);

        CfResult cf = run_cf(std::move(loan_copy), dm, n_per, dup, dial_name, rng,
                             do_dump ? &dc : nullptr, loan_caches[loan_idx]);

        if (cf.has_error) {
            #pragma omp critical
            {
                errors.push_back(loan_id + "|" + std::to_string(path) + ": " + cf.error_msg);
            }
        } else {
            const auto& gkey = loan_group_keys[loan_idx];
            int orig_age = loan_orig_age[loan_idx];
            auto& ps = port_partial[tid];
            auto& gs = grp_partial[tid][gkey];

            auto& gs_per = grp_partial_per[tid][gkey];

            for (int p = 0; p < n_per; ++p) {
                int age = orig_age + p;
                for (int c = 0; c < CF_COL_LEN; ++c) {
                    double v = cf.loan_cf[p][c];
                    ps[p][c] += v;        // portfolio: period-indexed
                    gs[age][c] += v;      // group: age-indexed
                    gs_per[p][c] += v;    // group: period-indexed
                }
            }

            // Accumulate probabilities by loan age and by period (flat indexing, no locks)
            {
                auto& pp = prob_partial[tid][gkey];
                auto& pb = pbal_partial[tid][gkey];
                auto& pp_per = prob_partial_per[tid][gkey];
                auto& pb_per = pbal_partial_per[tid][gkey];
                double inv = (dup > 1) ? 1.0 / dup : 1.0;
                for (size_t pi = 0; pi < cf.prob_log.size(); ++pi) {
                    int age = orig_age + static_cast<int>(pi);
                    int per = static_cast<int>(pi);
                    const auto& pe = cf.prob_log[pi];
                    double bb = pe.begin_bal * inv;
                    // Age-indexed
                    pb[age] += bb;
                    int base_age = age * n_prob_cols;
                    for (int c = 0; c < n_prob_cols; ++c)
                        pp[base_age + c] += pe.probs[c] * bb;
                    // Period-indexed
                    pb_per[per] += bb;
                    int base_per = per * n_prob_cols;
                    for (int c = 0; c < n_prob_cols; ++c)
                        pp_per[base_per + c] += pe.probs[c] * bb;
                }
            }

            if (do_dump && !dc.rows.empty()) {
                #pragma omp critical(dump_collect)
                {
                    dump_entries.push_back({loan_id, path, std::move(dc)});
                }
            }
        }
    }

    // Sort dump entries by loan_id then path, and write
    if (dump_cfg.enabled && !dump_entries.empty()) {
        std::sort(dump_entries.begin(), dump_entries.end(),
            [](const DumpEntry& a, const DumpEntry& b) {
                if (a.loan_id != b.loan_id) return a.loan_id < b.loan_id;
                return a.path < b.path;
            });
        std::cout << "  Writing dump.csv (" << dump_entries.size()
                  << " loan-paths) to " << dump_cfg.output_dir << "\n";
        dump_write_csv(dump_cfg.output_dir, dump_entries);
    }

    // Reduce partials
    GroupedBatchResult result;
    result.portfolio.cf_sum.assign(n_per, std::vector<double>(CF_COL_LEN, 0.0));
    result.max_age = max_age;

    // Initialize group prob accumulators (flat: max_age * n_prob_cols)
    std::unordered_map<std::string, ProbAccum> group_prob_weighted;
    std::unordered_map<std::string, std::vector<double>> group_prob_bal_total;
    // Period-indexed group CF + prob accumulators
    std::unordered_map<std::string, std::vector<std::vector<double>>> group_cf_period;
    std::unordered_map<std::string, ProbAccum> group_prob_weighted_per;
    std::unordered_map<std::string, std::vector<double>> group_prob_bal_total_per;
    for (const auto& [key, _] : group_orig_bal) {
        group_prob_weighted[key].assign(max_age * n_prob_cols, 0.0);
        group_prob_bal_total[key].assign(max_age, 0.0);
        group_cf_period[key].assign(n_per, std::vector<double>(CF_COL_LEN, 0.0));
        group_prob_weighted_per[key].assign(n_per * n_prob_cols, 0.0);
        group_prob_bal_total_per[key].assign(n_per, 0.0);
    }

    for (int t = 0; t < actual_threads; ++t) {
        // Portfolio: period-indexed
        for (int p = 0; p < n_per; ++p)
            for (int c = 0; c < CF_COL_LEN; ++c)
                result.portfolio.cf_sum[p][c] += port_partial[t][p][c];

        // Groups: age-indexed
        for (auto& [key, tcf] : grp_partial[t]) {
            auto& dst = group_cf[key];
            for (int a = 0; a < max_age; ++a)
                for (int c = 0; c < CF_COL_LEN; ++c)
                    dst[a][c] += tcf[a][c];
        }

        // Groups: period-indexed
        for (auto& [key, tcf] : grp_partial_per[t]) {
            auto& dst = group_cf_period[key];
            for (int p = 0; p < n_per; ++p)
                for (int c = 0; c < CF_COL_LEN; ++c)
                    dst[p][c] += tcf[p][c];
        }

        // Prob: age-indexed flat reduction
        for (auto& [key, tpp] : prob_partial[t]) {
            auto& dst = group_prob_weighted[key];
            auto& dst_bal = group_prob_bal_total[key];
            auto& src_bal = pbal_partial[t][key];
            for (int a = 0; a < max_age; ++a)
                dst_bal[a] += src_bal[a];
            int flat_size = max_age * n_prob_cols;
            for (int i = 0; i < flat_size; ++i)
                dst[i] += tpp[i];
        }

        // Prob: period-indexed flat reduction
        for (auto& [key, tpp] : prob_partial_per[t]) {
            auto& dst = group_prob_weighted_per[key];
            auto& dst_bal = group_prob_bal_total_per[key];
            auto& src_bal = pbal_partial_per[t][key];
            for (int p = 0; p < n_per; ++p)
                dst_bal[p] += src_bal[p];
            int flat_size = n_per * n_prob_cols;
            for (int i = 0; i < flat_size; ++i)
                dst[i] += tpp[i];
        }
    }

    result.portfolio.errors = std::move(errors);
    result.portfolio.n_done = total_tasks - static_cast<int>(result.portfolio.errors.size());
    result.portfolio.n_error = static_cast<int>(result.portfolio.errors.size());
    result.group_cf = std::move(group_cf);
    result.group_cf_period = std::move(group_cf_period);
    result.group_orig_bal = std::move(group_orig_bal);
    result.total_orig_bal = total_orig_bal;
    result.n_prob_cols = n_prob_cols;
    result.group_prob_weighted = std::move(group_prob_weighted);
    result.group_prob_bal_total = std::move(group_prob_bal_total);
    result.group_prob_weighted_period = std::move(group_prob_weighted_per);
    result.group_prob_bal_total_period = std::move(group_prob_bal_total_per);
    result.prob_keys = dm.prob_schema.col_names;

    return result;
}

}  // namespace rrm::runners
