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
Adding JP's vectors for select deals. Please refer to the previous email for RateDown300, SuperBull, and SuperBear comparisons.

**Summary**

- JP's turnover model looks fine, but has very strong seasonality — probably the same order of magnitude as before we dialed seasonality down to 60%.
- For the refi model, I still don't see a need to adjust the burnout curve — they decay at about the same speed.
- JP's vectors for high-WAC or recent-vintage deals are higher than ours, but even for recent vintages, JP vectors appear too high (even higher than YB).
- **I would still recommend no dial for the new CRT model.** If we really want some form of dial, we could add a numeric dial that expires in 4 years.

Model fits, tracking, and all vectors are attached. The CRT vector Excel includes all scenarios and their CPR — feel free to explore. Below I'm only showing the comparison.

**Minimal Risk Impact**

![](2026-02-26-16-31-51.png)

**CAS 2019-HRP1**

![](2026-02-26-16-07-08.png) ![](2026-02-26-16-11-28.png)

**STACR 2018-HQA2**

![](2026-02-26-16-06-34.png) ![](2026-02-26-16-11-53.png)

**STACR 2022-DNA2**

![](2026-02-26-16-06-20.png) ![](2026-02-26-16-12-19.png)

**CAS 2022-R06**

![](2026-02-26-16-07-26.png) ![](2026-02-26-16-13-23.png)

**STACR 2024-DNA3**

![](2026-02-26-16-07-47.png) ![](2026-02-26-16-13-44.png)

**STACR 2025-DNA2**

![](2026-02-26-16-08-21.png) ![](2026-02-26-16-14-00.png)

**STACR 2024-HQA2**

![](2026-02-26-16-09-31.png) ![](2026-02-26-16-14-43.png)

**STACR 2024-DNA2**

![](2026-02-26-16-09-48.png) ![](2026-02-26-16-15-02.png)

**CAS 2025-R02**

![](2026-02-26-16-08-36.png) ![](2026-02-26-16-14-23.png)

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