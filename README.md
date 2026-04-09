# Howard's Toolbox

A collection of productivity tools and workflows for quantitative research.

## Structure

```
howard-toolbox/
├── emailer/                  # Email content generator with Markdown support
│   ├── run.py                # Main entry point (edit MD_CONTENT here)
│   ├── render.py             # MD -> HTML rendering, base64 images, clipboard
│   ├── generate_diagram.py   # Matplotlib simulation flowchart generator
│   ├── ai_instructions.md    # AI prompt guide for email formatting
│   ├── assets/               # Image assets (auto-managed)
│   └── outputs/              # Generated HTML files
│
├── tests/                    # Smoke tests
│   └── test_smoke.py         # Import tests for all modules
│
├── dial/                     # Dial calibration & model JSON updates
│   ├── update_dials.py       # CLI: generate specs and apply dial overrides
│   ├── dial_utils.py         # Tracking file parsing & summary extraction
│   ├── run.py                # Batch dial-ratio analysis across deal types
│   ├── dial.ipynb            # Notebook: dial command generator & analysis
│   ├── *_all_dials_spec.json # Spec files per product (STACR, HE, NONQM, MI)
│   └── outputs/              # Excel outputs (dial ratio by deal)
│
├── formatter/                # Template-driven Excel formatting tool
│   ├── format_excel.py       # Engine + CLI (scan, apply, auto-format)
│   ├── templates/            # Saved JSON format specs
│   │   └── risk_diff.json    # Risk diff report template
│   └── README.md             # Detailed usage guide (AI agents: read this first)
│
├── quant_workflows/          # Quantitative workflows and commands
│   ├── quant_workflows_notebook.ipynb  # 18 organized sections
│   └── README.md             # Comprehensive workflow documentation
│
├── usage/                    # Cursor API usage analysis
│   └── analyze.py            # CLI: CSV -> interactive HTML dashboard
│
├── .gitignore
├── AGENTS.md                 # Continual-learning memory (auto-mined from chats)
├── pyproject.toml            # ruff linter config
├── README.md                 # This file
└── requirements.txt          # Python dependencies
```

---

## Tools

### 1. Email Content Generator (`emailer/`)

Converts Markdown to HTML for rich email composition.

**Quick start:**

```bash
python emailer/run.py
```

**Features:**

- Markdown to HTML with tables and styling
- LaTeX math support via CodeCogs
- Image embedding (local files -> base64)
- Clipboard integration (Windows-only; `pywin32` + `Pillow`)
- Special tag: `{{CLIPBOARD}}` for dynamic images
- Markdown image links are auto-normalized into `assets/` when possible
- Missing local images warn and keep original `src` (not embedded); set `STRICT_IMAGES = True` to error
- AI prompt guide (`ai_instructions.md`) for consistent formatting

### 2. Dial Updates (`dial/`)

Calibrate model dials from tracking data and apply overrides to produce new model JSON files.

**Three workflows:**

1. **Generate a dial spec** from an existing model JSON (extracts all transitions with shocks):
  ```bash
   python dial/update_dials.py --generate-spec "dial/stacr_v1.8.0_all_dials_spec.json" --generate-only-dials --generate-group-by-model --input "path/to/model.json"
  ```
2. **Edit the spec** (one dial can target many transitions):
  ```json
   {
     "model_detail": "data/STACR/ModelFiles/crt_1_8_0/gam_begg_stacr_M9PtoC_2025_10_02.txt",
     "targets": ["M90->M90toC", "M120->M120toC", "M150->M150toC"],
     "cohort": "CAS",
     "start_date": "20240701",
     "dial": 0.98
   }
  ```
3. **Apply the spec** to generate a new JSON:
  ```bash
   python dial/update_dials.py --spec "dial/stacr_v1.8.0_all_dials_spec.json" --output "path/to/output.json" --version "V1.8.1"
  ```

**Dial ratio analysis** (compares dialed vs undialed tracking, computes implied dials):

```bash
python dial/run.py
```

Reads latest tracking files from network, outputs a multi-sheet Excel (`dial/outputs/`).

**Notebook** (`dial/dial.ipynb`):

- Run the first cell to generate `--generate-spec` and `--spec` commands
- Lower cells contain dial ratio analysis and visualization

**CLI flags:**

- `--generate-only-dials` excludes transitions with no `Shock` (no dial)
- `--generate-group-by-model` groups transitions that share the same model file
- `--generate-verbose-targets` uses expanded target objects instead of shorthand
- Overrides apply by default; use `"disabled": true` to skip a line
- Dial values of `1.0` are treated as "no dial" and remove the shock
- `convert_cohort` defaults to true; set `"convert_cohort": false` on a line to prevent conversion
- If the original model uses a flat-only dial (e.g., `"0.719x for 400"`), updates keep that flat-only format

### 3. Excel Formatter (`formatter/`)

Template-driven Excel formatting for management-quality reports. Scan any Excel file to auto-detect column types and generate a draft format template, then apply it for consistent output.

**AI agents: read `[formatter/README.md](formatter/README.md)` before using this tool.**

**Quick start:**

```bash
# Scan a file (understand its structure)
python formatter/format_excel.py data.xlsx --scan --header-row 3

# Apply a saved template
python formatter/format_excel.py data.xlsx -t formatter/templates/risk_diff.json -o data_formatted.xlsx
```

**Features:**

- JSON templates define all formatting rules (number formats, headers, colors, conditional formatting, column renames)
- `--scan` auto-detects column types (date, text, float, integer, percentage) and suggests formats
- Magnitude-based fallback: triple-digit numbers get 0 decimals, single-digit get 2, etc.
- Header styling with freeze panes and auto-filter
- 3-color-scale conditional formatting
- Column rename (visual only, last step)
- Auto column widths
- `--inplace` with atomic write and `.bak` backup
- Preserves Excel formulas (dual workbook loading)

### 4. Usage Analyzer (`usage/`)

Generates a self-contained interactive HTML report from a Cursor usage-events CSV export.

**Quick start:**

```bash
python usage/analyze.py ~/Downloads/usage-events-2026-04-09.csv --since 2026-01-01
```

**Features:**

- 11 interactive Plotly charts: daily volume by model family, 7-day rolling trend, stacked token breakdown (cache/input/output), model distribution donuts, activity heatmap (ET), cache efficiency, max mode adoption, billing kind, log-scale request size distribution, monthly summary
- KPI dashboard with total requests, tokens, cache hit rate, trend
- Auto-generated insight boxes (top model, peak activity, 30-day trend)
- Monthly and per-model summary tables
- `--name` flag personalizes the report title (default: Howard)
- `--since` filters old data; `--out` sets output path

**CLI flags:**

- `--since YYYY-MM-DD` -- only include events on or after this date
- `--name Name` -- personalize the report title (default: Howard)
- `--out path.html` -- output path (default: `<csv_dir>/<name>_cursor_usage.html`)

### 5. Quantitative Workflows (`quant_workflows/`)

Comprehensive notebook with 18 sequentially organized sections:

**Flat File Generation (4-6):** CRT/LP updates, HELOC data, monthly refresh
**Vector Generation (7-9):** Tracking vectors, ad-hoc LMSim, position-only runs
**Risk (10):** Portfolio risk analysis and vectors
**Other (11-18):** Debug, utilities, deal lists, database ops, IntexLoader

**Features:**

- Auto-calculates `AS_OF_DATE` to most recent business day
- Secure credential handling (environment variables)
- Generator functions for reusable commands
- Clear visual section markers

**Quick start:**

```bash
jupyter notebook quant_workflows/quant_workflows_notebook.ipynb
```

**See `[quant_workflows/README.md](quant_workflows/README.md)` for full documentation.**

---

## For AI Agents / Developers

### Emailer Architecture

- **Entry Point**: `emailer/run.py` is the main script. User edits `MD_CONTENT` string here.
- **Rendering Logic**: `emailer/render.py` handles:
  - Markdown -> HTML (using `markdown` lib)
  - Post-processing with `BeautifulSoup` (tables, styling, unwrap images)
  - LaTeX Math -> CodeCogs images (`$$...$$` -> `<img src="...">`)
  - Local Images -> Base64 encoded strings when the file exists
- **Clipboard**: The script uses `win32clipboard` to put the final HTML into the Windows clipboard.
- **Special Tags**:
  - `{{CLIPBOARD}}`: Replaced at runtime with the image currently in the OS clipboard.
- **AI Instructions**: `emailer/ai_instructions.md` defines the prompt style for AI-generated email content.

### Dial Architecture

- **CLI Entry Point**: `dial/update_dials.py` -- generates specs and applies overrides.
  - `--generate-spec` mode: reads a model JSON, enumerates all transitions with shocks, writes a spec file.
  - Default mode: reads a spec, loads model JSON, applies overrides, bumps version, writes output.
- **Utility Functions**: `dial/dial_utils.py` -- tracking workbook parsing, summary extraction, error window selection.
- **Batch Analysis**: `dial/run.py` -- loops over deal types, reads dialed/undialed tracking files, computes implied dials, outputs formatted Excel.
- **Notebook**: `dial/dial.ipynb` -- interactive command generator and analysis cells.
- **Spec Files**: `*_all_dials_spec.json` -- product-specific dial configurations (STACR, HE, NONQM, MI).

### Formatter Architecture

- **CLI Entry Point**: `formatter/format_excel.py` -- scan files and apply templates.
  - `--scan` mode: reads Excel with `data_only=True`, detects column types (date/text/float/integer/percentage), computes stats (min/max/median_abs), outputs JSON report + draft template.
  - Apply mode: loads workbook twice (data_only for value sampling, normal for editing), applies formatting in strict order (number formats -> header style -> conditional formatting -> column renames -> auto-widths), saves output.
- **Templates**: `formatter/templates/*.json` -- reusable formatting specs. All column keys reference original header names. See `formatter/README.md` for full field reference.
- **Design Rules**: One template = one header structure. Duplicate headers apply to all matches. `--inplace` always creates `.bak` backup. Renaming is always the last step.

### Usage Analyzer Architecture

- **CLI Entry Point**: `usage/analyze.py` -- loads CSV, builds charts, renders HTML.
  - `load_data()`: reads CSV, parses dates, classifies models into families, coerces numeric columns.
  - 11 chart functions (`chart_daily_volume`, `chart_trend`, etc.) each return a Plotly figure.
  - `build_report()`: computes KPIs, aggregates, calls all chart functions, assembles HTML with inline Plotly divs.
  - Plotly.js loaded from CDN (no local dependency in the output HTML).
- **Dependencies**: `pandas`, `plotly`, `numpy`. Output HTML is self-contained.
- **Timezone**: Heatmap converts UTC to ET (UTC-4) by default.

### Quant Workflows Architecture

- **Single Notebook**: `quant_workflows_notebook.ipynb` contains all workflows
- **Global Config**: Cell 1 auto-calculates `AS_OF_DATE` to most recent business day
- **Generator Functions**: Reusable command builders for common operations
- **Organization**: 18 sections grouped logically (Flat Files -> Vectors -> Risk -> Other)
- **Section Markers**: Visual separators for easy navigation
- **Security**: Environment variables for credentials (no hardcoded tokens)
- **No External Dependencies**: Self-contained, just needs Jupyter

---

## Setup

### Prerequisites

```bash
pip install -r requirements.txt
```

### Emailer

1. Edit `emailer/run.py` -> modify `MD_CONTENT`
  - Prefer `![]()` for auto-normalization; HTML `<img>` should already use `assets/` or a valid relative path
2. Run: `python emailer/run.py`
3. Paste from clipboard into email client

### Dial Updates

1. Generate a spec: `python dial/update_dials.py --generate-spec "dial/spec.json" --generate-only-dials --input "path/to/model.json"`
2. Edit the spec JSON (adjust dial values, start dates, enable/disable lines)
3. Apply: `python dial/update_dials.py --spec "dial/spec.json"`

### Workflows

1. Open: `jupyter notebook quant_workflows/quant_workflows_notebook.ipynb`
2. Run Cell 1 to configure (AS_OF_DATE auto-calculates to latest business day)
3. Navigate to desired section using visual markers
4. Copy/run commands as needed

**For Git operations:** Set `GITHUB_TOKEN` environment variable before use

```powershell
# PowerShell
$env:GITHUB_TOKEN = "your_token_here"
```

---

## Security

### Environment Variables for Credentials

The notebook uses environment variables for sensitive data:

**GitHub Token (Section 12):**

```powershell
# PowerShell
$env:GITHUB_TOKEN = "your_token_here"

# Bash
export GITHUB_TOKEN="your_token_here"
```

**Best Practices:**

- Never commit tokens or credentials to the repository
- Use environment variables for all sensitive data
- Rotate tokens regularly
- Clear notebook outputs before committing
- GitHub will block pushes containing secrets

---

## Recent Updates

### April 2026

- Added `usage/analyze.py` -- Cursor API usage analyzer that generates interactive HTML dashboards from usage-events CSV exports (11 Plotly charts, KPI cards, insight boxes, summary tables)
- `--name` flag for personalized reports; `--since` to filter date range

### March 2026

- Added `emailer/ai_instructions.md` -- AI prompt guide for consistent email formatting (image syntax, math, Outlook spacing rules)
- Added `pyproject.toml` with `ruff` config and `tests/test_smoke.py` for automated linting and smoke tests
- Added `AGENTS.md` at repo root -- continual-learning memory bootstrapped from past chat transcripts
- Added `.cursor/rules/workflow.mdc` -- Plan Mode nudge and workflow guardrails
- Added rule priorities to all `.mdc` files (90/70/40) to prevent conflicts
- Fixed Unicode checkmark crash on cp1252 Windows console in `render.py` (replaced with ASCII `[OK]`)
- Added `ruff` and `pytest` to `requirements.txt`

### February 2026

- Code review: fixed operator precedence bug in `dial_utils.py` section boundary detection
- Code review: fixed duplicated imports in `generate_diagram.py`
- Code review: corrected type hint in `render.py`
- Added missing dependencies to `requirements.txt` (`pandas`, `openpyxl`, `numpy`, `matplotlib`)
- Added `.gitignore`
- Updated README to reflect full codebase (dial analysis scripts, AI instructions, spec files)

### January 2026

- **Security**: Removed hardcoded GitHub token, switched to environment variables
- **Organization**: Renumbered sections 1-18 sequentially
- **Automation**: AS_OF_DATE auto-calculates to most recent business day
- **Navigation**: Added visual section markers
- **Documentation**: Comprehensive README with best practices
- **Sections**: Improved titles ("HELOC Flatfile" -> "HELOC Data Updates")

---

*Maintained by: Howard Zeng ([hzeng@libremax.com](mailto:hzeng@libremax.com))*