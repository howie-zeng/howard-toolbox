#pragma once

#include "types.h"
#include "io/macro_reader.h"

#include <functional>
#include <string>
#include <unordered_set>
#include <vector>

namespace rrm {

// ---------------------------------------------------------------------------
// VarKind — mirrors Python's VarKind enum
// ---------------------------------------------------------------------------
enum class VarKind { STATIC, TIME_VARYING, MACRO, PATH_DEPENDENT };

// ---------------------------------------------------------------------------
// VarContext — lookup tables available to macro update functions
// ---------------------------------------------------------------------------
struct VarContext {
    const io::LookupTable* calendar_table = nullptr;
    const io::LookupTable* fico_coupon_table = nullptr;
};

// ---------------------------------------------------------------------------
// VarDef — one registered variable
// ---------------------------------------------------------------------------
struct VarDef {
    std::string name;
    VarKind kind;
    bool is_age_var = false;

    // TIME_VARYING: called each period (age vars after model, others before)
    std::function<void(LoanDict&, int)> update_fn;

    // MACRO: called each period only when mode="custom"
    std::function<void(LoanDict&, const VarContext&)> macro_fn;

    // PATH_DEPENDENT: called on each drawn transition (from -> to)
    std::function<void(LoanDict&, const std::string&, const std::string&)> path_fn;
};

// ---------------------------------------------------------------------------
// VarRegistry — central registry of all variable update logic
// ---------------------------------------------------------------------------
class VarRegistry {
public:
    void register_var(VarDef def);

    /// Advance age fields, then update period context + macros for next_period.
    /// Call AFTER model eval.
    void step_period(LoanDict& loan, int next_period, const VarContext& ctx) const;

    /// Update PATH_DEPENDENT vars from the drawn from->to transition.
    void step_transition(LoanDict& loan, const std::string& from_status,
                         const std::string& to_status) const;

    /// Names of all registered (non-static) variables.
    std::unordered_set<std::string> dynamic_var_names() const;

private:
    std::vector<VarDef> vars_;
    // Indices into vars_, bucketed by kind at registration so the per-period /
    // per-transition hot loops skip the full-vector kind scan. Indices (not
    // pointers) stay valid as vars_ grows by append.
    std::vector<size_t> age_idx_;     // TIME_VARYING + is_age_var  (pass 1, after model)
    std::vector<size_t> period_idx_;  // TIME_VARYING, non-age      (pass 2, before model)
    std::vector<size_t> macro_idx_;   // MACRO                      (pass 2, after period vars)
    std::vector<size_t> path_idx_;    // PATH_DEPENDENT             (per drawn transition)
};

// ---------------------------------------------------------------------------
// Build the default registry with all standard variables registered.
// Macro vars are only registered with macro_fn if their names appear
// in `active_macro_vars`.
// ---------------------------------------------------------------------------
VarRegistry build_var_registry(const std::unordered_set<std::string>& active_macro_vars = {});

}  // namespace rrm
