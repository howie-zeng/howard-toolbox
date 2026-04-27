#pragma once

#include <cstdint>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <variant>
#include <vector>

namespace rrm {

using LoanValue = std::variant<int, double, std::string>;
using LoanDict  = std::unordered_map<std::string, LoanValue>;

int         get_int(const LoanDict& d, const std::string& key);
std::string get_string(const LoanDict& d, const std::string& key);
double      get_numeric(const LoanDict& d, const std::string& key);

void set_val(LoanDict& d, const std::string& key, int v);
void set_val(LoanDict& d, const std::string& key, double v);
void set_val(LoanDict& d, const std::string& key, const std::string& v);

extern const std::vector<std::string> CF_COL;
extern const int CF_COL_LEN;
extern const std::unordered_map<std::string, int> CF_DICT;

struct CfIndices {
    int cnt, begin_bal, end_bal, int_pmt, prin_pmt, sch_int, sch_prin;
    int pif_cnt, pif_bal, liq_cnt, liq_bal;
};

CfIndices extract_cf_indices(const std::unordered_map<std::string, int>& cf_dict);

struct CFTask {
    LoanDict    loan;
    int         path = 0;
    std::string task_id;
};

struct TransitionResult {
    std::string              status_to;
    std::vector<double>      prob_proj;
    double                   u = -1.0;
};

using StatusMap = std::unordered_map<std::string, std::vector<std::string>>;
using PmtMatrix = std::unordered_map<std::string,
                      std::unordered_map<std::string, double>>;

}  // namespace rrm
