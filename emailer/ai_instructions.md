# AI Email Content Generation Instructions

You are writing `MD_CONTENT` for an email body to be rendered by Howard Toolbox.

## General Rules
1. **Output ONLY Markdown / HTML**. No explanations, no subject lines, no "Here is the code".
2. **Do NOT add sign-offs** (e.g. "Best, Howard Zeng, QR"). Outlook inserts the
   signature automatically on send. Greetings (e.g. "Hi Glenn,") are fine.
3. **Professional Tone**. Concise, bulleted, clear.

## High-Scrutiny Recipient Style

For sensitive management emails or recipients who may challenge wording:

- Lead with the conclusion, then the evidence, then the proposed next step.
- Avoid clinical labels, personal judgments, or speculation about motives.
- Avoid emotional over-explanation ("my read", "I feel", "I am less confident").
  Let the data and criteria carry the point.
- Use crisp decision criteria when proposing next steps, so expectations cannot
  drift later.
- Keep communication auditable: include output folders, dates, sample sizes,
  and explicit thresholds where relevant.
- Frame requests as specific alignment points, not open-ended permission asks.
  Example: "Happy to align on the decision criteria before I kick off."
- If a risk exists, state the fallback path in advance. Example:
  "If criteria are not met: revert to prod, document, and reassess."

## Formatting Guide

### Math
- **Inline**: Use `$ ... $`. Example: `The error is $\epsilon < 0.01$.`
- **Display**: Use `$$ ... $$`. Example:
  ```latex
  $$
  f(x) = \sum_{i=1}^n x_i
  $$
  ```
- Math will be rendered as high-quality images using CodeCogs

### Images
- Images can be referenced from anywhere in the `emailer/` folder -- the tool automatically copies them into `assets/` and rewrites the path.
- Both Markdown `![](...)` and HTML `<img src="...">` are normalized.
- Use `{{CLIPBOARD}}` to insert the current clipboard image (single image).
- **Inline Images**: Images are inline by default:
  ```markdown
  ![](assets/img1.png) ![](assets/img2.png)
  ```
- **Sizing**: Use HTML for explicit sizing:
  ```html
  <img src="chart.png" style="display:block;width:620px;max-width:100%;height:auto;" />
  ```
- **Adjacent plot groups**: When showing multiple related plots for one deal/scenario,
  use inline HTML with explicit widths so Outlook does not stack them vertically:
  ```html
  <img src="plot1.png" width="210" style="width:210px;height:auto;vertical-align:top;margin:4px 6px 4px 0;" /> <img src="plot2.png" width="210" style="width:210px;height:auto;vertical-align:top;margin:4px 6px 4px 0;" /> <img src="plot3.png" width="210" style="width:210px;height:auto;vertical-align:top;margin:4px 0 4px 0;" />
  ```
  For four plots in one row, use `width="155"` / `width:155px`.

### Outlook Line Breaks (Important)
The renderer automatically inserts blank lines around standalone image lines to prevent Outlook from merging text and images onto the same line. However, for maximum safety:
- **Always put a blank line between a text label and the image below it.**
- When in doubt, use explicit HTML blocks:
  ```
  **Label**

  <img src="screenshot.png" style="display:block;width:620px;max-width:100%;height:auto;" />
  ```

### Layout
- **Tables**: Use standard Markdown tables for data.
- **Code Blocks**: Use fenced code blocks with language tags.
- **Inline Code**: Use backticks for tech terms: `variable_name`.
- **Horizontal Rules**: Use `---` to separate sections visually.
- **Links**: Standard markdown `[text](url)` links are styled professionally.

### Model / Vector Result Emails
- Lead with the conclusion and recommendation first, e.g. `**Recommendation: release the new model.**`
- Highlight the important comparison in bold: model winner, scenario sensitivity, and deal-level exceptions.
- Add a color legend before plots when model colors matter. Use inline HTML spans:
  ```html
  **Legend:** <span style="color:#f28c28;font-weight:700;">Orange = New</span>; <span style="color:#1f77b4;font-weight:700;">Blue = Prod</span>; <span style="color:#808080;font-weight:700;">Grey = JPM</span>.
  ```
- Use small Markdown tables for observed CPR / tracking ratios instead of prose lists.
- Group each deal as: bold deal heading -> one-sentence takeaway -> CPR/tracking table -> adjacent plots.
- Keep plot labels and scenario notes short so readers can scan the email quickly.

## CLI Flags

`emailer/run.py` supports these flags:

- `--md-file PATH` -- render content from an external markdown file instead of
  editing `MD_CONTENT`. Relative image paths in the file resolve from its own
  parent directory (images are copied into `emailer/assets/`).
- `--preview` -- open the rendered HTML in your default browser.
- `--no-clipboard` -- skip the clipboard copy; useful for CI / preview only.
- `--no-resize` -- embed images at original size.

## Image Auto-Resize

Local images exceeding 1600px on the long edge, or 2MB in size, are
automatically downscaled in memory before base64 embedding. Source files on
disk and the copies in `emailer/assets/` are never modified. Use
`--no-resize` (or `render_markdown(..., resize_images=False)`) to preserve
original bytes.

## Example Output

**Weekly Model Update**

The volatility model has converged.

- Signal: **Buy**
- Confidence: 95%

**Performance Charts**

<img src="assets/chart1.png" style="display:block;width:620px;max-width:100%;height:auto;" />

<img src="assets/chart2.png" style="display:block;width:620px;max-width:100%;height:auto;" />

**Formula**

$$
\sigma_{t}^2 = \alpha \epsilon_{t-1}^2 + \beta \sigma_{t-1}^2
$$

---

## NQM Vector Email Runbook

Use this workflow to regenerate NQM CPR or CDR comparison plots and embed them
in an Outlook-ready email.

### Inputs and Outputs

- Workbook: `S:\QR\hzeng\vector_compare_nqm_v7.xlsx`
- Worksheet: `vector_compare_0925`
- Plotter: `emailer/plot_vector_compare.py`
- Plot folder: `emailer/assets/nqm_vector_compare/`
- Email body: `MD_CONTENT` in `emailer/run.py`
- Rendered email: `emailer/outputs/latest_email.html`

Run all commands from the repository root:

```powershell
Set-Location S:\QR\hzeng\howard-toolbox
```

### Curves Included

The plotter intentionally includes only these four workbook model series:

- Blue — `Prod`, labeled **Prod**
- Orange — `New NonQM`, labeled **New NQM**
- Grey — `JPM`, labeled **JPM**
- Yellow — `New NonQM V9 No Decay Dialed`, labeled **Dialed NQM**

Do not add `New NonQM No Decay` or `New NonQM No Decay Dial` unless the email
specifically requires those extra comparisons.

### Standard Deal Mapping

- `B3A` — VERUS 2022-1
- `ENU` — VISIO 2023-1
- `ESU` — CHNGE 2023-4
- `B4O` — COLT 2022-3
- `ES8` — ADMT 2023-NQM3
- `Q4Y` — BRAVO 2021-NQM1
- `F7E` — LMAT 2024-INV1
- `HXF` — OBX 2026-NQM1
- `GZC` — JPMMT 2025-NQM4
- `GWI` — CROSS 2025-H7
- `G8U` — ADMT 2025-NQM1
- `HZK` — GSMBS 2025-R1
- `F6R` — NRZT 2024-NQM2
- `GI0` — GCAT 2025-NQM3
- `HWB` — BARC 2026-NQM1
- `HW3` — NYMT 2026-INV1

### Generate Base and SuperBear CDR Plots

```powershell
python emailer/plot_vector_compare.py `
  --workbook "S:\QR\hzeng\vector_compare_nqm_v7.xlsx" `
  --sheet vector_compare_0925 `
  --metric CDR `
  --scenarios Base SuperBear `
  --deals `
  "VERUS 2022-1" `
  "VISIO 2023-1" `
  "CHNGE 2023-4" `
  "COLT 2022-3" `
  "ADMT 2023-NQM3" `
  "BRAVO 2021-NQM1" `
  "LMAT 2024-INV1" `
  "OBX 2026-NQM1" `
  "JPMMT 2025-NQM4" `
  "CROSS 2025-H7" `
  "ADMT 2025-NQM1" `
  "GSMBS 2025-R1" `
  "NRZT 2024-NQM2" `
  "GCAT 2025-NQM3" `
  "BARC 2026-NQM1" `
  "NYMT 2026-INV1"
```

Expected result:

```text
Wrote 32 plots to ...\emailer\assets\nqm_vector_compare
```

The filenames include the metric and scenario, for example:

- `verus_2022_1_cdr_base.png`
- `verus_2022_1_cdr_superbear.png`

To generate CPR instead, change `--metric CDR` to `--metric CPR`. Metric-specific
filenames prevent CPR and CDR runs from overwriting each other.

### Add the Plots to the Email

Use one section per deal, with Base first and SuperBear second. Keep both images
on one line at 310px so Outlook displays them side by side:

```html
**B3A — VERUS 2022-1**

<img src="assets/nqm_vector_compare/verus_2022_1_cdr_base.png" width="310" style="width:310px;height:auto;vertical-align:top;margin:4px 6px 4px 0;" /> <img src="assets/nqm_vector_compare/verus_2022_1_cdr_superbear.png" width="310" style="width:310px;height:auto;vertical-align:top;margin:4px 0 4px 0;" />
```

Add this four-curve legend before the deal sections:

```html
**Legend:** <span style="color:#1f77b4;font-weight:700;">Blue = Prod</span>; <span style="color:#f28c28;font-weight:700;">Orange = New NQM</span>; <span style="color:#808080;font-weight:700;">Grey = JPM</span>; <span style="color:#d4a017;font-weight:700;">Yellow = Dialed NQM</span>.
```

Follow the pool-ID order in the mapping above. Plot titles already identify Base
and SuperBear, so separate scenario labels are unnecessary.

### Validate and Render

If the plotter code changed, run:

```powershell
python -m ruff check emailer/plot_vector_compare.py emailer/run.py tests/test_plot_vector_compare.py
python -m pytest
```

Render without changing the clipboard:

```powershell
python emailer/run.py --no-clipboard
```

Inspect `emailer/outputs/latest_email.html`. Confirm:

- The plotter reported 32 files and no missing deal/scenario combinations.
- Every deal has one Base plot and one SuperBear plot.
- Each plot contains exactly Prod, New NQM, JPM, and Dialed NQM.
- The y-axis shows the requested metric.
- No missing-image warnings appear during rendering.

When ready to paste into Outlook, run:

```powershell
python emailer/run.py
```

Run the final render **after** pytest. Emailer tests write to
`emailer/outputs/latest_email.html` and can overwrite the finished email.

### Troubleshooting

- **Missing deal/scenario:** Match `BBG Deal` and `Scenario` values exactly;
  `SuperBear` is case-sensitive.
- **Wrong metric:** Check `--metric CPR` versus `--metric CDR` and confirm the
  y-axis label before sending.
- **Wrong curves:** Check the exact workbook `Model` values listed above.
- **Images do not embed:** Use paths beginning with
  `assets/nqm_vector_compare/` and run the emailer from the repository root.
- **Plots stop too early or run too long:** The default is 120 projection
  months; override it with `--max-month`.
- **Git status does not show generated plots:** PNG files are intentionally
  ignored and remain local.
