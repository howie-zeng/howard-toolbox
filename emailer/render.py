"""Email HTML rendering with clipboard support for Windows."""

import os
import re
import html
import urllib.parse
import base64
import mimetypes
from typing import Optional

try:
    import win32clipboard
except ImportError:
    win32clipboard = None

import markdown
from bs4 import BeautifulSoup, Tag

STYLES = {
    "container": (
        "font-family:'Times New Roman',Times,serif;line-height:1.6;"
        "color:#333;max-width:700px;font-size:16px;"
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


def copy_to_clipboard(html_fragment: str) -> None:
    """
    Copy HTML to Windows clipboard in HTML Format for Outlook/Gmail.
    """
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


def _math_to_image_tag(match, display=False):
    """Convert latex to a high-quality image tag using CodeCogs."""
    latex = match.group(1)
    encoded = urllib.parse.quote(latex)
    
    src = f"https://latex.codecogs.com/png.latex?\\dpi{{150}}\\bg_white\\,{encoded}"
    
    style = "vertical-align:-4px;"
    if display:
        style = "display:block;margin:16px auto;max-width:100%;height:auto;"
        
    return f'<img src="{src}" style="{style}" alt="{html.escape(latex)}" />'


def _preprocess_math(text):
    """Convert $...$ and $$...$$ to image tags."""
    code_blocks = []
    
    def save_code(match):
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_{len(code_blocks)-1}__"
    
    text = re.sub(r'```[\s\S]*?```', save_code, text)
    text = re.sub(r'`[^`]+`', save_code, text)
    
    text = re.sub(r'\$\$([\s\S]+?)\$\$', lambda m: _math_to_image_tag(m, display=True), text)
    text = re.sub(r'\$([^\$\n]+?)\$', lambda m: _math_to_image_tag(m, display=False), text)
    
    for i, block in enumerate(code_blocks):
        text = text.replace(f"__CODE_BLOCK_{i}__", block)
        
    return text


def _ensure_blank_lines_around_image_lines(text: str) -> str:
    """
    Outlook can place text and images on the same line if image lines are not
    separated from surrounding text. Normalize standalone image lines so they
    always have a blank line before and after them.
    """
    lines = text.splitlines()
    normalized: list[str] = []
    in_fenced_code = False

    def is_standalone_image_line(line: str) -> bool:
        stripped = line.strip()
        return bool(
            re.match(r'^!\[[^\]]*\]\([^)]+\)$', stripped)
            or re.match(r'^<img\b[^>]*?/?>$', stripped, flags=re.IGNORECASE)
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


def render_markdown(
    markdown_text: str,
    output_path: Optional[str] = None,
    base_path: Optional[str] = None,
) -> str:
    """
    Render raw markdown to HTML with email-friendly formatting.
    
    Args:
        markdown_text: Raw markdown string
        output_path: Optional file path to save HTML
        base_path: Base path to resolve relative image links
    
    Returns:
        Rendered HTML string
    """
    if base_path is None:
        base_path = os.getcwd()

    text = _preprocess_math(markdown_text)
    text = _ensure_blank_lines_around_image_lines(text)
    raw_html = markdown.markdown(text, extensions=['tables', 'fenced_code', 'attr_list'])
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    # --- Process Images ---
    missing_images = []
    for img in soup.find_all('img'):
        src = img.get('src')
        if src and not re.match(r'^(http|https|data):', src):
            abs_path = os.path.abspath(os.path.join(base_path, src))
            if os.path.exists(abs_path):
                try:
                    with open(abs_path, "rb") as f:
                        data = f.read()
                        if len(data) > 2_000_000:
                            print(f"Warning: {src} is {len(data)/1e6:.1f}MB -- large images slow Outlook paste")
                        encoded = base64.b64encode(data).decode('utf-8')
                        mime_type, _ = mimetypes.guess_type(abs_path)
                        if not mime_type:
                            mime_type = 'image/png'
                        img['src'] = f"data:{mime_type};base64,{encoded}"
                except Exception as e:
                    print(f"Warning: Failed to embed image {src}: {e}")
            else:
                missing_images.append(f"{src} -> {abs_path}")
        
        current_style = img.get('style', '')
        if 'display' not in current_style:
            img['style'] = f"display:inline-block;{STYLES['img_default']}{current_style}"
        
        if not (img.get('width') or img.get('height') or 'width' in current_style or 'height' in current_style):
            img['style'] += "max-width:100%;height:auto;"

    # --- Unwrap Paragraphs containing only images ---
    for p in soup.find_all('p'):
        contents = [c for c in p.contents if not (isinstance(c, str) and not c.strip())]
        if contents and all(isinstance(c, Tag) and c.name == 'img' for c in contents):
            p.unwrap()

    # --- Process Tables ---
    for table in soup.find_all('table'):
        is_data_table = bool(table.find('thead'))
        
        if is_data_table:
            table['border'] = '0'
            table['cellpadding'] = '0'
            table['cellspacing'] = '0'
            table['style'] = STYLES["table"]
            
            if table.thead:
                table.thead['style'] = STYLES["thead"]
            
            for th in table.find_all('th'):
                th['style'] = STYLES["th"]
                
            for td in table.find_all('td'):
                td['style'] = STYLES["td"]
        else:
            table['style'] = table.get('style', '') + ";border-collapse:collapse;border:none;"
            for td in table.find_all('td'):
                td['style'] = td.get('style', '') + ";padding:4px;vertical-align:top;border:none;"

    # --- Process Blockquotes ---
    for bq in soup.find_all('blockquote'):
        bq['style'] = STYLES["blockquote"]

    # --- Process Headers ---
    for h_name in ['h1', 'h2', 'h3']:
        for h in soup.find_all(h_name):
            h['style'] = STYLES["heading"]

    # --- Process Code Blocks ---
    for pre in soup.find_all('pre'):
        pre['style'] = STYLES["pre"]
        if pre.code:
            pre.code['style'] = STYLES["pre_code"]

    # --- Process Inline Code ---
    for code in soup.find_all('code'):
        if code.parent.name != 'pre':
            code['style'] = STYLES["inline_code"]

    # --- Process Links ---
    for a in soup.find_all('a'):
        a['style'] = STYLES["link"]

    # --- Process Lists ---
    for list_tag in soup.find_all(['ul', 'ol']):
        list_tag['style'] = STYLES["list"]
    
    for li in soup.find_all('li'):
        li['style'] = STYLES["li"]

    # --- Process Horizontal Rules ---
    for hr in soup.find_all('hr'):
        hr['style'] = STYLES["hr"]

    if missing_images:
        print("Warning: Missing local image files (not embedded):")
        for item in missing_images:
            print(f" - {item}")

    # Wrap in container
    container = f"""
<div style="{STYLES['container']}">
    {str(soup)}
</div>
    """

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(container)
            
    return container
