#pragma once

#include "types.h"
#include <string>
#include <unordered_map>
#include <vector>

namespace rrm {

struct DumpConfig {
    bool enabled = false;
    int max_loans = 10;
    int max_paths = 10;
    std::string output_dir;
};

struct DumpRow {
    int per = 0;
    std::string from_status;
    std::string to_status;
    std::unordered_map<std::string, double> features;       // loan numeric fields
    std::unordered_map<std::string, std::string> str_features;  // loan string fields
    std::unordered_map<std::string, double> probs;          // transition probs
    // ── cashflow fields (grouped at end of CSV) ──
    double note_rate = 0.0;   // note rate (copy for CF context)
    double pi_pmt    = 0.0;   // scheduled monthly P&I payment
    double num_pay   = 0.0;   // number of payments this period (from pmt matrix)
    double begin_bal = 0.0;
    double end_bal   = 0.0;
    double int_pmt   = 0.0;
    double prin_pmt  = 0.0;
    double loss      = 0.0;
};

struct DumpCollector {
    std::vector<DumpRow> rows;
};

struct DumpEntry {
    std::string loan_id;
    int path;
    DumpCollector collector;
};

/// Snapshot all numeric/string loan fields into a DumpRow.
void dump_snap_loan(DumpRow& row, const LoanDict& loan);

/// Write all dump entries to a single CSV file.
void dump_write_csv(const std::string& output_dir,
                    const std::vector<DumpEntry>& entries);

}  // namespace rrm
