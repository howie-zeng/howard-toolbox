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
DEFAULT_FROZEN_EVAL = Path("llm_clo_parser/data/frozen_eval.csv")
DEFAULT_TRAIN_PKL = Path("S:/QR/Models/NLP_Parse/train_new/train_pkl.pkl")
REQUIRED_EVAL_COLUMNS = ["sample_id", "text"]
OLD_TO_LOCAL_LABELS = {
    "Ticker": "ticker",
    "Cusip": "cusip",
    "BidPrice": "bid_price",
    "OfferPrice": "offer_price",
    "BidSpread": "bid_spread",
    "OfferSpread": "offer_spread",
    "BidSize": "bid_size",
    "OfferSize": "offer_size",
    "Rating": "rating",
    "WAL": "wal",
    "Yield": "yield",
}
OPTIONAL_LABEL_COLUMNS = [
    "ticker",
    "cusip",
    "tranche",
    "side",
    "bid_price",
    "offer_price",
    "bid_spread",
    "offer_spread",
    "bid_size",
    "offer_size",
    "rating",
    "wal",
    "yield",
]


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


@dataclass(frozen=True)
class CsvInventory:
    csv_path: Path
    row_count: int
    columns: list[str]
    missing_required_columns: list[str]
    blank_text_rows: int
    source_kind_counts: dict[str, int]
    label_fill_counts: dict[str, int]

    def print_summary(self) -> None:
        print(f"CSV path: {self.csv_path}")
        print(f"Rows: {self.row_count}")
        print(f"Columns: {len(self.columns)}")
        if self.missing_required_columns:
            print("Missing required columns:")
            for column in self.missing_required_columns:
                print(f"  {column}")
        else:
            print("Required columns: ok")
        print(f"Blank text rows: {self.blank_text_rows}")
        if self.source_kind_counts:
            print("source_kind counts:")
            for source_kind, count in sorted(self.source_kind_counts.items()):
                print(f"  {source_kind}: {count}")
        print("Label fill counts:")
        for column, count in sorted(self.label_fill_counts.items()):
            print(f"  {column}: {count}")


@dataclass(frozen=True)
class TrainPklExport:
    input_path: Path
    output_path: Path
    asset_class: str
    rows_read: int
    rows_written: int
    positive_rows: int
    skipped_duplicate_label_rows: int

    def print_summary(self) -> None:
        print(f"Input: {self.input_path}")
        print(f"Output: {self.output_path}")
        print(f"Asset class: {self.asset_class}")
        print(f"Rows read: {self.rows_read}")
        print(f"Rows written: {self.rows_written}")
        print(f"Rows with labels: {self.positive_rows}")
        print(f"Rows skipped for duplicate labels: {self.skipped_duplicate_label_rows}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline helpers for LLM CLO parser data preparation.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    csv_inventory = subparsers.add_parser(
        "inventory-csv",
        help="Validate a local frozen-eval CSV using only the default Python environment.",
    )
    csv_inventory.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_FROZEN_EVAL,
        help=f"Local frozen-eval CSV to inspect. Default: {DEFAULT_FROZEN_EVAL}",
    )

    export_train = subparsers.add_parser(
        "export-train-pkl",
        help="Convert cached spaCy training rows into the local flat CSV format.",
    )
    export_train.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_TRAIN_PKL,
        help=f"Read-only train_pkl.pkl path. Default: {DEFAULT_TRAIN_PKL}",
    )
    export_train.add_argument("--asset-class", default="CLO", help="Asset class to export, default: CLO.")
    export_train.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_FROZEN_EVAL,
        help=f"Local output CSV. Default: {DEFAULT_FROZEN_EVAL}",
    )
    export_train.add_argument(
        "--include-negative",
        action="store_true",
        help="Include rows without labeled entities. Default exports only labeled rows.",
    )

    inventory = subparsers.add_parser(
        "inventory-pickles",
        help="Optional legacy diagnostic for parser test pickles. Requires LMQR runtime dependencies.",
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


def inventory_csv(csv_path: Path) -> CsvInventory:
    csv_path = csv_path.resolve()
    row_count = 0
    blank_text_rows = 0
    source_kind_counts: Counter[str] = Counter()
    label_fill_counts: Counter[str] = Counter()

    with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        columns = list(reader.fieldnames or [])
        missing_required = [column for column in REQUIRED_EVAL_COLUMNS if column not in columns]

        for row in reader:
            row_count += 1
            text = _clean_cell(row.get("text"))
            if not text:
                blank_text_rows += 1

            source_kind = _clean_cell(row.get("source_kind"))
            if source_kind:
                source_kind_counts[source_kind] += 1

            for column in OPTIONAL_LABEL_COLUMNS:
                if _clean_cell(row.get(column)):
                    label_fill_counts[column] += 1

    return CsvInventory(
        csv_path=csv_path,
        row_count=row_count,
        columns=columns,
        missing_required_columns=missing_required,
        blank_text_rows=blank_text_rows,
        source_kind_counts=dict(source_kind_counts),
        label_fill_counts={column: label_fill_counts[column] for column in OPTIONAL_LABEL_COLUMNS},
    )


def export_train_pkl(
    input_path: Path,
    output_path: Path,
    asset_class: str,
    include_negative: bool = False,
) -> TrainPklExport:
    asset_class_norm = asset_class.upper()
    input_path = input_path.resolve()
    output_path = output_path.resolve()

    with input_path.open("rb") as f:
        training_rows = pickle.load(f)

    rows: list[dict[str, Any]] = []
    rows_read = 0
    positive_rows = 0
    skipped_duplicate_label_rows = 0

    for idx, training_row in enumerate(training_rows):
        if not isinstance(training_row, tuple) or len(training_row) < 4:
            continue

        row_text, entity_dict, context_text, row_asset_class = training_row[:4]
        if str(row_asset_class).upper() != asset_class_norm:
            continue

        rows_read += 1
        entities = entity_dict.get("entities", []) if isinstance(entity_dict, dict) else []
        if entities:
            positive_rows += 1
        elif not include_negative:
            continue

        label_values, duplicate_labels = _extract_label_values(str(row_text), entities)
        if duplicate_labels:
            skipped_duplicate_label_rows += 1
            continue

        export_row: dict[str, Any] = {
            "sample_id": f"{asset_class_norm.lower()}_{idx:06d}",
            "text": _row_body(str(row_text)),
            "raw_text": str(row_text),
            "context_text": str(context_text),
            "source_kind": "train_pkl",
            "asset_type": asset_class_norm,
            "has_labels": bool(entities),
        }
        for old_label, local_label in OLD_TO_LOCAL_LABELS.items():
            export_row[local_label] = label_values.get(old_label, "")

        rows.append(export_row)

    _write_training_export_csv(output_path, rows)
    return TrainPklExport(
        input_path=input_path,
        output_path=output_path,
        asset_class=asset_class_norm,
        rows_read=rows_read,
        rows_written=len(rows),
        positive_rows=positive_rows,
        skipped_duplicate_label_rows=skipped_duplicate_label_rows,
    )


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


def _extract_label_values(row_text: str, entities: list[Any]) -> tuple[dict[str, str], set[str]]:
    label_values: dict[str, str] = {}
    duplicate_labels: set[str] = set()
    for entity in entities:
        if not isinstance(entity, (list, tuple)) or len(entity) != 3:
            continue
        start, end, label = entity
        if label not in OLD_TO_LOCAL_LABELS:
            continue
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if not (0 <= start < end <= len(row_text)):
            continue
        value = row_text[start:end].strip()
        if label in label_values and label_values[label] != value:
            duplicate_labels.add(label)
        label_values[label] = value
    return label_values, duplicate_labels


def _row_body(row_text: str) -> str:
    if "\x1f" not in row_text:
        return row_text.strip()
    return row_text.split("\x1f", 1)[1].strip()


def _clean_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _write_training_export_csv(output_path: Path, rows: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sample_id",
        "text",
        "raw_text",
        "context_text",
        "source_kind",
        "asset_type",
        "has_labels",
        *OPTIONAL_LABEL_COLUMNS,
    ]
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


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

    if args.command == "inventory-csv":
        inventory = inventory_csv(args.input)
        inventory.print_summary()
        return 0

    if args.command == "export-train-pkl":
        export = export_train_pkl(args.input, args.output, args.asset_class, args.include_negative)
        export.print_summary()
        return 0

    if args.command == "inventory-pickles":
        inventory = inventory_pickles(args.pickle_dir, args.sector, args.csv_out, args.lmqr_root)
        inventory.print_summary()
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2
