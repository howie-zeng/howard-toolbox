"""
Script to generate a fancy email from raw markdown.
Just edit the MD_CONTENT variable below and run this script.

Usage: python run.py
"""

import os
import datetime
from PIL import ImageGrab

from render import render_markdown

# Get the directory where this script lives
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SCRIPT_DIR, "assets")
OUTPUTS_DIR = os.path.join(SCRIPT_DIR, "outputs")


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


# -----------------------------------------------------------------------------
# EDIT YOUR MARKDOWN CONTENT HERE
# -----------------------------------------------------------------------------
MD_CONTENT = r"""
**Proposal: Jumbo Monitor Screen & Monthly Reporting**

**1. Overview**

This proposal outlines the plan for a new **Jumbo Monitor Screen**. As a preliminary step before building the full interactive monitor, we can distribute the key tracking metrics as a **monthly email report**.

**2. Future Enhancements**

Once the baseline monthly report is established, we can expand the monitor to include additional groupings such as:
*   **WAC**
*   **Vintage**
*   **Position Only** vs. **All Deals**
*   Other custom stratifications

**3. Examples**

Here are two examples of the proposed reporting format:

**A. Shelf Tracking**

*(Insert Shelf Tracking Summary Table/Chart Here)*

**B. IO Deal Tracking**

*(Insert IO Deal Tracking Summary Table/Chart Here)*
"""

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    os.makedirs(ASSETS_DIR, exist_ok=True)
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    
    final_content = process_clipboard_images(MD_CONTENT)
    
    print("Formatting email...")
    render_markdown(
        final_content,
        copy=True,
        output_path=os.path.join(OUTPUTS_DIR, "latest_email.html"),
        base_path=SCRIPT_DIR,
    )
    print("\n---------------------------------------------------------")
    print("Done! The HTML is in your clipboard.")
    print("1. Go to Outlook/Gmail")
    print("2. Paste (Ctrl+V)")
    print("---------------------------------------------------------")


# python emailer\run.py