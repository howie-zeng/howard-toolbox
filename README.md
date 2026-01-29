
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
├── quant_workflows/     # Quantitative workflows and commands
│   ├── README.md        # Comprehensive workflow documentation (411 lines)
│   └── quant_workflows_notebook.ipynb  # 18 organized sections (1500+ lines)
│
├── README.md            # This file
└── requirements.txt     # Python dependencies
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

### 2. Quantitative Workflows (`quant_workflows/`)

Comprehensive notebook with 18 sequentially organized sections:

**📁 Flat File Generation (4-6):** CRT/LP updates, HELOC data, monthly refresh  
**📊 Vector Generation (7-9):** Tracking vectors, ad-hoc LMSim, position-only runs  
**📈 Risk (10):** Portfolio risk analysis and vectors  
**🔧 Other (11-18):** Debug, utilities, deal lists, database ops, IntexLoader

**Features:**
- ✅ Auto-calculates `AS_OF_DATE` to most recent business day
- ✅ Secure credential handling (environment variables)
- ✅ Generator functions for reusable commands
- ✅ Clear visual section markers
- ✅ Comprehensive monthly refresh checklist

**Quick start:**
```bash
jupyter notebook quant_workflows/quant_workflows_notebook.ipynb
```

**See [`quant_workflows/README.md`](quant_workflows/README.md) for full documentation.**

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
- **Global Config**: Cell 1 auto-calculates `AS_OF_DATE` to most recent business day
- **Generator Functions**: Reusable command builders for common operations
- **Organization**: 18 sections grouped logically (Flat Files → Vectors → Risk → Other)
- **Section Markers**: Visual separators (📁📊📈🔧) for easy navigation
- **Security**: Environment variables for credentials (no hardcoded tokens)
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
1. Open: `jupyter notebook quant_workflows/quant_workflows_notebook.ipynb`
2. Run Cell 1 to configure (AS_OF_DATE auto-calculates to latest business day)
3. Navigate to desired section using visual markers (📁📊📈🔧)
4. Copy/run commands as needed

**For Git operations:** Set `GITHUB_TOKEN` environment variable before use
```powershell
# PowerShell
$env:GITHUB_TOKEN = "your_token_here"
```

---

## 🔒 Security

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
- ✅ Never commit tokens or credentials to the repository
- ✅ Use environment variables for all sensitive data
- ✅ Rotate tokens regularly
- ✅ Clear notebook outputs before committing
- ⚠️ GitHub will block pushes containing secrets

---

---

## 📝 Recent Updates

### January 2026
- ✅ **Security**: Removed hardcoded GitHub token, switched to environment variables
- ✅ **Organization**: Renumbered sections 1-18 sequentially
- ✅ **Automation**: AS_OF_DATE auto-calculates to most recent business day
- ✅ **Navigation**: Added visual section markers (📁📊📈🔧)
- ✅ **Documentation**: Comprehensive README with best practices
- ✅ **Sections**: Improved titles ("HELOC Flatfile" → "HELOC Data Updates")

---

*Maintained by: Howard Zeng (hzeng@libremax.com)*
