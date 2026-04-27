#pragma once

#include "types.h"
#include <algorithm>
#include <optional>
#include <set>
#include <string>
#include <tuple>
#include <unordered_map>
#include <vector>

namespace rrm {

std::optional<std::pair<std::string, std::string>>
dq_bucket_for_status(const std::string& status);

StatusMap normalize_status_to_roll(const StatusMap& m);

struct StatusUniverse {
    std::vector<std::string>                        from_status_list;
    std::vector<std::string>                        to_status_list;
    std::vector<std::string>                        all_status_list;
    std::unordered_map<std::string, std::string>    clean_status_dict;
};

StatusUniverse derive_status_universe(const StatusMap& status_to_roll);

uint32_t stable_seed(uint32_t seed0, const std::string& loan_id, int path);

bool should_continue(const LoanDict& loan, int per, int end_per,
                     const std::string& status);

}  // namespace rrm
