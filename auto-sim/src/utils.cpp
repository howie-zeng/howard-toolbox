#include "utils.h"
#include <algorithm>
#include <set>
#include <stdexcept>

namespace rrm {

std::optional<std::pair<std::string, std::string>>
dq_bucket_for_status(const std::string& status) {
    if (status == "D1M") return std::make_pair("dq30",  "dq30_bal");
    if (status == "D2M") return std::make_pair("dq60",  "dq60_bal");
    if (status == "D3M") return std::make_pair("dq90",  "dq90_bal");
    if (status == "D4M" || status == "D5M" ||
        status == "D6M" || status == "D7M")
        return std::make_pair("dq120", "dq120_bal");
    return std::nullopt;
}

StatusMap normalize_status_to_roll(const StatusMap& m) {
    StatusMap out = m;
    for (auto& [k, v] : out) {
        if (std::find(v.begin(), v.end(), k) == v.end())
            v.push_back(k);
    }
    return out;
}

StatusUniverse derive_status_universe(const StatusMap& status_to_roll) {
    StatusUniverse u;
    std::set<std::string> to_set, all_set;

    for (const auto& [from, tos] : status_to_roll) {
        u.from_status_list.push_back(from);
        all_set.insert(from);
        for (const auto& t : tos) {
            to_set.insert(t);
            all_set.insert(t);
        }
    }
    u.to_status_list.assign(to_set.begin(), to_set.end());
    u.all_status_list.assign(all_set.begin(), all_set.end());

    for (const auto& s : u.all_status_list) {
        auto dot = s.find('.');
        u.clean_status_dict[s] = (dot != std::string::npos) ? s.substr(0, dot) : s;
    }
    return u;
}

// FNV-1a 64-bit, matching Python stable_seed_from_loan_id
uint32_t stable_seed(uint32_t seed0, const std::string& loan_id, int path) {
    std::string s = std::to_string(seed0) + "|" + loan_id + "|" + std::to_string(path);
    uint64_t h = 1469598103934665603ULL;
    for (char ch : s) {
        h ^= static_cast<uint64_t>(ch);
        h *= 1099511628211ULL;
    }
    return static_cast<uint32_t>(h % (1ULL << 32));
}

bool should_continue(const LoanDict& loan, int per, int end_per,
                     const std::string& status) {
    double end_bal = get_numeric(loan, "end_bal");
    int loan_age   = get_int(loan, "loan_age");
    return end_bal > 0.1
        && per < end_per
        && status != "PIF" && status != "LIQ"
        && loan_age <= 480
        && loan_age >= 0;
}

}  // namespace rrm
