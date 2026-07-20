#include "prob_schema.h"
#include <algorithm>
#include <map>

namespace rrm {

ProbSchema build_prob_schema(
    const StatusMap& status_to_roll,
    const std::unordered_map<std::string, std::string>& clean_status_dict) {

    // Helper: look up clean name, fall back to raw
    auto clean = [&](const std::string& s) -> std::string {
        auto it = clean_status_dict.find(s);
        return (it != clean_status_dict.end()) ? it->second : s;
    };

    // 1. Enumerate all column names with their (from_status, ri) origin
    struct ColOrigin { std::string from_status; size_t ri; };
    std::map<std::string, ColOrigin> name_to_origin;  // sorted map for determinism

    for (const auto& [from_status, roll_to] : status_to_roll) {
        std::string clean_from = clean(from_status);
        for (size_t ri = 0; ri < roll_to.size(); ++ri) {
            std::string col_name;
            if (roll_to[ri] == from_status) {
                col_name = "from" + clean_from + "_stay";
            } else {
                col_name = "from" + clean_from + "_" + clean(roll_to[ri]);
            }
            // First occurrence wins (duplicates shouldn't happen with valid config)
            if (name_to_origin.find(col_name) == name_to_origin.end()) {
                name_to_origin[col_name] = {from_status, ri};
            }
        }
    }

    // 2. Assign sorted indices
    ProbSchema schema;
    schema.n_cols = static_cast<int>(name_to_origin.size());
    std::unordered_map<std::string, int> name_to_idx;
    for (const auto& [name, _] : name_to_origin) {
        int idx = static_cast<int>(schema.col_names.size());
        schema.col_names.push_back(name);
        name_to_idx[name] = idx;
    }

    // 3. Build StatusLayout for each from-status
    for (const auto& [from_status, roll_to] : status_to_roll) {
        std::string clean_from = clean(from_status);
        ProbSchema::StatusLayout sl;
        sl.col_idx.resize(roll_to.size());

        for (size_t ri = 0; ri < roll_to.size(); ++ri) {
            std::string col_name;
            if (roll_to[ri] == from_status) {
                col_name = "from" + clean_from + "_stay";
            } else {
                col_name = "from" + clean_from + "_" + clean(roll_to[ri]);
            }
            sl.col_idx[ri] = name_to_idx.at(col_name);
        }

        schema.layout[from_status] = std::move(sl);
    }

    return schema;
}

std::unordered_map<std::string, double> ProbSchema::to_map(
    const std::vector<double>& flat) const {
    std::unordered_map<std::string, double> result;
    for (int i = 0; i < n_cols && i < static_cast<int>(flat.size()); ++i) {
        if (flat[i] != 0.0)
            result[col_names[i]] = flat[i];
    }
    return result;
}

}  // namespace rrm
