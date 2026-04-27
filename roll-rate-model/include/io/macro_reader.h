#pragma once

#include <string>
#include <unordered_map>
#include <vector>

namespace rrm::io {

/// Generic keyed lookup table: {composite_key -> {column_name -> value}}
/// Key is built by joining one or more key columns with "|".
using LookupTable = std::unordered_map<std::string, std::unordered_map<std::string, double>>;

/// Read a CSV into a keyed lookup table.
///
/// @param path         CSV file path (returns empty if file does not exist)
/// @param key_columns  Column names to use as the composite key (joined with "|").
///                     If empty, the first column is used as key.
///
/// All non-key columns are treated as named double values.
/// Non-parseable values are silently skipped.
///
/// Examples:
///   read_lookup_csv("cpi_table.csv", {})
///     -> {"2025-12": {"cpi_inflator_36": 0.0918, "cpi_inflator_12": 0.0268}}
///
///   read_lookup_csv("FICO_BKT_COUPON.csv", {"vint_moyy", "fico_bkt"})
///     -> {"201309|[0-620)": {"fico_bkt_coupon": 0.2226}}
///
LookupTable read_lookup_csv(const std::string& path,
                            const std::vector<std::string>& key_columns = {});

}  // namespace rrm::io
