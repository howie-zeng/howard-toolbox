from __future__ import annotations

import argparse
import csv
import pickle
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_LMQR_ROOT = Path("S:/QR/GitHub/LibreMax-QR/master/LMQR")
DEFAULT_PICKLE_DIR = Path("S:/QR/Risk/ColorParserTestPickles")


@dataclass(frozen=True)
class PickleInventory:
    pickle_dir: Path
    sector: str
    total_files: int
    sector_files: int
    status_counts: dict[str, int]
    success_rows: int
    failures: list[str]

    def print_summary(self) -> None:
        print(f"Pickle directory: {self.pickle_dir}")
        print(f"Sector: {self.sector}")
        print(f"Pickle files scanned: {self.total_files}")
        print(f"Matching sector files: {self.sector_files}")
        print(f"Successful parsed rows: {self.success_rows}")
        if self.status_counts:
            print("Status counts:")
            for status, count in sorted(self.status_counts.items()):
                print(f"  {status}: {count}")
        else:
            print("Status counts: none")
        if self.failures:
            print("Note: unreadable pickles are usually caused by missing LMQR runtime dependencies.")
            print("Unreadable pickles:")
            for failure in self.failures[:10]:
                print(f"  {failure}")
            if len(self.failures) > 10:
                print(f"  ... {len(self.failures) - 10} more")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline helpers for LLM CLO parser data preparation.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory = subparsers.add_parser(
        "inventory-pickles",
        help="Read parser test pickles and report sector/status counts without modifying source data.",
    )
    inventory.add_argument("--sector", default="clo", help="Sector to inventory, default: clo.")
    inventory.add_argument(
        "--pickle-dir",
        type=Path,
        default=DEFAULT_PICKLE_DIR,
        help=f"Directory containing parser test .pickle files. Default: {DEFAULT_PICKLE_DIR}",
    )
    inventory.add_argument(
        "--lmqr-root",
        type=Path,
        default=DEFAULT_LMQR_ROOT,
        help=f"Read-only LMQR root used only to import pickle classes. Default: {DEFAULT_LMQR_ROOT}",
    )
    inventory.add_argument(
        "--csv-out",
        type=Path,
        help="Optional local CSV path for per-pickle metadata. Use llm_clo_parser/outputs/.",
    )

    return parser


def inventory_pickles(
    pickle_dir: Path,
    sector: str,
    csv_out: Path | None = None,
    lmqr_root: Path = DEFAULT_LMQR_ROOT,
) -> PickleInventory:
    _ensure_lmqr_imports(lmqr_root)
    pickle_dir = pickle_dir.resolve()
    sector_norm = sector.lower()
    pickle_paths = sorted(pickle_dir.glob("*.pickle"))
    status_counts: Counter[str] = Counter()
    failures: list[str] = []
    metadata_rows: list[dict[str, Any]] = []
    success_rows = 0
    sector_files = 0

    for path in pickle_paths:
        try:
            with path.open("rb") as f:
                result = pickle.load(f)
        except Exception as exc:
            failures.append(f"{path.name}: {exc}")
            continue

        result_sector = str(getattr(result, "sector", "")).lower()
        if result_sector != sector_norm:
            continue

        sector_files += 1
        status = _status_value(getattr(result, "status", None))
        status_counts[status] += 1
        row_count = _result_row_count(getattr(result, "results", None))
        if status == "success":
            success_rows += row_count

        email = getattr(result, "email", None)
        metadata_rows.append(
            {
                "pickle_file": path.name,
                "sector": result_sector,
                "status": status,
                "row_count": row_count,
                "subject": getattr(email, "subject", None),
                "datetime_received": getattr(email, "datetime_received", None),
                "sender": _email_sender(email),
                "has_attachments": getattr(email, "has_attachments", None),
            }
        )

    if csv_out is not None:
        _write_metadata_csv(csv_out, metadata_rows)

    return PickleInventory(
        pickle_dir=pickle_dir,
        sector=sector_norm,
        total_files=len(pickle_paths),
        sector_files=sector_files,
        status_counts=dict(status_counts),
        success_rows=success_rows,
        failures=failures,
    )


def _status_value(status: Any) -> str:
    value = getattr(status, "value", None)
    if value is not None:
        return str(value)
    return str(status)


def _ensure_lmqr_imports(lmqr_root: Path) -> None:
    lmqr_root_str = str(lmqr_root)
    if lmqr_root.exists() and lmqr_root_str not in sys.path:
        sys.path.append(lmqr_root_str)


def _result_row_count(results: Any) -> int:
    if results is None:
        return 0
    try:
        return len(results)
    except TypeError:
        return 0


def _email_sender(email: Any) -> str | None:
    if email is None:
        return None
    sender = getattr(email, "sender", None)
    if sender is None:
        return None
    return getattr(sender, "email_address", None) or getattr(sender, "name", None) or str(sender)


def _write_metadata_csv(csv_out: Path, rows: list[dict[str, Any]]) -> None:
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "pickle_file",
        "sector",
        "status",
        "row_count",
        "subject",
        "datetime_received",
        "sender",
        "has_attachments",
    ]
    with csv_out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "inventory-pickles":
        inventory = inventory_pickles(args.pickle_dir, args.sector, args.csv_out, args.lmqr_root)
        inventory.print_summary()
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2
