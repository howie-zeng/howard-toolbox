#pragma once

#include "types.h"
#include "data_mgr.h"
#include "dump.h"
#include <string>
#include <unordered_map>
#include <vector>

namespace rrm::runners {

struct BatchResult {
    std::vector<std::vector<double>> cf_sum;
    std::vector<std::string> errors;
    int n_done = 0;
    int n_error = 0;
};

// Per-group probability accumulator: flat vector of size max_age * n_prob_cols
using ProbAccum = std::vector<double>;

struct GroupedBatchResult {
    BatchResult portfolio;                           // overall (period-indexed)
    std::unordered_map<std::string,                  // group_key -> cf_sum[loan_age]
        std::vector<std::vector<double>>> group_cf;
    std::unordered_map<std::string, double> group_orig_bal;
    double total_orig_bal = 0.0;
    int max_age = 0;                                 // max loan_age index in group_cf

    // Probability tracking per group (flat: index = age * n_prob_cols + col)
    int n_prob_cols = 0;
    std::unordered_map<std::string, ProbAccum> group_prob_weighted;
    std::unordered_map<std::string, std::vector<double>> group_prob_bal_total;
    std::vector<std::string> prob_keys;  // column names from ProbSchema

    // Period-indexed group accumulators (same groups, indexed by projection period)
    std::unordered_map<std::string,
        std::vector<std::vector<double>>> group_cf_period;
    std::unordered_map<std::string, ProbAccum> group_prob_weighted_period;
    std::unordered_map<std::string, std::vector<double>> group_prob_bal_total_period;
};

// Simple portfolio-level run (unchanged)
BatchResult run_batch(
    std::vector<LoanDict>& loans,
    DataMgr& dm,
    int n_per,
    int dup,
    int n_threads,
    uint32_t seed0,
    const std::string& dial_name);

// Grouped run: accumulates CF per group_key
GroupedBatchResult run_batch_grouped(
    std::vector<LoanDict>& loans,
    DataMgr& dm,
    int n_per,
    int dup,
    int n_threads,
    uint32_t seed0,
    const std::string& dial_name,
    const std::vector<std::string>& group_by,
    const DumpConfig& dump_cfg = {});

}  // namespace rrm::runners
