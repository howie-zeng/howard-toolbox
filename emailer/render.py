"""Email HTML rendering, asset normalization, and Windows clipboard support.

Public surface:
    render_markdown(text, output_path=None, base_path=None) -> str
    copy_to_clipboard(html_fragment) -> None
    normalize_local_images(text, *, base_dir=None, assets_dir=None) -> str
    process_clipboard_images(text, *, assets_dir=None) -> str
"""

from __future__ import annotations

import base64
import datetime
import html as html_module
import mimetypes
import re
import shutil
import urllib.parse
from pathlib import Path

import markdown
from bs4 import BeautifulSoup, Tag

try:
    import win32clipboard
except ImportError:
    win32clipboard = None

EMAILER_DIR = Path(__file__).resolve().parent
DEFAULT_ASSETS_DIR = EMAILER_DIR / "assets"

STYLES = {
    "container": (
        "font-family:Aptos,Calibri,'Segoe UI',Arial,sans-serif;line-height:1.6;"
        "color:#333;max-width:700px;font-size:15px;"
    ),
    "img_default": "vertical-align:middle;margin:4px 6px 4px 0;",
    "heading": "margin-top:24px;margin-bottom:16px;font-weight:700;color:#2c3e50;",
    "table": "border-collapse:collapse;width:100%;margin:16px 0;border:1px solid #eee;",
    "thead": "background-color:#f8f9fa;",
    "th": "padding:12px;text-align:left;border-bottom:2px solid #ddd;font-weight:600;color:#34495e;",
    "td": "padding:12px;border-bottom:1px solid #eee;color:#555;",
    "blockquote": (
        "border-left:4px solid #3498db;margin:16px 0;padding:8px 16px;"
        "background-color:#f0f7fb;color:#555;font-style:italic;"
    ),
    "pre": (
        "background-color:#f6f8fa;border-radius:6px;padding:16px;"
        "font-family:Consolas,Monaco,'Andale Mono','Ubuntu Mono',monospace;"
        "font-size:14px;line-height:1.45;overflow:auto;border:1px solid #d0d7de;"
    ),
    "pre_code": "font-family:inherit;color:#24292f;",
    "inline_code": (
        "background-color:rgba(175,184,193,0.2);border-radius:6px;"
        "padding:0.2em 0.4em;font-family:Consolas,Monaco,monospace;"
        "font-size:85%;"
    ),
    "link": "color:#0969da;text-decoration:none;font-weight:500;",
    "list": "padding-left:24px;margin-top:0;margin-bottom:16px;",
    "li": "margin-bottom:4px;",
    "hr": "height:1px;background-color:#d0d7de;border:none;margin:24px 0;",
}

_URL_PREFIX_RE = re.compile(r"^(http|https|data):", flags=re.IGNORECASE)
_MD_IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
_HTML_IMG_RE = re.compile(
    r'(<img\b[^>]*\bsrc\s*=\s*")([^"]+)("[^>]*>)', flags=re.IGNORECASE
)

DEFAULT_MAX_LONG_EDGE_PX = 1600
DEFAULT_RESIZE_SIZE_THRESHOLD_BYTES = 2_000_000


# -----------------------------------------------------------------------------
# Clipboard (Windows)
# -----------------------------------------------------------------------------
def copy_to_clipboard(html_fragment: str) -> None:
    """Copy HTML to Windows clipboard in HTML Format for Outlook/Gmail."""
    if win32clipboard is None:
        raise RuntimeError("win32clipboard required; install pywin32 on Windows")

    full_html = (
        "<html><body>"
        "<!--StartFragment-->"
        f"{html_fragment}"
        "<!--EndFragment-->"
        "</body></html>"
    )
    full_bytes = full_html.encode("utf-8")

    header_template = (
        "Version:0.9\r\n"
        "StartHTML:{:010d}\r\n"
        "EndHTML:{:010d}\r\n"
        "StartFragment:{:010d}\r\n"
        "EndFragment:{:010d}\r\n"
    )

    dummy_header = header_template.format(0, 0, 0, 0).encode("utf-8")
    start_html = len(dummy_header)
    end_html = start_html + len(full_bytes)

    start_frag_marker = "<!--StartFragment-->"
    end_frag_marker = "<!--EndFragment-->"

    start_frag_char = full_html.index(start_frag_marker) + len(start_frag_marker)
    end_frag_char = full_html.index(end_frag_marker)

    start_fragment = start_html + len(full_html[:start_frag_char].encode("utf-8"))
    end_fragment = start_html + len(full_html[:end_frag_char].encode("utf-8"))

    header = header_template.format(
        start_html, end_html, start_fragment, end_fragment
    ).encode("utf-8")
    payload = header + full_bytes

    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        cf_html = win32clipboard.RegisterClipboardFormat("HTML Format")
        win32clipboard.SetClipboardData(cf_html, payload)
    finally:
        win32clipboard.CloseClipboard()


# -----------------------------------------------------------------------------
# Asset / image preprocessing (moved from run.py)
# -----------------------------------------------------------------------------
def _ensure_asset(path: str, base_dir: Path, assets_dir: Path) -> str:
    """Return a path rewritten to `assets/<name>` if a matching local file can be
    copied into `assets_dir`. Otherwise returns the original path unchanged.

    Rules:
    - URLs and data: URIs pass through.
    - If the path already starts with ``assets/`` and is missing from
      ``assets_dir``, try copying from ``base_dir/<basename>``.
    - Otherwise try ``base_dir/<path>``; on success, copy into ``assets_dir``
      and rewrite to ``assets/<basename>``.
    """
    if _URL_PREFIX_RE.match(path):
        return path

    if path.startswith("assets/"):
        asset_path = EMAILER_DIR / path
        if not asset_path.exists():
            alt_src = base_dir / Path(path).name
            if alt_src.exists():
                assets_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(alt_src, asset_path)
        return path

    src_path = (base_dir / path).resolve() if not Path(path).is_absolute() else Path(path)
    if src_path.exists():
        assets_dir.mkdir(parents=True, exist_ok=True)
        dest_path = assets_dir / src_path.name
        if not dest_path.exists():
            shutil.copy2(src_path, dest_path)
        return f"assets/{src_path.name}"

    return path


def normalize_local_images(
    markdown_text: str,
    *,
    base_dir: Path | str | None = None,
    assets_dir: Path | str | None = None,
) -> str:
    """Copy referenced local images into ``assets_dir`` and rewrite paths.

    Handles both Markdown ``![alt](path)`` and HTML ``<img src="path">`` forms.

    ``base_dir`` is the directory to resolve relative image paths against
    (defaults to the ``emailer/`` package directory, preserving legacy behavior).
    ``assets_dir`` is the destination for copied images (defaults to
    ``emailer/assets``).
    """
    base = Path(base_dir) if base_dir else EMAILER_DIR
    assets = Path(assets_dir) if assets_dir else DEFAULT_ASSETS_DIR

    def replace_md(match: re.Match[str]) -> str:
        target = match.group(1).strip()
        path = target.split()[0].strip('"').strip("'")
        new_path = _ensure_asset(path, base, assets)
        if new_path != path:
            return match.group(0).replace(path, new_path)
        return match.group(0)

    result = _MD_IMG_RE.sub(replace_md, markdown_text)

    def replace_html(match: re.Match[str]) -> str:
        prefix, path, suffix = match.group(1), match.group(2), match.group(3)
        new_path = _ensure_asset(path, base, assets)
        return f"{prefix}{new_path}{suffix}"

    return _HTML_IMG_RE.sub(replace_html, result)


def process_clipboard_images(
    markdown_text: str,
    *,
    assets_dir: Path | str | None = None,
) -> str:
    """Replace the ``{{CLIPBOARD}}`` tag with the current clipboard image.

    If no image is present, leaves a visible placeholder in the output so the
    user notices. Requires Pillow on Windows for ``ImageGrab``.
    """
    if "{{CLIPBOARD}}" not in markdown_text:
        return markdown_text

    from PIL import ImageGrab

    assets = Path(assets_dir) if assets_dir else DEFAULT_ASSETS_DIR

    print("Checking clipboard for image...")
    img = ImageGrab.grabclipboard()

    if img is None:
        print("Warning: {{CLIPBOARD}} tag found, but no image in clipboard.")
        return markdown_text.replace("{{CLIPBOARD}}", "**[NO IMAGE IN CLIPBOARD]**")

    if isinstance(img, list):
        print(f"Clipboard contains file paths: {img}")
        return markdown_text.replace(
            "{{CLIPBOARD}}", f"**[CLIPBOARD WAS FILE PATH: {img[0]}]**"
        )

    assets.mkdir(parents=True, exist_ok=True)
    filename = f"paste_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = assets / filename
    img.save(filepath, "PNG")
    print(f"Saved clipboard image to {filepath}")
    return markdown_text.replace("{{CLIPBOARD}}", f"![](assets/{filename})")


# -----------------------------------------------------------------------------
# Image resize (in-memory, does not touch source files or assets/)
# -----------------------------------------------------------------------------
def maybe_resize_image_bytes(
    data: bytes,
    *,
    max_long_edge: int = DEFAULT_MAX_LONG_EDGE_PX,
    size_threshold_bytes: int = DEFAULT_RESIZE_SIZE_THRESHOLD_BYTES,
) -> tuple[bytes, bool]:
    """Return ``(maybe_resized_bytes, did_resize)``.

    Triggers resize when the image's longest edge exceeds ``max_long_edge`` or
    its serialized size exceeds ``size_threshold_bytes``. The resized bytes
    are only returned when they are smaller than the original. If Pillow
    cannot decode the image, the original bytes are returned unchanged.

    Never mutates source files on disk -- operates entirely in memory.
    """
    import io

    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError:
        return data, False

    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (OSError, UnidentifiedImageError):
        return data, False

    fmt = img.format or "PNG"
    width, height = img.size
    long_edge = max(width, height)

    needs_resize = long_edge > max_long_edge
    needs_recompress = len(data) > size_threshold_bytes

    if not needs_resize and not needs_recompress:
        img.close()
        return data, False

    if needs_resize:
        scale = max_long_edge / long_edge
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        working = img.resize(new_size, Image.LANCZOS)
    else:
        working = img.copy()

    buf = io.BytesIO()
    try:
        if fmt == "JPEG":
            working.save(buf, format="JPEG", quality=85, optimize=True)
        elif fmt == "PNG":
            working.save(buf, format="PNG", optimize=True)
        else:
            working.save(buf, format=fmt)
    except (OSError, ValueError):
        img.close()
        working.close()
        return data, False

    img.close()
    working.close()
    new_data = buf.getvalue()
    if len(new_data) < len(data):
        return new_data, True
    return data, False


# -----------------------------------------------------------------------------
# Math preprocessing
# -----------------------------------------------------------------------------
def _math_to_image_tag(match: re.Match[str], display: bool = False) -> str:
    latex = match.group(1)
    encoded = urllib.parse.quote(latex)
    src = f"https://latex.codecogs.com/png.latex?\\dpi{{150}}\\bg_white\\,{encoded}"
    style = "vertical-align:-4px;"
    if display:
        style = "display:block;margin:16px auto;max-width:100%;height:auto;"
    return f'<img src="{src}" style="{style}" alt="{html_module.escape(latex)}" />'


def _preprocess_math(text: str) -> str:
    """Convert ``$...$`` and ``$$...$$`` to image tags, leaving code blocks alone."""
    code_blocks: list[str] = []

    def save_code(match: re.Match[str]) -> str:
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_{len(code_blocks) - 1}__"

    text = re.sub(r"```[\s\S]*?```", save_code, text)
    text = re.sub(r"`[^`]+`", save_code, text)

    text = re.sub(
        r"\$\$([\s\S]+?)\$\$", lambda m: _math_to_image_tag(m, display=True), text
    )
    text = re.sub(
        r"\$([^\$\n]+?)\$", lambda m: _math_to_image_tag(m, display=False), text
    )

    for i, block in enumerate(code_blocks):
        text = text.replace(f"__CODE_BLOCK_{i}__", block)

    return text


# -----------------------------------------------------------------------------
# Outlook line-break normalization
# -----------------------------------------------------------------------------
def _ensure_blank_lines_around_image_lines(text: str) -> str:
    """Insert blank lines around standalone image lines so Outlook doesn't
    merge them with adjacent text."""
    lines = text.splitlines()
    normalized: list[str] = []
    in_fenced_code = False

    def is_standalone_image_line(line: str) -> bool:
        stripped = line.strip()
        return bool(
            re.match(r"^!\[[^\]]*\]\([^)]+\)$", stripped)
            or re.match(r"^<img\b[^>]*?/?>$", stripped, flags=re.IGNORECASE)
        )

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fenced_code = not in_fenced_code
            normalized.append(line)
            continue

        if not in_fenced_code and is_standalone_image_line(line):
            if normalized and normalized[-1].strip():
                normalized.append("")
            normalized.append(line)
            next_line = lines[idx + 1] if idx + 1 < len(lines) else ""
            if next_line.strip():
                normalized.append("")
            continue

        normalized.append(line)

    return "\n".join(normalized)


# -----------------------------------------------------------------------------
# Main renderer
# -----------------------------------------------------------------------------
def render_markdown(
    markdown_text: str,
    output_path: str | None = None,
    base_path: str | None = None,
    *,
    resize_images: bool = True,
    max_long_edge: int = DEFAULT_MAX_LONG_EDGE_PX,
) -> str:
    """Render raw markdown to HTML with email-friendly formatting.

    Args:
        markdown_text: Raw markdown string.
        output_path: Optional file path to save the rendered HTML.
        base_path: Base path to resolve relative image ``src`` attributes. If
            omitted, defaults to the current working directory (legacy behavior).
        resize_images: If True (default), downscale large local images
            in-memory before base64 embedding. Does not mutate source files.
        max_long_edge: Long-edge pixel cap used when ``resize_images`` is True.

    Returns:
        Rendered HTML string.
    """
    base = Path(base_path).resolve() if base_path else Path.cwd()

    text = _preprocess_math(markdown_text)
    text = _ensure_blank_lines_around_image_lines(text)
    raw_html = markdown.markdown(text, extensions=["tables", "fenced_code", "attr_list"])
    soup = BeautifulSoup(raw_html, "html.parser")

    # --- Process Images ---
    missing_images: list[str] = []
    for img in soup.find_all("img"):
        src = img.get("src")
        if src and not _URL_PREFIX_RE.match(src):
            abs_path = (base / src).resolve()
            if abs_path.exists():
                try:
                    data = abs_path.read_bytes()
                    original_size = len(data)
                    if resize_images:
                        data, did_resize = maybe_resize_image_bytes(
                            data, max_long_edge=max_long_edge
                        )
                        if did_resize:
                            print(
                                f"Resized {src}: {original_size / 1e6:.2f}MB -> "
                                f"{len(data) / 1e6:.2f}MB (long-edge cap {max_long_edge}px)"
                            )
                    if len(data) > 2_000_000:
                        print(
                            f"Warning: {src} is {len(data) / 1e6:.1f}MB "
                            "-- large images slow Outlook paste"
                        )
                    encoded = base64.b64encode(data).decode("utf-8")
                    mime_type, _ = mimetypes.guess_type(str(abs_path))
                    if not mime_type:
                        mime_type = "image/png"
                    img["src"] = f"data:{mime_type};base64,{encoded}"
                except OSError as e:
                    print(f"Warning: Failed to embed image {src}: {e}")
            else:
                missing_images.append(f"{src} -> {abs_path}")

        current_style = img.get("style", "")
        if "display" not in current_style:
            img["style"] = f"display:inline-block;{STYLES['img_default']}{current_style}"

        if not (
            img.get("width")
            or img.get("height")
            or "width" in current_style
            or "height" in current_style
        ):
            img["style"] += "max-width:100%;height:auto;"

    # --- Unwrap paragraphs that contain only images ---
    for p in soup.find_all("p"):
        contents = [c for c in p.contents if not (isinstance(c, str) and not c.strip())]
        if contents and all(isinstance(c, Tag) and c.name == "img" for c in contents):
            p.unwrap()

    # --- Tables ---
    for table in soup.find_all("table"):
        is_data_table = bool(table.find("thead"))
        if is_data_table:
            table["border"] = "0"
            table["cellpadding"] = "0"
            table["cellspacing"] = "0"
            table["style"] = STYLES["table"]
            if table.thead:
                table.thead["style"] = STYLES["thead"]
            for th in table.find_all("th"):
                th["style"] = STYLES["th"]
            for td in table.find_all("td"):
                td["style"] = STYLES["td"]
        else:
            table["style"] = table.get("style", "") + ";border-collapse:collapse;border:none;"
            for td in table.find_all("td"):
                td["style"] = td.get("style", "") + ";padding:4px;vertical-align:top;border:none;"

    # --- Blockquotes ---
    for bq in soup.find_all("blockquote"):
        bq["style"] = STYLES["blockquote"]

    # --- Headings ---
    for h_name in ["h1", "h2", "h3"]:
        for h in soup.find_all(h_name):
            h["style"] = STYLES["heading"]

    # --- Code blocks ---
    for pre in soup.find_all("pre"):
        pre["style"] = STYLES["pre"]
        if pre.code:
            pre.code["style"] = STYLES["pre_code"]

    # --- Inline code ---
    for code in soup.find_all("code"):
        if code.parent.name != "pre":
            code["style"] = STYLES["inline_code"]

    # --- Links ---
    for a in soup.find_all("a"):
        a["style"] = STYLES["link"]

    # --- Lists ---
    for list_tag in soup.find_all(["ul", "ol"]):
        list_tag["style"] = STYLES["list"]
    for li in soup.find_all("li"):
        li["style"] = STYLES["li"]

    # --- Horizontal rules ---
    for hr in soup.find_all("hr"):
        hr["style"] = STYLES["hr"]

    if missing_images:
        print("Warning: Missing local image files (not embedded):")
        for item in missing_images:
            print(f" - {item}")

    container = f'\n<div style="{STYLES["container"]}">\n    {soup!s}\n</div>\n    '

    if output_path:
        Path(output_path).write_text(container, encoding="utf-8")

    return container
