"""Generate a fancy email from raw markdown.

Edit ``MD_CONTENT`` below and run::

    python emailer/run.py

The rendered HTML will be copied to the Windows clipboard, ready to paste
into Outlook or Gmail.

CLI flags::

    --md-file PATH      Read markdown body from a file instead of MD_CONTENT.
                        Relative image paths resolve from the file's folder.
    --preview           Open the rendered HTML in the default browser.
    --no-clipboard      Render to file only; skip the clipboard copy.
    --no-resize         Embed images at original size (skip auto-resize).
"""

from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

try:
    from .render import (
        EMAILER_DIR,
        copy_to_clipboard,
        normalize_local_images,
        process_clipboard_images,
        render_markdown,
    )
except ImportError:  # running as `python emailer/run.py`
    from render import (  # type: ignore[no-redef]
        EMAILER_DIR,
        copy_to_clipboard,
        normalize_local_images,
        process_clipboard_images,
        render_markdown,
    )

OUTPUTS_DIR = EMAILER_DIR / "outputs"


# ARM % by Deal as of Latest Reporting Date:
# | Date       | Deal Name        | Pool ID | ARM %  |
# |------------|------------------|---------|--------|
# | 2026-05-01 | ADMT 2023-NQM3   | ES8     | 0.57   |
# | 2026-05-01 | ADMT 2024-NQM1   | EVD     | 0.19   |
# | 2026-05-01 | BRAVO 2021-NQM1  | Q4Y     | 65.25  |
# | 2026-05-01 | CHNGE 2022-1     | B9U     | 17.77  |
# | 2026-05-01 | CHNGE 2022-2     | B9V     | 9.3    |
# | 2026-05-01 | CHNGE 2023-4     | ESU     | 16.58  |
# | 2026-05-01 | COLT 2022-3      | B4O     | 22.59  |
# | 2026-05-01 | JPMMT 2025-VIS2  | GIK     | 13.31  |
# | 2026-04-01 | NYMT 2025-INV2   | GXD     | 6.42   |
# | 2026-05-01 | VERUS 2022-1     | B3A     | 6.34   |
# | 2026-05-01 | VERUS 2022-3     | B4U     | 5.54   |
# | 2026-05-01 | VISIO 2023-1     | ENU     | 20.94  |


# -----------------------------------------------------------------------------
# EDIT YOUR MARKDOWN CONTENT HERE
# -----------------------------------------------------------------------------
MD_CONTENT = r"""
Team,

I cleaned up how the resi pipeline computes `reporting_month` and redesigned the tracking workflow. Summary below.

**Background**

Each resi product's reporting month was previously computed with hardcoded `DATEADD(MONTH, N, ...)` literals. Those offsets were duplicated across roughly 14 SQL config templates across unload, stats, and transition flows, plus a few Python download paths. That duplication was fragile.

**What changed**

- Added one source of truth for reporting-month offsets in `agencydata/config/resi_date_offsets.py`.
- The config defines, by product, the offset `R` where `reporting_month = factor_month + R`.
- It also generates the SQL / BigQuery month expressions used by stats, unload, transition, and DV01/Figure BigQuery configs.
- All relevant templates now pull from this config instead of hardcoding the month shift.

Offsets:

| Product / source | Offset |
|---|---:|
| CAS | +2 |
| STACR | +1 |
| MIR | +2 |
| SBT | +2 |
| SPI | +1 |
| FNM | +7 |
| NONQM / JUMBO / HELOC-CoreLogic | +0 |
| HELOC-Figure | +1 |

The tracking report now keys off `factor_month`. It previously built the month axis by shifting `factor_date` per deal type, which was fragile. It now derives the axis from `factor_month + R` using the same shared config.

**Automation**

The old all-in-one monthly run is now two readiness-gated jobs that watch for data and run themselves:

- A daily **Unload** job checks each product's source data and kicks off the data load as soon as a new complete month is available (and alerts if a source is overdue).
- A **Tracking** job then checks whether that product's data is fully in and, once it is, runs the tracking and reports for it.

Both do real work **at most once per product per month**, only on or after the first business day, weekdays — and skip quietly when nothing is ready. So tracking keeps itself current per product, with no manual kickoffs, and is safe to run daily (idempotent).


Happy to walk through any of it.
"""


# -----------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python emailer/run.py",
        description="Render markdown to an Outlook-ready HTML email.",
    )
    parser.add_argument(
        "--md-file",
        type=Path,
        default=None,
        help="Read markdown body from PATH (relative image paths resolve from its folder).",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Open the rendered HTML in the default browser.",
    )
    parser.add_argument(
        "--no-clipboard",
        action="store_true",
        help="Skip copying HTML to the Windows clipboard (useful for CI / preview only).",
    )
    parser.add_argument(
        "--no-resize",
        action="store_true",
        help="Embed images at their original size (skip auto-resize).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.md_file is not None:
        md_path = args.md_file.expanduser().resolve()
        if not md_path.is_file():
            parser.error(f"--md-file not found: {md_path}")
        content = md_path.read_text(encoding="utf-8")
        base_dir = md_path.parent
        source_desc = str(md_path)
    else:
        content = MD_CONTENT
        base_dir = EMAILER_DIR
        source_desc = "MD_CONTENT (inline)"

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    content = process_clipboard_images(content)
    content = normalize_local_images(content, base_dir=base_dir)

    print(f"Formatting email from {source_desc} ...")
    output_path = OUTPUTS_DIR / "latest_email.html"
    html = render_markdown(
        content,
        output_path=str(output_path),
        base_path=str(EMAILER_DIR),
        resize_images=not args.no_resize,
    )

    if not args.no_clipboard:
        copy_to_clipboard(html)
        print("[OK] Copied rendered email to clipboard")
    else:
        print(f"[OK] Rendered HTML written to {output_path}")

    if args.preview:
        webbrowser.open(output_path.as_uri())
        print(f"[OK] Opened preview in browser: {output_path}")

    print("\n---------------------------------------------------------")
    if not args.no_clipboard:
        print("Done! The HTML is in your clipboard.")
        print("1. Go to Outlook/Gmail")
        print("2. Paste (Ctrl+V)")
    else:
        print(f"Output file: {output_path}")
    print("---------------------------------------------------------")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
