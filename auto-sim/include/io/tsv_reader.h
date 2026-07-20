#pragma once

#include <string>
#include <vector>

namespace rrm::io {

struct CoefRow {
    std::string model;
    std::string var_name1;
    std::string var_val1;
    std::string var_name2;
    std::string var_val2;
    double      value;
};

std::vector<CoefRow> read_coef_file(const std::string& path);

}  // namespace rrm::io
