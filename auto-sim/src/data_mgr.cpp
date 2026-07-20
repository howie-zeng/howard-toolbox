#include "data_mgr.h"
#include "io/pmt_matrix_reader.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>

namespace fs = std::filesystem;

namespace rrm {

void DataMgr::init(const std::string& input_dir,
                   const StatusMap& status_to_roll_cfg,
                   const std::string& dial_name,
                   int n_per_arg,
                   const std::string& coef_version,
                   const std::unordered_map<std::string, MacroVarConfig>& macro_cfg,
                   const std::string& severity_coef,
                   const std::string& lag_dist_path,
                   const std::string& manheim_path) {
    n_per = n_per_arg;

    status_to_roll = normalize_status_to_roll(status_to_roll_cfg);
    status_universe = derive_status_universe(status_to_roll);
    clean_status_dict = status_universe.clean_status_dict;
    prob_schema = build_prob_schema(status_to_roll, clean_status_dict);

    // Pre-compute transition layout per from-status (avoids inner-loop string/hash work)
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

    var_ctx.calendar_table = calendar_macro_table.empty() ? nullptr : &calendar_macro_table;
    var_ctx.fico_coupon_table = fico_coupon_table.empty() ? nullptr : &fico_coupon_table;

    var_registry = build_var_registry(active_macro_vars);

    // Partition model terms into static/dynamic for logit caching
    model_coef.classify_terms(var_registry.dynamic_var_names());

    // --- Two-part severity (recovery-rate GAM + recovery-lag dist) — config-gated ---
    if (!severity_coef.empty())
        load_severity(coef_dir, severity_coef, lag_dist_path, manheim_path);
}

static std::string bucket_of_lag(int L) {
    if (L <= 0) return "0";
    if (L == 1) return "1";
    if (L <= 3) return "2-3";
    if (L <= 6) return "4-6";
    return "7-12";
}

void DataMgr::load_severity(const std::string& coef_dir, const std::string& severity_coef,
                            const std::string& lag_dist_path, const std::string& manheim_path) {
    // 1. recovery-rate GAM -> model_coef under "SEV"
    std::string sev_path = coef_dir + "/" + severity_coef;
    if (fs::exists(sev_path)) {
        model_coef.read_model(sev_path, "SEV");
        has_severity = true;
    }
    // 2. recovery-lag distribution (platform<tab>lag_bucket<tab>prob)
    if (fs::exists(lag_dist_path)) {
        std::ifstream f(lag_dist_path);
        std::string line; std::getline(f, line);  // header
        std::unordered_map<std::string, std::vector<std::pair<std::string, double>>> rows;
        while (std::getline(f, line)) {
            size_t c1 = line.find('\t'), c2 = line.find('\t', c1 + 1);
            if (c1 == std::string::npos || c2 == std::string::npos) continue;
            std::string plat = line.substr(0, c1);
            std::string lab  = line.substr(c1 + 1, c2 - c1 - 1);
            double prob = std::stod(line.substr(c2 + 1));
            rows[plat].emplace_back(lab, prob);
        }
        for (auto& [plat, lst] : rows) {
            double cum = 0.0;
            for (auto& [lab, p] : lst) { cum += p; lag_cdf[plat].emplace_back(lab, cum); }
            for (auto& [lab, p] : lst) {
                if (lag_label_map.count(lab)) continue;
                if (lab == "never")      lag_label_map[lab] = {-1, ""};
                else if (lab == "13+")   lag_label_map[lab] = {13, "13+"};
                else { int L = std::stoi(lab); lag_label_map[lab] = {L, bucket_of_lag(L)}; }
            }
        }
    }
    // 3. Manheim used-vehicle index (DATE,MANHEIM) -> {year*12+month: value}, gap-filled forward
    if (fs::exists(manheim_path)) {
        std::ifstream f(manheim_path);
        std::string line; std::getline(f, line);  // header
        std::map<int, double> pts;
        while (std::getline(f, line)) {
            size_t c = line.find(',');
            if (c == std::string::npos) continue;
            std::string d = line.substr(0, c);
            int y = 0, m = 0;
            if (d.size() >= 7 && d[4] == '-') { y = std::stoi(d.substr(0, 4)); m = std::stoi(d.substr(5, 2)); }
            else { size_t s1 = d.find('/'), s2 = d.find('/', s1 + 1);  // M/D/YYYY
                   if (s1 == std::string::npos || s2 == std::string::npos) continue;
                   m = std::stoi(d.substr(0, s1)); y = std::stoi(d.substr(s2 + 1)); }
            pts[y * 12 + m] = std::stod(line.substr(c + 1));
        }
        if (!pts.empty()) {
            double last = pts.begin()->second;
            for (int ym = pts.begin()->first; ym <= pts.rbegin()->first; ++ym) {
                auto it = pts.find(ym); if (it != pts.end()) last = it->second;
                manheim[ym] = last;
            }
        }
    }
    std::cout << "  Severity: model=" << (has_severity ? "loaded" : "MISSING")
              << ", lag platforms=" << lag_cdf.size()
              << ", manheim months=" << manheim.size() << "\n";
}

}  // namespace rrm
