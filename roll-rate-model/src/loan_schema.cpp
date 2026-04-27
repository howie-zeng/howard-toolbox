#include "loan_schema.h"
#include <stdexcept>
#include <string>

namespace rrm {

static const char* MONTH_NAMES[] = {
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
};

int days_in_month(int year, int month) {
    static const int dm[] = {0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    if (month == 2 && (year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)))
        return 29;
    return dm[month];
}

void advance_month(int base_y, int base_m, int months,
                   int& out_y, int& out_m) {
    int total = base_y * 12 + (base_m - 1) + months;
    out_y = total / 12;
    out_m = total % 12 + 1;
}

std::string end_of_month_str(int y, int m) {
    int d = days_in_month(y, m);
    char buf[16];
    std::snprintf(buf, sizeof(buf), "%04d-%02d-%02d", y, m, d);
    return buf;
}

void parse_year_month(const std::string& dt, int& y, int& m) {
    if (dt.size() < 7)
        throw std::runtime_error("invalid date for r_dt: " + dt);
    // Detect format by position of separator
    if (dt[4] == '-') {
        // YYYY-MM-DD or YYYY-MM
        y = std::stoi(dt.substr(0, 4));
        m = std::stoi(dt.substr(5, 2));
    } else if (dt.find('/') != std::string::npos) {
        // MM/DD/YYYY
        auto p1 = dt.find('/');
        auto p2 = dt.find('/', p1 + 1);
        if (p2 == std::string::npos)
            throw std::runtime_error("invalid date for r_dt: " + dt);
        m = std::stoi(dt.substr(0, p1));
        y = std::stoi(dt.substr(p2 + 1));
    } else {
        throw std::runtime_error("unrecognized date format for r_dt: " + dt);
    }
}


// ─── Time-varying state ──────────────────────────────────────────────────

void init_time_varying(LoanDict& loan) {
    // Parse r_dt into _start_year, _start_month
    auto it = loan.find("r_dt");
    if (it == loan.end())
        throw std::runtime_error("r_dt missing — cannot init time-varying state");
    std::string r_dt = get_string(loan, "r_dt");
    int sy, sm;
    parse_year_month(r_dt, sy, sm);
    set_val(loan, "_start_year", sy);
    set_val(loan, "_start_month", sm);

    // Initialize time-varying fields at period -1 (pre-sim state)
    int term = get_int(loan, "term");
    int loan_age = get_int(loan, "loan_age");
    double age_pct = (term > 0) ? static_cast<double>(loan_age) / term : 0.0;
    set_val(loan, "age", loan_age);
    set_val(loan, "age_pct", age_pct);
    set_val(loan, "c_age_pct", age_pct);
    set_val(loan, "age_fc", age_pct);

    // month, days_to_month_end, month_group from r_dt
    set_val(loan, "month", std::string(MONTH_NAMES[sm - 1]));
    int pmt_day = 15;
    {
        auto pmt_it = loan.find("pmt_day");
        if (pmt_it != loan.end()) pmt_day = static_cast<int>(get_numeric(loan, "pmt_day"));
    }
    int dim = days_in_month(sy, sm);
    int dte = dim - std::min(pmt_day, dim);
    set_val(loan, "days_to_month_end", dte);
    set_val(loan, "month_group", std::string(dte <= 28 ? "30_Day" : "31_Day"));
}

}  // namespace rrm
