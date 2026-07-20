#include "model/transition.h"
#include "model/model_coef.h"
#include "model/roll.h"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>

namespace rrm::model {

// Normalize in-place: clamp negatives/NaN, then normalize to sum=1.
static void normalize_probs_inplace(std::vector<double>& probs, int stay_idx) {
    for (auto& p : probs) {
        if (std::isnan(p) || std::isinf(p) || p < 0.0) p = 0.0;
    }
    double s = std::accumulate(probs.begin(), probs.end(), 0.0);
    if (s <= 0.0) {
        std::fill(probs.begin(), probs.end(), 0.0);
        probs[stay_idx] = 1.0;
        return;
    }
    double inv = 1.0 / s;
    for (auto& v : probs) v *= inv;
}

static size_t sample_choice(
    const std::vector<double>& prob_proj,
    std::mt19937& rng,
    double& u_out) {

    std::uniform_real_distribution<double> dist(0.0, 1.0);
    double u = dist(rng);
    u_out = u;

    double cumulative = 0.0;
    for (size_t i = 0; i < prob_proj.size(); ++i) {
        cumulative += prob_proj[i];
        if (u <= cumulative) return i;
    }
    return prob_proj.size() - 1;
}

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
    const LogitCache& logit_cache) {

    int stay_idx = tl.stay_idx;

    // exp(logit) for each non-stay transition
    std::vector<double> scores;
    scores.reserve(roll_to.size());
    for (size_t i = 0; i < roll_to.size(); ++i) {
        if (static_cast<int>(i) == stay_idx) continue;
        if (!tl.has_model[i]) {
            scores.push_back(0.0);
        } else {
            const std::string& model_name = tl.model_names[i];
            auto cache_it = logit_cache.find(model_name);
            double z = (cache_it != logit_cache.end())
                ? cache_it->second + model_coef.calc_dynamic(loan, model_name)
                : model_coef.calc(loan, model_name);
            scores.push_back(std::exp(z));
        }
    }

    // softmax: p_i = exp(z_i) / (1 + sum(exp(z_j)))
    double tmp_all = 1.0 + std::accumulate(scores.begin(), scores.end(), 0.0);

    std::vector<double> prob_proj;
    prob_proj.reserve(roll_to.size());
    double nonstay_sum = 0.0;
    size_t j = 0;
    for (size_t i = 0; i < roll_to.size(); ++i) {
        if (static_cast<int>(i) == stay_idx) {
            prob_proj.push_back(0.0);
        } else {
            double p = scores[j] / tmp_all;
            prob_proj.push_back(p);
            nonstay_sum += p;
            ++j;
        }
    }
    prob_proj[stay_idx] = std::max(0.0, 1.0 - nonstay_sum);

    // dial adjustment (skip entirely when no dials configured)
    if (!dial_name.empty()) {
        // Build segment values dynamically from dial file's column names
        std::vector<std::string> seg_vals;
        const auto& seg_col_names = roll.seg_cols(dial_name);
        for (const auto& col : seg_col_names) {
            auto it = loan.find(col);
            if (it != loan.end()) {
                if (auto* s = std::get_if<std::string>(&it->second)) seg_vals.push_back(*s);
                else if (auto* iv = std::get_if<int>(&it->second)) seg_vals.push_back(std::to_string(*iv));
                else if (auto* dv = std::get_if<double>(&it->second)) seg_vals.push_back(std::to_string(static_cast<int>(*dv)));
                else seg_vals.push_back("*");
            } else {
                seg_vals.push_back("*");
            }
        }
        for (size_t i = 0; i < roll_to.size(); ++i)
            prob_proj[i] *= roll.get_dial(dial_name, from_status, roll_to[i], dial_per,
                                          seg_vals);
        normalize_probs_inplace(prob_proj, stay_idx);
    }

    double u = 0.0;
    size_t pick_idx = sample_choice(prob_proj, rng, u);

    return TransitionResult{roll_to[pick_idx], std::move(prob_proj), u};
}

}  // namespace rrm::model
