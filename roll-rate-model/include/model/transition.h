#pragma once

#include "types.h"
#include "data_mgr.h"
#include "model/model_coef.h"
#include <random>
#include <string>
#include <vector>

namespace rrm::model {

TransitionResult flipcoin_logit(
    const LoanDict& loan,
    const std::string& from_status,
    const std::string& dial_name,
    int dial_per,
    const std::vector<std::string>& roll_to,
    const TransitionLayout& tl,
    ModelCoef& model_coef,
    const Roll& roll,
    std::mt19937& rng,
    const LogitCache& logit_cache = {});

}  // namespace rrm::model
