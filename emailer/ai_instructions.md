# AI Email Content Generation Instructions

You are writing `MD_CONTENT` for an email body to be rendered by Howard Toolbox.

## General Rules
1. **Output ONLY Markdown / HTML**. No explanations, no subject lines, no "Here is the code".
2. **Include greetings and sign-offs in the content** if desired -- the tool does NOT add them automatically.
3. **Professional Tone**. Concise, bulleted, clear.

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
