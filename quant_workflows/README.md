# Quantitative Workflows Notebook

A comprehensive, organized collection of commands and workflows for quantitative research operations.

## 📋 Overview

This notebook contains all the commands needed to run monthly quantitative operations, featuring:

**✨ New in v2.0:**
- ✅ Auto-calculating dates (no manual date entry needed!)
- ✅ Secure credential handling (environment variables)
- ✅ Visual section markers for easy navigation
- ✅ Sequential numbering (1-18)
- ✅ Enhanced security (no hardcoded tokens)

**Operations Covered:**
- Jenkins workflow orchestration
- Data updates (CRT, LP, HELOC, DV01)
- Vector generation (LMSim)
- Risk runs and portfolio analysis
- Tracking reports
- Database operations and queries

## 🚀 Quick Start

### 1. Open the Notebook
```bash
jupyter notebook quant_workflows_notebook.ipynb
```

### 2. Run Global Configuration (Cell 1)
**✨ New!** AS_OF_DATE now auto-calculates to the most recent business day (excluding weekends).

```python
# Run Cell 1 - it auto-calculates AS_OF_DATE
# Output: >>> Configuration loaded for date: 20260128

# Override manually if needed:
# AS_OF_DATE = "20251001"

# Other settings:
EMAIL_RECIPIENTS = "hzeng@libremax.com"
RAY_CLUSTER = "east-spot"
```

**What's Auto-Calculated:**
- `AS_OF_DATE` → Most recent business day
- `date_ranges` → Start/end dates for unloading

### 3. Navigate Using Visual Markers
Look for these section markers to quickly find what you need:
- 📁 **FLAT FILE GENERATION** (Sections 4-6)
- 📊 **VECTOR GENERATION** (Sections 7-9)
- 📈 **RISK OPERATIONS** (Section 10)
- 🔧 **OTHER OPERATIONS** (Sections 11-18)

---

## 📚 Table of Contents

The notebook is organized by workflow type with clear section markers.

### Core Workflows
| Section | Description | When to Use |
|---------|-------------|-------------|
| **1. Jenkins Workflows** | Monthly tracking workflow steps | Monthly process checklist |
| **2. HECM Reports** | Automated HECM report generation | Monthly HECM reporting |
| **3. CRT Pseudo Deals** | Create pseudo pools | New month setup |

### 📁 Flat File Generation
| Section | Description | When to Use |
|---------|-------------|-------------|
| **4. CRT and LP Data Updates** | Update CRT/LP flat files | Daily/weekly data refresh |
| **5. HELOC Data Updates** | HELOC-specific flat file updates | HELOC deal updates |
| **6. Monthly Data Refresh** | Comprehensive update commands | End-of-month full refresh |

### 📊 Vector Generation
| Section | Description | When to Use |
|---------|-------------|-------------|
| **7. Tracking Vectors** | ECA, Matrix, Forward Projection | Monthly tracking runs |
| **8. Ad-hoc LMSim** | One-off simulation commands | Testing, special analyses |
| **9. Position-Only Runs** | Quick position updates | Daily position updates |

### 📈 Risk
| Section | Description | When to Use |
|---------|-------------|-------------|
| **10. Risk Runs** | Generate risk vectors/JSON | Portfolio risk analysis |

### 🔧 Other Operations
| Section | Description | When to Use |
|---------|-------------|-------------|
| **11. Debug Operations** | LMSim debugging commands | Troubleshooting |
| **12. Utilities** | Git, Ray job management | Infrastructure tasks |
| **13. Deal Lists** | Common deal identifiers | Reference for deal names |
| **14. Quick Generator** | Dynamic workflow builder | Generate full workflows |
| **15. Google Cloud** | BigQuery access instructions | Cloud database queries |
| **16. Tape Cracking** | New deal onboarding | Adding new deals |
| **17. Database Ops** | SQL queries, kill jobs | Database management |
| **18. IntexLoader** | Load Intex data | Intex data updates |

---

## 🎯 Common Use Cases

### Monthly Tracking Workflow
```python
# 1. Check AS_OF_DATE in Cell 1 (auto-calculated to latest business day)
# Override if needed: AS_OF_DATE = "20251101"

# 2. Run Section 1 - Jenkins Workflows (follow in order)

# 3. Flat File Generation:
#    - Section 3: CRT Pseudo Deals
#    - Section 6: Monthly Data Refresh (comprehensive)
#    - Section 4 & 5: Specific updates as needed

# 4. Vector Generation:
#    - Section 7: Tracking Vectors & Reports
```

### Quick Data Update for One Deal
```python
# Go to Section 4 - CRT and LP Data Updates
# Use the ad-hoc examples (Cell after generator function)

# Example:
# Python agencydata/wh_lp_update.py --skip_unload --deal_type "JUMBO2_0" --deal_list "CHASE 2024-6" --force_save_stats
```

### Generate Position-Only Vectors
```python
# Go to Section 9 - Position-Only Runs
# Update the variables:
AS_OF_DATE_POS = 20251201
purpose = "PROD"
deal_type = "JUMBO2_0"

# Run the cell to generate commands
```

Current LMSim vector commands use `-purpose` rather than the old
`-dbsavefromdll_json*` flags. For forward-projection / position-only runs, use
the tracking purpose convention:

```powershell
python lmsimvectors\lm_sim_pub_main.py -as_of_date 20260519 -mode batch-ray `
  -request_mode forward_proj -purpose NQM_SIM2_V1_tracking `
  -scenarios_batch "default+opera" -deal_type NONQM `
  -position_only -position_asofdate 20260519 -ray_cluster east
```

### Debug a Simulation Issue
```python
# Go to Section 10 - Debug Operations
# Choose production or development debug command
# Run LMSim with debug logging enabled
```

---

## 💡 Tips & Best Practices

### 1. **AS_OF_DATE Auto-Calculates**
- The global `AS_OF_DATE` now defaults to the most recent business day (excludes weekends)
- It cascades through all commands automatically
- Override manually if needed: `AS_OF_DATE = "20251101"`

### 2. **Use Generator Functions**
Instead of hardcoding commands, use the provided functions:

```python
# ❌ Don't do this (hard to maintain)
cmd = "python agencydata\\wh_crt_update.py --deal_type CAS --deal_list 'CAS 2022-R02' --force_save_stats"

# ✅ Do this (flexible and reusable)
cmd = generate_wh_crt_update(
    deal_type="CAS",
    deal_list="CAS 2022-R02",
    force_save_stats=True
)
```

### 3. **Follow the Workflow Order**
- Notebook is organized by logical flow: **Flat Files → Vectors → Risk → Other**
- Section markers (`# Flat File Gen`, `# Vector`, `# Risk`, `# Other`) help navigate
- Section 6 (Monthly Refresh) positioned logically after flat file updates

### 4. **Section 6 is Your Monthly Checklist**
- Use it for comprehensive end-of-month data refreshes
- All deal types covered in one place
- Copy/paste commands directly into terminal

### 5. **Save Custom Configurations**
If you frequently run the same combination:

```python
# Create a custom cell with your common settings
MY_DEAL_TYPE = "JUMBO2_0"
MY_PURPOSE = "Howard_jumbo_prod"
MY_SCENARIOS = "Base,ParallelUp200,ParallelDn200"

# Then use these in generator functions
commands = generate_lmsim_commands(
    MY_DEAL_TYPE, AS_OF_DATE, MY_PURPOSE,
    scenarios=MY_SCENARIOS
)
```

### 6. **Reference Deal Lists**
Section 13 contains pre-defined deal lists for common scenarios:
- `DEAL_LISTS['STACR_RECENT']`
- `DEAL_LISTS['HELOC_GRADE']`
- `DEAL_LISTS['JUMBO_RECENT']`

---

## 🔧 Customization Guide

### Adding a New Command Pattern

1. **Find the appropriate section** (or create a new one)
2. **Add a generator function** if the command is reusable
3. **Document parameters** clearly
4. **Add an example** showing typical usage

Example:
```python
def generate_my_custom_workflow(deal_type, date, purpose):
    """Generate custom workflow for XYZ analysis
    
    Args:
        deal_type: Deal type (e.g., "CRT", "JUMBO2_0")
        date: As-of date (YYYYMMDD)
        purpose: Purpose tag for database
    
    Returns:
        Command string ready to execute
    """
    return f"python my_script.py --deal_type {deal_type} --date {date} --purpose {purpose}"

# Example usage:
cmd = generate_my_custom_workflow("JUMBO2_0", "20251001", "PROD")
print(cmd)
```

### Creating a New Section

Use this markdown template:
```markdown
## X. Your Section Name
Brief description of what this section contains
```

Then add code cells with clear comments and examples.

---

## 🗂️ File Organization

```
quant_workflows/
├── README.md                        # This file (411 lines)
└── quant_workflows_notebook.ipynb   # Main notebook (1500+ lines, 18 sections)
```

---

## 📝 Workflow Patterns

### Pattern 1: Data Update → Vector Generation → Tracking
```python
# Step 1: Update flat files
cmd_update = generate_wh_crt_update(deal_type="CAS", ...)

# Step 2: Generate vectors
commands = generate_lmsim_commands(deal_type="CAS", ...)

# Step 3: Generate tracking report
tracking_cmd = generate_tracking_command(deal_type="CAS", ...)
```

### Pattern 2: Position-Only Daily Updates
```python
# Quick daily position update without full run
as_of_date = "20251115"
deal_types = "CRT,JUMBO2_0,NONQM,HELOC"
purpose = "PROD"

# See Section 9 for ready-to-use commands
```

For forward projection, the notebook builds `tracking_purpose = f"{purpose}_tracking"`
and passes it with `-purpose`. The base purpose is still used for non-forward
modes such as ECA.

### Pattern 3: Risk Run for Portfolio
```python
# Step 1: Get CUSIPs (Section 10 has common lists)
cusips = CRT_CUSIPS  # or define your own

# Step 2: Generate risk run
cmd = generate_risk_run(date, "RATE_HEDGE", cusips, purpose)
```

Section 10 includes reusable CUSIP lists for CRT, HELOC, MIR, Jumbo, and NQM.
Use `NQM_CUSIPS` for the current NQM risk-run package.

---

## ⚠️ Important Notes

### Security Best Practices ✅

**Environment Variables (Section 12):**
The notebook now uses environment variables for GitHub tokens instead of hardcoding them:

```powershell
# PowerShell
$env:GITHUB_TOKEN = "your_token_here"

# Bash
export GITHUB_TOKEN="your_token_here"
```

**Security Checklist:**
- ✅ Tokens stored in environment variables (not hardcoded)
- ✅ Tokens masked in output (`***TOKEN***`)
- ✅ GitHub will block pushes containing secrets
- ⚠️ Always clear cell outputs before committing
- ⚠️ Never commit credentials or API keys
- ⚠️ Rotate tokens regularly

### Ray Cluster Configuration
Default cluster is `east-spot`. If it's down:
- Change `RAY_CLUSTER = "east"` in global config
- Or override in individual commands

### Database Connections
Some operations require database access. Ensure:
- VPN connection is active
- Database credentials are current
- Network has access to required resources

---

## 🆘 Troubleshooting

### "Command not found" errors
- Ensure you're in the correct Git repo directory (C:\Git\LMQR or C:\Git\LMQR_prod)
- Check Python environment is activated
- Verify paths in global configuration (Cell 1)

### Ray job stuck/hanging
- Use Section 12 (Utilities) to stop Ray jobs
- Update `job_id` variable with your job ID
- Run the curl command for your cluster

### Data update fails
- Check date formats (YYYYMMDD vs YYYYMM)
- Verify deal names match Bloomberg conventions
- Check database connectivity

### IntexLoader errors
- Verify deal list exists in Intex system
- Check date range is valid
- Ensure database has write permissions

---

## 📞 Support

For questions or issues:
- Check this README first
- Review comments in the notebook cells
- Consult team documentation
- Contact: hzeng@libremax.com

---

## 🔄 Maintenance

### Weekly
- Review Section 8 (Ad-hoc commands) - move repeated patterns to organized sections

### Monthly
- Update `AS_OF_DATE` in Cell 1 (or let it auto-calculate)
- Run Section 6 (Monthly Refresh)
- Archive old commands that are no longer needed

### Quarterly
- Review and update deal lists (Section 13)
- Update CUSIP lists (Section 10)
- Check for deprecated commands

---

## 📈 Version History

### v2.0 - January 2026
- ✅ **Security**: Removed hardcoded GitHub token, switched to environment variables
- ✅ **Organization**: Renumbered all sections sequentially (1-18)
- ✅ **Automation**: AS_OF_DATE auto-calculates to most recent business day
- ✅ **Navigation**: Added visual section markers (📁📊📈🔧)
- ✅ **Titles**: Improved section names for clarity
- ✅ **Documentation**: Enhanced README with security best practices

### v1.0 - Initial Release
- Consolidated scattered commands into logical groups
- Added generator functions for common patterns
- Created comprehensive monthly refresh checklist
- Organized into 18 sections

---

## 🎓 Learning Resources

New to the notebook? Start here:
1. Read the Overview section
2. Review Common Use Cases
3. Run through a simple workflow (e.g., single deal update)
4. Explore generator functions in Section 7
5. Bookmark frequently-used sections

---

*Last updated: January 2026*
