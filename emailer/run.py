"""
Script to generate a fancy email from raw markdown.
Just edit the MD_CONTENT variable below and run this script.

Usage: python run.py
"""

import os
import datetime
import re
import shutil
from PIL import ImageGrab

from render import render_markdown

# Get the directory where this script lives
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SCRIPT_DIR, "assets")
OUTPUTS_DIR = os.path.join(SCRIPT_DIR, "outputs")
STRICT_IMAGES = False


def process_clipboard_images(markdown_text):
    """
    Look for {{CLIPBOARD}} tag. If found, save clipboard image to assets/ and replace tag.
    """
    if "{{CLIPBOARD}}" not in markdown_text:
        return markdown_text

    print("Checking clipboard for image...")
    img = ImageGrab.grabclipboard()
    
    if img is None:
        print("Warning: {{CLIPBOARD}} tag found, but no image in clipboard.")
        return markdown_text.replace("{{CLIPBOARD}}", "**[NO IMAGE IN CLIPBOARD]**")

    os.makedirs(ASSETS_DIR, exist_ok=True)

    filename = f"paste_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = os.path.join(ASSETS_DIR, filename)
    
    if isinstance(img, list):
        print(f"Clipboard contains file paths: {img}")
        return markdown_text.replace("{{CLIPBOARD}}", f"**[CLIPBOARD WAS FILE PATH: {img[0]}]**")
    else:
        img.save(filepath, "PNG")
        print(f"Saved clipboard image to {filepath}")
        return markdown_text.replace("{{CLIPBOARD}}", f"![](assets/{filename})")


def _ensure_asset(path: str) -> str:
    """
    Given a local image path, ensure it lives in assets/.
    Copies from SCRIPT_DIR if needed. Returns the (possibly rewritten) path.
    """
    if re.match(r'^(http|https|data):', path):
        return path

    if path.startswith("assets/"):
        asset_path = os.path.join(SCRIPT_DIR, path)
        if not os.path.exists(asset_path):
            alt_src = os.path.join(SCRIPT_DIR, os.path.basename(path))
            if os.path.exists(alt_src):
                os.makedirs(ASSETS_DIR, exist_ok=True)
                shutil.copy2(alt_src, asset_path)
        return path

    src_path = os.path.join(SCRIPT_DIR, path)
    if os.path.exists(src_path):
        os.makedirs(ASSETS_DIR, exist_ok=True)
        dest_path = os.path.join(ASSETS_DIR, os.path.basename(path))
        if not os.path.exists(dest_path):
            shutil.copy2(src_path, dest_path)
        return f"assets/{os.path.basename(path)}"

    return path


def normalize_local_images(markdown_text):
    """
    Ensure all images (Markdown ![](…) and HTML <img src="…">) are loaded
    from assets/. Copies files into assets/ and rewrites paths as needed.
    """
    # Handle Markdown images: ![alt](path)
    md_pattern = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')

    def replace_md(match):
        target = match.group(1).strip()
        path = target.split()[0].strip('"').strip("'")
        new_path = _ensure_asset(path)
        if new_path != path:
            return match.group(0).replace(path, new_path)
        return match.group(0)

    result = md_pattern.sub(replace_md, markdown_text)

    # Handle HTML images: <img src="path" ...>
    html_pattern = re.compile(r'(<img\b[^>]*\bsrc\s*=\s*")([^"]+)("[^>]*>)', flags=re.IGNORECASE)

    def replace_html(match):
        prefix, path, suffix = match.group(1), match.group(2), match.group(3)
        new_path = _ensure_asset(path)
        return f"{prefix}{new_path}{suffix}"

    result = html_pattern.sub(replace_html, result)

    return result
# NQM stats

#         I         O         S 
# 46.497065 50.292392  3.210543 

# -----------------------------------------------------------------------------
# EDIT YOUR MARKDOWN CONTENT HERE
# -----------------------------------------------------------------------------
MD_CONTENT = fr"""
Please see the attached PDF for details, including how the data is processed.

High-DTI borrowers show a higher D90+ rate and take much longer to recover (left: WALA 6–60; right: WALA 60–120).

![](2026-03-13-18-24-01.png)

![](2026-03-13-18-24-18.png)

90+ delinquency rate by WALA: seasoned loans flatten out, while high-DTI loans show elevated delinquency rates within the same FICO bucket.

![](2026-03-13-18-22-24.png)
"""



# -----------------------------------------------------------------------------

if __name__ == "__main__":
    os.makedirs(ASSETS_DIR, exist_ok=True)
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    
    final_content = process_clipboard_images(MD_CONTENT)
    final_content = normalize_local_images(final_content)
    
    print("Formatting email...")
    render_markdown(
        final_content,
        copy=True,
        output_path=os.path.join(OUTPUTS_DIR, "latest_email.html"),
        base_path=SCRIPT_DIR,
        strict_images=STRICT_IMAGES,
    )
    print("\n---------------------------------------------------------")
    print("Done! The HTML is in your clipboard.")
    print("1. Go to Outlook/Gmail")
    print("2. Paste (Ctrl+V)")
    print("---------------------------------------------------------")


# python emailer\run.py