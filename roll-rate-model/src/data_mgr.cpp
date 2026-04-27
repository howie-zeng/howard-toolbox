#include "data_mgr.h"
#include "io/pmt_matrix_reader.h"
#include <filesystem>
#include <iostream>

namespace fs = std::filesystem;

namespace rrm {

void DataMgr::init(const std::string& input_dir,
                   const StatusMap& status_to_roll_cfg,
                   const std::string& dial_name,
                   int n_per_arg,
                   const std::string& coef_version,
                   const std::unordered_map<std::string, MacroVarConfig>& macro_cfg) {
    n_per = n_per_arg;

    status_to_roll = normalize_status_to_roll(status_to_roll_cfg);
    status_universe = derive_status_universe(status_to_roll);
    clean_status_dict = status_universe.clean_status_dict;
    prob_schema = build_prob_schema(status_to_roll, clean_status_dict);

    // Pre-compute transition layout per from-status
    for (const auto& [from_s, roll_to] : status_to_roll) {
        TransitionLayout tl;
        auto cf_it = clean_status_dict.find(from_s);
        tl.clean_from = (cf_it != clean_status_dict.end()) ? cf_it->second : from_s;
        tl.model_names.resize(roll_to.size());
        for (size_t ri = 0; ri < roll_to.size(); ++ri) {
            if (roll_to[ri] == from_s) {
                tl.stay_idx = static_cast<int>(ri);
            } else {
                auto ct_it = clean_status_dict.find(roll_to[ri]);
                std::string clean_to = (ct_it != clean_status_dict.end()) ? ct_it->second : roll_to[ri];
                tl.model_names[ri] = model::get_model_name(tl.clean_from, clean_to);
            }
        }
        transition_layout[from_s] = std::move(tl);
    }

    // --- Coefficients ---
    fs::path coef_path = fs::path(input_dir) / "coef";
    if (!coef_version.empty())
        coef_path /= coef_version;
    std::string coef_dir = coef_path.string();

    for (const auto& from_status : status_universe.from_status_list) {
        std::string from_file = "from" + from_status;
        std::string cp = coef_dir + "/" + from_file + ".txt";
        if (fs::exists(cp)) {
            model_coef.read(coef_dir, from_file);
        }
    }

    // Populate has_model flags (must come after coef files are loaded)
    for (auto& [from_s, tl] : transition_layout) {
        tl.has_model.resize(tl.model_names.size(), false);
        for (size_t ri = 0; ri < tl.model_names.size(); ++ri) {
            if (static_cast<int>(ri) != tl.stay_idx)
                tl.has_model[ri] = model_coef.has_model(tl.model_names[ri]);
        }
    }

    // --- Payment matrix ---
    std::string pmt_path = (fs::path(input_dir) / "pmt_matrix.txt").string();
    if (fs::exists(pmt_path)) {
        pmt_matrix = io::read_pmt_matrix(pmt_path);
    }

    // --- Dials ---
    if (!dial_name.empty()) {
        roll.read_dial(input_dir, "dial", dial_name,
                       status_universe.all_status_list, n_per);
    }

    // --- Macro variables ---
    std::unordered_set<std::string> active_macro_vars;

    for (const auto& [var_name, cfg] : macro_cfg) {
        if (cfg.mode != "custom" || cfg.path.empty()) continue;
        active_macro_vars.insert(var_name);

        if (var_name == "rate_incentive_ALL") {
            if (fico_coupon_table.empty()) {
                fico_coupon_table = io::read_lookup_csv(cfg.path, cfg.key_columns);
                std::cout << "  Macro " << var_name << ": "
                          << fico_coupon_table.size() << " entries from " << cfg.path << "\n";
            }
        } else {
            // Calendar-indexed: deduplicate by path
            if (calendar_macro_table.empty()) {
                calendar_macro_table = io::read_lookup_csv(cfg.path, cfg.key_columns);
                std::cout << "  Macro table: " << calendar_macro_table.size()
                          << " rows from " << cfg.path << "\n";
            }
        }
    }

    // Build VarContext (pointers to loaded tables)
    var_ctx.calendar_table = calendar_macro_table.empty() ? nullptr : &calendar_macro_table;
    var_ctx.fico_coupon_table = fico_coupon_table.empty() ? nullptr : &fico_coupon_table;

    // Build VarRegistry with active macro vars
    var_registry = build_var_registry(active_macro_vars);

    // Partition model terms into static/dynamic for logit caching
    model_coef.classify_terms(var_registry.dynamic_var_names());
}

}  // namespace rrm
