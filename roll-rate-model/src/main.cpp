#include "data_mgr.h"
#include "dump.h"
#include "io/json_reader.h"
#include "runners/cf_parallel.h"
#include "types.h"

#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

#ifdef _OPENMP
#include <omp.h>
#endif

namespace fs = std::filesystem;

// ─── Minimal JSON config parser ──────────────────────────────────────────
// Parses the config file to extract:
//   - string/int/double scalars
//   - status_to_roll: { "C": ["C","D1M",...], ... }
//   - terminal_statuses: ["PIF","LIQ"]

namespace {

struct ConfigParser {
    const std::string& src;
    size_t pos = 0;

    char peek() const { return pos < src.size() ? src[pos] : '\0'; }
    char next() { return pos < src.size() ? src[pos++] : '\0'; }

    void skip_ws() {
        while (pos < src.size()) {
            char c = src[pos];
            if (c == ' ' || c == '\t' || c == '\n' || c == '\r') { ++pos; continue; }
            // skip // comments
            if (c == '/' && pos + 1 < src.size() && src[pos + 1] == '/') {
                while (pos < src.size() && src[pos] != '\n') ++pos;
                continue;
            }
            break;
        }
    }

    std::string parse_string() {
        if (next() != '"') throw std::runtime_error("expected '\"'");
        std::string out;
        while (pos < src.size()) {
            char c = next();
            if (c == '"') return out;
            if (c == '\\') {
                char esc = next();
                if (esc == '"') out += '"';
                else if (esc == '\\') out += '\\';
                else if (esc == 'n') out += '\n';
                else out += esc;
            } else {
                out += c;
            }
        }
        throw std::runtime_error("unterminated string");
    }

    std::vector<std::string> parse_string_array() {
        skip_ws();
        if (next() != '[') throw std::runtime_error("expected '['");
        std::vector<std::string> arr;
        skip_ws();
        if (peek() == ']') { ++pos; return arr; }
        while (true) {
            skip_ws();
            arr.push_back(parse_string());
            skip_ws();
            char sep = next();
            if (sep == ']') break;
            if (sep != ',') throw std::runtime_error("expected ',' or ']'");
        }
        return arr;
    }

    // Skip any JSON value (string, number, object, array, bool, null)
    void skip_value() {
        skip_ws();
        char c = peek();
        if (c == '"') { parse_string(); return; }
        if (c == '{') { skip_object(); return; }
        if (c == '[') { skip_array(); return; }
        // number, bool, null
        while (pos < src.size()) {
            char ch = src[pos];
            if (ch == ',' || ch == '}' || ch == ']' || ch == ' ' || ch == '\n' || ch == '\r' || ch == '\t')
                break;
            ++pos;
        }
    }

    void skip_object() {
        if (next() != '{') throw std::runtime_error("expected '{'");
        skip_ws();
        if (peek() == '}') { ++pos; return; }
        while (true) {
            skip_ws(); parse_string(); // key
            skip_ws(); if (next() != ':') throw std::runtime_error("expected ':'");
            skip_value();
            skip_ws();
            char sep = next();
            if (sep == '}') break;
            if (sep != ',') throw std::runtime_error("expected ',' or '}'");
        }
    }

    void skip_array() {
        if (next() != '[') throw std::runtime_error("expected '['");
        skip_ws();
        if (peek() == ']') { ++pos; return; }
        while (true) {
            skip_value();
            skip_ws();
            char sep = next();
            if (sep == ']') break;
            if (sep != ',') throw std::runtime_error("expected ',' or ']'");
        }
    }

    // Parse status_to_roll: { "C": ["C","D1M",...], ... }
    rrm::StatusMap parse_status_map() {
        skip_ws();
        if (next() != '{') throw std::runtime_error("expected '{'");
        rrm::StatusMap result;
        skip_ws();
        if (peek() == '}') { ++pos; return result; }
        while (true) {
            skip_ws();
            std::string key = parse_string();
            skip_ws();
            if (next() != ':') throw std::runtime_error("expected ':'");
            result[key] = parse_string_array();
            skip_ws();
            char sep = next();
            if (sep == '}') break;
            if (sep != ',') throw std::runtime_error("expected ',' or '}'");
        }
        return result;
    }

    // Parse a number (int or double)
    double parse_number() {
        skip_ws();
        std::string num;
        while (pos < src.size()) {
            char ch = peek();
            if (std::isdigit(static_cast<unsigned char>(ch)) || ch == '.' ||
                ch == '-' || ch == '+' || ch == 'e' || ch == 'E') {
                num += next();
            } else break;
        }
        return std::stod(num);
    }
};

struct Config {
    std::string deal_name = "default";
    std::string input_dir = "input";
    std::string scenario = "base";
    std::string coef_version;
    rrm::StatusMap status_to_roll;
    std::vector<std::string> group_by = {"term", "grade"};
    int n_per = 360;
    int dup = 1;
    int seed = 42;
    int workers = 0;
    double liq_severity = 0.60;
    std::string dial_name;
    std::string loans_path;
    std::string output_path;
    std::unordered_map<std::string, rrm::MacroVarConfig> macro_vars;
    rrm::DumpConfig dump;
};

Config parse_config(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) throw std::runtime_error("cannot open config: " + path);
    std::ostringstream ss;
    ss << f.rdbuf();
    std::string content = ss.str();

    Config cfg;
    ConfigParser p{content};
    p.skip_ws();
    if (p.next() != '{') throw std::runtime_error("config must be a JSON object");

    while (true) {
        p.skip_ws();
        if (p.peek() == '}') { ++p.pos; break; }
        std::string key = p.parse_string();
        p.skip_ws();
        if (p.next() != ':') throw std::runtime_error("expected ':'");
        p.skip_ws();

        if (key == "deal_name") {
            cfg.deal_name = p.parse_string();
        } else if (key == "input_dir") {
            cfg.input_dir = p.parse_string();
        } else if (key == "scenario") {
            cfg.scenario = p.parse_string();
        } else if (key == "coef_version") {
            cfg.coef_version = p.parse_string();
        } else if (key == "status_to_roll") {
            cfg.status_to_roll = p.parse_status_map();
        } else if (key == "group_by") {
            cfg.group_by = p.parse_string_array();
        } else if (key == "n_per") {
            cfg.n_per = static_cast<int>(p.parse_number());
        } else if (key == "dup") {
            cfg.dup = static_cast<int>(p.parse_number());
        } else if (key == "seed") {
            cfg.seed = static_cast<int>(p.parse_number());
        } else if (key == "workers") {
            cfg.workers = static_cast<int>(p.parse_number());
        } else if (key == "liq_severity") {
            cfg.liq_severity = p.parse_number();
        } else if (key == "dial_name") {
            cfg.dial_name = p.parse_string();
        } else if (key == "prepped_loans_path") {
            cfg.loans_path = p.parse_string();
        } else if (key == "output_path") {
            cfg.output_path = p.parse_string();
        } else if (key == "macro") {
            // Parse: { "var_name": {"mode": "...", "path": "..."}, ... }
            p.skip_ws();
            if (p.next() != '{') throw std::runtime_error("macro must be an object");
            while (true) {
                p.skip_ws();
                if (p.peek() == '}') { ++p.pos; break; }
                std::string var_name = p.parse_string();
                p.skip_ws();
                if (p.next() != ':') throw std::runtime_error("expected ':'");
                p.skip_ws();
                // Parse the per-variable config object
                rrm::MacroVarConfig vcfg;
                if (p.next() != '{') throw std::runtime_error("macro var config must be an object");
                while (true) {
                    p.skip_ws();
                    if (p.peek() == '}') { ++p.pos; break; }
                    std::string vk = p.parse_string();
                    p.skip_ws();
                    if (p.next() != ':') throw std::runtime_error("expected ':'");
                    p.skip_ws();
                    if (vk == "mode") vcfg.mode = p.parse_string();
                    else if (vk == "path") vcfg.path = p.parse_string();
                    else if (vk == "key_columns") vcfg.key_columns = p.parse_string_array();
                    else p.skip_value();
                    p.skip_ws();
                    if (p.peek() == ',') ++p.pos;
                }
                cfg.macro_vars[var_name] = std::move(vcfg);
                p.skip_ws();
                if (p.peek() == ',') ++p.pos;
            }
        } else if (key == "dump") {
            // Parse nested dump object: { "enabled": true, "max_loans": 10, ... }
            p.skip_ws();
            if (p.next() != '{') throw std::runtime_error("dump must be an object");
            while (true) {
                p.skip_ws();
                if (p.peek() == '}') { ++p.pos; break; }
                std::string dk = p.parse_string();
                p.skip_ws();
                if (p.next() != ':') throw std::runtime_error("expected ':'");
                p.skip_ws();
                if (dk == "enabled") {
                    // Parse bool: true/false
                    std::string bval;
                    while (p.pos < p.src.size() && std::isalpha(static_cast<unsigned char>(p.peek())))
                        bval += p.next();
                    cfg.dump.enabled = (bval == "true");
                } else if (dk == "max_loans") {
                    cfg.dump.max_loans = static_cast<int>(p.parse_number());
                } else if (dk == "max_paths") {
                    cfg.dump.max_paths = static_cast<int>(p.parse_number());
                } else if (dk == "output_dir") {
                    cfg.dump.output_dir = p.parse_string();
                } else {
                    p.skip_value();
                }
                p.skip_ws();
                if (p.peek() == ',') ++p.pos;
            }
        } else {
            p.skip_value();
        }

        p.skip_ws();
        if (p.peek() == ',') ++p.pos;
    }

    return cfg;
}

}  // namespace

// ─── CSV output ──────────────────────────────────────────────────────────

static void write_cf_csv(const std::vector<std::vector<double>>& cf_sum,
                         const std::string& path) {
    fs::create_directories(fs::path(path).parent_path());
    std::ofstream f(path);
    if (!f.is_open()) throw std::runtime_error("cannot open output: " + path);

    // header
    f << "period";
    for (int c = 0; c < rrm::CF_COL_LEN; ++c) {
        f << ',' << rrm::CF_COL[c];
    }
    f << '\n';

    // rows
    for (int r = 0; r < (int)cf_sum.size(); ++r) {
        f << (r + 1);
        for (int c = 0; c < rrm::CF_COL_LEN; ++c) {
            f << ',' << cf_sum[r][c];
        }
        f << '\n';
    }
}

// ─── Metrics computation ─────────────────────────────────────────────────

struct MetricRow {
    int period;
    double cpr, cdr, cgl;
    double begin_bal, pif_bal, liq_bal, loss, cum_loss;
    double dq30_bal, dq60_bal, dq90_bal, dq120_bal;
};

static std::vector<MetricRow> compute_metrics(
    const std::vector<std::vector<double>>& cf, double orig_bal) {

    rrm::CfIndices ci = rrm::extract_cf_indices(rrm::CF_DICT);
    int i_pif_bal = rrm::CF_DICT.at("pif_bal");
    int i_liq_bal = rrm::CF_DICT.at("liq_bal");
    int i_loss    = rrm::CF_DICT.at("loss");
    int i_dq30    = rrm::CF_DICT.at("dq30_bal");
    int i_dq60    = rrm::CF_DICT.at("dq60_bal");
    int i_dq90    = rrm::CF_DICT.at("dq90_bal");
    int i_dq120   = rrm::CF_DICT.at("dq120_bal");

    double cum_loss = 0.0;
    std::vector<MetricRow> out;

    for (int p = 0; p < static_cast<int>(cf.size()); ++p) {
        const auto& row = cf[p];
        double bb = row[ci.begin_bal];
        double sp = row[ci.sch_prin];
        double pif_bal = row[i_pif_bal];
        double liq_bal = row[i_liq_bal];
        double loss = row[i_loss];
        cum_loss += loss;

        double denom = bb - sp;
        double smm_pre = (denom > 0.1) ? std::min(pif_bal / denom, 1.0) : 0.0;
        double cpr = 1.0 - std::pow(1.0 - smm_pre, 12.0);

        double smm_def = (bb > 0.1) ? liq_bal / bb : 0.0;
        double cdr = 1.0 - std::pow(1.0 - smm_def, 12.0);

        double cgl = (orig_bal > 0) ? cum_loss / orig_bal : 0.0;

        MetricRow mr;
        mr.period = p + 1;
        mr.cpr = cpr; mr.cdr = cdr; mr.cgl = cgl;
        mr.begin_bal = bb; mr.pif_bal = pif_bal; mr.liq_bal = liq_bal;
        mr.loss = loss; mr.cum_loss = cum_loss;
        mr.dq30_bal = row[i_dq30]; mr.dq60_bal = row[i_dq60];
        mr.dq90_bal = row[i_dq90]; mr.dq120_bal = row[i_dq120];
        out.push_back(mr);
    }
    return out;
}

static void write_metrics_portfolio_csv(
    const std::vector<MetricRow>& metrics, const std::string& path) {

    fs::create_directories(fs::path(path).parent_path());
    std::ofstream f(path);
    if (!f.is_open()) throw std::runtime_error("cannot open output: " + path);

    f << std::fixed;
    f << "period,cpr,cdr,cgl,begin_bal,pif_bal,liq_bal,loss,cum_loss\n";
    for (const auto& m : metrics) {
        if (m.begin_bal < 0.01 && m.cpr == 0 && m.cdr == 0) continue;
        f << m.period << ','
          << std::setprecision(6) << m.cpr << ','
          << m.cdr << ',' << m.cgl << ','
          << std::setprecision(2) << m.begin_bal << ','
          << m.pif_bal << ',' << m.liq_bal << ','
          << m.loss << ',' << m.cum_loss << '\n';
    }
}

// Parse "term=60|grade=PP-A" into map
static std::unordered_map<std::string, std::string> parse_group_key(const std::string& key) {
    std::unordered_map<std::string, std::string> result;
    std::istringstream iss(key);
    std::string part;
    while (std::getline(iss, part, '|')) {
        auto eq = part.find('=');
        if (eq != std::string::npos) {
            result[part.substr(0, eq)] = part.substr(eq + 1);
        }
    }
    return result;
}

static void write_metrics_grouped_csv(
    const rrm::runners::GroupedBatchResult& gr,
    const std::vector<std::string>& group_by,
    const std::string& path) {

    fs::create_directories(fs::path(path).parent_path());
    std::ofstream f(path);
    if (!f.is_open()) throw std::runtime_error("cannot open output: " + path);

    f << std::fixed;

    // header
    for (const auto& g : group_by) f << g << ',';
    f << "loan_age,cpr,cdr,cgl,begin_bal,pif_bal,liq_bal,loss,cum_loss,"
      << "dq30_bal,dq60_bal,dq90_bal,dq120_bal";
    for (const auto& pk : gr.prob_keys) f << ',' << pk;
    f << '\n';

    // Collect and sort group keys
    std::vector<std::string> keys;
    for (const auto& [k, _] : gr.group_cf) keys.push_back(k);
    std::sort(keys.begin(), keys.end());

    int max_age = gr.max_age;

    for (const auto& key : keys) {
        const auto& cf = gr.group_cf.at(key);
        double orig_bal = gr.group_orig_bal.at(key);
        auto parts = parse_group_key(key);

        auto metrics = compute_metrics(cf, orig_bal);

        const auto* pw_ptr = gr.group_prob_weighted.count(key)
            ? &gr.group_prob_weighted.at(key) : nullptr;
        const auto* pb_ptr = gr.group_prob_bal_total.count(key)
            ? &gr.group_prob_bal_total.at(key) : nullptr;

        // Helper: write prob columns for a given age index
        int n_cols = gr.n_prob_cols;
        auto write_probs = [&](int age_idx) {
            for (int c = 0; c < n_cols; ++c) {
                double val = 0.0;
                if (pw_ptr && pb_ptr && age_idx >= 0
                    && age_idx < static_cast<int>(pb_ptr->size())) {
                    double bal = (*pb_ptr)[age_idx];
                    if (bal > 0) {
                        int flat_idx = age_idx * n_cols + c;
                        if (flat_idx < static_cast<int>(pw_ptr->size()))
                            val = (*pw_ptr)[flat_idx] / bal;
                    }
                }
                f << ',' << std::setprecision(6) << val;
            }
        };

        // Probs at age A predict the transition observed at age A+1.
        // Financials at age A reflect what was observed at age A.
        // cf_array[A] holds cashflows from the transition at age A,
        // whose outcome is observed at age A+1.
        //
        // So: row for loan_age N:
        //   financials = metrics from cf_array[N-1]  (transition at N-1, observed at N)
        //   probs      = prob_array[N]               (predicting outcome at N+1)
        //
        // Row for the minimum starting age: probs only (nothing observed yet).

        // Emit rows by walking loan_age from 0 to max_age.
        // metrics[i] corresponds to cf_array[i], labeled period = i+1.
        // So metrics[i] financials belong to loan_age = i+1.

        // Track which ages have probs (to find starting age for probs-only row)
        bool emitted_first = false;
        double cum_loss_adj = 0.0;

        for (int age = 0; age < max_age; ++age) {
            // Check if this age has probs or is a financial row
            bool has_probs = pw_ptr && pb_ptr
                && age < static_cast<int>(pb_ptr->size())
                && (*pb_ptr)[age] > 0.0;
            // Financial data for this age comes from metrics[age-1]
            bool has_financials = (age >= 1)
                && (age - 1) < static_cast<int>(metrics.size())
                && (metrics[age - 1].begin_bal > 0.01
                    || metrics[age - 1].cpr > 0
                    || metrics[age - 1].cdr > 0);

            if (!has_probs && !has_financials) continue;

            for (const auto& g : group_by) f << parts[g] << ',';
            f << age << ',';

            if (has_financials) {
                const auto& m = metrics[age - 1];
                f << std::setprecision(6) << m.cpr << ',' << m.cdr << ',' << m.cgl << ','
                  << std::setprecision(2) << m.begin_bal << ','
                  << m.pif_bal << ',' << m.liq_bal << ','
                  << m.loss << ',' << m.cum_loss << ','
                  << m.dq30_bal << ',' << m.dq60_bal << ','
                  << m.dq90_bal << ',' << m.dq120_bal;
            } else {
                f << ",,,,,,,,,,,";  // 12 empty financial columns
            }

            write_probs(age);
            f << '\n';
        }
    }
}


static void write_metrics_grouped_period_csv(
    const rrm::runners::GroupedBatchResult& gr,
    const std::vector<std::string>& group_by,
    int n_per,
    const std::string& path) {

    fs::create_directories(fs::path(path).parent_path());
    std::ofstream f(path);
    if (!f.is_open()) throw std::runtime_error("cannot open output: " + path);

    f << std::fixed;

    // header
    for (const auto& g : group_by) f << g << ',';
    f << "period,cpr,cdr,cgl,begin_bal,pif_bal,liq_bal,loss,cum_loss,"
      << "dq30_bal,dq60_bal,dq90_bal,dq120_bal";
    for (const auto& pk : gr.prob_keys) f << ',' << pk;
    f << '\n';

    // Collect and sort group keys
    std::vector<std::string> keys;
    for (const auto& [k, _] : gr.group_cf_period) keys.push_back(k);
    std::sort(keys.begin(), keys.end());

    int n_cols = gr.n_prob_cols;

    for (const auto& key : keys) {
        const auto& cf = gr.group_cf_period.at(key);
        double orig_bal = gr.group_orig_bal.at(key);
        auto parts = parse_group_key(key);

        auto metrics = compute_metrics(cf, orig_bal);

        const auto* pw_ptr = gr.group_prob_weighted_period.count(key)
            ? &gr.group_prob_weighted_period.at(key) : nullptr;
        const auto* pb_ptr = gr.group_prob_bal_total_period.count(key)
            ? &gr.group_prob_bal_total_period.at(key) : nullptr;

        auto write_probs = [&](int per_idx) {
            for (int c = 0; c < n_cols; ++c) {
                double val = 0.0;
                if (pw_ptr && pb_ptr && per_idx >= 0
                    && per_idx < static_cast<int>(pb_ptr->size())) {
                    double bal = (*pb_ptr)[per_idx];
                    if (bal > 0) {
                        int flat_idx = per_idx * n_cols + c;
                        if (flat_idx < static_cast<int>(pw_ptr->size()))
                            val = (*pw_ptr)[flat_idx] / bal;
                    }
                }
                f << ',' << std::setprecision(6) << val;
            }
        };

        for (int p = 0; p < static_cast<int>(metrics.size()); ++p) {
            const auto& m = metrics[p];
            if (m.begin_bal < 0.01 && m.cpr == 0 && m.cdr == 0) continue;

            for (const auto& g : group_by) f << parts[g] << ',';
            f << (p + 1) << ',';
            f << std::setprecision(6) << m.cpr << ',' << m.cdr << ',' << m.cgl << ','
              << std::setprecision(2) << m.begin_bal << ','
              << m.pif_bal << ',' << m.liq_bal << ','
              << m.loss << ',' << m.cum_loss << ','
              << m.dq30_bal << ',' << m.dq60_bal << ','
              << m.dq90_bal << ',' << m.dq120_bal;

            write_probs(p);
            f << '\n';
        }
    }
}

// ─── CLI ─────────────────────────────────────────────────────────────────

static void print_usage() {
    std::cerr << "Usage: sim_main --config <config.json> [options]\n"
              << "  --config <path>        Config file (required)\n"
              << "  --output <path>        Output CSV path\n"
              << "  --deal-name <name>     Override deal_name\n"
              << "  --coef-version <name>  Override coef_version\n"
              << "  --group-by <a,b,c>     Override group_by (comma-separated)\n"
              << "  --dial-name <name>     Override dial_name\n"
              << "  --scen <name>          Scenario name (default: 'base')\n"
              << "  --n-per  <int>         Periods per loan\n"
              << "  --dup    <int>         Monte Carlo paths per loan\n"
              << "  --seed   <int>         Base random seed\n"
              << "  --workers <int>        Thread count\n"
              << "  --dump <loans> <paths> Enable dump (max loans, max paths)\n";
}

int main(int argc, char* argv[]) {
    std::string config_path;
    std::string output_override;
    std::string deal_name_override;
    std::string coef_version_override;
    std::string group_by_override;
    std::string dial_name_override;
    std::string scen_override;
    int n_per_override = -1;
    int dup_override = -1;
    int seed_override = -1;
    int workers_override = -1;
    int dump_loans = -1, dump_paths = -1;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--config" && i + 1 < argc) { config_path = argv[++i]; }
        else if (arg == "--output" && i + 1 < argc) { output_override = argv[++i]; }
        else if (arg == "--deal-name" && i + 1 < argc) { deal_name_override = argv[++i]; }
        else if (arg == "--coef-version" && i + 1 < argc) { coef_version_override = argv[++i]; }
        else if (arg == "--group-by" && i + 1 < argc) { group_by_override = argv[++i]; }
        else if (arg == "--dial-name" && i + 1 < argc) { dial_name_override = argv[++i]; }
        else if (arg == "--scen" && i + 1 < argc) { scen_override = argv[++i]; }
        else if (arg == "--n-per" && i + 1 < argc) { n_per_override = std::atoi(argv[++i]); }
        else if (arg == "--dup" && i + 1 < argc) { dup_override = std::atoi(argv[++i]); }
        else if (arg == "--seed" && i + 1 < argc) { seed_override = std::atoi(argv[++i]); }
        else if (arg == "--workers" && i + 1 < argc) { workers_override = std::atoi(argv[++i]); }
        else if (arg == "--dump" && i + 2 < argc) {
            dump_loans = std::atoi(argv[++i]);
            dump_paths = std::atoi(argv[++i]);
        }
        else if (arg == "--help" || arg == "-h") { print_usage(); return 0; }
    }

    if (config_path.empty()) {
        std::cerr << "Error: --config is required\n";
        print_usage();
        return 1;
    }

    try {
        // Parse config
        Config cfg = parse_config(config_path);

        // Apply CLI overrides
        if (!deal_name_override.empty()) cfg.deal_name = deal_name_override;
        if (!coef_version_override.empty()) cfg.coef_version = coef_version_override;
        if (!dial_name_override.empty()) cfg.dial_name = dial_name_override;
        if (!group_by_override.empty()) {
            cfg.group_by.clear();
            std::istringstream ss(group_by_override);
            std::string token;
            while (std::getline(ss, token, ',')) {
                if (!token.empty()) cfg.group_by.push_back(token);
            }
        }
        std::string scenario = !scen_override.empty() ? scen_override : cfg.scenario;
        if (n_per_override > 0) cfg.n_per = n_per_override;
        if (dup_override > 0)   cfg.dup = dup_override;
        if (seed_override >= 0) cfg.seed = seed_override;
        if (workers_override > 0) cfg.workers = workers_override;
        if (dump_loans >= 0) {
            cfg.dump.enabled = true;
            cfg.dump.max_loans = dump_loans;
            cfg.dump.max_paths = dump_paths;
        }
        if (cfg.dump.enabled && cfg.dump.output_dir.empty())
            cfg.dump.output_dir = "output/" + cfg.deal_name + "/" + scenario + "/dump";

        // Default workers = all CPU cores
        if (cfg.workers <= 0) {
#ifdef _OPENMP
            cfg.workers = std::max(1, omp_get_num_procs());
#else
            cfg.workers = 1;
#endif
        }

        // Resolve paths
        std::string deal_dir = cfg.input_dir + "/deals/" + cfg.deal_name;
        if (cfg.loans_path.empty())
            cfg.loans_path = deal_dir + "/loans_prepped.json";
        if (!output_override.empty())
            cfg.output_path = output_override;
        if (cfg.output_path.empty())
            cfg.output_path = "output/" + cfg.deal_name + "/" + scenario + "/sim_results.csv";

        if (cfg.status_to_roll.empty()) {
            throw std::runtime_error("status_to_roll missing or empty in config");
        }

        // Init data manager
        std::cout << "Initializing data manager (input_dir=" << cfg.input_dir << ")...\n";
        rrm::DataMgr dm;
        dm.init(cfg.input_dir, cfg.status_to_roll, cfg.dial_name, cfg.n_per, cfg.coef_version, cfg.macro_vars);
        dm.liq_severity = cfg.liq_severity;

        // Print loaded models
        std::vector<std::string> expected_models;
        for (const auto& [from, tos] : cfg.status_to_roll) {
            for (const auto& to : tos) {
                if (to != from) {
                    std::string name = rrm::model::get_model_name(from, to);
                    bool ok = dm.model_coef.has_model(name);
                    expected_models.push_back(name + (ok ? " [OK]" : " [MISSING]"));
                }
            }
        }
        std::sort(expected_models.begin(), expected_models.end());
        std::cout << "  Models:\n";
        for (const auto& m : expected_models)
            std::cout << "    " << m << "\n";

        // Load loans
        std::cout << "Loading loans from " << cfg.loans_path << "...\n";
        auto loans = rrm::io::read_loan_json(cfg.loans_path);
        std::cout << "  " << loans.size() << " loans loaded\n";

        // Run simulation (grouped)
        const auto& group_by = cfg.group_by;
        int total_tasks = static_cast<int>(loans.size()) * cfg.dup;
        std::cout << "Running simulation: n_per=" << cfg.n_per
                  << ", dup=" << cfg.dup
                  << ", seed=" << cfg.seed
                  << ", workers=" << cfg.workers
                  << " (" << total_tasks << " tasks)\n";

        auto t0 = std::chrono::high_resolution_clock::now();

        auto gr = rrm::runners::run_batch_grouped(
            loans, dm, cfg.n_per, cfg.dup, cfg.workers,
            static_cast<uint32_t>(cfg.seed), cfg.dial_name, group_by,
            cfg.dump);

        auto t1 = std::chrono::high_resolution_clock::now();
        double elapsed = std::chrono::duration<double>(t1 - t0).count();

        auto& result = gr.portfolio;
        std::cout << "  Done in " << elapsed << "s"
                  << " (" << result.n_done << " done, "
                  << result.n_error << " errors)\n";

        if (!result.errors.empty()) {
            std::cout << "  Errors (" << result.errors.size() << " total):\n";
            int show = std::min(5, static_cast<int>(result.errors.size()));
            for (int i = 0; i < show; ++i)
                std::cout << "    " << result.errors[i] << "\n";
        }

        // Derive output directory from output_path
        std::string out_dir = fs::path(cfg.output_path).parent_path().string();
        if (out_dir.empty()) out_dir = ".";

        // Write raw CF (Portfolio sheet)
        write_cf_csv(result.cf_sum, cfg.output_path);
        std::cout << "  Portfolio: " << cfg.output_path << "\n";

        // Compute metrics
        auto port_metrics = compute_metrics(result.cf_sum, gr.total_orig_bal);

        // Write Metrics_Portfolio
        std::string port_path = out_dir + "/metrics_portfolio.csv";
        write_metrics_portfolio_csv(port_metrics, port_path);
        std::cout << "  Metrics_Portfolio: " << port_path
                  << " (" << gr.group_cf.size() << " groups)\n";

        // Write Metrics_Grouped (age-indexed)
        std::string grp_path = out_dir + "/metrics_grouped.csv";
        write_metrics_grouped_csv(gr, group_by, grp_path);
        std::cout << "  Metrics_Grouped: " << grp_path << "\n";

        // Write Metrics_Grouped_Period (period-indexed)
        std::string grp_per_path = out_dir + "/metrics_grouped_period.csv";
        write_metrics_grouped_period_csv(gr, group_by, cfg.n_per, grp_per_path);
        std::cout << "  Metrics_Grouped_Period: " << grp_per_path << "\n";

        // Consolidate CSVs into single XLSX
        std::string xlsx_path = out_dir + "/sim_results.xlsx";
        std::string py_cmd = "python tools/csvs_to_xlsx.py \"" + out_dir + "\" \"" + xlsx_path + "\"";
        std::cout << "Consolidating to XLSX...\n";
        int rc = std::system(py_cmd.c_str());
        if (rc != 0) {
            std::cout << "  (XLSX consolidation skipped — python not available)\n";
        }

        return 0;

    } catch (const std::exception& e) {
        std::cerr << "FATAL: " << e.what() << "\n";
        return 1;
    }
}
