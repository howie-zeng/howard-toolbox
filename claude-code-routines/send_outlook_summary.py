"""Send a Markdown daily summary through Outlook.

Default behavior is a dry run. Use ``--draft`` to create an Outlook draft or
``--send`` to send the message.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TO = "hzeng@libremax.com"
DEFAULT_OUTPUTS_DIR = Path(__file__).resolve().parent / "outputs"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a Markdown summary and send it through Outlook.",
    )
    parser.add_argument(
        "--body-file",
        type=Path,
        default=None,
        help="Markdown file containing the summary body.",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Summary date in YYYY-MM-DD or YYYYMMDD format. Default: today.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_OUTPUTS_DIR,
        help=f"Directory used to resolve default body file. Default: {DEFAULT_OUTPUTS_DIR}",
    )
    parser.add_argument("--to", default=DEFAULT_TO, help=f"Recipient. Default: {DEFAULT_TO}")
    parser.add_argument(
        "--subject",
        default=None,
        help="Email subject. Default: Daily RESI/CLO Summary - <body file stem>",
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Render only; do not open Outlook.")
    mode.add_argument("--draft", action="store_true", help="Create an Outlook draft.")
    mode.add_argument("--send", action="store_true", help="Send the Outlook email.")
    parser.add_argument(
        "--fallback-draft",
        action="store_true",
        help="If --send fails, create an Outlook draft instead.",
    )
    return parser


def _parse_summary_date(value: str | None) -> dt.date:
    if not value:
        return dt.date.today()
    compact = value.replace("-", "")
    try:
        return dt.datetime.strptime(compact, "%Y%m%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid --date {value!r}; expected YYYY-MM-DD or YYYYMMDD"
        ) from exc


def _default_body_file(summary_date: dt.date, input_dir: Path) -> Path:
    return input_dir / f"daily-resi-clo-summary-{summary_date:%Y%m%d}.md"


def _render_markdown(markdown_text: str) -> str:
    sys.path.insert(0, str(REPO_ROOT))
    from emailer.render import render_markdown

    return render_markdown(markdown_text, base_path=str(REPO_ROOT))


def _outlook_app():
    try:
        import win32com.client  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("pywin32 is required for Outlook automation") from exc

    return win32com.client.Dispatch("Outlook.Application")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    summary_date = _parse_summary_date(args.date)
    body_path = args.body_file or _default_body_file(summary_date, args.input_dir)
    body_path = body_path.expanduser().resolve()
    if not body_path.is_file():
        parser.error(f"--body-file not found: {body_path}")

    markdown_text = body_path.read_text(encoding="utf-8")
    html = _render_markdown(markdown_text)
    subject = args.subject or f"Daily RESI/CLO Summary - {summary_date:%Y-%m-%d}"

    if args.dry_run or not (args.draft or args.send):
        print(f"[DRY RUN] To: {args.to}")
        print(f"[DRY RUN] Subject: {subject}")
        print(f"[DRY RUN] HTML length: {len(html):,} chars")
        return 0

    outlook = _outlook_app()
    message = outlook.CreateItem(0)
    message.To = args.to
    message.Subject = subject
    message.HTMLBody = html

    try:
        if args.send:
            message.Send()
            print(f"[OK] Sent Outlook email to {args.to}")
        else:
            message.Save()
            print(f"[OK] Created Outlook draft for {args.to}")
    except Exception as exc:
        if not (args.send and args.fallback_draft):
            raise
        fallback = outlook.CreateItem(0)
        fallback.To = args.to
        fallback.Subject = f"[DRAFT FALLBACK] {subject}"
        fallback.HTMLBody = html
        fallback.Save()
        print(f"[WARN] Send failed: {exc}")
        print(f"[OK] Created Outlook draft fallback for {args.to}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
