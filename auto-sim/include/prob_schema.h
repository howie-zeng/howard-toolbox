#pragma once

#include "types.h"
#include <string>
#include <unordered_map>
#include <vector>

namespace rrm {

struct ProbSchema {
    int n_cols = 0;
    std::vector<std::string> col_names;  // sorted alphabetically

    // Per from-status: maps roll_to index -> flat column index
    struct StatusLayout {
        std::vector<int> col_idx;  // col_idx[ri] for every ri in roll_to
    };
    std::unordered_map<std::string, StatusLayout> layout;

    // Convert flat prob vector back to string-keyed map (for dump path)
    std::unordered_map<std::string, double> to_map(
        const std::vector<double>& flat) const;
};

ProbSchema build_prob_schema(
    const StatusMap& status_to_roll,
    const std::unordered_map<std::string, std::string>& clean_status_dict);

}  // namespace rrm
