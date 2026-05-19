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
Hi Glenn,

Please see below for the updated model fit.

**Updates based on our discussion**

- Dropped bonds with missing size instead of filling missing size with 3mm.
- Reduced the flexibility of the Crossover smooth so the curve is more stable and the confidence band is tighter.
- Dropped NumMosToReinv from the model, as the term was unstable.
- Dropped WAP, as it is no longer significant in the updated fit.

**Updated model fit**

![](2026-05-19-16-24-34.png)
"""


# MD_CONTENT = r"""
# Hi Intex Support Team,

# I have a few questions about the dates shown on the collateral stats payment page. We are trying to understand what those dates represent and how they relate to the latest payment date shown in the investor reports.

# **Example 1: ACHM 2023-HE1**

# For ACHM 2023-HE1, Intex shows the most recent collateral stats date as March 2026, while the investor report shows the most recent payment date as April 2026.

# ![](2026-05-11-17-40-49.png)

# ![](2026-05-11-17-40-56.png)


# **Example 2: VISIO 2023-1 (ENU) and VERUS 2022-1 (B3A)**

# Both deals have an April 2026 payment date. However, on the Intex collateral stats page, VERUS 2022-1 shows April 2026 as the most recent date, while VISIO 2023-1 shows March 2026 as the most recent date.

# ![](2026-05-11-17-46-06.png)

# ![](2026-05-11-17-46-31.png)

# ![](2026-05-11-17-42-17.png)

# ![](2026-05-11-17-42-53.png)

# Could you help clarify:

# - What does the most recent date on the collateral stats payment page represent?
# - Why can it differ from the latest payment date in the investor report for some deals but not others?
# - Why would two deals with the same April 2026 payment date show different most recent dates on the collateral stats page?

# """


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
