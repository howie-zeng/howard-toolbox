"""Debug dump — writes a single CSV with all dumped loan-path snapshots."""
import csv
import os
from typing import Dict, List, Optional, Tuple


def should_dump(config: Optional[dict]) -> Optional[dict]:
    """Return dump config if enabled, else None."""
    if not config:
        return None
    d = config.get("dump")
    if not d or not d.get("enabled"):
        return None
    deal_name = config.get("deal_name", "default")
    return {
        "max_loans": d.get("max_loans", 10),
        "max_paths": d.get("max_paths", 10),
        "output_dir": d.get("output_dir", f"output/{deal_name}/dump"),
    }


def new_collector() -> dict:
    """Create a fresh collector for one loan-path."""
    return {"rows": []}


def snap_pre(collector: dict, loan: dict, per: int, status: str) -> None:
    """Capture loan state before model eval."""
    snap = {"_per": per, "_from": status}
    for k, v in loan.items():
        if not k.startswith("_"):
            snap[k] = v
    collector["_cur"] = snap


def snap_post(collector: dict, status_to: str, probs: dict,
              begin_bal: float, end_bal: float,
              int_pmt: float, prin_pmt: float, loss: float) -> None:
    """Complete snapshot with transition result and cashflows."""
    snap = collector.pop("_cur", None)
    if snap is None:
        return
    snap["_to"] = status_to
    snap["_begin_bal"] = begin_bal
    snap["_end_bal"] = end_bal
    snap["_int_pmt"] = int_pmt
    snap["_prin_pmt"] = prin_pmt
    snap["_loss"] = loss
    for k, v in probs.items():
        if not k.startswith("_"):
            snap[k] = v
    collector["rows"].append(snap)


def write_csv(output_dir: str,
              entries: List[Tuple[str, int, dict]]) -> str:
    """Write all dump entries to a single CSV.

    entries: list of (loan_id, path, collector) tuples.
    Returns the CSV file path.
    """
    if not entries:
        return ""

    # Discover all columns across all entries
    all_keys: set = set()
    for _, _, collector in entries:
        for row in collector["rows"]:
            all_keys.update(row.keys())

    ctx = ["_per", "_from", "_to"]
    cf = ["_begin_bal", "_end_bal", "_note_rate", "_pi_pmt", "_num_pay",
          "_int_pmt", "_prin_pmt", "_loss"]
    prob = sorted(k for k in all_keys if k.startswith("from"))
    feat = sorted(k for k in all_keys
                  if k not in ctx and k not in cf
                  and not k.startswith("from") and not k.startswith("_"))

    cols = ["loan_id", "path"] + ctx + feat + prob + cf

    os.makedirs(output_dir, exist_ok=True)
    fpath = os.path.join(output_dir, "dump.csv")
    with open(fpath, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for loan_id, path, collector in entries:
            for row in collector["rows"]:
                out = []
                for c in cols:
                    if c == "loan_id":
                        out.append(loan_id)
                    elif c == "path":
                        out.append(path)
                    else:
                        out.append(row.get(c, ""))
                w.writerow(out)
    return fpath
