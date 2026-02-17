# Excel Formatter

Template-driven Excel formatting tool for producing management-quality reports.

A JSON template defines formatting rules (number formats, header styling, conditional formatting, column renames, auto-widths). The AI agent scans any Excel file, proposes a template, and applies it. Saved templates can be re-applied standalone via CLI.

---

## AI Agent Instructions

**Read this section first before formatting any Excel file.**

### Workflow

1. **Scan** the file to understand its structure:
   ```bash
   python formatter/format_excel.py <file.xlsx> --scan --header-row <N>
   ```
   This outputs a JSON report with per-column type detection, value statistics, and a `draft_template` you can use as a starting point.

2. **Review the scan output.** Pay attention to:
   - `detected_type` for each column (date, text, float, integer, percentage, likely_percentage)
   - `stats.median_abs` to judge appropriate decimal places
   - `suggested_format` as a starting point
   - Columns flagged as `likely_percentage` need user confirmation before using `0.00%`
   - Sheets with different header structures (different `header_row`) need separate templates

3. **Create or select a template.** Either:
   - Use an existing template from `formatter/templates/`
   - Modify the `draft_template` from the scan output
   - Build a new template from scratch (see Template Reference below)

4. **Apply the template:**
   ```bash
   # To a new output file
   python formatter/format_excel.py <file.xlsx> -t <template.json> -o <output.xlsx>

   # In-place (creates .bak backup automatically)
   python formatter/format_excel.py <file.xlsx> -t <template.json> --inplace
   ```

5. **Verify** the output by opening it or spot-checking with openpyxl.

### Critical Rules for AI Agents

- **Default to first sheet only.** Unless the user explicitly asks for other sheets, format only the first sheet. Do not scan or process other sheets. The output file should contain only the formatted sheet — do not carry over unformatted sheets.
- **All template keys reference ORIGINAL header names** in the input file. Never use renamed names as keys.
- **Duplicate headers** (e.g., "Yield" appearing 3 times for New/Prod/Diff sections): `column_formats` and `column_rename` apply to ALL matching columns. Use `col_indices` in `conditional_format` if you need to target a specific one.
- **header_row** is 1-based Excel row numbering. It must point to the row with actual column names, NOT merged super-headers above it. Financial reports commonly use row 3 (rows 1-2 are super-headers like "New", "Prod", "Diff").
- **Sheets with different structures** (different header rows, different columns) need separate template files. Run the tool twice rather than trying to force one template on all sheets.
- **Never auto-apply percentage formatting.** If the scan flags `likely_percentage`, ask the user to confirm. Small decimals (yields, durations, default rates) are easily misclassified.
- **`--inplace` always creates a `.bak` backup** before overwriting. The write is atomic (temp file then replace).

### Deciding on Formats

Use these guidelines for financial data:

| Column Type | Typical Values | Recommended Format |
|---|---|---|
| Coupon / Yield | 2.55, 7.03, -13.76 | `0.00` |
| Mark (bond price) | 77.08, 104.77, 123.28 | `0.00` |
| Z-spread (bps) | 196, -500, 1652 | `#,##0` |
| WAL (years) | 1.6, 2.5, 3.9 | `0.0` |
| Eff Duration | -33.9, 0.05, 10.4 | `0.0` |
| Spread Duration | 0.12, 1.44, 8.56 | `0.00` |
| Key Rate Duration | -58.0, 27.3, -17.9 | `0.0` |
| Default Rate (fraction) | 0.24, 1.43, 4.79 | `0.000` |
| Cum Loss (fraction) | 0.013, 0.10, 3.14 | `0.000` |
| Severity (%) | 3.6, 10.0, 67.6 | `0.0` |
| Writedown | 0, -49.4 | `0.00` |
| Date | 2026-02-11 | `mm/dd/yyyy` |
| Percentage | 0.05 (= 5%) | `0.00%` |

When in doubt, use the **magnitude_format fallback** rule:
- |median| >= 100 --> `#,##0` (integer)
- |median| >= 10  --> `#,##0.0` (1 decimal)
- |median| < 10   --> `0.00` (2 decimals)

---

## CLI Reference

```
python formatter/format_excel.py <input> [options]

positional arguments:
  input                 Path to the Excel file

options:
  --scan                Scan file and print JSON report to stdout
  --header-row N        1-based header row number (default: 1)
  -t, --template FILE   JSON template file to apply
  -o, --output FILE     Output file path
  --inplace             Overwrite input file (creates .bak backup first)
```

### Examples

```bash
# Scan with header on row 3
python formatter/format_excel.py data.xlsx --scan --header-row 3

# Apply template to new file
python formatter/format_excel.py data.xlsx -t templates/risk_diff.json -o data_formatted.xlsx

# Apply in-place (safe: creates data.xlsx.bak)
python formatter/format_excel.py data.xlsx -t templates/risk_diff.json --inplace

# Scan and pipe draft template to a file
python formatter/format_excel.py data.xlsx --scan --header-row 3 > scan_output.json
```

---

## Template Reference

A template is a JSON file. **Every section is optional** -- use only what you need.

### Minimal Template (just number formatting)

```json
{
    "name": "my_template",
    "header_row": 1,
    "column_formats": {
        "Price": "0.00",
        "Volume": "#,##0"
    }
}
```

### Full Template (all features)

```json
{
    "name": "risk_diff",
    "sheets": ["Base"],
    "exclude_sheets": [],
    "header_row": 3,
    "super_header_style": {
        "font_bold": true,
        "font_color": "#FFFFFF",
        "font_size": 11,
        "fill_color": "#0F1D36",
        "alignment": "center",
        "border_style": "thin",
        "border_color": "#0F1D36"
    },
    "header_style": {
        "font_bold": true,
        "font_color": "#FFFFFF",
        "font_size": 10,
        "fill_color": "#1B2A4A",
        "alignment": "center",
        "border_style": "medium",
        "border_color": "#1B2A4A",
        "freeze": true,
        "auto_filter": false
    },
    "section_dividers": [8, 17, 26],
    "section_divider_color": "#1B2A4A",
    "section_colors": ["#2C3E50", "#1B4332", "#1B2A4A", "#6B2C3E"],
    "borders": { "color": "#D9D9D9", "style": "thin" },
    "outer_border": { "color": "#1B2A4A", "style": "medium" },
    "group_by_column": {
        "column": "Asset Subtype",
        "colors": ["#E8EDF2", "#E7F0E5", "#FDF2E9", "#F0E6EF",
                   "#E5ECF0", "#F5EADF", "#E6EDE8", "#F2E8E8"]
    },
    "column_rename": {
        "Sprd Dur": "Spread Duration",
        "Rem Def": "Remaining Default",
        "Cum loss": "Cumulative Loss"
    },
    "column_formats": {
        "Yield": "0.00",
        "Zspread": "#,##0",
        "WAL": "0.0",
        "Eff Dur": "0.0",
        "Date": "mm/dd/yyyy"
    },
    "magnitude_format": {
        "enabled": true,
        "priority": "fallback",
        "rules": [
            {"min_abs": 100, "format": "#,##0"},
            {"min_abs": 10,  "format": "#,##0.0"},
            {"min_abs": 0,   "format": "0.00"}
        ]
    },
    "conditional_format": [
        {
            "col_indices": [26, 27, 28, 29, 30, 31, 32, 33, 34],
            "type": "3_color_scale",
            "min_color": "#F8696B",
            "mid_color": "#FCFCFF",
            "max_color": "#63BE7B"
        }
    ],
    "col_width": "auto"
}
```

### Field Reference

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | string | -- | Template name (for identification only) |
| `sheets` | list | `["*"]` | Which sheets to process. `["*"]` = all sheets. Or list specific names. |
| `exclude_sheets` | list | `[]` | Sheet names to skip (removed from `sheets` selection). |
| `header_row` | int | `1` | 1-based row containing column headers. Must be the row with actual column names, not merged super-headers. |
| **Header Styling** | | | |
| `super_header_style` | object | -- | Style for rows above `header_row` (e.g., section labels like "Base", "New", "Prod"). Same sub-fields as `header_style`. |
| `header_style` | object | -- | Main header row visual styling. See sub-fields below. |
| `header_style.font_bold` | bool | -- | Bold header text. |
| `header_style.font_color` | string | -- | Header font color (hex, e.g., `"#FFFFFF"`). |
| `header_style.font_size` | int | -- | Font size in points. |
| `header_style.fill_color` | string | -- | Header background color (hex, e.g., `"#1B2A4A"`). |
| `header_style.alignment` | string | -- | Horizontal alignment: `"center"`, `"left"`, `"right"`. Vertically centered automatically. |
| `header_style.border_style` | string | `"thin"` | Header border weight: `"thin"`, `"medium"`, `"thick"`. |
| `header_style.border_color` | string | `"#000000"` | Header border color. |
| `header_style.freeze` | bool | -- | Freeze panes below the header row. |
| `header_style.auto_filter` | bool | -- | Add auto-filter dropdowns to the header row. |
| **Section Styling** | | | |
| `section_dividers` | list | -- | 1-based column indices where sections start (e.g., `[8, 17, 26]`). Draws a medium left border at each. |
| `section_divider_color` | string | `"#4472C4"` | Color for section divider borders. |
| `section_colors` | list | -- | Fill colors for each section header (super-header + header rows). One color per section: `[before 1st divider, 1st section, 2nd, ...]`. |
| **Data Styling** | | | |
| `borders` | object | -- | Thin borders on all data cells. `{"color": "#D9D9D9", "style": "thin"}` |
| `outer_border` | object | -- | Medium border around entire table. `{"color": "#1B2A4A", "style": "medium"}` |
| `group_by_column` | object | -- | Color rows by group. Cycles through palette automatically for unlimited groups. |
| `group_by_column.column` | string | -- | Column header name to group by (e.g., `"Asset Subtype"`). |
| `group_by_column.colors` | list | 8 pastels | List of hex colors. Groups cycle through this palette. |
| `banded_rows` | object | -- | Fallback if no `group_by_column`. Simple alternating row color. `{"color": "#F2F2F2"}` |
| **Formatting** | | | |
| `column_rename` | object | -- | Map of `"original_name": "new_name"`. Applied last (visual only). |
| `column_formats` | object | -- | Map of `"column_name": "excel_format"`. Highest priority. Keys = original header names. |
| `magnitude_format` | object | -- | Automatic formatting based on column value magnitudes. |
| `magnitude_format.enabled` | bool | `false` | Enable magnitude-based fallback formatting. |
| `magnitude_format.priority` | string | `"fallback"` | Always `"fallback"` -- only applies to columns NOT in `column_formats`. |
| `magnitude_format.rules` | list | -- | List of `{"min_abs": N, "format": "..."}`. Checked top-to-bottom against column median absolute value; first match wins. |
| `conditional_format` | list | -- | List of conditional formatting rules. |
| `conditional_format[].columns` | list | -- | Column names to apply to (all matches). |
| `conditional_format[].col_indices` | list | -- | 1-based column indices (takes precedence over `columns` if both provided). |
| `conditional_format[].type` | string | `"3_color_scale"` | Currently supports `"3_color_scale"`. |
| `conditional_format[].min_color` | string | `"#F8696B"` | Color for minimum values (red). |
| `conditional_format[].mid_color` | string | `"#FFFFFF"` | Color for midpoint values (white). |
| `conditional_format[].max_color` | string | `"#63BE7B"` | Color for maximum values (green). |
| `col_width` | string | -- | Set to `"auto"` to auto-size columns based on content. |
| **Cleanup** | | | |
| `hide_zero_columns` | bool | `false` | Hide columns where every data value is exactly 0 (or empty). Data is preserved, column is just hidden in Excel. Runs before all other formatting. |

---

## How It Works

### Order of Operations

When applying a template, the engine processes each target sheet in this order:

1. **Detect data bounds** -- find first/last column with a header (blank columns like A are excluded from all styling)
2. **Hide zero columns** -- hide columns where all data values are exactly 0
3. **Apply number formats** -- `column_formats` first (explicit), then `magnitude_format` as fallback
4. **Apply header + super-header style** -- font, fill, alignment, freeze panes; per-section colors if configured
5. **Apply data style** -- borders, group-by-column row coloring (or banded rows), number right-alignment
6. **Apply section dividers** -- thick left borders at section boundaries
7. **Apply outer border** -- medium border around entire table
8. **Apply conditional formatting** -- color scales on targeted columns
9. **Apply column renames** -- visual rename of headers (uses original column map)
10. **Auto column widths** -- sizes columns based on content (runs after renames)

### Magnitude Format

Instead of formatting cell-by-cell (which creates visual inconsistency), the engine uses column-level heuristics:

1. For each numeric column not covered by `column_formats`, sample all values
2. Compute the **median absolute value** (excluding zeros) of the column
3. Match against `magnitude_format.rules` (top-to-bottom, first match wins)
4. Apply that format to the **entire column**

This ensures a column with values like 348, -500, 182 gets `#,##0` (integer) uniformly, while a column with 1.6, 2.5, 2.3 gets `0.00` uniformly.

### Dual Workbook Loading

The engine loads the workbook twice:
- **data_only=True**: For reading computed values (formulas resolved to numbers) -- used for magnitude calculation and column width estimation.
- **data_only=False**: For editing -- preserves formulas, applies formatting, saves.

This means magnitude formatting works correctly even when columns contain Excel formulas.

---

## Saved Templates

| Template | Use For |
|---|---|
| `templates/risk_diff.json` | All sheets in a risk diff file (formats all metrics, conditional formatting on all metric columns). Simple, no section styling. |
| `templates/risk_diff_base.json` | **Base sheet only** -- the go-to template for risk diff comparisons. Includes section colors (Base/New/Prod/Diff), section dividers, group-by-Asset-Subtype row coloring, conditional formatting on Diff section only, outer border, and hide-zero-columns. |

---

## Risk Diff Comparison -- Recurring Workflow

**This is the most common use case.** Risk diff files compare "New" model results vs "Prod" (production) results, with a "Diff" section showing the delta. The user needs this formatted regularly for management distribution.

### Standard Risk Diff Layout

```
Row 2 (super-headers):  Base | New | Prod | Diff (New - Prod)
Row 3 (column headers):
  Cols B-G:    Date, Asset Subtype, Description, Cusip, Coupon, Mark
  Cols H-P:    New section   (Yield, Zspread, WAL, Eff Dur, Sprd Dur, Rem Def, Cum loss, Sev, Writedown)
  Cols Q-Y:    Prod section  (same 9 metrics)
  Cols Z-AH:   Diff section  (same 9 metrics -- these are the differences)
```

The column indices for the Diff section vary per file (depending on how many base columns there are and whether extra metrics like KRD are included). **Always scan first to confirm.**

### AI Agent Step-by-Step for Risk Diff Files

1. **Scan the file with `--header-row 3`** (risk diff files always use row 3):
   ```bash
   python formatter/format_excel.py <file.xlsx> --scan --header-row 3
   ```

2. **Identify the Diff section columns.** Look at the scan output for the target sheet. Find where the second set of duplicate column names starts (the Diff section). In the scan output, look at the super-header row:
   ```python
   # Quick way to find Diff columns:
   import openpyxl
   wb = openpyxl.load_workbook("<file.xlsx>", data_only=True)
   ws = wb["Base"]
   for cell in ws[2]:  # Row 2 = super-headers
       if cell.value and "Diff" in str(cell.value):
           print(f"Diff section starts at column {cell.column}")
           break
   ```

3. **Find ALL section boundaries** from the super-header row (row 2). Record where Base, New, Prod, Diff each start:
   ```python
   for cell in ws[2]:
       if cell.value:
           print(f"{cell.value} starts at column {cell.column}")
   ```

4. **Start from `templates/risk_diff_base.json`** and adjust:
   - `"sheets"`: target sheet name(s)
   - `"section_dividers"`: column indices where New, Prod, Diff start
   - `"col_indices"` in `conditional_format`: Diff section columns only
   - `"column_formats"`: add any extra metrics not in the template (e.g., KRD, FwdYield)
   - `"section_colors"` stays the same (4 colors for 4 sections)
   - `"group_by_column.column"`: verify the grouping column name matches

5. **Apply:**
   ```bash
   python formatter/format_excel.py <file.xlsx> -t formatter/templates/risk_diff_base.json -o <output.xlsx>
   ```

6. **For files with multiple scenario sheets** (e.g., Base, RateUp 200, SuperBear), either:
   - Run the tool once per sheet with different templates (adjusting `sheets` and `col_indices`)
   - Or use `templates/risk_diff.json` which applies to all sheets (but puts conditional formatting on ALL metric columns, not just Diff)

### Example: Formatting a New Risk Diff File

```bash
# 1. Scan
python formatter/format_excel.py new_risk_diff.xlsx --scan --header-row 3

# 2. AI reviews scan, finds Diff starts at column 26
#    Copies risk_diff_base.json, adjusts col_indices if needed

# 3. Apply
python formatter/format_excel.py new_risk_diff.xlsx -t formatter/templates/risk_diff_base.json -o new_risk_diff_formatted.xlsx
```

---

## Limitations

- **One template = one header structure.** If sheets have headers on different rows, use separate templates or `exclude_sheets`.
- **Duplicate header renames** apply to ALL matches. If "Yield" appears 3 times and you rename it, all 3 get renamed.
- **Conditional formatting stacks.** Running the tool multiple times adds duplicate rules. Use `-o` to write to a new file to avoid this.
- **Percentage detection is conservative.** The scan only flags percentages if the Excel format string contains `%` or if values are all in [-1, 1] AND the header contains a keyword like "Rate" or "Pct". This avoids misclassifying yields and durations.
- **openpyxl warnings** about "Unknown extension" and "Conditional Formatting extension" are normal for files with Excel-specific features. They don't affect functionality.

## Dependencies

- `openpyxl` (Python Excel library)
- Python standard library only (`statistics`, `shutil`, `tempfile`, `json`, `argparse`)
