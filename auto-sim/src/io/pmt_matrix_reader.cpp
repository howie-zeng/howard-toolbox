#include "io/pmt_matrix_reader.h"
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace rrm::io {

static std::vector<std::string> split_tab(const std::string& line) {
    std::vector<std::string> tokens;
    std::istringstream ss(line);
    std::string tok;
    while (std::getline(ss, tok, '\t')) tokens.push_back(tok);
    return tokens;
}

rrm::PmtMatrix read_pmt_matrix(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) throw std::runtime_error("cannot open pmt_matrix: " + path);

    std::string header_line;
    std::getline(f, header_line);
    auto header = split_tab(header_line);

    std::vector<std::string> to_statuses(header.begin() + 1, header.end());

    rrm::PmtMatrix matrix;
    for (const auto& ts : to_statuses) matrix[ts] = {};

    std::string line;
    while (std::getline(f, line)) {
        if (line.empty()) continue;
        auto cols = split_tab(line);
        if (cols.size() < 2) continue;

        std::string from_status = cols[0];
        for (size_t i = 1; i < cols.size() && (i - 1) < to_statuses.size(); ++i) {
            double val = std::stod(cols[i]);
            matrix[to_statuses[i - 1]][from_status] = val;
        }
    }
    return matrix;
}

}  // namespace rrm::io
