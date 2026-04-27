#include "model/roll.h"
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>

namespace fs = std::filesystem;

namespace rrm::model {

static std::vector<std::string> split_tab(const std::string& line) {
    std::vector<std::string> tokens;
    std::istringstream ss(line);
    std::string tok;
    while (std::getline(ss, tok, '\t')) tokens.push_back(tok);
    return tokens;
}

static std::string trim(const std::string& s) {
    size_t a = s.find_first_not_of(" \t\r\n");
    size_t b = s.find_last_not_of(" \t\r\n");
    return (a == std::string::npos) ? "" : s.substr(a, b - a + 1);
}

void Roll::read_dial(const std::string& input_dir, const std::string& folder_name,
                     const std::string& dial_prefix,
                     const std::vector<std::string>& all_status_list, int n_per) {
    n_per_ = n_per;
    int n_status = static_cast<int>(all_status_list.size());
    for (int i = 0; i < n_status; ++i) status_idx_[all_status_list[i]] = i;

    fs::path folder = fs::path(input_dir) / folder_name;
    if (!fs::is_directory(folder)) return;

    for (const auto& entry : fs::directory_iterator(folder)) {
        if (!entry.is_regular_file()) continue;
        std::string fname = entry.path().filename().string();
        if (fname.find(dial_prefix) != 0) continue;
        if (fname.size() < 4 || fname.substr(fname.size() - 4) != ".txt") continue;

        std::string dial_name = fname.substr(0, fname.size() - 4);

        std::ifstream f(entry.path());
        if (!f.is_open()) continue;

        // Parse header to detect segment columns
        std::string header_line;
        std::getline(f, header_line);
        auto header = split_tab(header_line);

        int status_col = -1;
        for (size_t i = 0; i < header.size(); ++i) {
            if (header[i] == "Status") { status_col = static_cast<int>(i); break; }
        }

        // Detect segment columns (between Status and first status column)
        std::vector<std::string> seg_cols;
        int to_col_start = (status_col >= 0) ? 1 : 0;
        for (int i = to_col_start; i < static_cast<int>(header.size()); ++i) {
            if (status_idx_.count(header[i])) { to_col_start = i; break; }
            seg_cols.push_back(header[i]);
        }
        dial_seg_cols_[dial_name] = seg_cols;

        std::vector<std::string> to_cols(header.begin() + to_col_start, header.end());

        // Parse rows, grouping by segment key
        // seg_key = "term|grade" or "*|*" or "" (unsegmented)
        struct SegState { std::string current_from; int per = 0; };
        std::unordered_map<std::string, SegState> state_by_seg;
        // segment_key -> DialArray
        std::unordered_map<std::string, DialArray> seg_arrays;

        std::string line;
        std::string current_seg_key;
        std::string current_from;
        while (std::getline(f, line)) {
            if (line.empty()) continue;
            auto cols = split_tab(line);

            // From-status
            std::string from_val;
            if (status_col >= 0 && status_col < static_cast<int>(cols.size()))
                from_val = trim(cols[status_col]);

            if (!from_val.empty())
                current_from = from_val;

            // Segment key — only update when from_val is non-empty (header row)
            if (!from_val.empty() && !seg_cols.empty()) {
                current_seg_key.clear();
                for (size_t si = 0; si < seg_cols.size(); ++si) {
                    int ci = 1 + static_cast<int>(si);
                    std::string sv = (ci < static_cast<int>(cols.size())) ? trim(cols[ci]) : "*";
                    if (!current_seg_key.empty()) current_seg_key += "|";
                    current_seg_key += sv;
                }
            }
            std::string seg_key = current_seg_key;

            std::string state_key = current_from + "|" + seg_key;
            auto& ss = state_by_seg[state_key];
            if (!from_val.empty()) {
                ss.current_from = from_val;
                ss.per = 0;
            }

            if (ss.current_from.empty() || status_idx_.count(ss.current_from) == 0) {
                ss.per++;
                continue;
            }
            int fi = status_idx_[ss.current_from];

            // Init segment array
            if (seg_arrays.find(seg_key) == seg_arrays.end()) {
                DialArray arr;
                arr.n_status = n_status;
                arr.n_per = n_per;
                arr.data.assign(n_status * n_status * n_per, std::nan(""));
                seg_arrays[seg_key] = std::move(arr);
            }
            auto& arr = seg_arrays[seg_key];

            for (size_t c = 0; c < to_cols.size(); ++c) {
                int data_col = to_col_start + static_cast<int>(c);
                if (data_col >= static_cast<int>(cols.size())) break;
                if (status_idx_.count(to_cols[c]) == 0) continue;
                int ti = status_idx_[to_cols[c]];
                try {
                    double val = std::stod(cols[data_col]);
                    if (ss.per < n_per)
                        arr.data[fi * n_status * n_per + ti * n_per + ss.per] = val;
                } catch (...) {}
            }
            ss.per++;
        }

        // Store: fallback = unsegmented or "*|*"
        std::string wildcard_key;
        for (size_t i = 0; i < seg_cols.size(); ++i) {
            if (i > 0) wildcard_key += "|";
            wildcard_key += "*";
        }

        for (auto& [seg_key, arr] : seg_arrays) {
            if (seg_key.empty() || seg_key == wildcard_key) {
                // Fallback: store under bare dial_name
                dial_arrays_[dial_name] = std::move(arr);
            } else {
                // Segmented: store under "dialname|seg_key"
                dial_arrays_[dial_name + "|" + seg_key] = std::move(arr);
            }
        }

        if (seg_arrays.count("") == 0 && seg_arrays.count(wildcard_key) == 0) {
            // No fallback found — ensure bare key exists as empty
            if (dial_arrays_.find(dial_name) == dial_arrays_.end()) {
                DialArray empty;
                empty.n_status = n_status;
                empty.n_per = n_per;
                empty.data.assign(n_status * n_status * n_per, std::nan(""));
                dial_arrays_[dial_name] = std::move(empty);
            }
        }

        int n_segs = static_cast<int>(seg_arrays.size());
        if (!seg_cols.empty()) {
            std::cout << "  Dial " << dial_name << ": " << n_segs
                      << " segments by " << seg_cols[0];
            for (size_t i = 1; i < seg_cols.size(); ++i)
                std::cout << ", " << seg_cols[i];
            std::cout << "\n";
        }
    }
}

const std::vector<std::string> Roll::empty_seg_cols_;

const std::vector<std::string>& Roll::seg_cols(const std::string& dial_name) const {
    auto it = dial_seg_cols_.find(dial_name);
    return (it != dial_seg_cols_.end()) ? it->second : empty_seg_cols_;
}

double Roll::get_dial(const std::string& dial_name,
                      const std::string& from_status,
                      const std::string& to_status,
                      int dial_per,
                      const std::vector<std::string>& seg_vals) const {
    if (dial_name.empty()) return 1.0;

    auto fi_it = status_idx_.find(from_status);
    auto ti_it = status_idx_.find(to_status);
    if (fi_it == status_idx_.end() || ti_it == status_idx_.end()) return 1.0;
    int fi = fi_it->second;
    int ti = ti_it->second;

    // Try segmented lookup if segment values provided
    if (!seg_vals.empty()) {
        std::string seg_key = dial_name;
        for (const auto& v : seg_vals) {
            seg_key += "|";
            seg_key += v;
        }
        auto it = dial_arrays_.find(seg_key);
        if (it != dial_arrays_.end()) {
            double v = it->second.at(fi, ti, dial_per);
            if (v == v) return v;  // not NaN
        }
    }

    // Fallback to unsegmented
    auto it = dial_arrays_.find(dial_name);
    if (it == dial_arrays_.end()) return 1.0;
    return it->second.at(fi, ti, dial_per);
}

}  // namespace rrm::model
