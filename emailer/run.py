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
Hi Team,

Here is the monthly tracking review for January 2026. The supporting charts are included below.

**1. Key Issue / Anomaly**

*   **NONQM M60 to D** is off by a large amount. The **6% M6 to D** rate looks unusually high.

![](2026-02-03-14-21-09.png)

I double-checked the numbers and the code. The **CDR calculations for NONQM** (and possibly **JUMBO** and **HELOC**) appear to be incorrect. If there are no objections, I will proceed with the fixes.

**2. Example Discrepancy**

Example NONQM deal (**CHNGE 2022-2**): our result shows **1.7 CDR** while **Intex** shows **0**.

![](2026-02-03-14-29-46.png)
![](2026-02-03-14-30-44.png)

**3. Implied vs Proposed Dial (by deal type)**

**STACR**
![](2026-02-03-14-31-41.png)

**CAS**
![](2026-02-03-14-31-48.png)

**JUMBO**  
Due to small loan counts for most transitions, I do **not** recommend applying any dial for JUMBO.
![](2026-02-03-14-47-43.png)

**HELOC (FIGRE)**
![](2026-02-03-14-32-52.png)

**NONQM**
![](2026-02-03-14-34-14.png)

**4. CPR by Deal Type**

**CAS**
![](2026-02-03-14-37-27.png)

**STACR**
![](2026-02-03-14-37-49.png)

**JUMBO**
![](2026-02-03-14-38-23.png)

**NONQM**
![](2026-02-03-14-38-39.png)

**HELOC (FIGRE)**
![](2026-02-03-14-38-53.png)

../2026-02-04-09-16-14.png

../2026-02-04-09-16-59.png
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