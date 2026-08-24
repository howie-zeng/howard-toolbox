"""Extract text, GAM coefficient tables, and page images from PDFs.

Use this for model-report PDFs (in-sample dumps, tracking decks) before
writing an email. Page numbers on the CLI are 1-based.

Examples::

    python emailer/parse_pdf.py info --pdf report.pdf
    python emailer/parse_pdf.py text --pdf report.pdf --pages 1-6
    python emailer/parse_pdf.py coefs --pdf report.pdf --page 2 --out coefs.csv
    python emailer/parse_pdf.py smooths --pdf report.pdf --page 3
    python emailer/parse_pdf.py render --pdf report.pdf --pages 4,6 \\
        --out-dir emailer/assets/fcls_model_update --prefix FCLStoREO \\
        --names smooth overtime
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import fitz

MINUS = "\u2212"
DEFAULT_COEF_SKIP = {
    "term",
    "Estimate",
    "Std. Error",
    "z value",
    "Pr(>|z|)",
    "signif",
    "Parametric coefficients",
    "Parametric coefficients (cont.)",
}
DEFAULT_SPLIT_X = 650.0


def normalize_minus(text: str) -> str:
    return text.replace(MINUS, "-").replace(",", "")


def parse_pages(spec: str) -> list[int]:
    """Parse a 1-based spec such as ``2,4-6`` into 0-based page indices."""
    pages: list[int] = []
    for raw in spec.split(","):
        part = raw.strip()
        if not part:
            raise ValueError(f"empty page token in {spec!r}")
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start, end = int(start_s), int(end_s)
            if start < 1 or end < start:
                raise ValueError(f"invalid page range {part!r} in {spec!r}")
            pages.extend(range(start - 1, end))
            continue
        page = int(part)
        if page < 1:
            raise ValueError(f"page numbers are 1-based, got {page}")
        pages.append(page - 1)
    return pages


def page_rows(page: fitz.Page) -> list[tuple[float, float, str]]:
    rows: list[tuple[float, float, str]] = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            text = "".join(span["text"] for span in line["spans"]).strip()
            if not text:
                continue
            x0 = min(span["bbox"][0] for span in line["spans"])
            y0 = min(span["bbox"][1] for span in line["spans"])
            rows.append((round(y0, 1), round(x0, 1), text))
    rows.sort()
    return rows


def rows_by_y(page: fitz.Page) -> dict[float, list[tuple[float, str]]]:
    by_y: dict[float, list[tuple[float, str]]] = defaultdict(list)
    for y, x, text in page_rows(page):
        by_y[y].append((x, text))
    return by_y


def take_coef(items: list[tuple[float, str]], skip: set[str] | None = None) -> dict[str, str] | None:
    skip = skip or DEFAULT_COEF_SKIP
    if len(items) < 5:
        return None
    term = items[0][1]
    if term in skip:
        return None
    est = normalize_minus(items[1][1])
    try:
        float(est)
    except ValueError:
        return None
    return {
        "term": term,
        "est": est,
        "se": normalize_minus(items[2][1]) if len(items) > 2 else "",
        "z": normalize_minus(items[3][1]) if len(items) > 3 else "",
        "p": normalize_minus(items[4][1]) if len(items) > 4 else "",
        "sig": items[5][1] if len(items) > 5 else "",
    }


def parse_coef_page(
    page: fitz.Page,
    skip: set[str] | None = None,
    split_x: float = DEFAULT_SPLIT_X,
) -> list[dict[str, str]]:
    coefs: list[dict[str, str]] = []
    grouped = rows_by_y(page)
    for y in sorted(grouped):
        items = sorted(grouped[y])
        left = take_coef(items, skip=skip)
        if left:
            coefs.append(left)
        idx = next((i for i, (x, _) in enumerate(items) if x >= split_x), None)
        if idx is not None:
            right = take_coef(items[idx:], skip=skip)
            if right:
                coefs.append(right)
    return coefs


def parse_smooths(page: fitz.Page) -> list[list[str]]:
    out: list[list[str]] = []
    grouped = rows_by_y(page)
    for y in sorted(grouped):
        texts = [t for _, t in sorted(grouped[y])]
        if texts and texts[0].startswith("s("):
            out.append(texts)
    return out


def render_page(doc: fitz.Document, page_index: int, dest: Path, zoom: float = 1.6) -> Path:
    page = doc[page_index]
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    dest.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(dest))
    return dest


def render_pages(
    pdf: Path,
    pages: list[int],
    out_dir: Path,
    prefix: str | None = None,
    names: list[str] | None = None,
    zoom: float = 1.6,
) -> list[Path]:
    if names is not None and len(names) != len(pages):
        raise ValueError(f"--names length {len(names)} does not match page count {len(pages)}")
    stem = prefix or pdf.stem
    doc = fitz.open(str(pdf))
    written: list[Path] = []
    try:
        for i, page_index in enumerate(pages):
            if page_index < 0 or page_index >= doc.page_count:
                raise ValueError(f"page {page_index + 1} out of range for {pdf} ({doc.page_count} pages)")
            dest = out_dir / (f"{stem}_{names[i]}.png" if names else f"{stem}_p{page_index + 1}.png")
            written.append(render_page(doc, page_index, dest, zoom=zoom))
    finally:
        doc.close()
    return written


def pdf_info(pdf: Path, preview_chars: int = 90) -> list[dict[str, str | int]]:
    doc = fitz.open(str(pdf))
    rows: list[dict[str, str | int]] = []
    try:
        for i, page in enumerate(doc):
            text = " ".join((page.get_text() or "").split())
            rows.append({"page": i + 1, "preview": text[:preview_chars]})
    finally:
        doc.close()
    return rows


def write_coefs_csv(coefs: list[dict[str, str]], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["term", "est", "se", "z", "p", "sig"])
        writer.writeheader()
        writer.writerows(coefs)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse and render pages from a model-report PDF.")
    sub = parser.add_subparsers(dest="command", required=True)

    info = sub.add_parser("info", help="List page count and a text preview per page.")
    info.add_argument("--pdf", type=Path, required=True)

    text = sub.add_parser("text", help="Dump page text.")
    text.add_argument("--pdf", type=Path, required=True)
    text.add_argument("--pages", default=None, help="1-based pages, e.g. 1-6 or 2,4. Default: all.")
    text.add_argument("--out", type=Path, default=None)

    coefs = sub.add_parser("coefs", help="Parse a parametric-coefficient table page to CSV.")
    coefs.add_argument("--pdf", type=Path, required=True)
    coefs.add_argument("--page", type=int, required=True, help="1-based page number.")
    coefs.add_argument("--out", type=Path, required=True)
    coefs.add_argument("--split-x", type=float, default=DEFAULT_SPLIT_X)

    smooths = sub.add_parser("smooths", help="Parse smooth-term rows (lines starting with s().")
    smooths.add_argument("--pdf", type=Path, required=True)
    smooths.add_argument("--page", type=int, required=True, help="1-based page number.")
    smooths.add_argument("--out", type=Path, default=None)

    render = sub.add_parser("render", help="Render pages to PNG.")
    render.add_argument("--pdf", type=Path, required=True)
    render.add_argument("--pages", required=True, help="1-based pages, e.g. 4,6.")
    render.add_argument("--out-dir", type=Path, required=True)
    render.add_argument("--prefix", default=None, help="Output stem. Default: PDF filename stem.")
    render.add_argument("--names", nargs="*", default=None, help="Optional suffixes, one per page.")
    render.add_argument("--zoom", type=float, default=1.6)
    return parser


def _resolve_pages(pdf: Path, spec: str | None) -> list[int]:
    if spec:
        return parse_pages(spec)
    doc = fitz.open(str(pdf))
    try:
        return list(range(doc.page_count))
    finally:
        doc.close()


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    pdf: Path = args.pdf
    if not pdf.is_file():
        raise SystemExit(f"PDF not found: {pdf}")

    if args.command == "info":
        rows = pdf_info(pdf)
        print(f"{pdf}  pages={len(rows)}")
        for row in rows:
            print(f"  {row['page']:>4}  {row['preview']}")
        return 0

    if args.command == "text":
        pages = _resolve_pages(pdf, args.pages)
        doc = fitz.open(str(pdf))
        chunks: list[str] = []
        try:
            for page_index in pages:
                chunks.append(f"=== page {page_index + 1} ===\n{(doc[page_index].get_text() or '').rstrip()}")
        finally:
            doc.close()
        body = "\n\n".join(chunks) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(body, encoding="utf-8")
        else:
            sys.stdout.write(body)
        return 0

    if args.command == "coefs":
        page_index = args.page - 1
        if page_index < 0:
            raise SystemExit("--page is 1-based")
        doc = fitz.open(str(pdf))
        try:
            coefs = parse_coef_page(doc[page_index], split_x=args.split_x)
        finally:
            doc.close()
        write_coefs_csv(coefs, args.out)
        print(f"wrote {len(coefs)} coefficients to {args.out}")
        return 0

    if args.command == "smooths":
        page_index = args.page - 1
        if page_index < 0:
            raise SystemExit("--page is 1-based")
        doc = fitz.open(str(pdf))
        try:
            rows = parse_smooths(doc[page_index])
        finally:
            doc.close()
        lines = [" | ".join(row) for row in rows]
        body = "\n".join(lines) + ("\n" if lines else "")
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(body, encoding="utf-8")
        else:
            sys.stdout.write(body if body else "")
        print(f"smooth rows={len(rows)}", file=sys.stderr)
        return 0

    if args.command == "render":
        written = render_pages(
            pdf,
            parse_pages(args.pages),
            args.out_dir,
            prefix=args.prefix,
            names=args.names,
            zoom=args.zoom,
        )
        for path in written:
            print(path)
        return 0

    raise SystemExit(f"unknown command {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
