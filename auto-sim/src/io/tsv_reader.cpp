#include "io/tsv_reader.h"
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

std::vector<CoefRow> read_coef_file(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) throw std::runtime_error("cannot open coef file: " + path);

    std::vector<CoefRow> rows;
    std::string line;

    std::getline(f, line);
    if (line.empty()) throw std::runtime_error("empty coef file: " + path);

    int line_num = 1;
    while (std::getline(f, line)) {
        ++line_num;
        if (line.empty()) continue;

        auto cols = split_tab(line);
        if (cols.size() < 4)
            throw std::runtime_error("malformed row at line " + std::to_string(line_num)
                                     + " in " + path + " (got " + std::to_string(cols.size()) + " cols)");

        CoefRow r;
        r.model     = cols[0];
        r.var_name1 = cols[1];
        r.var_val1  = cols[2];
        r.var_name2 = (cols.size() > 3) ? cols[3] : "";
        r.var_val2  = (cols.size() > 4) ? cols[4] : "";

        std::string val_str = (cols.size() > 5) ? cols[5] : "";
        if (val_str.empty())
            throw std::runtime_error("missing value at line " + std::to_string(line_num) + " in " + path);
        r.value = std::stod(val_str);

        rows.push_back(std::move(r));
    }
    return rows;
}

}  // namespace rrm::io
