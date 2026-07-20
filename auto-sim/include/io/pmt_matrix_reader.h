#pragma once

#include "types.h"
#include <string>

namespace rrm::io {

rrm::PmtMatrix read_pmt_matrix(const std::string& path);

}  // namespace rrm::io
