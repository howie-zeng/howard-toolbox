#include "types.h"
#include <stdexcept>

namespace rrm {

int get_int(const LoanDict& d, const std::string& key) {
    auto it = d.find(key);
    if (it == d.end()) throw std::runtime_error("missing key: " + key);
    return std::get<int>(it->second);
}

std::string get_string(const LoanDict& d, const std::string& key) {
    auto it = d.find(key);
    if (it == d.end()) throw std::runtime_error("missing key: " + key);
    return std::get<std::string>(it->second);
}

double get_numeric(const LoanDict& d, const std::string& key) {
    auto it = d.find(key);
    if (it == d.end()) throw std::runtime_error("missing key: " + key);
    if (auto* p = std::get_if<double>(&it->second)) return *p;
    if (auto* p = std::get_if<int>(&it->second))    return static_cast<double>(*p);
    throw std::runtime_error("key is not numeric: " + key);
}

void set_val(LoanDict& d, const std::string& key, int v)                { d[key] = v; }
void set_val(LoanDict& d, const std::string& key, double v)             { d[key] = v; }
void set_val(LoanDict& d, const std::string& key, const std::string& v) { d[key] = v; }

const std::vector<std::string> CF_COL = {
    "cnt", "begin_bal", "end_bal", "int_pmt", "sch_int", "prin_pmt", "sch_prin",
    "pif_bal", "net_recov", "loss", "liq_bal", "dq30", "dq60", "dq90", "dq120",
    "pif_cnt", "liq_cnt", "dq30_bal", "dq60_bal", "dq90_bal", "dq120_bal",
    "recov", "cost2srvc", "sfee_pmt", "bk", "cf", "cf_delta", "int_rate", "irr", "npv",
};

const int CF_COL_LEN = static_cast<int>(CF_COL.size());

static std::unordered_map<std::string, int> build_cf_dict() {
    std::unordered_map<std::string, int> m;
    for (int i = 0; i < CF_COL_LEN; ++i) m[CF_COL[i]] = i;
    return m;
}
const std::unordered_map<std::string, int> CF_DICT = build_cf_dict();

CfIndices extract_cf_indices(const std::unordered_map<std::string, int>& cf_dict) {
    return CfIndices{
        cf_dict.at("cnt"),       cf_dict.at("begin_bal"), cf_dict.at("end_bal"),
        cf_dict.at("int_pmt"),   cf_dict.at("prin_pmt"),  cf_dict.at("sch_int"),
        cf_dict.at("sch_prin"),
        cf_dict.at("pif_cnt"),   cf_dict.at("pif_bal"),
        cf_dict.at("liq_cnt"),   cf_dict.at("liq_bal"),
    };
}

}  // namespace rrm
