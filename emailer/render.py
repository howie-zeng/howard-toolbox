"""Email HTML rendering with clipboard support for Windows."""

import os
import re
import urllib.parse
import base64
import mimetypes
from pathlib import Path
from typing import Optional

import win32clipboard
import markdown
from bs4 import BeautifulSoup, Tag

DEFAULT_IMG_STYLE = (
    "vertical-align:middle;"
    "margin:4px 6px 4px 0;"
)


def copy_to_clipboard(html_fragment: str) -> None:
    """
    Copy HTML to Windows clipboard in HTML Format for Outlook/Gmail.
    """
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
        
    return f'<img src="{src}" style="{style}" alt="{latex}" />'


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


def render_markdown(
    markdown_text: str,
    copy: bool = True,
    output_path: Optional[str] = None,
    base_path: str = None
) -> str:
    """
    Render raw markdown to HTML with email-friendly formatting.
    
    Args:
        markdown_text: Raw markdown string
        copy: If True, copy HTML to clipboard automatically
        output_path: Optional file path to save HTML
        base_path: Base path to resolve relative image links
    
    Returns:
        Rendered HTML string
    """
    if base_path is None:
        base_path = os.getcwd()

    text = _preprocess_math(markdown_text)
    raw_html = markdown.markdown(text, extensions=['tables', 'fenced_code', 'attr_list'])
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    # --- Process Images ---
    for img in soup.find_all('img'):
        src = img.get('src')
        if src and not re.match(r'^(http|https|data):', src):
            abs_path = os.path.abspath(os.path.join(base_path, src))
            if os.path.exists(abs_path):
                try:
                    with open(abs_path, "rb") as f:
                        data = f.read()
                        encoded = base64.b64encode(data).decode('utf-8')
                        mime_type, _ = mimetypes.guess_type(abs_path)
                        if not mime_type:
                            mime_type = 'image/png'
                        img['src'] = f"data:{mime_type};base64,{encoded}"
                except Exception as e:
                    print(f"Warning: Failed to embed image {src}: {e}")
            else:
                img['src'] = Path(abs_path).as_uri()
        
        current_style = img.get('style', '')
        if 'display' not in current_style:
            img['style'] = f"display:inline-block;{DEFAULT_IMG_STYLE}{current_style}"
        
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
            table['style'] = "border-collapse:collapse;width:100%;margin:16px 0;border:1px solid #eee;"
            
            if table.thead:
                table.thead['style'] = "background-color:#f8f9fa;"
            
            for th in table.find_all('th'):
                th['style'] = "padding:12px;text-align:left;border-bottom:2px solid #ddd;font-weight:600;color:#34495e;"
                
            for td in table.find_all('td'):
                td['style'] = "padding:12px;border-bottom:1px solid #eee;color:#555;"
        else:
            table['style'] = table.get('style', '') + ";border-collapse:collapse;border:none;"
            for td in table.find_all('td'):
                td['style'] = td.get('style', '') + ";padding:4px;vertical-align:top;border:none;"

    # --- Process Blockquotes ---
    for bq in soup.find_all('blockquote'):
        bq['style'] = "border-left:4px solid #3498db;margin:16px 0;padding:8px 16px;background-color:#f0f7fb;color:#555;font-style:italic;"

    # --- Process Headers ---
    for h_name in ['h1', 'h2', 'h3']:
        for h in soup.find_all(h_name):
            h['style'] = "margin-top:24px;margin-bottom:16px;font-weight:700;color:#2c3e50;"

    # Wrap in container
    container = f"""
<div style="font-family:'Times New Roman',Times,serif;line-height:1.6;color:#2c3e50;max-width:700px;font-size:16px;">
    {str(soup)}
    <div style="border-top:1px solid #eaeaea;margin:24px 0;"></div>
    <div style="font-size:12px;color:#95a5a6;text-align:right;">
        Generated by <b>Howard Toolbox</b>
    </div>
</div>
    """

    if copy:
        copy_to_clipboard(container)
        print("✓ Copied markdown email to clipboard")
        
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(container)
            
    return container
