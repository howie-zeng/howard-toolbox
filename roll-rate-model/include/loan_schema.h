#pragma once

#include "types.h"
#include <string>

namespace rrm {

/// Initialize time-varying state before simulation loop.
/// Parses r_dt into _start_year/_start_month, sets month/month_group/etc.
void init_time_varying(LoanDict& loan);

// --- Date/calendar helpers (used by VarRegistry update functions) ---
int  days_in_month(int year, int month);
void advance_month(int base_y, int base_m, int months, int& out_y, int& out_m);
std::string end_of_month_str(int y, int m);
void parse_year_month(const std::string& dt, int& y, int& m);

}  // namespace rrm
