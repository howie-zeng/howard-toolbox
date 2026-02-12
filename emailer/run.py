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
Subject: Overview: Core files for adding a new product (LMSim)

Hi Team,

To add a new product with transition and cashflow simulation, here are the key areas of the codebase to modify.

### 1. Asset Definition
**Goal:** Define inputs and normalize raw data.
*   `LMAsset/include/Asset.h`: Base fields.
*   `LMAsset/include/ResiAsset.h` / `.cpp`: Residential logic (extend this or `Asset`).
*   `LMAsset/src/*Loader.cpp`: Input parsing (see `StacrLoader.cpp` for reference).

### 2. Cashflow Engine
**Goal:** Generate monthly cashflows from the asset.
*   `LMCashFlow/include/LoanCashFlow.h`: Data structures.
*   `LMCashFlow/src/*`: logic implementation.
*   `LMCashFlow/*Adaptor*`: The bridge between the asset and the model (e.g., `ResiAssetCashFlowAdaptor`).

### 3. Transition Model
**Goal:** Simulate state transitions (Current → Prepaid/Default).
*   `LMModel/include/TransSimple.h`: Main simulation loop.
*   `LMModel/include/TransState.h`: State definitions.
*   `LMModel/include/ResiModelVariable.h`: Model variables (predictors).
*   `LMModel/ResiModelVariableLoader.cpp`: Loads model coefficients from files.

### 4. Wiring & Execution
**Goal:** Hook it all together.
*   `LMModel/src/ModelFactory.cpp`: Logic to select the new model type.
*   `LMAssetVisitor/src/ResiAssetVisitor.cpp`: Instantiates and runs the model.

---

### Implementation Checklist

1.  **Asset**: Create/Update Loader & Asset class.
2.  **Cashflow**: Implement `CashFlowAdaptor` for the new product.
3.  **Model**: Subclass `TransStateModel` (or reuse `TransSimple` if fits).
4.  **Factory**: Register the new model in `ModelFactory`.
5.  **Config**: Register new variables in `ResiModelVariableLoader`.

Let me know if you need help with a specific component.

Best,
[Your Name]
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