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
