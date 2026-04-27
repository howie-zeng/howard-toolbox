#pragma once

#include "types.h"
#include "io/tsv_reader.h"
#include <cmath>
#include <map>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <variant>
#include <vector>

namespace rrm::model {

struct Lookup1dInfo {
    std::vector<std::pair<std::string, double>> levels;  // linear scan; typically 2-12 entries
};

struct Smooth1dInfo {
    double xmin, xmax;
    double step_inv;   // 1 / step — pre-computed for fast interpolation
    int    xn;         // number of intervals (points - 1)
    std::vector<double> lookup;
};

struct Lookup2dInfo {
    std::map<std::pair<std::string, std::string>, double> lookup;
};

struct SmoothByNumInfo {
    Smooth1dInfo smooth;
    double wmin = 0.0, wmax = 1.0;
};

struct SmoothByFctInfo {
    std::unordered_map<std::string, Smooth1dInfo> smooth_dict;
};

struct Smooth2dInfo {
    double xmin, xmax, xstep_inv;
    int    xn;
    double ymin, ymax, ystep_inv;
    int    yn;
    std::vector<std::vector<double>> lookup;
};

using CoefTerm = std::variant<
    double,
    Lookup1dInfo, Smooth1dInfo,
    Lookup2dInfo, SmoothByNumInfo, SmoothByFctInfo, Smooth2dInfo>;

using ModelFormula = std::unordered_map<std::string, CoefTerm>;
using ModelFormula2D = std::map<std::pair<std::string, std::string>, CoefTerm>;

using LogitCache = std::unordered_map<std::string, double>;

double smooth_1d_calc(double x, const Smooth1dInfo& info);
double smooth_2d_calc(double x, double y, const Smooth2dInfo& info);

std::string get_model_name(const std::string& from_status,
                           const std::string& to_status);

class ModelCoef {
public:
    /// Auto-detect model structure from coef file (no specs required).
    void read(const std::string& coef_dir, const std::string& from_model);

    /// Partition terms into static/dynamic based on time-varying var names.
    void classify_terms(const std::unordered_set<std::string>& dynamic_vars);

    /// Evaluate all terms.
    double calc(const LoanDict& loan,
                const std::string& from_status,
                const std::string& to_status) const;

    /// Evaluate all terms by pre-built model name.
    double calc(const LoanDict& loan,
                const std::string& model_name) const;

    /// Evaluate dynamic terms only by model name (call each period, add to cached static).
    double calc_dynamic(const LoanDict& loan,
                        const std::string& model_name) const;

    /// Build static logit cache for all models for a given loan.
    LogitCache build_static_cache(const LoanDict& loan) const;

    bool has_model(const std::string& model_name) const;

private:
    struct ModelLink {
        double intercept = 0.0;
        std::unordered_map<std::string, CoefTerm>                         terms_1d;
        std::map<std::pair<std::string, std::string>, CoefTerm>           terms_2d;
        // Partitioned views (populated by classify_terms)
        std::vector<std::pair<std::string, const CoefTerm*>>              static_1d;
        std::vector<std::pair<std::string, const CoefTerm*>>              dynamic_1d;
        std::vector<std::tuple<std::string, std::string, const CoefTerm*>> static_2d;
        std::vector<std::tuple<std::string, std::string, const CoefTerm*>> dynamic_2d;
    };

    std::unordered_map<std::string, ModelLink> model_link_;

    void build_model_auto(const std::string& model_name,
                          const std::vector<io::CoefRow>& rows);

    // Shared eval helpers for partitioned term lists
    double eval_terms_1d(const LoanDict& loan,
        const std::vector<std::pair<std::string, const CoefTerm*>>& terms) const;
    double eval_terms_2d(const LoanDict& loan,
        const std::vector<std::tuple<std::string, std::string, const CoefTerm*>>& terms) const;
};

}  // namespace rrm::model
