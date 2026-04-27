#pragma once

#include "types.h"
#include <string>
#include <vector>

namespace rrm::io {

std::vector<rrm::LoanDict> read_loan_json(const std::string& path);

}  // namespace rrm::io
