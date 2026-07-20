#pragma once

#include "types.h"
#include "data_mgr.h"
#include "dump.h"
#include <random>
#include <vector>

namespace rrm {

struct ProbEntry {
    double begin_bal = 0.0;
    std::vector<double> probs;  // indexed by ProbSchema column
};

struct CfResult {
    std::vector<std::vector<double>> loan_cf;
    std::vector<ProbEntry> prob_log;  // one per active period
    bool  has_error = false;
    std::string error_msg;
};

CfResult run_cf(LoanDict loan,
                DataMgr& dm,
                int n_per,
                int dup,
                const std::string& dial_name,
                std::mt19937& rng,
                DumpCollector* dump = nullptr,
                const model::LogitCache& logit_cache = {});

}  // namespace rrm
