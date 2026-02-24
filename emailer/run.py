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


def normalize_local_images(markdown_text):
    """
    Ensure images are loaded from assets/ per README.
    If an image is referenced outside assets/, copy it into assets/ and rewrite the link.
    """
    pattern = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')

    def replace_match(match):
        target = match.group(1).strip()
        # Strip optional title portion (e.g., "path" "title")
        path = target.split()[0].strip('"').strip("'")

        if re.match(r'^(http|https|data):', path):
            return match.group(0)

        # If already assets/, ensure file exists (copy from root if needed)
        if path.startswith("assets/"):
            asset_path = os.path.join(SCRIPT_DIR, path)
            if not os.path.exists(asset_path):
                alt_src = os.path.join(SCRIPT_DIR, os.path.basename(path))
                if os.path.exists(alt_src):
                    os.makedirs(ASSETS_DIR, exist_ok=True)
                    shutil.copy2(alt_src, asset_path)
            return match.group(0)

        # If referenced from current folder (or parent), copy into assets/ and rewrite
        src_path = os.path.join(SCRIPT_DIR, path)
        if os.path.exists(src_path):
            os.makedirs(ASSETS_DIR, exist_ok=True)
            dest_path = os.path.join(ASSETS_DIR, os.path.basename(path))
            if not os.path.exists(dest_path):
                shutil.copy2(src_path, dest_path)
            return match.group(0).replace(path, f"assets/{os.path.basename(path)}")

        return match.group(0)

    return pattern.sub(replace_match, markdown_text)


# -----------------------------------------------------------------------------
# EDIT YOUR MARKDOWN CONTENT HERE
# -----------------------------------------------------------------------------
MD_CONTENT = r"""
**Summary of Changes**

- Changed ratio to spread with LLPA adjustment; LLPA also used in refi/turnover cutoff.
- Changed 3y3m median to 6m1m median, from ratio to spread.
- Dropped `cur_bal`; using inflation-adjusted original balance instead.
- Servicer and state moved to a second-stage model.
- Lowered the weight for the COVID period and slightly increased the weight for the post-COVID period.

![](2026-02-23-17-06-29.png)

---

**Model Fits**

Fits attached below. I think we can start implementing the new model and running vectors.

![](2026-02-23-18-01-04.png)

![](2026-02-23-16-58-22.png)

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