#pragma once

#include <string>
#include <unordered_map>
#include <vector>

namespace rrm::model {

class Roll {
public:
    void read_dial(const std::string& input_dir, const std::string& folder_name,
                   const std::string& dial_prefix,
                   const std::vector<std::string>& all_status_list, int n_per);

    double get_dial(const std::string& dial_name,
                    const std::string& from_status,
                    const std::string& to_status,
                    int dial_per,
                    const std::vector<std::string>& seg_vals = {}) const;

    /// Segment column names for a given dial (e.g. {"term","grade"}).
    const std::vector<std::string>& seg_cols(const std::string& dial_name) const;

private:
    std::unordered_map<std::string, int> status_idx_;
    int n_per_ = 0;

    struct DialArray {
        std::vector<double> data;
        int n_status = 0;
        int n_per = 0;

        double at(int fi, int ti, int per) const {
            if (fi < 0 || ti < 0 || per < 0 || per >= n_per) return 1.0;
            int idx = fi * n_status * n_per + ti * n_per + per;
            if (idx < 0 || idx >= static_cast<int>(data.size())) return 1.0;
            double v = data[idx];
            return (v != v) ? 1.0 : v;  // NaN -> 1.0
        }
    };

    // Key: "dialname" for fallback, "dialname|term|grade" for segmented
    std::unordered_map<std::string, DialArray> dial_arrays_;

    // Segment column names per dial (e.g. "upst_ctd1" -> {"term","grade"})
    std::unordered_map<std::string, std::vector<std::string>> dial_seg_cols_;
    static const std::vector<std::string> empty_seg_cols_;
};

}  // namespace rrm::model
