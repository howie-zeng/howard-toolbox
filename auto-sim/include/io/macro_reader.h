#pragma once

#include <string>
#include <unordered_map>
#include <vector>

namespace rrm::io {

/// Keyed lookup table: composite key ("|"-joined key columns) -> {column -> value}.
using LookupTable = std::unordered_map<std::string, std::unordered_map<std::string, double>>;

/// Read a CSV into a keyed lookup. key_columns form the composite key (empty => first column);
/// remaining columns become named doubles. Missing file or unparseable values are skipped.
LookupTable read_lookup_csv(const std::string& path,
                            const std::vector<std::string>& key_columns = {});

}  // namespace rrm::io
