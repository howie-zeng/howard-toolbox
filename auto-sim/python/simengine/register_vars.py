"""Variable registration system for the roll-rate simulation engine.

Structure:
  1. Framework  — VarKind, VarDef, VarRegistry, helpers (rarely edited)
  2. Definitions — one reg_*() function per variable (edit here to add/change)
  3. build_default_registry() — calls all reg_*() functions
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =====================================================================
# 1. Framework
# =====================================================================

class VarKind(Enum):
    STATIC = auto()          # set once during prep, never changes
    TIME_VARYING = auto()    # updated each simulation period (function of period)
    MACRO = auto()           # time-dependent projection, flat by default
    PATH_DEPENDENT = auto()  # updated on each drawn transition (function of from->to)


@dataclass
class VarDef:
    """Registration record for a single variable.

    init_fn:   (loan, ctx) -> value           called once at prep
    update_fn: (loan, period) -> value        called each sim period (TIME_VARYING only)
    path_fn:   (loan, from_status, to_status) -> value
                                              called on each drawn transition (PATH_DEPENDENT only)
    """
    name: str
    kind: VarKind
    deps: List[str] = field(default_factory=list)
    default: Any = None
    init_fn: Optional[Callable] = None
    update_fn: Optional[Callable] = None
    path_fn: Optional[Callable] = None
    doc: str = ""


class VarRegistry:
    """Central registry of all variable definitions."""

    def __init__(self):
        self._vars: Dict[str, VarDef] = {}
        self._sorted_tv: Optional[List[VarDef]] = None

    def register(self, vdef: VarDef) -> None:
        self._vars[vdef.name] = vdef
        self._sorted_tv = None

    def register_c_fields(self, c_fields: Set[str]) -> None:
        """Auto-register c_* fields discovered from coef scan."""
        for cf in c_fields:
            if cf in self._vars:
                continue
            base = cf[2:]
            self.register(VarDef(
                name=cf, kind=VarKind.TIME_VARYING, deps=[base],
                update_fn=_make_c_updater(base),
                doc=f"Auto-copy of {base}",
            ))

    def get(self, name: str) -> Optional[VarDef]:
        return self._vars.get(name)

    def time_varying_names(self) -> Set[str]:
        return {v.name for v in self._vars.values() if v.kind == VarKind.TIME_VARYING}

    def macro_names(self) -> Set[str]:
        return {v.name for v in self._vars.values() if v.kind == VarKind.MACRO}

    def derive_initial(self, loan: Dict, ctx: Dict[str, Any] = None,
                       c_fields: Set[str] = frozenset()) -> None:
        """Apply all init_fn derivations once per loan at prep time."""
        if ctx is None:
            ctx = {}
        for vdef in self._vars.values():
            if vdef.init_fn and vdef.name not in loan:
                val = vdef.init_fn(loan, ctx)
                if val is not None:
                    loan[vdef.name] = val
        for cf in c_fields:
            base = cf[2:]
            if cf not in loan and loan.get(base) is not None:
                loan[cf] = float(loan[base])

    def init_time_state(self, loan: Dict) -> None:
        """Record starting state before sim loop."""
        r_dt = loan.get("r_dt")
        if not r_dt:
            raise ValueError(
                f"loan {loan.get('loan_id', '?')} has no r_dt — "
                "cannot initialise time-varying state"
            )
        y, m = _parse_year_month(r_dt)
        loan["_start_year"], loan["_start_month"] = y, m

    # Age-related variable names — updated AFTER model eval
    _AGE_VARS = frozenset({"loan_age", "age", "age_pct", "c_age_pct", "age_fc"})

    def step_period(self, loan: Dict, next_period: int) -> None:
        """Advance age fields, then update period context for next_period.

        Call AFTER model eval. Combines the old advance_age + update_period.
        """
        tv = self._topo_sorted_tv()
        # Pass 1: advance age (close current period)
        for vdef in tv:
            if vdef.update_fn and vdef.name in self._AGE_VARS:
                loan[vdef.name] = vdef.update_fn(loan, next_period)
        # Pass 2: update period context (prepare next period)
        for vdef in tv:
            if vdef.update_fn and vdef.name not in self._AGE_VARS:
                loan[vdef.name] = vdef.update_fn(loan, next_period)

    def step_transition(self, loan: Dict, from_status: str, to_status: str) -> None:
        """Update PATH_DEPENDENT vars from the drawn transition. Call right after
        the transition is drawn, so the new values feed the next period's scoring."""
        for vdef in self._vars.values():
            if vdef.kind == VarKind.PATH_DEPENDENT and vdef.path_fn:
                loan[vdef.name] = vdef.path_fn(loan, from_status, to_status)

    def _topo_sorted_tv(self) -> List[VarDef]:
        if self._sorted_tv is not None:
            return self._sorted_tv
        tv = {v.name: v for v in self._vars.values()
              if v.kind == VarKind.TIME_VARYING and v.update_fn}
        in_degree = {n: 0 for n in tv}
        adj: Dict[str, List[str]] = {n: [] for n in tv}
        for n, vd in tv.items():
            for d in vd.deps:
                if d in tv:
                    adj[d].append(n)
                    in_degree[n] += 1
        queue = [n for n, deg in in_degree.items() if deg == 0]
        result: List[VarDef] = []
        while queue:
            n = queue.pop(0)
            result.append(tv[n])
            for ch in adj[n]:
                in_degree[ch] -= 1
                if in_degree[ch] == 0:
                    queue.append(ch)
        seen = {v.name for v in result}
        for n, vd in tv.items():
            if n not in seen:
                result.append(vd)
        self._sorted_tv = result
        return result


# -- Helpers --

def _parse_year_month(date_str) -> Tuple[int, int]:
    """Extract (year, month_num) from date string.

    Raises ValueError if date_str is None or unparseable.
    """
    if date_str is None:
        raise ValueError("date_str is None")
    s = str(date_str).strip()
    if "/" in s:
        p = s.split("/")
        return int(p[2]), int(p[0])
    else:
        p = s.split("-")
        return int(p[0]), int(p[1])


def _end_of_month(year: int, month: int) -> str:
    day = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-{day:02d}"


def _advance_month(year: int, month: int, periods: int) -> Tuple[int, int]:
    total = (year * 12) + (month - 1) + periods
    return total // 12, total % 12 + 1


def _date_to_ym(date_str) -> str:
    if date_str is None:
        return ""
    s = str(date_str).strip()
    if "/" in s:
        p = s.split("/")
        return f"{p[2]}-{int(p[0]):02d}"
    return s[:7]


def _ym_offset(ym: str, months: int) -> str:
    try:
        y, m = int(ym[:4]), int(ym[5:7])
        total = y * 12 + (m - 1) + months
        return f"{total // 12:04d}-{total % 12 + 1:02d}"
    except (ValueError, IndexError):
        return ""


def _bucket_fico(fico_val,
                 breaks=(-float("inf"), 620, 650, 680, 710, 750, float("inf")),
                 labels=("[0-620)", "[620-650)", "[650-680)", "[680-710)",
                         "[710-750)", "[750+)")):
    if fico_val is None:
        return ""
    v = float(fico_val)
    for i in range(len(breaks) - 1):
        if breaks[i] <= v < breaks[i + 1]:
            return labels[i]
    return labels[-1]


def _make_c_updater(base: str) -> Callable:
    def _u(loan, per):
        return loan.get(base)
    return _u


# =====================================================================
# 2. Variable definitions — one function per variable
# =====================================================================

# ----- TIME-VARYING -----

def reg_r_dt(reg: VarRegistry):
    """r_dt = report date, advanced to end of next month each period."""

    def update(loan, per):
        sy = loan["_start_year"]
        sm = loan["_start_month"]
        y, m = _advance_month(sy, sm, per)
        return _end_of_month(y, m)

    reg.register(VarDef(
        name="r_dt",
        kind=VarKind.TIME_VARYING,
        deps=[],
        update_fn=update,
    ))


def reg_loan_age(reg: VarRegistry):
    """loan_age = increments by 1 each period."""

    reg.register(VarDef(
        name="loan_age",
        kind=VarKind.TIME_VARYING,
        deps=[],
        update_fn=lambda loan, per: loan.get("loan_age", 0) + 1,
    ))


def reg_age(reg: VarRegistry):
    """age = alias for loan_age."""

    reg.register(VarDef(
        name="age",
        kind=VarKind.TIME_VARYING,
        deps=["loan_age"],
        init_fn=lambda loan, ctx: loan.get("loan_age"),
        update_fn=lambda loan, per: loan["loan_age"],
    ))


def reg_age_pct(reg: VarRegistry):
    """age_pct = loan_age / orig_term (fraction of the loan's full life; uses the
    ORIGINAL term, not the remaining term that drives amortization)."""

    def _oterm(loan):
        # prefer orig_term; fall back to term for tapes without the split
        return loan.get("orig_term", loan.get("term"))

    def init(loan, ctx):
        la, t = loan.get("loan_age"), _oterm(loan)
        if la is not None and t is not None and float(t) != 0:
            return float(la) / float(t)
        return None

    def update(loan, per):
        t = float(_oterm(loan) or 1)
        return float(loan["loan_age"]) / t if t != 0 else 0.0

    reg.register(VarDef(
        name="age_pct",
        kind=VarKind.TIME_VARYING,
        deps=["loan_age", "orig_term"],
        init_fn=init,
        update_fn=update,
    ))


def reg_c_age_pct(reg: VarRegistry):
    """c_age_pct = smooth-clampable copy of age_pct."""

    reg.register(VarDef(
        name="c_age_pct",
        kind=VarKind.TIME_VARYING,
        deps=["age_pct"],
        update_fn=lambda loan, per: loan.get("age_pct"),
    ))


def reg_month(reg: VarRegistry):
    """month = name of r_dt's own month (report-anchored, matching training's
    add_asof_features — no shift). The old +1 shift for season_shift=1 was
    dropped in the retrain.
    """

    MONTHS = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    def _month_name(loan, per):
        r_dt = loan.get("r_dt")
        if r_dt:
            _, m = _parse_year_month(r_dt)
        else:
            _, m = _advance_month(loan["_start_year"], loan["_start_month"], per)
        return MONTHS[m - 1]

    reg.register(VarDef(
        name="month",
        kind=VarKind.TIME_VARYING,
        deps=["r_dt"],
        init_fn=lambda loan, ctx: _month_name(loan, 0),
        update_fn=_month_name,
    ))


def reg_days_to_month_end(reg: VarRegistry):
    """days_to_month_end = days from payment day to r_dt's month-end
    (report-anchored, matching training's _add_days_to_month_end). Bigger gap =
    more room to roll late by report. Old +1-month shift dropped in the retrain."""

    def _days(loan, per):
        r_dt = loan.get("r_dt")
        if r_dt:
            year, month = _parse_year_month(r_dt)
        else:
            year, month = _advance_month(loan["_start_year"],
                                         loan["_start_month"], per)
        pmt_day = int(loan.get("pmt_day", 15))
        dim = calendar.monthrange(year, month)[1]
        return dim - min(pmt_day, dim)

    reg.register(VarDef(
        name="days_to_month_end",
        kind=VarKind.TIME_VARYING,
        deps=["r_dt", "pmt_day"],
        init_fn=lambda loan, ctx: _days(loan, 0) if loan.get("r_dt") else None,
        update_fn=_days,
    ))


# ----- MACRO -----

def reg_cpi_inflator_36(reg: VarRegistry):
    """cpi_inflator_36 = (CPI_now / CPI_36mo_ago) - 1.  Default flat 1.0."""

    def init(loan, ctx):
        cpi = ctx.get("cpi_lookup")
        if not cpi:
            return None
        r_ym = _date_to_ym(loan.get("r_dt"))
        cpi_now = cpi.get(r_ym)
        if cpi_now:
            cpi_36 = cpi.get(_ym_offset(r_ym, -36))
            if cpi_36 and cpi_36 > 0:
                return round(cpi_now / cpi_36 - 1, 4)
        return None

    reg.register(VarDef(
        name="cpi_inflator_36",
        kind=VarKind.MACRO,
        deps=["r_dt"],
        default=1.0,
        init_fn=init,
    ))


def reg_cpi_inflator_12(reg: VarRegistry):
    """cpi_inflator_12 = (CPI_now / CPI_12mo_ago) - 1.  Default flat 1.0."""

    def init(loan, ctx):
        cpi = ctx.get("cpi_lookup")
        if not cpi:
            return None
        r_ym = _date_to_ym(loan.get("r_dt"))
        cpi_now = cpi.get(r_ym)
        if cpi_now:
            cpi_12 = cpi.get(_ym_offset(r_ym, -12))
            if cpi_12 and cpi_12 > 0:
                return round(cpi_now / cpi_12 - 1, 4)
        return None

    reg.register(VarDef(
        name="cpi_inflator_12",
        kind=VarKind.MACRO,
        deps=["r_dt"],
        default=1.0,
        init_fn=init,
    ))


# ----- STATIC -----

def reg_int_rate(reg: VarRegistry):
    """int_rate = note_rate (copied once at prep)."""

    reg.register(VarDef(
        name="int_rate",
        kind=VarKind.STATIC,
        deps=["note_rate"],
        init_fn=lambda loan, ctx: loan.get("note_rate"),
    ))


def reg_pmt_day(reg: VarRegistry):
    """pmt_day = payment day-of-month. Prefer a tape value (auto_tape fills
    missing first-payment dates with the deal median); else derive from
    f_pmt_dt; else 15."""

    def init(loan, ctx):
        existing = loan.get("pmt_day")
        if existing is not None:
            try:
                return int(existing)
            except (TypeError, ValueError):
                pass
        fdt = loan.get("f_pmt_dt")
        if fdt is None:
            return None
        s = str(fdt).strip()
        try:
            return int(s.split("/")[1]) if "/" in s else int(s.split("-")[2])
        except (IndexError, ValueError):
            return 15

    reg.register(VarDef(
        name="pmt_day",
        kind=VarKind.STATIC,
        deps=["f_pmt_dt"],
        init_fn=init,
    ))

def reg_rate_incentive(reg: VarRegistry):
    """rate_incentive_ALL = coupon_at_r_dt - coupon_at_vintage.

    MACRO (matches C++ VarKind::MACRO), not STATIC: recomputed every period from
    the coupon lookup (runner macro loop). Classifying it static froze its ctp
    smooth in the logit cache at the prep value, so it stopped tracking rising
    rates and Python over-predicted prepay. init_fn seeds period 0."""

    def init(loan, ctx):
        fc = ctx.get("fico_coupon_lookup")
        if not fc:
            return None
        orig_ym = _date_to_ym(loan.get("orig_dt"))
        r_ym = _date_to_ym(loan.get("r_dt"))
        fico_bkt = loan.get("fico_bkt") or _bucket_fico(loan.get("ofico"))  # prefer tape's label
        vint_key = orig_ym.replace("-", "") if orig_ym else ""
        r_key = r_ym.replace("-", "") if r_ym else ""
        coupon_vint = fc.get(f"{vint_key}|{fico_bkt}")
        coupon_r = fc.get(f"{r_key}|{fico_bkt}")
        if coupon_r is not None and coupon_vint is not None:
            # Keep full precision: training and C++ don't round; rounding to 4dp
            # here desynced the ctp smooth vs C++.
            return coupon_r - coupon_vint
        return None

    reg.register(VarDef(
        name="rate_incentive_ALL",
        kind=VarKind.MACRO,
        deps=["ofico", "orig_dt", "r_dt"],
        init_fn=init,
    ))

def reg_lending_environment(reg: VarRegistry):
    """lending_environment = year + (month - 1)/12 of orig date (smooth numeric
    for GAM splines). Stored raw; the smooth's grid bounds handle clamping (the
    model's pmax() floors at 2021).
    """

    def init(loan, ctx):
        orig_dt = loan.get("orig_dt")
        if orig_dt is None:
            return None
        y, m = _parse_year_month(orig_dt)
        return round(y + (m - 1) / 12, 2)

    reg.register(VarDef(
        name="lending_environment",
        kind=VarKind.STATIC,
        deps=["orig_dt"],
        init_fn=init,
    ))


def reg_fico_bkt(reg: VarRegistry):
    """_fico_bkt = FICO bucket from ofico (e.g. '[650-680)').
    Used by rate_incentive_ALL recomputation at sim time.
    """

    def init(loan, ctx):
        bkt = loan.get("fico_bkt")          # prefer the tape's own bucket label
        if bkt:
            return bkt
        ofico = loan.get("ofico")
        return _bucket_fico(ofico) if ofico is not None else None

    reg.register(VarDef(
        name="_fico_bkt",
        kind=VarKind.STATIC,
        deps=["ofico"],
        init_fn=init,
    ))


def reg_coupon_at_vintage(reg: VarRegistry):
    """_coupon_at_vintage = FICO coupon at origination (from fico_coupon_lookup
    by orig_dt + ofico bucket). Used by rate_incentive_ALL recomputation.
    """

    def init(loan, ctx):
        fc = ctx.get("fico_coupon_lookup")
        if not fc:
            return None
        orig_ym = _date_to_ym(loan.get("orig_dt"))
        fico_bkt = loan.get("fico_bkt") or _bucket_fico(loan.get("ofico"))  # prefer tape's label
        vint_key = orig_ym.replace("-", "") if orig_ym else ""
        return fc.get(f"{vint_key}|{fico_bkt}")

    reg.register(VarDef(
        name="_coupon_at_vintage",
        kind=VarKind.STATIC,
        deps=["ofico", "orig_dt"],
        init_fn=init,
    ))


# =====================================================================
# 3. Registry builder — calls all reg_*() functions
# =====================================================================

# dq6_bkt: bounded 6-month delinquency memory. State is a 6-bit rolling mask in
# loan['_dq6_mask'] (bit k = delinquent k months ago). Bucket = f(#bits set),
# matching consolidate.py's pd.cut(bins=[-1,0,1,3,6], labels=["0","1","2-3","4-6"]).
# Precompute count->bucket and mask->bucket so the hot path is one shift + one lookup.
_DQ6_COUNT_BUCKET = ("0", "1", "2-3", "2-3", "4-6", "4-6", "4-6")     # index = count 0..6
_DQ6_MASK_BUCKET = tuple(_DQ6_COUNT_BUCKET[bin(m).count("1")] for m in range(64))
_DQ_STATES = frozenset(("D1M", "D2M", "D3M", "D4M"))


def reg_dq6_bkt(reg: VarRegistry):
    """# months delinquent (D1M..D4M) in the TRAILING 6 (excl. current month),
    bucketed 0/1/2-3/4-6 — a bounded, decaying delinquency memory. O(1) per step:
    a 6-bit rolling mask + one table lookup. Timing mirrors consolidate.py's
    shift(1..6): each step records the state the loan was IN this period
    (from_status), and the value read when scoring period t reflects t-1..t-6."""
    def init(loan, ctx):
        m = loan.get("_dq6_mask")
        if m is None:
            return loan.get("dq6_bkt", "0")                  # prep seeded the mask/bucket
        return _DQ6_MASK_BUCKET[int(m) & 63]

    def path(loan, from_status, to_status):
        m = int(loan.get("_dq6_mask", 0) or 0)
        flag = 1 if from_status in _DQ_STATES else 0
        m = ((m << 1) | flag) & 63
        loan["_dq6_mask"] = m
        return _DQ6_MASK_BUCKET[m]

    reg.register(VarDef(
        name="dq6_bkt", kind=VarKind.PATH_DEPENDENT,
        default="0", init_fn=init, path_fn=path,
        doc="Trailing-6-month delinquency count, bucketed (0/1/2-3/4-6).",
    ))


def build_default_registry() -> VarRegistry:
    """Create the standard registry by calling every reg_*() definition."""
    reg = VarRegistry()

    # Time-varying
    reg_r_dt(reg)
    reg_loan_age(reg)
    reg_age(reg)
    reg_age_pct(reg)
    reg_c_age_pct(reg)
    reg_month(reg)
    reg_days_to_month_end(reg)

    # Macro
    reg_cpi_inflator_36(reg)
    reg_cpi_inflator_12(reg)

    # Static (auto's covariates; MPL-only vars — oterm_f, month_group,
    # adj_balance_cpi, rel_fico_ratio_ALL, term_fico, term_platform, vint_qtr —
    # dropped since auto doesn't use them)
    reg_int_rate(reg)
    reg_pmt_day(reg)
    reg_rate_incentive(reg)
    reg_lending_environment(reg)
    reg_fico_bkt(reg)
    reg_coupon_at_vintage(reg)

    # Path-dependent delinquency-history feature: bounded 6-month DQ memory used by
    # the history-aware ctd1 (PRIME_BASE_HISTORY). Superseded the older ever_dq_flag
    # / months_in_current_bkt latch+streak (removed — they homogenized the Current
    # pool and over-suppressed C->D1M). dq6_bkt decays, so re-default risk cools off.
    reg_dq6_bkt(reg)

    return reg
