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


# -----------------------------------------------------------------------------
# EDIT YOUR MARKDOWN CONTENT HERE
# -----------------------------------------------------------------------------
MD_CONTENT = r"""
Hi Gloria,

Thanks for the update. I wanted to clarify the sequencing. My understanding is that H-1B and green card processes can sometimes proceed in parallel. Is there a company policy or legal reason that the H-1B process needs to be completed before the green card process can begin?

If the green card process cannot be started in parallel, could you confirm whether my H-1B will be filed with premium processing? I understand that this is often standard, but I wanted to make sure.

Could you also share the expected timeline for when the green card process would begin?
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
