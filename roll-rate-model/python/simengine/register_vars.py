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
    STATIC = auto()        # set once during prep, never changes
    TIME_VARYING = auto()  # updated each simulation period
    MACRO = auto()         # time-dependent projection, flat by default


@dataclass
class VarDef:
    """Registration record for a single variable.

    init_fn:   (loan, ctx) -> value   called once at prep
    update_fn: (loan, period) -> value   called each sim period (TIME_VARYING only)
    """
    name: str
    kind: VarKind
    deps: List[str] = field(default_factory=list)
    default: Any = None
    init_fn: Optional[Callable] = None
    update_fn: Optional[Callable] = None
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

    def by_kind(self, kind: VarKind) -> List[VarDef]:
        return [v for v in self._vars.values() if v.kind == kind]

    def time_varying_names(self) -> Set[str]:
        return {v.name for v in self._vars.values() if v.kind == VarKind.TIME_VARYING}

    def macro_names(self) -> Set[str]:
        return {v.name for v in self._vars.values() if v.kind == VarKind.MACRO}

    def static_names(self) -> Set[str]:
        return {v.name for v in self._vars.values() if v.kind == VarKind.STATIC}

    def all_names(self) -> Set[str]:
        return set(self._vars.keys())

    def macro_defaults(self) -> Dict[str, Any]:
        return {v.name: v.default for v in self._vars.values()
                if v.kind == VarKind.MACRO and v.default is not None}

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


# -- Macro scenario helpers --

def macro_ramp(start: float, end: float, n_months: int) -> List[float]:
    """Linear ramp: macro_ramp(0.02, 0.05, 4) -> [0.02, 0.03, 0.04, 0.05]"""
    if n_months <= 1:
        return [end]
    return [start + (end - start) * i / (n_months - 1) for i in range(n_months)]


def macro_step(before: float, after: float, step_month: int,
               n_months: int) -> List[float]:
    """Step function: flat at `before` until step_month, then `after`."""
    return [before if i < step_month else after for i in range(n_months)]


def macro_flat(value: float, n_months: Optional[int] = None):
    """Constant. Returns scalar if n_months is None, else a list."""
    return value if n_months is None else [value] * n_months


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
    """age_pct = loan_age / term."""

    def init(loan, ctx):
        la, t = loan.get("loan_age"), loan.get("term")
        if la is not None and t is not None and float(t) != 0:
            return float(la) / float(t)
        return None

    def update(loan, per):
        t = float(loan.get("term", 1))
        return float(loan["loan_age"]) / t if t != 0 else 0.0

    reg.register(VarDef(
        name="age_pct",
        kind=VarKind.TIME_VARYING,
        deps=["loan_age", "term"],
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
    """month = calendar month name of r_dt, regularized to standard month names."""

    MONTHS = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    def update(loan, per):
        r_dt = loan.get("r_dt")
        if r_dt:
            _, m = _parse_year_month(r_dt)
            return MONTHS[m - 1]
        sy = loan["_start_year"]
        sm = loan["_start_month"]
        _, pm = _advance_month(sy, sm, per)
        return MONTHS[pm - 1]

    reg.register(VarDef(
        name="month",
        kind=VarKind.TIME_VARYING,
        deps=["r_dt"],
        update_fn=update,
    ))


def reg_days_to_month_end(reg: VarRegistry):
    """days_to_month_end = days remaining in the projection month after pmt_day."""

    def update(loan, per):
        r_dt = loan.get("r_dt")
        if r_dt:
            year, month = _parse_year_month(r_dt)
        else:
            sy = loan["_start_year"]
            sm = loan["_start_month"]
            year, month = _advance_month(sy, sm, per)
        pmt_day = int(loan.get("pmt_day", 15))
        dim = calendar.monthrange(year, month)[1]
        return dim - min(pmt_day, dim)

    reg.register(VarDef(
        name="days_to_month_end",
        kind=VarKind.TIME_VARYING,
        deps=["r_dt", "pmt_day"],
        update_fn=update,
    ))


def reg_month_group(reg: VarRegistry):
    """month_group = '30_Day' if days_to_month_end <= 28, else '31_Day'."""

    reg.register(VarDef(
        name="month_group",
        kind=VarKind.TIME_VARYING,
        deps=["days_to_month_end"],
        update_fn=lambda loan, per: (
            "30_Day" if loan.get("days_to_month_end", 30) <= 28 else "31_Day"
        ),
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


def reg_oterm_f(reg: VarRegistry):
    """oterm_f = str(term), categorical factor for model lookup."""

    def init(loan, ctx):
        t = loan.get("term")
        if t is not None:
            return str(int(t)) if isinstance(t, (int, float)) else str(t)
        return None

    reg.register(VarDef(
        name="oterm_f",
        kind=VarKind.STATIC,
        deps=["term"],
        init_fn=init,
    ))


def reg_pmt_day(reg: VarRegistry):
    """pmt_day = day-of-month extracted from first payment date."""

    def init(loan, ctx):
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


def reg_adj_balance_cpi(reg: VarRegistry):
    """adj_balance_cpi = orig_bal / CPI_at_origination.  Computed once at prep."""

    def init(loan, ctx):
        cpi = ctx.get("cpi_lookup")
        if not cpi:
            return None
        orig_ym = _date_to_ym(loan.get("orig_dt"))
        cpi_orig = cpi.get(orig_ym)
        orig_bal = loan.get("orig_bal")
        if cpi_orig and cpi_orig > 0 and orig_bal is not None:
            return round(float(orig_bal) / cpi_orig, 4)
        return None

    reg.register(VarDef(
        name="adj_balance_cpi",
        kind=VarKind.STATIC,
        deps=["orig_bal", "orig_dt"],
        init_fn=init,
    ))


def reg_rel_fico_ratio(reg: VarRegistry):
    """rel_fico_ratio_ALL = note_rate / fico_bkt_coupon at vintage.  Computed once at prep."""

    def init(loan, ctx):
        fc = ctx.get("fico_coupon_lookup")
        if not fc:
            return None
        orig_ym = _date_to_ym(loan.get("orig_dt"))
        fico_bkt = _bucket_fico(loan.get("ofico"))
        note_rate = loan.get("note_rate")
        vint_key = orig_ym.replace("-", "") if orig_ym else ""
        coupon = fc.get(f"{vint_key}|{fico_bkt}")
        if note_rate is not None and coupon and coupon > 0:
            return round(float(note_rate) / coupon, 4)
        return None

    reg.register(VarDef(
        name="rel_fico_ratio_ALL",
        kind=VarKind.STATIC,
        deps=["note_rate", "ofico", "orig_dt"],
        init_fn=init,
    ))


def reg_term_fico(reg: VarRegistry):
    """term_fico = term crossed with FICO bucket, e.g. '36.[650-680)'."""

    def init(loan, ctx):
        term = loan.get("term")
        ofico = loan.get("ofico")
        if term is None or ofico is None:
            return ""
        t = int(term) if isinstance(term, (int, float)) else term
        bkt = _bucket_fico(ofico)
        return f"{t}.{bkt}"

    reg.register(VarDef(
        name="term_fico",
        kind=VarKind.STATIC,
        deps=["term", "ofico"],
        init_fn=init,
    ))


def reg_term_platform(reg: VarRegistry):
    """term_platform = term crossed with platform_f, e.g. '36.Prosper'."""

    def init(loan, ctx):
        term = loan.get("term")
        pf = loan.get("platform_f")
        if term is None or pf is None:
            return ""
        t = int(term) if isinstance(term, (int, float)) else term
        return f"{t}.{pf}"

    reg.register(VarDef(
        name="term_platform",
        kind=VarKind.STATIC,
        deps=["term", "platform_f"],
        init_fn=init,
    ))


def reg_rate_incentive(reg: VarRegistry):
    """rate_incentive_ALL = coupon_at_r_dt - coupon_at_vintage.  Computed once at prep."""

    def init(loan, ctx):
        fc = ctx.get("fico_coupon_lookup")
        if not fc:
            return None
        orig_ym = _date_to_ym(loan.get("orig_dt"))
        r_ym = _date_to_ym(loan.get("r_dt"))
        fico_bkt = _bucket_fico(loan.get("ofico"))
        vint_key = orig_ym.replace("-", "") if orig_ym else ""
        r_key = r_ym.replace("-", "") if r_ym else ""
        coupon_vint = fc.get(f"{vint_key}|{fico_bkt}")
        coupon_r = fc.get(f"{r_key}|{fico_bkt}")
        if coupon_r is not None and coupon_vint is not None:
            return round(coupon_r - coupon_vint, 4)
        return None

    reg.register(VarDef(
        name="rate_incentive_ALL",
        kind=VarKind.STATIC,
        deps=["ofico", "orig_dt", "r_dt"],
        init_fn=init,
    ))


def reg_vint_qtr(reg: VarRegistry):
    """vint_qtr = vintage quarter derived from orig_dt, e.g. '2025-Q1'."""

    def init(loan, ctx):
        ym = _date_to_ym(loan.get("orig_dt"))
        if not ym or len(ym) < 7:
            return None
        try:
            y, m = int(ym[:4]), int(ym[5:7])
            return f"{y}-Q{(m - 1) // 3 + 1}"
        except (ValueError, IndexError):
            return None

    reg.register(VarDef(
        name="vint_qtr",
        kind=VarKind.STATIC,
        deps=["orig_dt"],
        init_fn=init,
    ))


def reg_lending_environment(reg: VarRegistry):
    """lending_environment = year + (month - 1) / 12 of origination date.

    Captures the macro lending regime as a smooth numeric for GAM splines.
    Floored at 2021 by the model's pmax() wrapper — we store the raw value
    and let the smooth's grid bounds handle clamping.
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
    """_fico_bkt = FICO bucket string from ofico (e.g. '[650-680)').

    Used by rate_incentive_ALL recomputation at sim time.
    """

    def init(loan, ctx):
        ofico = loan.get("ofico")
        if ofico is None:
            return None
        return _bucket_fico(ofico)

    reg.register(VarDef(
        name="_fico_bkt",
        kind=VarKind.STATIC,
        deps=["ofico"],
        init_fn=init,
    ))


def reg_coupon_at_vintage(reg: VarRegistry):
    """_coupon_at_vintage = FICO coupon rate at origination.

    Looked up from fico_coupon_lookup by orig_dt + ofico bucket.
    Used by rate_incentive_ALL recomputation at sim time.
    """

    def init(loan, ctx):
        fc = ctx.get("fico_coupon_lookup")
        if not fc:
            return None
        orig_ym = _date_to_ym(loan.get("orig_dt"))
        fico_bkt = _bucket_fico(loan.get("ofico"))
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
    reg_month_group(reg)

    # Macro
    reg_cpi_inflator_36(reg)
    reg_cpi_inflator_12(reg)

    # Static
    reg_int_rate(reg)
    reg_oterm_f(reg)
    reg_pmt_day(reg)
    reg_adj_balance_cpi(reg)
    reg_rel_fico_ratio(reg)
    reg_rate_incentive(reg)
    reg_term_fico(reg)
    reg_term_platform(reg)
    reg_vint_qtr(reg)
    reg_lending_environment(reg)
    reg_fico_bkt(reg)
    reg_coupon_at_vintage(reg)

    return reg
