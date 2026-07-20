#pragma once

#include "types.h"
#include "utils.h"
#include "prob_schema.h"
#include "model/model_coef.h"
#include "model/roll.h"
#include "io/macro_reader.h"
#include "var_registry.h"

#include <string>
#include <unordered_map>
#include <unordered_set>

namespace rrm {

/// Per-variable macro configuration from JSON.
struct MacroVarConfig {
    std::string mode = "default";  // "default" or "custom"
    std::string path;
    std::vector<std::string> key_columns;  // for composite-key CSVs
};

// Pre-computed per from-status: model names, clean name, stay index.
// Avoids repeated string construction + hash lookups in the inner loop.
struct TransitionLayout {
    std::string clean_from;
    int stay_idx = -1;
    std::vector<std::string> model_names;  // model_names[ri] for each roll_to entry ("" for stay)
    std::vector<bool> has_model;           // has_model[ri] — false for stay or missing models
};

class DataMgr {
public:
    void init(const std::string& input_dir,
              const StatusMap& status_to_roll_cfg,
              const std::string& dial_name = "",
              int n_per = 360,
              const std::string& coef_version = "",
              const std::unordered_map<std::string, MacroVarConfig>& macro_cfg = {},
              const std::string& severity_coef = "",
              const std::string& lag_dist_path = "",
              const std::string& manheim_path = "");

    StatusMap                                         status_to_roll;
    std::unordered_map<std::string, std::string>      clean_status_dict;
    StatusUniverse                                    status_universe;
    PmtMatrix                                         pmt_matrix;
    model::ModelCoef                                  model_coef;
    model::Roll                                       roll;
    ProbSchema                                        prob_schema;
    std::unordered_map<std::string, TransitionLayout> transition_layout;
    double                                            liq_severity = 0.60;
    int                                               n_per = 360;

    // --- Variable registry + macro scenario ---
    VarRegistry  var_registry;
    VarContext   var_ctx;
    io::LookupTable calendar_macro_table;
    io::LookupTable fico_coupon_table;

    // --- Two-part severity (recovery-rate GAM + empirical recovery-lag dist) ---
    bool has_severity = false;
    // platform -> [(label, cumulative_prob)]  (label in {"0".."12","13+","never"})
    std::unordered_map<std::string, std::vector<std::pair<std::string, double>>> lag_cdf;
    // label -> (lag_months, recovery_lag_bkt); lag_months = -1 means "never recovers"
    std::unordered_map<std::string, std::pair<int, std::string>>                 lag_label_map;
    std::unordered_map<int, double>                                              manheim;  // year*12+month -> value
    void load_severity(const std::string& coef_dir, const std::string& severity_coef,
                       const std::string& lag_dist_path, const std::string& manheim_path);
};

}  // namespace rrm
