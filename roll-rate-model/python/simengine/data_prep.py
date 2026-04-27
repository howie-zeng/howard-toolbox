"""All data loading and preparation — coef files, pmt matrix, dials, loans, schema."""
from __future__ import annotations

import csv
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .register_vars import (
    VarKind, VarDef, VarRegistry, build_default_registry,
    macro_ramp, macro_step, macro_flat,
)
from .gam_dump import dump_gam_models  # noqa: F401 — re-exported



# =====================================================================
# FIELD RENAMES — dv01 standard -> model field names
# Only renames if old name exists and new name doesn't (safe for either format)
# =====================================================================
DV01_RENAME_MAP = {
    "dv01_id":                "loan_id",
    "loan_term_orig":         "term",
    "fico_orig":              "ofico",
    "home_ownership":         "hm_owner",
    "employ_status":          "employed_f",
    "loan_purpose":           "purpose",
    "loan_rate_gross_orig":   "note_rate",
    "eop_status":             "status",
    "eop_balance":            "end_bal",
    "loan_balance_orig":      "orig_bal",
    "loan_grade":             "grade",
    "platform":               "platform_f",
    "loan_payment_date_first_contractual": "f_pmt_dt",
    "loan_origination_date":  "orig_dt",
    "as_of_date":             "r_dt",
    "pti_orig":               "opti",
}

# =====================================================================
# VALUE MAPS — standardize dv01 categorical values to model labels
# Edit here to add/change value mappings (applied after field renames)
# =====================================================================
STATUS_VALUE_MAP = {
    "Current":                  "C",
    "1 - 29 Days Delinquent":   "C",       # sub-30 treated as current
    "30 - 59 Days Delinquent":  "D1M",
    "60 - 89 Days Delinquent":  "D2M",
    "90 - 119 Days Delinquent": "D3M",
    ">= 120 Days Delinquent":   "D4M",
    "Charged Off":              "LIQ",
    "Paid Off":                 "PIF",
    "Paid Off - Negative Balance": "PIF",
    # Numeric codes (from R merge pipeline) -> model labels
    "0": "C",
    "1": "D1M",
    "2": "D2M",
    "3": "D3M",
    "4": "D4M",
    "5": "LIQ",
    "-1": "PIF",
    "-2": "PIF",
    # Pass-through for already-mapped values
    "C": "C",
    "D1M": "D1M",
    "D2M": "D2M",
    "D3M": "D3M",
    "D4M": "D4M",
    "PIF": "PIF",
    "LIQ": "LIQ",
}

HOMEOWNERSHIP_VALUE_MAP = {
    # R: map_homeownership() -> factor(levels = c("Rent","Own","Mortgage"))
    # Unmapped / None -> NA (v_hm_owner=0 handles it)
    "Own - Mortgage":    "Mortgage",
    "Own - No Mortgage": "Own",
    "Rent":     "Rent",
    "Own":      "Own",
    "Mortgage": "Mortgage",
    "Other":    "Other",
}

# R: employed = fcase(is.na -> NA, emp_status %in% NOT_EMPLOYED -> "No", default -> "Yes")
# NOT_EMPLOYED = c("Other", "Unemployed", "Missing", "Retired")
# Factor levels: c("No", "Yes").  NA -> v_employed handles it.
EMPLOYMENT_VALUE_MAP = {
    "Other":      "No",
    "Unemployed": "No",
    "Missing":    "No",
    "Retired":    "No",
}
PURPOSE_VALUE_MAP = {
    # R: map_purpose() -> factor(levels = c("Debt Consol","CC",...,"Vacation"))
    # Unmapped / NA -> NA (no v_flag for purpose, just no lookup match -> 0)
    "Debt Consolidation":          "Debt Consol",
    "Credit Card Refinancing":     "CC",
    "Home Improvement":            "Home Improvement",
    "Medical Expenses":            "Medical",
    "Vehicle":  "Vehicle",
    "Business": "Business",
    "Vacation": "Vacation",
}

# Map of field_name -> (value_map, default_for_unmapped_non_None, default_for_None)
# Applied in order after renames.
# If raw is None -> use 3rd element (default_for_None). None = stays None (v_flag handles).
# If raw is non-None but not in map -> use 2nd element (unmapped_default).
FIELD_VALUE_MAPS = {
    "status":      (STATUS_VALUE_MAP,        None,      None),
    "hm_owner":    (HOMEOWNERSHIP_VALUE_MAP, None,      "Missing"),  # None -> Missing (model level)
    "employed_f":  (EMPLOYMENT_VALUE_MAP,    "Yes",     "Missing"),  # None -> Missing (model level)
    "purpose":     (PURPOSE_VALUE_MAP,       "Missing", "Missing"),   # unmapped or None -> Missing
}

# =====================================================================
# MISSING DATA DEFAULTS — placeholder values for smooth variables
# When a smooth source is None, set this default + v_flag=0 zeroes it out
# =====================================================================
# =====================================================================
# DERIVED FIELDS — computed once during loan prep
# Edit derive_initial_fields() to add/change derived field formulas.
# c_* fields (e.g. c_age_pct, c_credit_age) are auto-copied from their
# base field (age_pct, credit_age). Smooth1D.eval() clamps to knot bounds.
# Missing smooth fields with v_* flags auto-default to 0.
# =====================================================================
DERIVED_FIELD_NAMES = {
    "int_rate", "age", "age_pct", "oterm_f",
    "pmt_day", "days_to_month_end", "month_group",
    "vint_qtr", "lending_environment", "platform_type_f",
    "_fico_bkt", "_coupon_at_vintage",
    # c_* fields auto-added from model coef scan
}

DERIVED_FIELD_DEPS = {
    "int_rate":              ["note_rate"],
    "age":                   ["loan_age"],
    "age_pct":               ["loan_age", "term"],
    "oterm_f":               ["term"],
    "pmt_day":               ["f_pmt_dt"],
    "days_to_month_end":     ["pmt_day", "month", "r_dt"],
    "month_group":           ["days_to_month_end"],
    "vint_qtr":              ["orig_dt"],
    "lending_environment":   ["orig_dt"],
    "platform_type_f":       [],  # defaults to "A" if platform_f missing
    "_fico_bkt":             ["ofico"],
    "_coupon_at_vintage":    ["ofico", "orig_dt"],
    # c_* deps auto-added: c_X -> [X]
}


def derive_initial_fields(loan: Dict, c_fields: set = frozenset(),
                          ctx: Dict[str, Any] = None) -> None:
    """Compute derived fields from raw loan data. Called once per loan during prep.

    Delegates to VarRegistry.derive_initial().

    Args:
        c_fields: set of c_* field names from model coef files (auto-copy from base).
        ctx: context dict with lookup tables (cpi_lookup, fico_coupon_lookup, etc.)
    """
    _get_registry().derive_initial(loan, ctx=ctx, c_fields=c_fields)


# =====================================================================
# TIME-VARYING FIELDS — delegates to VarRegistry from register_vars.py
# =====================================================================

# Module-level default registry (lazy singleton)
_DEFAULT_REGISTRY: Optional[VarRegistry] = None


def _get_registry() -> VarRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = build_default_registry()
    return _DEFAULT_REGISTRY


def init_time_varying_state(loan: Dict) -> None:
    """Record starting state before sim loop. Call once per loan."""
    _get_registry().init_time_state(loan)


def step_period_fields(loan: Dict, next_period: int) -> None:
    """Advance age + update period context for next_period. Call AFTER model eval."""
    _get_registry().step_period(loan, next_period)

# =====================================================================
# MACRO DEFAULTS — flat scenario values applied if not on loan
# Edit here to change macro assumptions
# =====================================================================
MACRO_DEFAULTS = {
    "cpi_inflator_36": 1.0,
    "cpi_inflator_12": 1.0,
}

# =====================================================================
# RECOMMENDED FIELDS — for aggregation/reporting (warning if missing)
# =====================================================================
RECOMMENDED_FIELDS = ["grade", "vint_qtr", "orig_bal"]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config(path: str) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Status topology (defaults — overridden by config)
# ---------------------------------------------------------------------------

DEFAULT_STATUS_TO_ROLL = {
    "C":   ["C", "D1M", "D2M", "D3M", "D4M", "PIF", "LIQ"],
    "D1M": ["D1M", "C", "D2M", "D3M", "D4M", "PIF", "LIQ"],
    "D2M": ["D2M", "C", "D1M", "D3M", "D4M", "PIF", "LIQ"],
    "D3M": ["D3M", "C", "D1M", "D2M", "D4M", "PIF", "LIQ"],
    "D4M": ["D4M", "C", "D1M", "D2M", "D3M", "PIF", "LIQ"]
}

DEFAULT_TERMINAL_STATUSES = {"PIF", "LIQ"}

DEFAULT_DQ_BUCKETS = {
    "D1M": ("dq30", "dq30_bal"),
    "D2M": ("dq60", "dq60_bal"),
    "D3M": ("dq90", "dq90_bal"),
    "D4M": ("dq120", "dq120_bal"),
}

# Backwards-compat aliases (runner.py imports these)
TERMINAL_STATUSES = DEFAULT_TERMINAL_STATUSES
DQ_BUCKETS = DEFAULT_DQ_BUCKETS


def normalize_status_to_roll(m: Dict[str, List[str]]) -> Dict[str, List[str]]:
    out = {k: list(v) for k, v in m.items()}
    for k, v in out.items():
        if k not in v:
            v.insert(0, k)
    return out


def derive_status_universe(status_to_roll: Dict[str, List[str]]):
    from_list = list(status_to_roll.keys())
    to_set = set()
    for tos in status_to_roll.values():
        to_set.update(tos)
    all_set = sorted(set(from_list) | to_set)
    clean = {s: s.split(".")[0] for s in all_set}
    return from_list, sorted(to_set), all_set, clean


# ---------------------------------------------------------------------------
# Coef file reader  (mirrors model_coef.read from Python reference)
# ---------------------------------------------------------------------------

@dataclass
class CoefRow:
    model: str
    var_name1: str
    var_val1: str
    var_name2: str
    var_val2: str
    value: float


def read_coef_file(path: str) -> List[CoefRow]:
    rows = []
    with open(path, "r") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for r in reader:
            rows.append(CoefRow(
                model=r["model"],
                var_name1=r["var_name1"].strip(),
                var_val1=r["var_val1"],
                var_name2=r.get("var_name2", "").strip(),
                var_val2=r.get("var_val2", ""),
                value=float(r["value"]) if r["value"].strip() else 0.0,
            ))
    return rows


def load_all_coef(coef_dir: str, from_statuses: List[str]) -> Dict[str, List[CoefRow]]:
    result = {}
    for fs in from_statuses:
        path = os.path.join(coef_dir, f"from{fs}.txt")
        if os.path.isfile(path):
            result[fs] = read_coef_file(path)
    return result


# ---------------------------------------------------------------------------
# Smooth / lookup structures built from coef rows
# ---------------------------------------------------------------------------

@dataclass
class Smooth1D:
    var_name: str
    xmin: float
    xmax: float
    n: int
    step: float
    grid: List[float]

    def eval(self, x: float) -> float:
        xc = max(self.xmin, min(x, self.xmax))
        if self.n <= 0 or self.step <= 0:
            return 0.0
        x_in = (xc - self.xmin) / self.step
        x_left = int(x_in)
        x_right = x_left + 1
        if x_right < len(self.grid):
            return (self.grid[x_right] - self.grid[x_left]) * (x_in - x_left) + self.grid[x_left]
        return self.grid[-1]


@dataclass
class Lookup1D:
    var_name: str
    table: Dict[str, float] = field(default_factory=dict)

    def eval(self, key: str) -> float:
        return self.table.get(key, 0.0)


@dataclass
class SmoothByFactor:
    smooth_var: str
    factor_var: str
    smooths: Dict[str, Smooth1D] = field(default_factory=dict)

    def eval(self, x: float, factor: str) -> float:
        s = self.smooths.get(factor)
        return s.eval(x) if s else 0.0


@dataclass
class SmoothByNum:
    smooth_var: str
    weight_var: str
    smooth: Optional[Smooth1D] = None

    def eval(self, x: float, w: float) -> float:
        return self.smooth.eval(x) * w if self.smooth else 0.0


@dataclass
class ModelLink:
    intercept: float = 0.0
    lookups: Dict[str, Lookup1D] = field(default_factory=dict)
    smooths: Dict[str, Smooth1D] = field(default_factory=dict)
    smooth_by_factors: Dict[Tuple[str, str], SmoothByFactor] = field(default_factory=dict)
    smooth_by_nums: Dict[Tuple[str, str], SmoothByNum] = field(default_factory=dict)


def _build_smooth(var_name: str, rows: List[CoefRow]) -> Smooth1D:
    vals = sorted(rows, key=lambda r: float(r.var_val1))
    grid_points = [float(r.var_val1) for r in vals]
    grid_values = [r.value for r in vals]
    if len(grid_points) < 2:
        return Smooth1D(var_name, 0, 1, 0, 1, grid_values)
    xmin = grid_points[0]
    xmax = grid_points[-1]
    n = len(grid_points) - 1
    step = (xmax - xmin) / n if n > 0 else 1.0
    return Smooth1D(var_name, xmin, xmax, n, step, grid_values)


def build_model_link(rows: List[CoefRow]) -> ModelLink:
    link = ModelLink()

    by_var1: Dict[str, List[CoefRow]] = {}
    by_var12: Dict[Tuple[str, str], List[CoefRow]] = {}

    for r in rows:
        if r.var_name2 and r.var_name2.strip():
            by_var12.setdefault((r.var_name1, r.var_name2), []).append(r)
        else:
            by_var1.setdefault(r.var_name1, []).append(r)

    if "intercept" in by_var1:
        link.intercept = by_var1["intercept"][0].value

    for var_name, var_rows in by_var1.items():
        if var_name == "intercept":
            continue
        is_numeric = all(_is_numeric(r.var_val1) for r in var_rows)
        if is_numeric and len(var_rows) > 5:
            link.smooths[var_name] = _build_smooth(var_name, var_rows)
        else:
            lookup = Lookup1D(var_name)
            for r in var_rows:
                lookup.table[r.var_val1] = r.value
            link.lookups[var_name] = lookup

    for (vn1, vn2), var_rows in by_var12.items():
        vals2 = {r.var_val2 for r in var_rows if r.var_val2.strip()}
        is_v1_numeric = all(_is_numeric(r.var_val1) for r in var_rows)

        if is_v1_numeric and len(vals2) > 1:
            sbf = SmoothByFactor(vn1, vn2)
            by_factor: Dict[str, List[CoefRow]] = {}
            for r in var_rows:
                by_factor.setdefault(r.var_val2, []).append(r)
            for fct, frows in by_factor.items():
                sbf.smooths[fct] = _build_smooth(vn1, frows)
            link.smooth_by_factors[(vn1, vn2)] = sbf
        elif is_v1_numeric:
            sbn = SmoothByNum(vn1, vn2, _build_smooth(vn1, var_rows))
            link.smooth_by_nums[(vn1, vn2)] = sbn
        else:
            lookup = Lookup1D(vn1)
            for r in var_rows:
                key = f"{r.var_val1}|{r.var_val2}"
                lookup.table[key] = r.value
            link.lookups[f"{vn1}|{vn2}"] = lookup

    return link


def _is_numeric(s: str) -> bool:
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


def build_all_models(
    coef_by_from: Dict[str, List[CoefRow]],
) -> Dict[str, ModelLink]:
    models = {}
    for from_status, rows in coef_by_from.items():
        by_model: Dict[str, List[CoefRow]] = {}
        for r in rows:
            model_name = f"from{from_status}_{r.model}"
            by_model.setdefault(model_name, []).append(r)
        for model_name, model_rows in by_model.items():
            models[model_name] = build_model_link(model_rows)
    return models


def calc(link: ModelLink, loan: Dict[str, Any]) -> float:
    result = link.intercept

    for var_name, lookup in link.lookups.items():
        if "|" in var_name:
            parts = var_name.split("|")
            v1 = str(loan.get(parts[0], ""))
            v2 = str(loan.get(parts[1], ""))
            result += lookup.eval(f"{v1}|{v2}")
        else:
            val = str(loan.get(var_name, ""))
            result += lookup.eval(val)

    for var_name, smooth in link.smooths.items():
        val = loan.get(var_name)
        if val is not None:
            result += smooth.eval(float(val))

    for (sv, fv), sbf in link.smooth_by_factors.items():
        x = loan.get(sv)
        f = str(loan.get(fv, ""))
        if x is not None:
            result += sbf.eval(float(x), f)

    for (sv, wv), sbn in link.smooth_by_nums.items():
        x = loan.get(sv)
        w = loan.get(wv)
        if x is not None and w is not None:
            result += sbn.eval(float(x), float(w))

    return result


def classify_model_terms(models: Dict[str, ModelLink], dynamic_vars: Set[str]) -> None:
    """Classify each model's terms as static or dynamic.

    Static terms depend only on variables that never change during simulation.
    Dynamic terms depend on at least one time-varying or macro variable.
    Stores _static_*/_dynamic_* lists on each ModelLink for use by
    calc_static/calc_dynamic.
    """
    for link in models.values():
        link._static_lookups = []
        link._dynamic_lookups = []
        for var_name, lookup in link.lookups.items():
            parts = var_name.split("|") if "|" in var_name else [var_name]
            if any(p in dynamic_vars for p in parts):
                link._dynamic_lookups.append((var_name, lookup))
            else:
                link._static_lookups.append((var_name, lookup))

        link._static_smooths = []
        link._dynamic_smooths = []
        for var_name, smooth in link.smooths.items():
            if var_name in dynamic_vars:
                link._dynamic_smooths.append((var_name, smooth))
            else:
                link._static_smooths.append((var_name, smooth))

        link._static_sbf = []
        link._dynamic_sbf = []
        for (sv, fv), sbf in link.smooth_by_factors.items():
            if sv in dynamic_vars or fv in dynamic_vars:
                link._dynamic_sbf.append((sv, fv, sbf))
            else:
                link._static_sbf.append((sv, fv, sbf))

        link._static_sbn = []
        link._dynamic_sbn = []
        for (sv, wv), sbn in link.smooth_by_nums.items():
            if sv in dynamic_vars or wv in dynamic_vars:
                link._dynamic_sbn.append((sv, wv, sbn))
            else:
                link._static_sbn.append((sv, wv, sbn))


def _eval_terms(loan: Dict, lookups, smooths, sbf_list, sbn_list) -> float:
    """Evaluate a subset of model terms."""
    result = 0.0
    for var_name, lookup in lookups:
        if "|" in var_name:
            parts = var_name.split("|")
            result += lookup.eval(f"{loan.get(parts[0], '')}|{loan.get(parts[1], '')}")
        else:
            result += lookup.eval(str(loan.get(var_name, "")))
    for var_name, smooth in smooths:
        val = loan.get(var_name)
        if val is not None:
            result += smooth.eval(float(val))
    for sv, fv, sbf in sbf_list:
        x = loan.get(sv)
        if x is not None:
            result += sbf.eval(float(x), str(loan.get(fv, "")))
    for sv, wv, sbn in sbn_list:
        x, w = loan.get(sv), loan.get(wv)
        if x is not None and w is not None:
            result += sbn.eval(float(x), float(w))
    return result


def build_static_cache(models: Dict[str, ModelLink], loan: Dict) -> Dict[str, float]:
    """Pre-compute static model terms for a loan. Call once per loan."""
    cache = {}
    for name, link in models.items():
        cache[name] = link.intercept + _eval_terms(
            loan, link._static_lookups, link._static_smooths,
            link._static_sbf, link._static_sbn)
    return cache


def calc_dynamic(link: ModelLink, loan: Dict) -> float:
    """Evaluate only the dynamic (time-varying) model terms."""
    return _eval_terms(loan, link._dynamic_lookups, link._dynamic_smooths,
                       link._dynamic_sbf, link._dynamic_sbn)


# ---------------------------------------------------------------------------
# PMT matrix
# ---------------------------------------------------------------------------

def load_pmt_matrix(path: str) -> Dict[str, Dict[str, float]]:
    matrix: Dict[str, Dict[str, float]] = {}
    with open(path, "r") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        to_statuses = header[1:]
        for ts in to_statuses:
            matrix[ts] = {}
        for row in reader:
            if not row:
                continue
            from_status = row[0]
            for i, ts in enumerate(to_statuses):
                if i + 1 < len(row):
                    matrix[ts][from_status] = float(row[i + 1])
    return matrix


# ---------------------------------------------------------------------------
# Dial reader
# ---------------------------------------------------------------------------

def _make_dial_array(all_status: List[str], n_per: int) -> Tuple[List[float], Dict[str, int], int]:
    """Create a flat dial array initialized to NaN (unset)."""
    status_idx = {s: i for i, s in enumerate(all_status)}
    ns = len(all_status)
    data = [float('nan')] * (ns * ns * n_per)
    return data, status_idx, ns


def _dial_lookup(data, ns, n_per, fi, ti, per):
    if fi < 0 or ti < 0 or per < 0 or per >= n_per:
        return float('nan')
    idx = fi * ns * n_per + ti * n_per + per
    if 0 <= idx < len(data):
        return data[idx]
    return float('nan')


def load_dial(path: str, all_status: List[str], n_per: int) -> Dict:
    """Load dial file. Supports optional term/grade segmentation columns.

    Old format (still works):
        Status  C   D1M   D2M  ...
        C       1.0 1.05  1.0  ...

    New format (segmented):
        Status  term  grade  C   D1M   D2M  ...
        C       36    A      1.0 1.05  1.0  ...
        C       *     *      1.0 1.02  1.0  ...   <- fallback

    Returns dict with 'segments' (keyed by "term|grade") and 'fallback'.
    """
    if not os.path.isfile(path):
        return {}
    status_idx = {s: i for i, s in enumerate(all_status)}
    ns = len(all_status)

    with open(path, "r") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)

    # Detect segment columns (between Status and first status column)
    seg_cols = []  # e.g. ["term", "grade"]
    status_col_idx = 0 if header[0] == "Status" else -1
    to_col_start = 1 if status_col_idx == 0 else 0
    # Any column between Status and the first status-name column is a segment col
    for i in range(to_col_start, len(header)):
        if header[i] in status_idx:
            to_col_start = i
            break
        seg_cols.append(header[i])

    to_cols = header[to_col_start:]

    # Parse rows into segments
    segments: Dict[str, List[float]] = {}  # "term|grade" -> flat array
    current_from = ""
    current_seg_key = ""
    per_by_seg: Dict[str, int] = {}

    with open(path, "r") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader)  # skip header
        for row in reader:
            if not row:
                continue

            # Parse from-status
            from_val = row[0].strip() if status_col_idx == 0 else ""
            if from_val:
                current_from = from_val

            # Parse segment key — only update on header rows (from_val non-empty)
            if from_val and seg_cols:
                seg_vals = []
                for si in range(len(seg_cols)):
                    col_i = 1 + si
                    seg_vals.append(row[col_i].strip() if col_i < len(row) else "*")
                current_seg_key = "|".join(seg_vals)
            seg_key = current_seg_key

            # Track period per (from_status, segment)
            state_key = f"{current_from}|{seg_key}"
            if from_val:
                per_by_seg[state_key] = 0
            per = per_by_seg.get(state_key, 0)

            fi = status_idx.get(current_from, -1)
            if fi < 0:
                per_by_seg[state_key] = per + 1
                continue

            # Init segment array on first encounter
            if seg_key not in segments:
                segments[seg_key] = [float('nan')] * (ns * ns * n_per)

            arr = segments[seg_key]
            for c, tc in enumerate(to_cols):
                ti = status_idx.get(tc, -1)
                if ti < 0:
                    continue
                data_col = to_col_start + c
                if data_col >= len(row):
                    break
                try:
                    val = float(row[data_col])
                    idx = fi * ns * n_per + ti * n_per + per
                    if 0 <= idx < len(arr):
                        arr[idx] = val
                except ValueError:
                    pass

            per_by_seg[state_key] = per + 1

    # Separate fallback (unsegmented or "*|*") from specific segments
    fallback_key = "|".join(["*"] * len(seg_cols)) if seg_cols else ""
    fallback = segments.pop(fallback_key, segments.pop("", None))

    # If no segment columns, the whole thing is the fallback
    if not seg_cols and fallback is None and len(segments) == 1:
        fallback = list(segments.values())[0]
        segments = {}

    return {
        "fallback": fallback,
        "segments": segments,
        "seg_cols": seg_cols,
        "status_idx": status_idx,
        "ns": ns,
        "n_per": n_per,
    }


def get_dial(dial_data: Dict, from_status: str, to_status: str, per: int,
             loan: Dict = None) -> float:
    """Look up dial multiplier. Tries segmented lookup first, falls back."""
    if not dial_data:
        return 1.0
    si = dial_data["status_idx"]
    fi = si.get(from_status, -1)
    ti = si.get(to_status, -1)
    if fi < 0 or ti < 0:
        return 1.0
    ns = dial_data["ns"]
    n_per = dial_data["n_per"]

    # Try segmented lookup
    seg_cols = dial_data.get("seg_cols", [])
    if seg_cols and loan is not None and dial_data.get("segments"):
        seg_key = "|".join(str(loan.get(c, "*")) for c in seg_cols)
        arr = dial_data["segments"].get(seg_key)
        if arr is not None:
            v = _dial_lookup(arr, ns, n_per, fi, ti, per)
            if v == v:  # not NaN
                return v

    # Fallback
    fb = dial_data.get("fallback")
    if fb is not None:
        v = _dial_lookup(fb, ns, n_per, fi, ti, per)
        if v == v:  # not NaN
            return v

    return 1.0


# ---------------------------------------------------------------------------
# Loan loading and preparation
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = ["loan_id", "end_bal", "int_rate", "term", "loan_age", "status"]


def _coerce_csv_row(row: Dict[str, str]) -> Dict[str, Any]:
    """Convert CSV string values: empty/NA -> None, numeric -> int/float, else str."""
    out: Dict[str, Any] = {}
    for k, v in row.items():
        v = v.strip()
        if v == "" or v.upper() in ("NA", "NULL", "NAN"):
            out[k] = None
            continue
        try:
            fv = float(v)
            out[k] = int(fv) if fv == int(fv) else fv
        except (ValueError, OverflowError):
            out[k] = v
    return out


def load_loans(path: str) -> List[Dict[str, Any]]:
    if path.lower().endswith(".csv"):
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            return [_coerce_csv_row(row) for row in reader]
    with open(path) as f:
        raw = json.load(f)
    if isinstance(raw, dict):
        raw = [raw]
    return raw


def _apply_field_renames(loan: Dict, renames: Dict[str, str]) -> None:
    for old, new in renames.items():
        if old in loan and new not in loan:
            loan[new] = loan.pop(old)


def _apply_value_maps(loan: Dict, field_maps: Dict) -> None:
    """Remap categorical values using FIELD_VALUE_MAPS tuples."""
    for field_name, map_tuple in field_maps.items():
        vmap, unmapped_default = map_tuple[0], map_tuple[1]
        none_default = map_tuple[2] if len(map_tuple) > 2 else None
        if field_name not in loan:
            # Key absent — treat same as None
            loan[field_name] = none_default
            continue
        raw = loan[field_name]
        if raw is None or (isinstance(raw, str) and raw.strip() == ""):
            loan[field_name] = none_default  # None/empty -> none_default (e.g. "Missing")
        else:
            s = str(raw).strip()
            loan[field_name] = vmap.get(s, vmap.get(raw, unmapped_default))


def _derive_month_from_date(loan: Dict) -> None:
    """Derive 'month' (calendar month name) from r_dt if not already present."""
    if "month" in loan and loan["month"] is not None:
        return
    r_dt = loan.get("r_dt")
    if r_dt is None:
        return
    s = str(r_dt).strip()
    try:
        if "/" in s:
            m = int(s.split("/")[0])
        else:
            m = int(s.split("-")[1])
        loan["month"] = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ][m - 1]
    except (IndexError, ValueError):
        pass


def detect_weight_flags(coef_dir: str, from_statuses: List[str]) -> Dict[str, str]:
    """Scan coef files for v_* interaction variables — these are weight flags.

    Returns {v_flag_name: paired_var_name1} for NA-aware flag generation.
    """
    flags: Dict[str, str] = {}
    for fs in from_statuses:
        path = os.path.join(coef_dir, f"from{fs}.txt")
        if not os.path.isfile(path):
            continue
        with open(path) as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                vn2 = row.get("var_name2", "").strip()
                if vn2.startswith("v_") and vn2 not in flags:
                    flags[vn2] = row.get("var_name1", "").strip()
    return flags




def extract_model_fields(coef_dir: str, from_statuses: List[str]) -> Dict[str, Any]:
    """Scan all coef files and extract every field the models reference.

    Returns {"all_fields": set, "v_flags": {flag_name: paired_var_name1}}.
    Also prints warnings for inconsistent v_flag usage across models.
    """
    all_fields: set = set()
    v_flags: Dict[str, str] = {}
    # Track which models use a smooth with/without v_flag
    smooth_with_flag: Dict[str, set] = {}    # {var_name1: {models that have v_flag}}
    smooth_without_flag: Dict[str, set] = {} # {var_name1: {models that lack v_flag}}
    for fs in from_statuses:
        path = os.path.join(coef_dir, f"from{fs}.txt")
        if not os.path.isfile(path):
            continue
        with open(path) as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                vn1 = row.get("var_name1", "").strip()
                vn2 = row.get("var_name2", "").strip()
                model = row.get("model", "").strip()
                model_key = f"from{fs}_{model}" if model else f"from{fs}"
                if vn1 and vn1 != "intercept":
                    all_fields.add(vn1)
                if vn2:
                    if vn2.startswith("v_"):
                        if vn2 not in v_flags:
                            v_flags[vn2] = vn1
                        smooth_with_flag.setdefault(vn1, set()).add(model_key)
                    else:
                        all_fields.add(vn2)
                        smooth_without_flag.setdefault(vn1, set()).add(model_key)
                elif vn1 and vn1 != "intercept":
                    # No var_name2 — check if this is a smooth (numeric var_val1)
                    vv1 = row.get("var_val1", "").strip()
                    try:
                        float(vv1)
                        # It's a smooth without a v_flag
                        smooth_without_flag.setdefault(vn1, set()).add(model_key)
                    except ValueError:
                        pass  # categorical — no tracking needed

    # Warn about inconsistent v_flag usage (field has v_flag in some models but not others)
    for var, flagged_models in smooth_with_flag.items():
        unflagged = smooth_without_flag.get(var, set())
        if unflagged:
            print(f"  WARN  `{var}` has v_flag in [{', '.join(sorted(flagged_models))}] "
                  f"but NOT in [{', '.join(sorted(unflagged))}]")
    # Also check: bare field X used without flag, while c_X has flag
    for flag_name, capped_var in v_flags.items():
        if capped_var.startswith("c_"):
            bare = capped_var[2:]
            unflagged = smooth_without_flag.get(bare, set())
            if unflagged:
                print(f"  WARN  `{bare}` used without v_flag in "
                      f"[{', '.join(sorted(unflagged))}] - `{capped_var}` has {flag_name} elsewhere")

    # Build set of fields that appear unflagged in some models
    # (if data is missing for these, imputed 0 is treated as real value)
    unflagged_smooth: Dict[str, set] = {}
    for flag_name, capped_var in v_flags.items():
        if capped_var.startswith("c_"):
            bare = capped_var[2:]
            uf = smooth_without_flag.get(bare, set())
            if uf:
                unflagged_smooth[bare] = uf
        uf = smooth_without_flag.get(capped_var, set())
        if uf:
            unflagged_smooth[capped_var] = uf

    return {"all_fields": all_fields, "v_flags": v_flags,
            "unflagged_smooth": unflagged_smooth}


def extract_categorical_levels(coef_dir: str, from_statuses: List[str]) -> Dict[str, set]:
    """Scan coef files and extract known levels for each categorical lookup field.

    Returns {field_name: {level1, level2, ...}} — only non-smooth, non-intercept fields
    that appear as var_val1 or var_val2 with discrete string values.
    The reference level is NOT included (it has no row in the coef file).
    """
    levels: Dict[str, set] = {}
    for fs in from_statuses:
        path = os.path.join(coef_dir, f"from{fs}.txt")
        if not os.path.isfile(path):
            continue
        with open(path) as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                vn1 = row.get("var_name1", "").strip()
                vv1 = row.get("var_val1", "").strip()
                vn2 = row.get("var_name2", "").strip()
                vv2 = row.get("var_val2", "").strip()
                # Only categorical lookups have non-numeric var_val
                if vn1 and vv1 and vn1 != "intercept":
                    try:
                        float(vv1)
                    except ValueError:
                        levels.setdefault(vn1, set()).add(vv1)
                if vn2 and vv2 and not vn2.startswith("v_"):
                    try:
                        float(vv2)
                    except ValueError:
                        levels.setdefault(vn2, set()).add(vv2)
    return levels


# ---------------------------------------------------------------------------
# Macro lookup loaders (CPI, FICO coupon benchmarks)
# ---------------------------------------------------------------------------

def _parse_cpi_date(date_str: str) -> str:
    """Convert CPI date formats to YYYY-MM key. Handles 'M/D/YYYY' and 'YYYY-MM-DD'."""
    date_str = date_str.strip()
    if "/" in date_str:
        parts = date_str.split("/")
        return f"{parts[2]}-{int(parts[0]):02d}"
    return date_str[:7]  # YYYY-MM


def _ym_add(ym: str, months: int) -> str:
    """Add months to a YYYY-MM string."""
    y, m = int(ym[:4]), int(ym[5:7])
    total = y * 12 + (m - 1) + months
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def _extend_cpi_forward(lookup: Dict[str, float], n_months: int = 120) -> None:
    """Extrapolate CPI forward using the trailing 12-month growth rate.

    Takes the last available CPI value and its value 12 months prior,
    derives a monthly rate, and projects forward n_months.
    """
    if not lookup:
        return
    last_ym = max(lookup.keys())
    last_cpi = lookup[last_ym]

    ym_12ago = _ym_add(last_ym, -12)
    cpi_12ago = lookup.get(ym_12ago)
    if cpi_12ago and cpi_12ago > 0:
        annual_rate = last_cpi / cpi_12ago - 1.0
    else:
        annual_rate = 0.025  # fallback 2.5%

    monthly_rate = (1.0 + annual_rate) ** (1.0 / 12) - 1.0

    cpi = last_cpi
    for i in range(1, n_months + 1):
        cpi *= (1.0 + monthly_rate)
        ym = _ym_add(last_ym, i)
        if ym not in lookup:
            lookup[ym] = round(cpi, 3)

    next_ym = _ym_add(last_ym, 1)
    print(f"  CPI extrapolated: {last_ym} ({last_cpi:.1f}) -> +{n_months}mo "
          f"@ {annual_rate*100:.2f}%/yr (monthly {monthly_rate*100:.3f}%), "
          f"e.g. {next_ym} = {lookup[next_ym]:.1f}")


def load_cpi_lookup(path: str, extend_months: int = 120) -> Dict[str, float]:
    """Load CPI CSV (DATE, CPIAUCNS) -> {YYYY-MM: cpi_value}.

    Auto-extrapolates forward using trailing 12-month growth rate.
    """
    lookup: Dict[str, float] = {}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ym = _parse_cpi_date(row["DATE"])
            lookup[ym] = float(row["CPIAUCNS"])
    _extend_cpi_forward(lookup, extend_months)
    return lookup


def load_macro_csv(path: str) -> Dict[str, Dict[str, float]]:
    """Load macro scenario CSV -> {YYYY-MM: {field: value}}.

    First column is 'date' (YYYY-MM key), remaining columns are macro fields.
    """
    macro: Dict[str, Dict[str, float]] = {}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ym = row["date"].strip()
            macro[ym] = {k: float(v) for k, v in row.items() if k != "date"}
    return macro


def load_fico_coupon_lookup(path: str) -> Dict[str, float]:
    """Load FICO coupon CSV (vint_moyy, fico_bkt, fico_bkt_coupon) -> {moyy|bkt: coupon}."""
    lookup: Dict[str, float] = {}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = f"{row['vint_moyy']}|{row['fico_bkt']}"
            lookup[key] = float(row["fico_bkt_coupon"])
    return lookup


def _date_to_ym(date_str: str) -> str:
    """Convert YYYY-MM-DD or similar to YYYY-MM."""
    if date_str is None:
        return ""
    s = str(date_str).strip()
    if "/" in s:
        parts = s.split("/")
        return f"{parts[2]}-{int(parts[0]):02d}"
    return s[:7]


def _ym_offset(ym: str, months: int) -> str:
    """Shift a YYYY-MM key by N months."""
    try:
        y, m = int(ym[:4]), int(ym[5:7])
        total = y * 12 + (m - 1) + months
        return f"{total // 12:04d}-{total % 12 + 1:02d}"
    except (ValueError, IndexError):
        return ""


def _bucket_fico(fico_val, breaks=(-float("inf"), 620, 650, 680, 710, 750, float("inf")),
                 labels=("[0-620)", "[620-650)", "[650-680)", "[680-710)", "[710-750)", "[750+)")):
    """Bucket a FICO score into standard ranges."""
    if fico_val is None:
        return ""
    v = float(fico_val)
    for i in range(len(breaks) - 1):
        if breaks[i] <= v < breaks[i + 1]:
            return labels[i]
    return labels[-1]


def apply_macro_lookups(
    loan: Dict,
    cpi_lookup: Optional[Dict[str, float]] = None,
    fico_coupon_lookup: Optional[Dict[str, float]] = None,
) -> None:
    """Derive macro/lookup-based fields on a loan dict (mutates in place).

    Fields derived:
      - adj_balance_cpi = orig_bal / CPI_at_origination
      - cpi_inflator_36 = (CPI_at_r_dt / CPI_36mo_ago) - 1
      - cpi_inflator_12 = (CPI_at_r_dt / CPI_12mo_ago) - 1  (if not already set)
      - rel_fico_ratio_ALL = note_rate / fico_bkt_coupon (at vintage)
      - rate_incentive_ALL = coupon_at_r_dt - coupon_at_vintage
    """
    # --- CPI-based fields ---
    if cpi_lookup:
        r_ym = _date_to_ym(loan.get("r_dt"))
        orig_ym = _date_to_ym(loan.get("orig_dt"))
        cpi_now = cpi_lookup.get(r_ym)
        cpi_orig = cpi_lookup.get(orig_ym)

        if "adj_balance_cpi" not in loan and cpi_orig and cpi_orig > 0:
            orig_bal = loan.get("orig_bal")
            if orig_bal is not None:
                loan["adj_balance_cpi"] = round(float(orig_bal) / cpi_orig, 4)

        if "cpi_inflator_36" not in loan and cpi_now:
            cpi_36 = cpi_lookup.get(_ym_offset(r_ym, -36))
            if cpi_36 and cpi_36 > 0:
                loan["cpi_inflator_36"] = round(cpi_now / cpi_36 - 1, 4)

        if "cpi_inflator_12" not in loan and cpi_now:
            cpi_12 = cpi_lookup.get(_ym_offset(r_ym, -12))
            if cpi_12 and cpi_12 > 0:
                loan["cpi_inflator_12"] = round(cpi_now / cpi_12 - 1, 4)

    # --- FICO coupon-based fields ---
    if fico_coupon_lookup:
        orig_ym = _date_to_ym(loan.get("orig_dt"))
        r_ym = _date_to_ym(loan.get("r_dt"))
        fico_bkt = _bucket_fico(loan.get("ofico"))
        note_rate = loan.get("note_rate")

        # Vintage month key (YYYYMM format used in lookup)
        vint_key = orig_ym.replace("-", "") if orig_ym else ""
        r_key = r_ym.replace("-", "") if r_ym else ""

        coupon_at_vint = fico_coupon_lookup.get(f"{vint_key}|{fico_bkt}")
        coupon_at_r = fico_coupon_lookup.get(f"{r_key}|{fico_bkt}")

        if "rel_fico_ratio_ALL" not in loan and note_rate is not None and coupon_at_vint and coupon_at_vint > 0:
            loan["rel_fico_ratio_ALL"] = round(float(note_rate) / coupon_at_vint, 4)

        if "rate_incentive_ALL" not in loan and coupon_at_r is not None and coupon_at_vint is not None:
            loan["rate_incentive_ALL"] = round(coupon_at_r - coupon_at_vint, 4)


def validate_loan(loan: Dict[str, Any]) -> None:
    missing = [f for f in REQUIRED_FIELDS if f not in loan]
    if missing:
        lid = loan.get("loan_id", "?")
        raise ValueError(f"loan {lid} missing: {missing}")


def _trace_missing_root(field_name: str, deps: Dict[str, List[str]],
                        loan: Dict) -> Optional[str]:
    """Trace a missing derived field to its root missing source.

    Returns a string like "Missing `f_pmt_dt` — needed for `days_to_month_end` -> `month_group`"
    or None if all sources are present (field should have been derivable).
    """
    chain = [field_name]
    current = field_name
    while current in deps:
        sources = deps[current]
        missing_src = [s for s in sources if s not in loan or loan[s] is None]
        if not missing_src:
            return None  # sources exist, derivation should have worked
        current = missing_src[0]
        chain.append(current)
    # chain is e.g. ["month_group", "days_to_month_end", "f_pmt_dt"]
    root = chain[-1]
    if len(chain) > 1:
        path = " -> ".join(f"`{c}`" for c in reversed(chain))
        return f"Missing `{root}` - needed for {path}"
    return f"Missing `{root}`"


def prepare_loans(
    loans: List[Dict[str, Any]],
    config: Dict[str, Any],
    coef_dir: Optional[str] = None,
    macro_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Full loan preparation: renames -> value maps -> month -> derived -> macro lookups -> defaults -> v_flags -> validate."""
    from_statuses = list(config.get("status_to_roll", DEFAULT_STATUS_TO_ROLL).keys())

    # Extract model-required fields and v_* flag mappings from coef files
    model_info: Dict[str, Any] = {"all_fields": set(), "v_flags": {}}
    cat_levels: Dict[str, set] = {}
    if coef_dir and os.path.isdir(coef_dir):
        model_info = extract_model_fields(coef_dir, from_statuses)
        cat_levels = extract_categorical_levels(coef_dir, from_statuses)

    v_flags = model_info["v_flags"]           # {v_flag: paired_var_name1}
    model_fields = model_info["all_fields"]   # all var_name1 + var_name2 (excl v_*)
    unflagged_smooth = model_info.get("unflagged_smooth", {})  # {field: {models without v_flag}}

    # -- Model summary --
    if cat_levels or model_fields:
        # Smooth fields = var_name1 fields that are NOT categorical
        cat_field_names = set(cat_levels.keys())
        smooth_field_names = sorted(f for f in model_fields
                                    if f not in cat_field_names
                                    and not f.startswith("v_"))
        print()
        print("  Model variables:")
        if cat_field_names:
            print("    Categorical:")
            for cf in sorted(cat_field_names):
                levels = sorted(cat_levels[cf])
                flag = f" (v_flag: v_{cf})" if f"v_{cf}" in v_flags else ""
                print(f"      {cf}: {', '.join(levels)}{flag}")
                # Reference level = not in coef file (absorbed into intercept)
                # Any observed value not in `levels` will be treated as reference
        if smooth_field_names:
            print("    Smooth:")
            for sf in smooth_field_names:
                flag = next((k for k, v in v_flags.items() if v == sf), None)
                suffix = f" (v_flag: {flag})" if flag else ""
                print(f"      {sf}{suffix}")
        if v_flags:
            print("    V-flags:", ", ".join(sorted(v_flags.keys())))
        print()

    # Auto-detect c_* fields from model (e.g. c_age_pct, c_credit_age, c_opti)
    c_fields = {f for f in model_fields if f.startswith("c_")}

    # Auto-detect smooth fields with v_* flags -> default to 0 when missing
    # (v_flag=0 zeroes out the smooth contribution; placeholder value doesn't matter)
    smooth_defaults = {}
    for flag_name, smooth_var in v_flags.items():
        smooth_defaults[smooth_var] = 0
        # If v_X -> c_X, also default the bare base field X (some models use it directly)
        if smooth_var.startswith("c_"):
            base = smooth_var[2:]
            if base in model_fields:
                smooth_defaults[base] = 0
        # Also default the c_* variant if it exists
        c_var = f"c_{smooth_var}"
        if c_var in model_fields:
            smooth_defaults[c_var] = 0

    # Determine which fields are derived/macro/auto (not expected on input)
    derived_names = set(DERIVED_FIELD_NAMES) | c_fields
    # Auto-add c_* deps
    deps = dict(DERIVED_FIELD_DEPS)
    for cf in c_fields:
        if cf not in deps:
            deps[cf] = [cf[2:]]  # c_X depends on X

    macro_names = set(MACRO_DEFAULTS.keys())
    lookup_names = {"adj_balance_cpi", "cpi_inflator_36", "cpi_inflator_12",
                    "rel_fico_ratio_ALL", "rate_incentive_ALL"}
    auto_names = derived_names | macro_names | set(v_flags.keys()) | lookup_names | set(smooth_defaults.keys())

    # Fields that must come from raw input
    required_from_input = (model_fields | set(REQUIRED_FIELDS)) - auto_names

    # Load macro lookup tables (if available)
    cpi_lookup: Optional[Dict[str, float]] = None
    fico_coupon_lookup: Optional[Dict[str, float]] = None
    if macro_dir is None:
        macro_dir = os.path.join(config.get("input_dir", "input"), "macro")
    cpi_path = os.path.join(macro_dir, "CPIAUCNS.csv")
    if os.path.isfile(cpi_path):
        cpi_lookup = load_cpi_lookup(cpi_path)
        print(f"  Loaded CPI lookup: {len(cpi_lookup)} months")
    fico_path = os.path.join(macro_dir, "FICO_BKT_COUPON.csv")
    if os.path.isfile(fico_path):
        fico_coupon_lookup = load_fico_coupon_lookup(fico_path)
        print(f"  Loaded FICO coupon lookup: {len(fico_coupon_lookup)} entries")

    # -- Counters for diagnostics --
    n_loans = len(loans)
    smooth_na_counts: Dict[str, int] = {k: 0 for k in smooth_defaults}
    vflag_zero_counts: Dict[str, int] = {k: 0 for k in v_flags}
    cat_na_counts: Dict[str, int] = {k: 0 for k in FIELD_VALUE_MAPS}

    prepared = []
    for i, loan in enumerate(loans):
        loan = dict(loan)

        # 1. Field renames (dv01 standard -> model names)
        _apply_field_renames(loan, DV01_RENAME_MAP)

        # Track categorical NAs (after rename, before value map)
        for cat_field in FIELD_VALUE_MAPS:
            if cat_field in loan and loan[cat_field] is None:
                cat_na_counts[cat_field] += 1

        # 2. Value standardization (status codes, homeownership, purpose)
        _apply_value_maps(loan, FIELD_VALUE_MAPS)

        # 3. Derive month from r_dt if missing
        _derive_month_from_date(loan)

        # 4. Derived fields + macro lookups (via registry init_fns)
        ctx = {"cpi_lookup": cpi_lookup, "fico_coupon_lookup": fico_coupon_lookup}
        derive_initial_fields(loan, c_fields=c_fields, ctx=ctx)

        # 5. Macro flat defaults (fill anything still missing)
        for key, val in MACRO_DEFAULTS.items():
            if key not in loan:
                loan[key] = val

        # 7. v_* flags — NA-aware (BEFORE smooth defaults so flags see None)
        for flag_name, smooth_var in v_flags.items():
            if flag_name in loan:
                continue
            base = flag_name[2:]  # strip "v_"
            if base in loan:
                loan[flag_name] = 0.0 if loan[base] is None else 1.0
            elif smooth_var in loan:
                loan[flag_name] = 0.0 if loan[smooth_var] is None else 1.0
            else:
                loan[flag_name] = 0.0
            if loan[flag_name] == 0.0:
                vflag_zero_counts[flag_name] = vflag_zero_counts.get(flag_name, 0) + 1

        # 8. Missing smooth defaults (placeholder value — AFTER v_flags so flags see None)
        #    Auto-detected: any smooth with a v_* flag defaults to 0 when missing.
        for key, default in smooth_defaults.items():
            if key not in loan or loan[key] is None:
                loan[key] = default
                smooth_na_counts[key] = smooth_na_counts.get(key, 0) + 1

        # 9. Validate — three tiers (check first loan only for field-level issues)
        if i == 0:
            # REQUIRED: model fields + cashflow fields
            missing_required = []
            for f in sorted(required_from_input):
                if f not in loan or loan[f] is None:
                    if f in deps:
                        trace = _trace_missing_root(f, deps, loan)
                        if trace:
                            missing_required.append(trace)
                    else:
                        missing_required.append(f"Missing `{f}`")
            if missing_required:
                print("REQUIRED fields missing (will error):")
                for msg in missing_required:
                    print(f"  {msg}")
                raise ValueError(
                    f"Loan prep stopped: {len(missing_required)} required field(s) missing. "
                    "See messages above."
                )

            # RECOMMENDED: aggregation fields
            missing_rec = [f for f in RECOMMENDED_FIELDS if f not in loan]
            if missing_rec:
                print(f"  WARN  recommended fields missing (for aggregation): {missing_rec}")

        # 10. Core validation
        validate_loan(loan)

        prepared.append(loan)

    # -- Print diagnostics --
    print()
    print(f"  Prep summary ({n_loans} loans):")

    # Smooth variables with missing data -> placeholder + flag
    any_smooth_msg = False
    for var, cnt in sorted(smooth_na_counts.items()):
        if cnt > 0:
            pct = 100 * cnt / n_loans
            # Check if this field is used without v_flag in some models
            uf_models = unflagged_smooth.get(var, set())
            if uf_models:
                models_str = ", ".join(sorted(uf_models))
                print(f"    {var}: NA {cnt}/{n_loans} ({pct:.1f}%) -> imputed {smooth_defaults[var]}, "
                      f"WARN: treated as real in [{models_str}] (no v_flag)")
            else:
                print(f"    {var}: NA {cnt}/{n_loans} ({pct:.1f}%) -> set to {smooth_defaults[var]}, v_flag=0")
            any_smooth_msg = True
    if not any_smooth_msg:
        print(f"    Smooth defaults: none needed (all present)")

    # v_flags that are zero (missing underlying data)
    for flag, cnt in sorted(vflag_zero_counts.items()):
        if cnt > 0:
            pct = 100 * cnt / n_loans
            base = flag[2:]
            print(f"    {flag}=0: {cnt}/{n_loans} ({pct:.1f}%) - smooth for `{base}` zeroed out")

    # Categorical NA rates
    for cat_field, cnt in sorted(cat_na_counts.items()):
        if cnt > 0:
            pct = 100 * cnt / n_loans
            map_tuple = FIELD_VALUE_MAPS.get(cat_field, (None, None, None))
            none_val = map_tuple[2] if len(map_tuple) > 2 else None
            if none_val:
                print(f"    {cat_field}: NA {cnt}/{n_loans} ({pct:.1f}%) -> set to '{none_val}'")
            else:
                print(f"    {cat_field}: NA {cnt}/{n_loans} ({pct:.1f}%) -> stays None (v_flag=0)")

    # Categorical level validation — check loan values vs model levels
    if cat_levels and prepared:
        observed_vals: Dict[str, Dict[str, int]] = {}  # {field: {value: count}}
        for loan in prepared:
            for field_name in cat_levels:
                val = loan.get(field_name)
                if val is not None:
                    s = str(val)
                    observed_vals.setdefault(field_name, {}).setdefault(s, 0)
                    observed_vals[field_name][s] += 1

        any_ref_msg = False
        for field_name, known in sorted(cat_levels.items()):
            obs = observed_vals.get(field_name, {})
            unknown = {v: c for v, c in obs.items() if v not in known}
            if unknown:
                if not any_ref_msg:
                    print()
                    print("  Categorical level check:")
                    any_ref_msg = True
                vals_str = ", ".join(f"'{v}'" for v in sorted(unknown))
                total = sum(unknown.values())
                print(f"    {field_name}: {vals_str} treated as reference ({total} loans)")

    return prepared


def save_prepped_loans(loans: List[Dict[str, Any]], path: str,
                       save_tsv: bool = False) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write("[\n")
        for i, loan in enumerate(loans):
            f.write("  ")
            json.dump(loan, f)
            if i < len(loans) - 1:
                f.write(",")
            f.write("\n")
        f.write("]\n")
    if save_tsv and loans:
        tsv_path = os.path.splitext(path)[0] + ".txt"
        cols = list(loans[0].keys())
        with open(tsv_path, "w", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(cols)
            for loan in loans:
                writer.writerow(loan.get(c, "") for c in cols)
        print(f"  Saved TSV: {tsv_path}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_year_month(date_str) -> Tuple[int, int]:
    """Extract (year, month_num) from date string. Returns (2024, 1) on failure."""
    if date_str is None:
        return 2024, 1
    s = str(date_str).strip()
    try:
        if "/" in s:
            parts = s.split("/")
            return int(parts[2]), int(parts[0])
        else:
            parts = s.split("-")
            return int(parts[0]), int(parts[1])
    except (IndexError, ValueError):
        return 2024, 1




# ---------------------------------------------------------------------------
# DataManager — ties it all together
# ---------------------------------------------------------------------------

@dataclass
class DataManager:
    models: Dict[str, ModelLink] = field(default_factory=dict)
    pmt_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    dial_data: Dict = field(default_factory=dict)
    status_to_roll: Dict[str, List[str]] = field(default_factory=dict)
    clean_status_dict: Dict[str, str] = field(default_factory=dict)
    all_status_list: List[str] = field(default_factory=list)
    terminal_statuses: set = field(default_factory=lambda: set(DEFAULT_TERMINAL_STATUSES))
    dq_buckets: Dict = field(default_factory=lambda: dict(DEFAULT_DQ_BUCKETS))
    macro: Dict[str, Any] = field(default_factory=dict)
    gam_models: List[Dict] = field(default_factory=list)
    liq_severity: float = 0.60
    n_per: int = 360


def init_data_manager(
    input_dir: str,
    n_per: int = 360,
    dial_name: str = "",
    liq_severity: float = 0.60,
    status_to_roll: Optional[Dict[str, List[str]]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> DataManager:
    dm = DataManager()

    # Pull from config if provided, otherwise use explicit args
    if config:
        dm.n_per = config.get("n_per", n_per)
        dm.liq_severity = config.get("liq_severity", liq_severity)
        status_to_roll = config.get("status_to_roll", DEFAULT_STATUS_TO_ROLL)
        dm.terminal_statuses = set(config.get("terminal_statuses", DEFAULT_TERMINAL_STATUSES))
        dq_raw = config.get("dq_buckets", DEFAULT_DQ_BUCKETS)
        dm.dq_buckets = {k: tuple(v) for k, v in dq_raw.items()}
        dm.gam_models = config.get("gam_models", [])
    else:
        dm.n_per = n_per
        dm.liq_severity = liq_severity
        if status_to_roll is None:
            status_to_roll = DEFAULT_STATUS_TO_ROLL

    dm.macro = dict(MACRO_DEFAULTS)

    dm.status_to_roll = normalize_status_to_roll(status_to_roll)
    from_list, _, all_list, clean = derive_status_universe(dm.status_to_roll)
    dm.clean_status_dict = clean
    dm.all_status_list = all_list

    coef_version = config.get("coef_version", "") if config else ""
    coef_dir = os.path.join(input_dir, "coef", coef_version) if coef_version else os.path.join(input_dir, "coef")
    if os.path.isdir(coef_dir):
        coef_by_from = load_all_coef(coef_dir, from_list)
        dm.models = build_all_models(coef_by_from)

    pmt_path = os.path.join(input_dir, "pmt_matrix.txt")
    if os.path.isfile(pmt_path):
        dm.pmt_matrix = load_pmt_matrix(pmt_path)

    if dial_name:
        dial_path = os.path.join(input_dir, "dial", f"{dial_name}.txt")
        dm.dial_data = load_dial(dial_path, all_list, dm.n_per)

    return dm


def print_model_matrix(dm: DataManager) -> None:
    """Print the transition matrix showing which models are loaded vs missing."""
    # Build set of configured (from, to) pairs from gam_models config
    configured = set()
    for gm in dm.gam_models:
        fs = gm.get("from_status", "")
        for m in gm.get("models", []):
            configured.add((fs, m.get("to_status", "")))

    # Collect all to-statuses
    to_set = set()
    for tos in dm.status_to_roll.values():
        to_set.update(tos)
    to_list = [s for s in dm.all_status_list if s in to_set]

    # Header
    col_w = 8
    header = "From\\To".ljust(col_w) + "".join(s.center(col_w) for s in to_list)
    sep = "-" * len(header)
    print(sep)
    print("  Transition Model Matrix")
    print(sep)
    print(header)
    print(sep)

    for from_s in dm.status_to_roll:
        row = from_s.ljust(col_w)
        roll_to = dm.status_to_roll[from_s]
        for to_s in to_list:
            if to_s == from_s:
                row += "(stay)".center(col_w)
            elif to_s in roll_to:
                model_name = f"from{from_s}_{to_s}"
                loaded = model_name in dm.models
                conf = (from_s, to_s) in configured
                if loaded:
                    row += "X".center(col_w)
                elif conf:
                    row += "o".center(col_w)
                else:
                    row += ".".center(col_w)
            else:
                row += "-".center(col_w)
        print(row)

    print(sep)
    print("  X = loaded   o = configured (not yet dumped)   . = no model (p=0)   - = not in roll")
    print()

    # PMT matrix
    if dm.pmt_matrix:
        print(sep)
        print("  Payment Matrix")
        print(sep)
        pmt_to = sorted(dm.pmt_matrix.keys())
        header2 = "From\\To".ljust(col_w) + "".join(s.center(col_w) for s in pmt_to)
        print(header2)
        print(sep)
        pmt_from = set()
        for ts in dm.pmt_matrix.values():
            pmt_from.update(ts.keys())
        for fs in sorted(pmt_from):
            row = fs.ljust(col_w)
            for ts in pmt_to:
                val = dm.pmt_matrix.get(ts, {}).get(fs, 0.0)
                row += f"{val:g}".center(col_w)
            print(row)
        print(sep)
    print()


# ---------------------------------------------------------------------------
# GAM dump (calls R subprocess with JSON config)
# ---------------------------------------------------------------------------

def _resolve_gam_paths(
    from_states: List[Dict], model_base: str,
) -> List[Dict]:
    resolved = []
    for entry in from_states:
        r = {
            "from_status": entry["from_status"],
            "output_file": entry["output_file"],
            "models": [],
        }
        for m in entry["models"]:
            path = m["path"]
            if not os.path.isabs(path):
                path = os.path.join(model_base, path)
            rm = {"path": path, "to_status": m["to_status"]}
            stacked = m.get("stacked", [])
            if stacked:
                rm["stacked"] = [
                    os.path.join(model_base, sp) if not os.path.isabs(sp) else sp
                    for sp in stacked
                ]
            r["models"].append(rm)
        resolved.append(r)
    return resolved


def dump_gam_models(
    config: Dict[str, Any],
    config_path: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> None:
    input_dir = config.get("input_dir", "input")
    if output_dir is None:
        coef_version = config.get("coef_version", "")
        output_dir = os.path.join(input_dir, "coef", coef_version) if coef_version else os.path.join(input_dir, "coef")
    model_base = config.get("model_base", "")
    from_states = config.get("gam_models", [])
    r_script = config.get("r_script", "tools/dump_gam_to_coef.R")
    rscript_exe = config.get("rscript_exe", "Rscript")

    os.makedirs(output_dir, exist_ok=True)

    resolved = _resolve_gam_paths(from_states, model_base)

    for entry in resolved:
        from_status = entry["from_status"]
        out_file = os.path.join(output_dir, entry["output_file"])
        for m in entry["models"]:
            model_path = m["path"]
            if not os.path.isfile(model_path):
                print(f"  WARNING: model not found: {model_path}")
                continue
            for sp in m.get("stacked", []):
                if not os.path.isfile(sp):
                    print(f"  WARNING: stacked model not found: {sp}")

        cmd = [rscript_exe, r_script, out_file]
        for m in entry["models"]:
            cmd.extend([m["path"], m["to_status"]])
            for sp in m.get("stacked", []):
                cmd.append(f"+{sp}")

        print(f"  Dumping from{from_status}: {', '.join(m['to_status'] for m in entry['models'])}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout.strip():
            print(result.stdout.rstrip())
        if result.returncode != 0:
            print(f"  STDERR: {result.stderr}")
            raise RuntimeError(f"R dump failed for from{from_status}")


