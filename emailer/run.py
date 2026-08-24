"""Generate a fancy email from raw markdown.

Edit ``MD_CONTENT`` below and run::

    python emailer/run.py

The rendered HTML will be copied to the Windows clipboard, ready to paste
into Outlook or Gmail.

CLI flags::

    --md-file PATH      Read markdown body from a file instead of MD_CONTENT.
                        Relative image paths resolve from the file's folder.
    --preview           Open the rendered HTML in the default browser.
    --no-clipboard      Render to file only; skip the clipboard copy.
    --no-resize         Embed images at original size (skip auto-resize).
"""

from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

try:
    from .render import (
        EMAILER_DIR,
        copy_to_clipboard,
        normalize_local_images,
        process_clipboard_images,
        render_markdown,
    )
except ImportError:  # running as `python emailer/run.py`
    from render import (  # type: ignore[no-redef]
        EMAILER_DIR,
        copy_to_clipboard,
        normalize_local_images,
        process_clipboard_images,
        render_markdown,
    )

OUTPUTS_DIR = EMAILER_DIR / "outputs"


# -----------------------------------------------------------------------------
# EDIT YOUR MARKDOWN CONTENT HERE
# -----------------------------------------------------------------------------
MD_CONTENT = r"""
Hi all,

**FCLS model update:** We refit the five FCLS models. The main takeaway is that judicial process, time in foreclosure, and CLTV are doing most of the work, and the time series pick up the COVID break plus the later rise in cures.

- **REO and liquidation** still drop sharply in 2020, then recover slowly. Judicial NY/NJ/FL and modified loans stay much slower to REO.
- **Payoff from FCLS** is the weakest fit. Higher CLTV and longer time in FCLS reduce payoff; house-price gains help.
- **Cure** is the biggest post-2021 shift: monthly FCLStoC moved from about 1–2% to a 6–7% plateau, and the model tracks that step.
- **Better (`B`)** is exit from FCLS to a non-current status. CES/Jumbo and repeat 30s raise it; judicial flags and long time-in-status lower it.
- **`cal_yr`** is in REO, liquidation, cure, and better (not payoff). I added it to capture FCLS policy and process changes. In every model that uses it, the recent end of the `cal_yr` smooth goes to 0: the term does not move recent predictions. It absorbs historical policy-driven volatility so the other features can fit the structural pattern.

**Legend:** points = actual monthly rate; line = predicted; point size = sample count.

---

**1. FCLStoREO**

In-sample n = 492,439. Deviance explained = 13.9%. The overtime plot captures the 2020 foreclosure freeze and a gradual recovery toward ~2.5% by 2026. Higher updated CLTV raises REO; higher HPA lowers it. Time in status ramps much more in judicial states.

| Term | Estimate | Notes |
| --- | ---: | --- |
| `judflgNY` | -2.91 | Slowest judicial REO |
| `judflgNJ` | -2.40 | Same direction as NY |
| `judflgFL` | -1.87 | Same direction as NY/NJ |
| `asofquarter2020Q2` | -1.94 | COVID freeze |
| `mod_fY` | -0.62 | Mods stay in FCLS longer |
| `data_source_fNQM_DSCR` | +0.76 | Faster REO vs base |

**Smooths**

<img src="assets/fcls_model_update/FCLStoREO_smooth.png" style="display:block;width:680px;max-width:100%;height:auto;" />

**FCLStoREO Over Time (grouped by dataset)**

<img src="assets/fcls_model_update/FCLStoREO_overtime.png" style="display:block;width:680px;max-width:100%;height:auto;" />

---

**2. FCLStoP**

In-sample n = 483,513. Deviance explained = 2.5%. This is the weakest of the five. Actuals are noisy around a ~2.5% predicted rate, then step up to ~2.9% after 2022. Payoff falls as CLTV, months since current, and months in status rise. 24-month HPA helps.

| Term | Estimate | Notes |
| --- | ---: | --- |
| `judflgNY` | -0.61 | Judicial loans pay off less from FCLS |
| `judflgJud` | -0.45 | Broader judicial drag |
| `data_source_fCES` | +0.39 | CES pays off more than Jumbo |
| `data_source_fJUMBO` | -0.27 | Lower FCLS payoff |
| `data_source_fNQM_BANKSTAT` | +0.30 | Higher than Jumbo |

**Smooths**

<img src="assets/fcls_model_update/FCLStoP_smooth.png" style="display:block;width:680px;max-width:100%;height:auto;" />

**FCLStoP Over Time (grouped by dataset)**

<img src="assets/fcls_model_update/FCLStoP_overtime.png" style="display:block;width:680px;max-width:100%;height:auto;" />

---

**3. FCLStoL**

In-sample n = 491,427. Deviance explained = 14.1%. The base liquidation rate trends down. The sharp spike months (2021, 2022, 2023, 2025) are STACR servicer bulk-liquidation months, absorbed by the `stacr_sweep` dummy rather than treated as a structural regime. NQM products liquidate much less than the CRT/agency base. Judicial flags again slow the exit.

| Term | Estimate | Notes |
| --- | ---: | --- |
| `stacr_sweep` | +1.82 | Outlier dummy: STACR bulk-liq months |
| `data_source_fNQM_DSCR` | -2.33 | NQM liquidates much less |
| `data_source_fNQM_BANKSTAT` | -2.07 | Same direction |
| `data_source_fJUMBO` | -1.14 | Lower than CRT base |
| `judflgNY` | -1.60 | Judicial delay |
| `servicer_fNEWREZ` | +0.62 | Faster liquidation |

**Smooths**

<img src="assets/fcls_model_update/FCLStoL_smooth.png" style="display:block;width:680px;max-width:100%;height:auto;" />

**FCLStoL Over Time (grouped by dataset)**

<img src="assets/fcls_model_update/FCLStoL_overtime.png" style="display:block;width:680px;max-width:100%;height:auto;" />

---

**4. FCLStoC**

In-sample n = 495,848. Deviance explained = 8.6%. This is the clearest regime change: cures stay low through 2021, then reprice to a 6–7% monthly plateau. Younger loans, low CLTV, and short time in status cure more. Repeat prior 30s also raise FCLStoC.

| Term | Estimate | Notes |
| --- | ---: | --- |
| `data_source_fCES` | +0.71 | Highest product cure |
| `dpd30times_f5` | +0.65 | Repeat DQ cures more |
| `judflgNY` | -0.64 | Judicial slower to cure |
| `data_source_fNQM_FULL` | +0.52 | Full-doc NQM higher |
| `judflgFL` | -0.48 | Same judicial drag |
| `purpose_fR` | -0.31 | Refi cures less than purchase |

**Smooths**

<img src="assets/fcls_model_update/FCLStoC_smooth.png" style="display:block;width:680px;max-width:100%;height:auto;" />

**FCLStoC Over Time (grouped by dataset)**

<img src="assets/fcls_model_update/FCLStoC_overtime.png" style="display:block;width:680px;max-width:100%;height:auto;" />

---

**5. FCLStoB (better: leave FCLS, not current)**

In-sample n = 491,339. Deviance explained = 4.2%. Fit is weaker. `B` is an improvement out of foreclosure that is not a full cure to current. The rate falls from 2017 highs, bottoms in 2020–21, then drifts back toward ~6%. Months in status is the strongest smooth: the longer the loan sits in FCLS, the less likely this partial exit. CES/Jumbo and repeat 30s raise it.

| Term | Estimate | Notes |
| --- | ---: | --- |
| `data_source_fCES` | +0.86 | Highest product better-rate |
| `data_source_fJUMBO` | +0.61 | Next after CES |
| `dpd30times_f5` | +0.56 | Repeat DQ |
| `judflgNY` | -0.52 | Judicial lower FCLStoB |
| `judflgJud` | -0.32 | Same direction |
| `fico_valid_fN` | -0.20 | Invalid FICO lower FCLStoB |

**Smooths**

<img src="assets/fcls_model_update/FCLStoB_smooth.png" style="display:block;width:680px;max-width:100%;height:auto;" />

**FCLStoB Over Time (grouped by dataset)**

<img src="assets/fcls_model_update/FCLStoB_overtime.png" style="display:block;width:680px;max-width:100%;height:auto;" />


"""

# -----------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python emailer/run.py",
        description="Render markdown to an Outlook-ready HTML email.",
    )
    parser.add_argument(
        "--md-file",
        type=Path,
        default=None,
        help="Read markdown body from PATH (relative image paths resolve from its folder).",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Open the rendered HTML in the default browser.",
    )
    parser.add_argument(
        "--no-clipboard",
        action="store_true",
        help="Skip copying HTML to the Windows clipboard (useful for CI / preview only).",
    )
    parser.add_argument(
        "--no-resize",
        action="store_true",
        help="Embed images at their original size (skip auto-resize).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.md_file is not None:
        md_path = args.md_file.expanduser().resolve()
        if not md_path.is_file():
            parser.error(f"--md-file not found: {md_path}")
        content = md_path.read_text(encoding="utf-8")
        base_dir = md_path.parent
        source_desc = str(md_path)
    else:
        content = MD_CONTENT
        base_dir = EMAILER_DIR
        source_desc = "MD_CONTENT (inline)"

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    content = process_clipboard_images(content)
    content = normalize_local_images(content, base_dir=base_dir)

    print(f"Formatting email from {source_desc} ...")
    output_path = OUTPUTS_DIR / "latest_email.html"
    html = render_markdown(
        content,
        output_path=str(output_path),
        base_path=str(EMAILER_DIR),
        resize_images=not args.no_resize,
    )

    if not args.no_clipboard:
        copy_to_clipboard(html)
        print("[OK] Copied rendered email to clipboard")
    else:
        print(f"[OK] Rendered HTML written to {output_path}")

    if args.preview:
        webbrowser.open(output_path.as_uri())
        print(f"[OK] Opened preview in browser: {output_path}")

    print("\n---------------------------------------------------------")
    if not args.no_clipboard:
        print("Done! The HTML is in your clipboard.")
        print("1. Go to Outlook/Gmail")
        print("2. Paste (Ctrl+V)")
    else:
        print(f"Output file: {output_path}")
    print("---------------------------------------------------------")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
