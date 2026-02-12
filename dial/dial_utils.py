from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional
import re

import pandas as pd


def trim_float(x: float) -> str:
    """Format float without trailing zeros (VBA-style Trim(CStr))."""
    s = format(x, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def dial_schedule(x: float, flat_months: int = 48, ramp_months: int = 23) -> str:
    """Generate the dial string for a scalar multiplier x."""
    if flat_months <= 0:
        raise ValueError(f"flat_months must be > 0 (got {flat_months})")
    if ramp_months <= 0:
        raise ValueError(f"ramp_months must be > 0 (got {ramp_months})")

    x = round(x, 3)
    parts = [f"{trim_float(x)}x for {flat_months}"]
    for i in range(1, ramp_months + 1):
        val = ((ramp_months + 1 - i) * x + i - 1) / ramp_months
        val = round(val, 3)
        parts.append(f"{trim_float(val)}x for 1")

    parts.append("1.0x for 1 1x")
    return " ".join(parts)


def find_status_row(df: pd.DataFrame) -> Optional[int]:
    """Return the row index where any cell equals 'Status' (case-insensitive)."""
    for i, row in df.iterrows():
        if any(str(cell).strip().lower() == "status" for cell in row):
            return i
    return None


def _clean_header(val) -> str:
    if pd.isna(val):
        return ""
    return str(val).strip()


def build_columns_from_status_header(df: pd.DataFrame, status_row_idx: int) -> list[str]:
    """
    Build column names using the 'Status' row and the row above.
    Forward-fills merged headers so grouped labels (e.g., '3M Error')
    apply to subsequent columns like Abs/Ratio.
    """
    header_main = df.iloc[status_row_idx].tolist()
    header_top_raw = (
        df.iloc[status_row_idx - 1].tolist()
        if status_row_idx > 0
        else [None] * len(header_main)
    )

    header_top = []
    last = ""
    for val in header_top_raw:
        cleaned = _clean_header(val)
        if cleaned:
            last = cleaned
        header_top.append(last)

    raw_columns = []
    for top_val, base_val in zip(header_top, header_main):
        top = _clean_header(top_val)
        base = _clean_header(base_val)
        if top and base and top != base:
            col_name = f"{top} {base}"
        elif base:
            col_name = base
        elif top:
            col_name = top
        else:
            col_name = ""
        raw_columns.append(col_name)

    # Ensure unique, non-empty column names
    new_columns: list[str] = []
    seen: dict[str, int] = {}
    for idx, col in enumerate(raw_columns):
        col = col if col else f"Unnamed: {idx}"
        if col in seen:
            seen[col] += 1
            col = f"{col}.{seen[col]}"
        else:
            seen[col] = 0
        new_columns.append(col)

    return new_columns


def normalize_error_window(window: Optional[str]) -> Optional[str]:
    if window is None:
        return None
    s = str(window).upper().replace(" ", "")
    if s.endswith("M"):
        return s
    if s.isdigit():
        return f"{s}M"
    return s


def select_error_columns(columns: Iterable, window: Optional[str]) -> list[str]:
    """Return columns containing the requested error window (e.g., '3M Error')."""
    if not window:
        return []
    needle = f"{window}ERROR"
    selected = []
    for col in columns:
        col_str = str(col).upper().replace(" ", "")
        if needle in col_str:
            selected.append(col)
    # Deduplicate while preserving order
    seen = set()
    return [c for c in selected if not (c in seen or seen.add(c))]


def find_latest_tracking_file(dealtype: str, base_dir: Path) -> Path:
    """
    Find the latest tracking file for a given dealtype in the base directory.

    Expected patterns:
      - tracking_*_{DEALTYPE}_YYYYMMDD.xlsx
      - tracking_{DEALTYPE}_*_CRT_YYYYMMDD.xlsx (e.g., CAS/STACR)
    Falls back to file modified time if date parsing fails.
    """
    dealtype_upper = dealtype.upper()
    base_dir = Path(base_dir)

    if not base_dir.exists():
        raise FileNotFoundError(f"Base directory not found: {base_dir}")

    candidates = list(base_dir.glob(f"tracking_*_{dealtype_upper}_*.xlsx"))
    if not candidates:
        candidates = list(base_dir.glob(f"tracking_{dealtype_upper}_*_CRT_*.xlsx"))
    if not candidates:
        raise FileNotFoundError(
            f"No tracking files found for dealtype '{dealtype}' in {base_dir}"
        )

    date_regex = re.compile(r"_(\d{8})\.xlsx$", re.IGNORECASE)

    def _file_key(p: Path):
        match = date_regex.search(p.name)
        if match:
            return match.group(1), p.stat().st_mtime
        # No date -> use mtime only (date key empty)
        return "", p.stat().st_mtime

    # Prefer date when available, otherwise mtime
    candidates.sort(key=_file_key)
    latest = candidates[-1]
    return latest


def extract_summary_rows(
    excel_path: Path,
    bucket_type: str,
    status_sheets: Iterable[str],
    exclude_sheets: Iterable[str],
    verbose: bool = True,
) -> list[dict]:
    """Extract summary rows from tracking workbook."""
    status_set = {s.upper() for s in status_sheets}
    exclude_set = {s.upper() for s in exclude_sheets}

    sheet_names = pd.ExcelFile(str(excel_path)).sheet_names
    if verbose:
        print("All sheet names:", sheet_names)

    summary_rows: list[dict] = []

    for sheet in sheet_names:
        if sheet.upper() in exclude_set:
            continue

        df = pd.read_excel(excel_path, sheet_name=sheet, header=None)

        status_row_idx = find_status_row(df)
        if status_row_idx is None:
            if verbose:
                print(f"'Status' row NOT found in sheet '{sheet}'")
            continue

        if verbose:
            print(f"'Status' row found in sheet '{sheet}' (row {status_row_idx}).")

        new_columns = build_columns_from_status_header(df, status_row_idx)
        df_data = df.iloc[status_row_idx + 1 :].copy()
        df_data.columns = new_columns
        df_data.reset_index(drop=True, inplace=True)

        # Status-only sheets: collect all Status rows
        if sheet.upper() in status_set:
            if verbose:
                print(f"  Collecting all Status rows in sheet '{sheet}'")
            for _, row in df_data.iterrows():
                status_val = str(row.get("Status", "")).strip()
                if status_val and status_val.lower() not in ("nan", "none"):
                    row_dict = row.to_dict()
                    row_dict["Sheet"] = sheet
                    row_dict["Bucket_Type"] = "STATUS"
                    summary_rows.append(row_dict)
            continue

        # Bucket sheets: find the specified bucket section's "ALL AVG" row
        in_target_section = False
        for idx, row in df_data.iterrows():
            bucket_val = str(row.get("Bucket", "")).strip().upper()

            if bucket_type.upper() in bucket_val and "ALL AVG" not in bucket_val:
                in_target_section = True

            if in_target_section and "ALL AVG" in bucket_val:
                if verbose:
                    print(
                        f"  Found {bucket_type} 'ALL AVG' at row {idx} in sheet '{sheet}'"
                    )
                row_dict = row.to_dict()
                row_dict["Sheet"] = sheet
                row_dict["Bucket_Type"] = bucket_type
                summary_rows.append(row_dict)
                in_target_section = False
                break

            if in_target_section and (
                pd.isna(row.get("Bucket"))
                or (
                    bucket_val
                    and bucket_type.upper() not in bucket_val
                    and "ALL AVG" not in bucket_val
                )
            ):
                in_target_section = False

    return summary_rows
