#include "data_mgr.h"
#include "io/json_reader.h"
#include "loan_schema.h"
#include "var_registry.h"
#include "model/model_coef.h"
#include <iostream>
#include <iomanip>
#include <cmath>

using namespace rrm;

int main() {
    StatusMap str = {
        {"C",   {"C","D1M","D2M","D3M","D4M","PIF","LIQ"}},
        {"D1M", {"D1M","C","D2M","D3M","D4M","PIF","LIQ"}},
        {"D2M", {"D2M","C","D1M","D3M","D4M","PIF","LIQ"}},
        {"D3M", {"D3M","C","D1M","D2M","D4M","PIF","LIQ"}},
        {"D4M", {"D4M","C","D1M","D2M","D3M","PIF","LIQ"}},
    };

    DataMgr dm;
    dm.init("input", str, "", 84);

    auto loans = io::read_loan_json("input/par_2026_1/loans_prepped.json");

    std::cout << std::fixed << std::setprecision(6);

    // Test indices covering all terms: 60, 36, 48, 24
    int indices[] = {0, 6, 21, 82, 1, 100, 1000, 5000, 10000, 15000};
    for (int idx : indices) {
        if (idx >= static_cast<int>(loans.size())) continue;
        auto loan = loans[idx];
        init_time_varying(loan);

        double d1m = dm.model_coef.calc(loan, "C", "D1M");
        double pif = dm.model_coef.calc(loan, "C", "PIF");

        std::string lid = "?";
        auto it = loan.find("loan_id");
        if (it != loan.end()) {
            if (auto* i = std::get_if<int>(&it->second)) lid = std::to_string(*i);
            else if (auto* s = std::get_if<std::string>(&it->second)) lid = *s;
        }

        auto mg_it = loan.find("month_group");
        std::string mg = mg_it != loan.end() ? get_string(loan, "month_group") : "MISSING";
        int dte = static_cast<int>(get_numeric(loan, "days_to_month_end"));
        int term = get_int(loan, "term");
        std::string oterm_f = "?";
        auto ot_it = loan.find("oterm_f");
        if (ot_it != loan.end()) {
            if (auto* s = std::get_if<std::string>(&ot_it->second)) oterm_f = *s;
            else if (auto* i = std::get_if<int>(&ot_it->second)) oterm_f = std::to_string(*i);
        }

        std::cout << "loan[" << idx << "] id=" << lid
                  << " term=" << term
                  << " oterm_f=" << oterm_f
                  << " D1M=" << d1m
                  << " PIF=" << pif
                  << " age_pct=" << get_numeric(loan, "age_pct")
                  << " month=" << get_string(loan, "month")
                  << " mg=" << mg
                  << " dte=" << dte << std::endl;
    }

    return 0;
}
