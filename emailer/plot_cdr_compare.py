"""Generate CDR comparison plots (prod vs dialed) for email updates.

Sibling of ``plot_vector_compare.py``: same Figure/Agg + ``assets/<name>/`` layout,
but reads the long-format CSV that ``dump_model_vectors``-style exports produce
(one row per purpose/deal/scenario/month) instead of an Excel sheet.

Views:

* ``deal``    (default) one figure per deal, three panels side by side -- Base,
              SuperBull, SuperBear -- each with prod against dialed. One image
              per deal keeps an email to 49 attachments instead of 147; pass
              ``--panels split`` for a separate PNG per deal per scenario.
* ``cohort``  one chart per scenario aggregating each cohort's balance-weighted
              mean. Useful as a summary because the untouched cohort's two lines
              land exactly on top of each other.

Usage::

    python emailer/plot_cdr_compare.py                          # every deal, 3 panels each
    python emailer/plot_cdr_compare.py --panels split           # one PNG per deal per scenario
    python emailer/plot_cdr_compare.py --view cohort            # cohort summary only
    python emailer/plot_cdr_compare.py --deals "VSTA 2024-CES1" # just one deal
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

EMAILER_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = Path(r"S:\QR\hzeng\heloc_jumbo_cdr_compare.csv")
DEFAULT_OUTPUT_DIR = EMAILER_DIR / "assets" / "heloc_jumbo_cdr"
DEFAULT_SCENARIOS = ["Base", "SuperBull", "SuperBear"]
DEFAULT_MAX_MONTH = 120

# Colours are the dataviz categorical slots 1 and 2, which pass the CVD and
# contrast checks in both light and dark (worst-pair delta-E 24.7 / 26.8). The JPM
# grey matches plot_vector_compare.py so the two scripts' output reads as a family;
# it is a reference line, so it stays thinner and recedes.
MODEL_STYLES = {
    "prod": {"label": "Prod", "color": "#2a78d6", "linewidth": 2.2},
    "new": {"label": "New (dialed)", "color": "#eb6834", "linewidth": 2.4},
    "jpm": {"label": "JPM", "color": "#808080", "linewidth": 2.0},
}
# A purpose_name containing any of these marks the row as the JPM reference series.
JPM_MARKERS = ("JPM",)

# Jumbo pool ids in this portfolio; everything else in the file is a HELOC-family
# deal. FIGRE and GRADE-FIG run V2_0_7 and carry none of the dials -> control.
JUMBO_POOL_IDS = {"EZE", "EZT", "EZW", "F7S", "F8J", "G9X", "GB8", "GIL", "GWG", "IBT", "IH7", "QVZ"}
COHORT_STYLES = {
    "HELOC (dialed V1_0_V5)": "-",
    "Jumbo (dialed v1.8.4)": "--",
    "Figure / Grade-FIG (control)": ":",
}
SCENARIO_TITLES = {"Base": "Base", "SuperBull": "SuperBull", "SuperBear": "SuperBear"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot CDR comparisons, prod vs dialed.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="long-format vector CSV")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--view", choices=["deal", "cohort", "both"], default="deal")
    parser.add_argument("--panels", choices=["combined", "split"], default="combined",
                        help="combined: one figure per deal with a panel per scenario; "
                             "split: one PNG per deal per scenario")
    parser.add_argument("--scenarios", default=",".join(DEFAULT_SCENARIOS))
    parser.add_argument("--max-month", type=int, default=DEFAULT_MAX_MONTH)
    parser.add_argument("--metric", default="cdr", help="column to plot (cdr, cpr, sev, d60, wac)")
    parser.add_argument("--deals", default=None, help="comma-separated deal names (default: all)")
    return parser


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()


def _as_float(value: object) -> float | None:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _cohort(pool_id: str, deal: str) -> str:
    if deal.startswith("FIGRE") or (deal.startswith("GRADE") and "FIG" in deal):
        return "Figure / Grade-FIG (control)"
    return "Jumbo (dialed v1.8.4)" if pool_id in JUMBO_POOL_IDS else "HELOC (dialed V1_0_V5)"


def load_rows(csv_path: Path, metric: str, max_month: int) -> list[dict[str, object]]:
    """Long-format rows, one per purpose/deal/scenario/month, with cohort attached."""
    rows: list[dict[str, object]] = []
    with csv_path.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            month, value, bal = _as_float(r["month"]), _as_float(r[metric]), _as_float(r["sbal"])
            if month is None or value is None or month > max_month:
                continue
            deal = str(r["bbg_name"])
            pname = str(r["purpose_name"]).upper()
            side = ("jpm" if any(m in pname for m in JPM_MARKERS)
                    else "new" if pname.startswith("NEW") else "prod")
            rows.append({
                "side": side,
                "deal": deal,
                "pool": str(r["poolid"]),
                "cohort": _cohort(str(r["poolid"]), deal),
                "scenario": str(r["scen"]),
                "month": month,
                "value": value,
                "weight": bal or 0.0,
            })
    if not rows:
        raise SystemExit(f"no usable rows for metric {metric!r} in {csv_path}")
    return rows


def _weighted_curve(rows: list[dict[str, object]]) -> tuple[list[float], list[float]]:
    """Balance-weighted mean by month; falls back to a plain mean where balance is 0."""
    num: dict[float, float] = defaultdict(float)
    den: dict[float, float] = defaultdict(float)
    plain: dict[float, list[float]] = defaultdict(list)
    for r in rows:
        m, v, w = float(r["month"]), float(r["value"]), float(r["weight"])
        num[m] += v * w
        den[m] += w
        plain[m].append(v)
    months = sorted(num)
    return months, [
        (num[m] / den[m]) if den[m] else (sum(plain[m]) / len(plain[m])) for m in months
    ]


def _finish(ax, fig, title: str, metric: str, max_month: int, out: Path) -> Path:
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel("Projection Month")
    ax.set_ylabel(f"{metric.upper()} (%)")
    ax.grid(True, alpha=0.25)
    ax.set_xlim(left=1, right=max_month)
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper right", frameon=True, fontsize=9)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    return out


def plot_cohorts(rows, scenario: str, output_dir: Path, metric: str, max_month: int) -> Path:
    """One chart per scenario: every cohort, prod vs dialed. Control lines overlap."""
    fig = Figure(figsize=(8.6, 4.8), dpi=150)
    FigureCanvasAgg(fig)
    ax = fig.subplots()
    for cohort, dash in COHORT_STYLES.items():
        for side, style in MODEL_STYLES.items():
            sub = [r for r in rows
                   if r["scenario"] == scenario and r["cohort"] == cohort and r["side"] == side]
            if not sub:
                continue
            months, vals = _weighted_curve(sub)
            ax.plot(months, vals, linestyle=dash, color=str(style["color"]),
                    linewidth=float(style["linewidth"]),
                    label=f"{cohort.split(' (')[0]} - {style['label']}")
    return _finish(ax, fig, f"{metric.upper()} by cohort - {scenario}", metric, max_month,
                   output_dir / f"cohort_{_slug(metric)}_{_slug(scenario)}.png")


def plot_deal(rows, deal: str, scenario: str, output_dir: Path, metric: str, max_month: int):
    """One chart for one deal and one scenario: prod vs dialed."""
    subset = [r for r in rows if r["deal"] == deal and r["scenario"] == scenario]
    if not subset or len({r["side"] for r in subset}) < 2:
        return None
    fig = Figure(figsize=(8.6, 4.8), dpi=150)
    FigureCanvasAgg(fig)
    ax = fig.subplots()
    for side, style in MODEL_STYLES.items():
        months, vals = _weighted_curve([r for r in subset if r["side"] == side])
        ax.plot(months, vals, color=str(style["color"]), linewidth=float(style["linewidth"]),
                label=str(style["label"]))
    return _finish(ax, fig, f"{deal} - {scenario}", metric, max_month,
                   output_dir / f"{_slug(deal)}_{_slug(metric)}_{_slug(scenario)}.png")


def plot_deal_panels(rows, deal: str, scenarios: list[str], output_dir: Path,
                     metric: str, max_month: int):
    """One figure per deal, a panel per scenario, prod vs dialed in each.

    The panels share a y-axis so the scenarios are directly comparable -- a per-panel
    scale would make a calm Base look as severe as SuperBear.
    """
    by_scen = {s: [r for r in rows if r["deal"] == deal and r["scenario"] == s] for s in scenarios}
    usable = [s for s in scenarios if by_scen[s] and len({r["side"] for r in by_scen[s]}) >= 2]
    if not usable:
        return None

    ymax = max(float(r["value"]) for s in usable for r in by_scen[s]) * 1.08 or 1.0
    fig = Figure(figsize=(4.6 * len(usable), 4.3), dpi=150)
    FigureCanvasAgg(fig)
    axes = fig.subplots(1, len(usable), sharey=True)
    if len(usable) == 1:
        axes = [axes]

    for ax, scen in zip(axes, usable):
        for side, style in MODEL_STYLES.items():
            months, vals = _weighted_curve([r for r in by_scen[scen] if r["side"] == side])
            ax.plot(months, vals, color=str(style["color"]),
                    linewidth=float(style["linewidth"]), label=str(style["label"]))
        ax.set_title(SCENARIO_TITLES.get(scen, scen), fontsize=11, fontweight="bold")
        ax.set_xlabel("Projection Month")
        ax.grid(True, alpha=0.25)
        ax.set_xlim(left=1, right=max_month)
        ax.set_ylim(bottom=0, top=ymax)
    axes[0].set_ylabel(f"{metric.upper()} (%)")
    axes[-1].legend(loc="upper right", frameon=True, fontsize=9)

    fig.suptitle(f"{deal} - {metric.upper()}, prod vs dialed", fontsize=13, fontweight="bold")
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / f"{_slug(deal)}_{_slug(metric)}_panels.png"
    fig.savefig(out, bbox_inches="tight")
    return out


def deal_shift(rows, deal: str) -> float:
    """Mean dialed/prod ratio across scenarios -- used only to order the output."""
    p = [float(r["value"]) for r in rows if r["deal"] == deal and r["side"] == "prod"]
    n = [float(r["value"]) for r in rows if r["deal"] == deal and r["side"] == "new"]
    if not p or not n or sum(p) == 0:
        return 1.0
    return sum(n) / sum(p)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    scenarios = [s.strip() for s in args.scenarios.split(",") if s.strip()]
    rows = load_rows(args.csv, args.metric, args.max_month)

    if args.deals:
        wanted = {d.strip().upper() for d in args.deals.split(",") if d.strip()}
        deals = [d for d in sorted({str(r["deal"]) for r in rows}) if d.upper() in wanted]
        missing = wanted - {d.upper() for d in deals}
        if missing:
            print(f"[warn] not in the CSV: {', '.join(sorted(missing))}")
    else:
        deals = sorted({str(r["deal"]) for r in rows})

    written: list[Path] = []
    if args.view in ("deal", "both"):
        # biggest mover first, so the interesting charts lead in the email
        for deal in sorted(deals, key=lambda d: abs(deal_shift(rows, d) - 1), reverse=True):
            if args.panels == "combined":
                out = plot_deal_panels(rows, deal, scenarios, args.output_dir,
                                       args.metric, args.max_month)
                if out is not None:
                    written.append(out)
            else:
                for scen in scenarios:
                    out = plot_deal(rows, deal, scen, args.output_dir,
                                    args.metric, args.max_month)
                    if out is not None:
                        written.append(out)
    if args.view in ("cohort", "both"):
        for scen in scenarios:
            written.append(plot_cohorts(rows, scen, args.output_dir, args.metric, args.max_month))

    for path in written:
        print(f"[OK] {path.name}")
    print(f"\n{len(written)} chart(s) for {len(deals)} deal(s) -> {args.output_dir}")
    if written:
        # --output-dir may be relative or outside the emailer tree; fall back to the
        # path as given rather than dying on the hint line after the work is done.
        try:
            rel = written[0].resolve().relative_to(EMAILER_DIR).as_posix()
        except ValueError:
            rel = written[0].as_posix()
        print(f"Reference in run.py MD_CONTENT as e.g.\n    ![{written[0].stem}]({rel})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
