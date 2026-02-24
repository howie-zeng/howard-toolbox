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
Hi team,

Update on the CRT prepay model pipeline — covers performance optimizations, new utility functions, and infrastructure improvements.

---

**1. Performance Optimizations**

- **Burnout backfill vectorized (73x speedup)**: Replaced the per-loan backfill loop with a single `data.table` non-equi join + bulk column computation. Runtime dropped from ~63s to <1s per data split. Tieout verified: 177,153 rows, 0 absolute difference across all burnout columns.
- **`fast_fit_model_v2`** / **`predict_w_cluster_v2`**: Both automatically subset data to only formula-referenced columns before passing to the cluster. Reduces memory and serialization overhead significantly for large datasets (10M+ rows).
- **Model report generation** (`model_report_all_optimized`): Rewrote the reporting system with parallel processing for continuous variable plots via `doParallel`/`foreach` (~5–6x faster with 7 variables on 8 cores). Added automatic intermediate file cleanup on failure, native two-stage model support, and large-dataset sampling. Separated into dedicated `model_report_optimized.R`.
- **King-Zeng undersampling** (`get_sample_undersampling`): Replaced the old `get_sample_over_sampling` with a fully vectorized `data.table` implementation. Eliminates `data.frame` conversion and `bind_rows` accumulation. Same math, cleaner edge-case handling, structured return with diagnostics.

---

**2. New Utility Functions**

- **`apply_recency_weighting`**: Exponential decay weighting by observation date with configurable half-life, caps, and diagnostic plots.
- **`get_stratified_random_sample`**: Stratified sampling for large datasets when full data exceeds memory/time budget for exploratory fitting.

---

**3. CRT Pipeline: End-to-End Workflow**

The CRT model pipeline now runs as a sequence of standalone scripts, each producing outputs consumed by the next.

**Step 1: Data Extraction** — `redshift_data/crt_get_data.R`
- Pulls loan-level CRT data from Redshift, samples by vintage, unloads via S3
- Output: `P:/CRT/cas_crt_YYYYMMDD.parquet`

**Step 2: Feature Engineering** — `crt/Data_prep/crt_data_prep.R`
- Splits raw data by loan ID, runs `prep_crt_data_v1.2` on each split
- Computes HPI, CLTV, all incentive/burnout variants (ratio, payment, spread, LLPA-spread), HAMP/HARP eligibility, transition targets
- Output: `P:/CRT/cas_crt_YYYYMMDD/prep_fannie_data_{i}_{date}_{version}.rds` (10 splits)

**Step 3a: Turnover** — Undersample + Fit
- `crt_turnover_undersample.R` — reads prep splits, filters by `inc_0_spread_llpa`, undersamples with KZ correction, builds training + tracking files
- `crt_turnover_model.R` — fits turnover GAM, generates comparison report vs PROD

**Step 3b: Refi** — Turnover Separation + Undersample + Fit
- `crt_refi_data_prep.R` — loads turnover model, predicts turnover per loan, flags `isTurnover` within each (date, spread bucket) using s4 strategy
- `crt_refi_undersample.R` — reads s4 output, drops turnovers from Cto0, undersamples, builds training + tracking files
- `crt_refinance_model.R` — fits two-stage refi GAM (Stage 1: economic drivers, Stage 2: servicer + state), generates comparison report vs PROD

**LLPA Grid** (prerequisite, run once or when grid changes) — `crt/crt_llpa.R`
- Generates `support_data/crt_llpa_interpolated.txt` consumed by Step 2
- Independent from Jumbo; edit `get_crt_llpa_base_grid()` to update CRT-specific values

![](assets/crt_pipeline_diagram.png)

All changes are on the CRT branch. Happy to walk through any of this in more detail.

Best,
Howard

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