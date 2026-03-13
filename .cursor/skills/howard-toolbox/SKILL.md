---
name: howard-toolbox
description: >-
  Project knowledge for howard-toolbox: a collection of productivity tools
  for quantitative research (emailer, dial calibration, Excel formatter,
  quant workflows). Use when the user mentions howard-toolbox, emailer,
  dial calibration, Excel formatter, quant workflows, or references any
  tool from that project. Also use when the workspace is howard-toolbox.
---

# Howard Toolbox

Productivity tools for quantitative research. This is the canonical source
of truth for project knowledge. The repo lives at `S:\QR\hzeng\howard-toolbox`;
`~/.cursor/skills/howard-toolbox` is a copy kept in sync for cross-workspace loading.

## Update Instructions

The agent may proactively propose updates to this file. All writes require a
diff preview and user approval before saving. Write to the repo
(`S:\QR\hzeng\howard-toolbox`) first — it is the source of truth. Then mirror
to `~/.cursor/skills/howard-toolbox/SKILL.md` for cross-workspace loading.
Consolidate if this file exceeds ~120 lines.

## Project Structure

```
howard-toolbox/
├── emailer/          # Markdown -> HTML email with clipboard support
│   ├── run.py        # Entry point (edit MD_CONTENT, run, paste)
│   ├── render.py     # MD -> HTML, base64 images, win32clipboard
│   └── generate_diagram.py  # Matplotlib flowcharts
│
├── dial/             # Model dial calibration & overrides
│   ├── update_dials.py  # CLI: generate specs, apply dial overrides
│   ├── dial_utils.py    # Tracking file parsing, summary extraction
│   └── run.py           # Batch dial-ratio analysis -> Excel
│
├── formatter/        # Template-driven Excel formatting
│   └── format_excel.py  # Scan, detect types, apply templates
│
├── quant_workflows/  # Jupyter notebook with 18 workflow sections
│   └── quant_workflows_notebook.ipynb
│
└── requirements.txt  # pywin32, markdown, Pillow, bs4, pandas, openpyxl, numpy, matplotlib
```

7 Python files (~3K lines). Budget: 12 max.

## Module Patterns

### emailer
- **Workflow**: Edit `MD_CONTENT` in `run.py` -> run -> paste from clipboard.
- `render.py`: markdown lib -> BeautifulSoup post-processing -> inline styles -> base64 image embed -> win32clipboard HTML Format.
- `{{CLIPBOARD}}` tag captures current OS clipboard image at runtime.
- Images auto-normalize into `assets/`. LaTeX converts to CodeCogs `<img>` tags.
- Platform: Windows-only (`win32clipboard`, `PIL.ImageGrab`).

### dial
- **Two modes**: (1) `--generate-spec` extracts all transitions from a model JSON, (2) `--spec` applies overrides to produce a new JSON with bumped version.
- `dial_utils.py` parses tracking Excel workbooks by bucket type, finds latest files by date in filename.
- `run.py` batch analysis: dialed vs undialed tracking -> implied dials -> formatted multi-sheet Excel.
- Dial `1.0` = "no dial" (removes Shock). Cohort vs simple shocks handled separately.

### formatter
- **Workflow**: `--scan` auto-detects column types -> edit JSON template -> apply.
- Dual workbook loading: `data_only=True` for sampling, normal for editing.
- Apply order: number formats -> header style -> data style -> dividers -> outer border -> conditional formatting -> renames -> auto-widths.
- Templates key on original header names; renames are last. `--inplace` does atomic write with `.bak`.

### quant_workflows
- Single Jupyter notebook, 18 sections. Cell 1 auto-calculates `AS_OF_DATE`.
- Uses `GITHUB_TOKEN` env var for Git operations.

## Coding Conventions

- Type hints on all function signatures.
- Error messages must be actionable (include paths, available values).
- Comments only where needed (why, not what).
- f-strings for formatting. `pathlib.Path` preferred for new code.
- No secrets in code: use env vars and placeholders.

## Known Gotchas

- `render.py` imports `win32clipboard` at top level -- crashes on non-Windows.
- `pd.ExcelFile` in `dial_utils.py` should be context-managed (known leak).
- `generate_diagram.py` `__main__` has a hardcoded absolute path.
- `.gitignore` excludes images and output dirs; stale tracked files may need `git rm --cached`.
