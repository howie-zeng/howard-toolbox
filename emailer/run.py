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
**Monthly Model Update: Return to Spread Incentive Framework**

As discussed in the "Jumbo Update," we are reverting to the spread incentive framework. This version introduces a new short-term PMMS momentum variable modeled with two smooths (Low WAC and High WAC).

**New Variable Definition**

The short-term momentum is defined as:

$$
\text{pmms30\_spread\_3m} = \text{pmms\_lag3m} - \text{pmms\_lowest\_weekly}
$$

Among several alternative media/momentum variables tested (e.g., `Media3y1m`, `Media1y1m`, `pmms30_spread_24m`), the 3-month PMMS spread (`pmms30_spread_3m`) performed the best.

**Model Updates & Performance**

**1. New Smooth Functions**
*Left: Low WAC | Right: High WAC*

![](assets/2026-01-29-16-05-11.png)

**2. Impact Analysis**
*Left: With New Variable | Right: Before Change*

![](assets/2026-01-29-16-05-17.png)

**3. Performance by Vintage**

![](assets/2026-01-29-16-07-32.png)
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
