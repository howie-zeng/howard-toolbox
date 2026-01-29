
# Howard's Toolbox

A collection of productivity tools and workflows for quantitative research.

## 📁 Structure

```
howard-toolbox/
├── emailer/              # Email content generator with Markdown support
│   ├── run.py           # Main entry point
│   ├── render.py        # MD -> HTML rendering logic
│   ├── assets/          # Images for embedding
│   └── outputs/         # Generated HTML files
│
└── commands/            # ⚠️ Rename to quant_workflows/
    ├── README.md        # Comprehensive workflow documentation
    └── quant_workflows_notebook.ipynb  # 18 organized sections of commands
```

---

## 🔧 Tools

### 1. Email Content Generator (`emailer/`)

Converts Markdown to HTML for rich email composition.

**Quick start:**
```bash
python emailer/run.py
```

**Features:**
- Markdown to HTML with tables and styling
- LaTeX math support via CodeCogs
- Image embedding (local files → base64)
- Clipboard integration
- Special tag: `{{CLIPBOARD}}` for dynamic images

### 2. Quantitative Workflows (`commands/`)

**📝 Recommended:** Rename this folder to `quant_workflows/` for clarity.

Comprehensive notebook with 18 organized sections covering:
- Jenkins workflows
- Data updates (CRT, LP, HELOC)
- Vector generation (LMSim)
- Risk runs and tracking
- Database operations
- Monthly refresh checklists

**Quick start:**
```bash
jupyter notebook commands/quant_workflows_notebook.ipynb
```

**See [`commands/README.md`](commands/README.md) for full documentation.**

---

## 🧠 For AI Agents / Developers

### Emailer Architecture

- **Entry Point**: `emailer/run.py` is the main script. User edits `MD_CONTENT` string here.
- **Rendering Logic**: `emailer/render.py` handles:
  - Markdown -> HTML (using `markdown` lib)
  - Post-processing with `BeautifulSoup` (tables, styling, unwrap images)
  - LaTeX Math -> CodeCogs images (`$$...$$` -> `<img src="...">`)
  - Local Images -> Base64 encoded strings (for email portability)
- **Clipboard**: The script uses `win32clipboard` to put the final HTML into the Windows clipboard.
- **Special Tags**:
  - `{{CLIPBOARD}}`: Replaced at runtime with the image currently in the OS clipboard.

### Quant Workflows Architecture

- **Single Notebook**: `quant_workflows_notebook.ipynb` contains all workflows
- **Global Config**: Cell 1 has variables that cascade through all commands
- **Generator Functions**: Reusable command builders for common operations
- **Organization**: 18 sections grouped by function (see TOC in notebook README)
- **No External Dependencies**: Self-contained, just needs Jupyter

---

## 📦 Setup

### Prerequisites
```bash
pip install -r requirements.txt
```

### Emailer
1. Edit `emailer/run.py` → modify `MD_CONTENT`
2. Run: `python emailer/run.py`
3. Paste from clipboard into email client

### Workflows
1. Open: `jupyter notebook commands/quant_workflows_notebook.ipynb`
2. Update `AS_OF_DATE` in Cell 1
3. Navigate to desired section
4. Copy/run commands as needed

---

## 🔄 Maintenance

### To Rename Commands Folder
```bash
# Close the notebook in Cursor first, then:
ren commands quant_workflows
```

Then update all documentation references.

---

*Maintained by: Howard Zeng (hzeng@libremax.com)*
