#include "io/macro_reader.h"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace fs = std::filesystem;

namespace rrm::io {

static std::string trim(std::string s) {
    while (!s.empty() && (s.front() == ' ' || s.front() == '\t')) s.erase(s.begin());
    while (!s.empty() && (s.back() == ' ' || s.back() == '\t' || s.back() == '\r')) s.pop_back();
    return s;
}

static std::vector<std::string> split_csv_line(const std::string& line) {
    std::vector<std::string> result;
    std::istringstream ss(line);
    std::string cell;
    while (std::getline(ss, cell, ','))
        result.push_back(trim(cell));
    return result;
}

LookupTable read_lookup_csv(const std::string& path,
                            const std::vector<std::string>& key_columns) {
    LookupTable result;
    if (!fs::exists(path)) return result;

    std::ifstream f(path);
    if (!f.is_open()) return result;

    // --- Header ---
    std::string header_line;
    if (!std::getline(f, header_line)) return result;
    auto cols = split_csv_line(header_line);
    if (cols.empty()) return result;

    // Determine which column indices are keys vs values
    std::vector<size_t> key_idx;
    std::vector<size_t> val_idx;

    if (key_columns.empty()) {
        // Default: first column is the key
        key_idx.push_back(0);
        for (size_t i = 1; i < cols.size(); ++i) val_idx.push_back(i);
    } else {
        for (const auto& kc : key_columns) {
            auto it = std::find(cols.begin(), cols.end(), kc);
            if (it == cols.end())
                throw std::runtime_error("key column '" + kc + "' not found in " + path);
            key_idx.push_back(static_cast<size_t>(it - cols.begin()));
        }
        for (size_t i = 0; i < cols.size(); ++i) {
            if (std::find(key_idx.begin(), key_idx.end(), i) == key_idx.end())
                val_idx.push_back(i);
        }
    }

    // --- Data rows ---
    std::string line;
    while (std::getline(f, line)) {
        if (line.empty()) continue;
        auto vals = split_csv_line(line);
        if (vals.size() < key_idx.size() + 1) continue;

        // Build composite key
        std::string key;
        for (size_t i = 0; i < key_idx.size(); ++i) {
            if (i > 0) key += '|';
            if (key_idx[i] < vals.size()) key += vals[key_idx[i]];
        }

        // Parse value columns
        std::unordered_map<std::string, double> row_data;
        for (size_t vi : val_idx) {
            if (vi >= vals.size()) continue;
            try {
                row_data[cols[vi]] = std::stod(vals[vi]);
            } catch (...) {}
        }

        result[key] = std::move(row_data);
    }

    return result;
}

}  // namespace rrm::io
