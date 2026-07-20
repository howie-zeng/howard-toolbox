#include "dump.h"
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <set>

namespace fs = std::filesystem;

namespace rrm {

void dump_snap_loan(DumpRow& row, const LoanDict& loan) {
    for (const auto& [k, v] : loan) {
        if (k.empty() || k[0] == '_') continue;
        if (auto* d = std::get_if<double>(&v))      { row.features[k] = *d; }
        else if (auto* i = std::get_if<int>(&v))     { row.features[k] = static_cast<double>(*i); }
        else if (auto* s = std::get_if<std::string>(&v)) { row.str_features[k] = *s; }
    }
}

void dump_write_csv(const std::string& output_dir,
                    const std::vector<DumpEntry>& entries) {
    if (entries.empty()) return;

    // Discover all feature, string, and prob keys across ALL entries
    std::set<std::string> feat_set, str_feat_set, prob_set;
    for (const auto& entry : entries) {
        for (const auto& row : entry.collector.rows) {
            for (const auto& [k, _] : row.features)     feat_set.insert(k);
            for (const auto& [k, _] : row.str_features) str_feat_set.insert(k);
            for (const auto& [k, _] : row.probs)        prob_set.insert(k);
        }
    }

    std::vector<std::string> feat(feat_set.begin(), feat_set.end());
    std::vector<std::string> str_feat(str_feat_set.begin(), str_feat_set.end());
    std::vector<std::string> prob(prob_set.begin(), prob_set.end());

    // Column order: loan_id, path, _per, _from, _to, str features, num features, probs, cf cols
    std::vector<std::string> cols = {"loan_id", "path", "_per", "_from", "_to"};
    cols.insert(cols.end(), str_feat.begin(), str_feat.end());
    cols.insert(cols.end(), feat.begin(), feat.end());
    cols.insert(cols.end(), prob.begin(), prob.end());
    cols.push_back("_begin_bal");
    cols.push_back("_end_bal");
    cols.push_back("_note_rate");
    cols.push_back("_pi_pmt");
    cols.push_back("_num_pay");
    cols.push_back("_int_pmt");
    cols.push_back("_prin_pmt");
    cols.push_back("_loss");

    fs::create_directories(output_dir);
    std::string fpath = output_dir + "/dump.csv";
    std::ofstream f(fpath);
    if (!f.is_open()) return;

    f << std::setprecision(8);

    // Header
    for (size_t i = 0; i < cols.size(); ++i) {
        if (i > 0) f << ',';
        f << cols[i];
    }
    f << '\n';

    // Rows
    for (const auto& entry : entries) {
        for (const auto& row : entry.collector.rows) {
            for (size_t i = 0; i < cols.size(); ++i) {
                if (i > 0) f << ',';
                const auto& col = cols[i];

                if (col == "loan_id")         { f << entry.loan_id; }
                else if (col == "path")       { f << entry.path; }
                else if (col == "_per")       { f << row.per; }
                else if (col == "_from")      { f << row.from_status; }
                else if (col == "_to")        { f << row.to_status; }
                else if (col == "_note_rate") { f << row.note_rate; }
                else if (col == "_pi_pmt")    { f << row.pi_pmt; }
                else if (col == "_num_pay")   { f << row.num_pay; }
                else if (col == "_begin_bal") { f << row.begin_bal; }
                else if (col == "_end_bal")   { f << row.end_bal; }
                else if (col == "_int_pmt")   { f << row.int_pmt; }
                else if (col == "_prin_pmt")  { f << row.prin_pmt; }
                else if (col == "_loss")      { f << row.loss; }
                else {
                    auto sit = row.str_features.find(col);
                    if (sit != row.str_features.end()) { f << sit->second; continue; }
                    auto fit = row.features.find(col);
                    if (fit != row.features.end()) { f << fit->second; continue; }
                    auto pit = row.probs.find(col);
                    if (pit != row.probs.end()) { f << pit->second; continue; }
                }
            }
            f << '\n';
        }
    }
}

}  // namespace rrm
