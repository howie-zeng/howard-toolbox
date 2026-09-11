# NQM FCLStD Redial Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. This is a model-calibration loop (MATRIX + tracking report), not a software feature — do not dispatch a subagent per task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recalibrate NQM `V1_8_0` FCLS→D so Dialed tracking matches the post-`PD`-fold Actuals (~2.6), replacing the 0.017x/0.018x shocks that were solved against liquidation-only Actuals.

**Architecture:** Follow `dial/DIAL_RUNBOOK.md` exactly. Round 1 changes only the two JSON keys that fold into report row `FCLStD` (`FCLStoD` and `FCLStoP`, both `To=D`). Deploy the JSON via git to Howard's LMSimData clone, rerun MATRIX under purpose `PROD`, rebuild the FCLS sheet into `tracking/Dev`, then compound. Do not merge to prod `N:\LMSimData` until `|FCLStD 6M ratio − 1| ≤ 1%`.

**Tech Stack:** `dial/dial_utils.py` (`dial_schedule(..., permanent=True)`), `C:\Git\LMSimData\data\NONQM\nonqm_v1.8.0_submodel.json`, LMQR `lm_sim_pub_main` MATRIX + `lmanalytics/tracking/transition_report.py`, SQL on `libremax.dbo.ResiTransitionTracking`.

## Global Constraints

- Canonical procedure: `dial/DIAL_RUNBOOK.md`. Orientation: `runbooks/dial-model.md`. After tracking converges: `dial/RISK_RUNBOOK.md` (out of scope until FCLStD is inside 1%).
- NQM deep-DQ dials are **permanent**: `"<x>x for 48 <x>x"` (`d81cd9f4`). A ramped `dial_schedule(x)` (no pad) silently reverts long-horizon vectors to 1x. Tracking will not catch that.
- **Do not use** `dial/update_dials.py --spec` (rewrites every `Version`, indent=4).
- **Do not use** `dial/apply_dials_inplace.py` for this job. Two independent failures: (1) `_build_dial_detail` only preserves `"Nx for M"` with no trailing pad, so `"0.017x for 48 0.017x"` falls through to a **ramped** `dial_schedule(0.662)`; (2) `dumps_like` has no trailing newline, and `nonqm_v1.8.0_submodel.json` ends in `\n`, so the formatting gate fails (or would reformat the file if the gate were skipped). Apply with the §4 snippet in Task 2, which calls `dial_schedule(x, permanent=True)`.
- Dial `1.0` means **remove** the Shock (`memories.mdc`). Never write `1.0x`.
- Never edit `N:\LMSimData` or `N:\DevSimData\LMSimData_Howard` in place. Git push from `C:\Git\LMSimData`, then `git pull` in the clone Ray will read.
- Do not bump `MODEL_VERSION_NONQM` / filename. Tracking is keyed on `V1_8_0_NONQM`. Shock-only edit.
- Do not overwrite `R:\QR\Resi_shared\tracking\Dialed\tracking_V1_8_0_NONQM_20260901.xlsx` until convergence. Iterate with `--dev`.
- Leave `FCLStoC` and `FCLStoREO` untouched in round 1. FCLS is `NormalizationMethod: SOFTMAX`; a 40x move on D/P will steal share. Read them after MATRIX; compound only if they moved.
- `FCLStoB` is a **second** report cell (broken `M270`→`M270P` fold). Probe rule is one cell per experiment — it is Round 2, not Round 1.
- Jumbo / HELOC are out of scope.

## Resolved parameters (DIAL_RUNBOOK §0)

| Parameter | Value | How confirmed |
|---|---|---|
| `DEAL_TYPE` | `NONQM_PSEUDO` | FCLS sheet is the `NQMFCLS` status cohort |
| `SUBMODEL_JSON` | `C:\Git\LMSimData\data\NONQM\nonqm_v1.8.0_submodel.json` | `SIM2_MODEL_PATHS['NONQM_PSEUDO']` |
| `TRACKING_PURPOSE` | `PROD` | `ResiTransitionTracking` for `NQMFCLS ALL` / `V1_8_0_NONQM`: live rows are `PROD` (Dialed) and `PROD_UNDIALED`. `NQM_SIM2_V7_TRACKING` stops at 2026-07-01 — stale. |
| `ASOF` | `20260901` | Matches the Sep workbook |
| `MODEL_VERSION` | `V1_8_0_NONQM` | File stamp and tracking key |
| `REPORT` (baseline) | `R:\QR\Resi_shared\tracking\Dialed\tracking_V1_8_0_NONQM_20260901.xlsx` | And Undialed twin |
| `STATUS_SHEETS` | `FCLS` only this job | |
| Howard clone | `N:\DevSimData\LMSimData_Howard` | `$env:SIM2_DATA_SUBDIR='DevSimData/LMSimData_Howard'` |
| Prod clone | `N:\LMSimData` | Pull only after merge to `main` |
| `StartDate` | `20250501` | Keep existing. A 20250801 lookback would mix old 0.017x into the 6M window. |

## Round-1 dial math (DIAL_RUNBOOK §1)

From the Sep **Undialed** FCLS sheet, WAC-style single rows (no `ALL AVG` on status sheets):

| Report row | 6M Ratio (Undialed) | `dial = 1 / 6M` | Current shock | Round 1? |
|---|---|---|---|---|
| `FCLStD` | 1.5109 | **0.662** | 0.017 / 0.018 | **Yes** |
| `FCLStB` | 0.5534 | 1.807 | 1.097 | Round 2 |
| `FCLStC` | 0.5410 | 1.848 | 1.76 | Observe only (Dialed 6M already 0.952) |
| `FCLStREO` | 0.4303 | 2.324 | 2.506 | Observe only (Dialed 6M already 1.078) |

Same 0.662 on both JSON keys — the report cell is the fold (`DIAL_RUNBOOK` §2). 3dp split (0.017/0.018) was only needed when the number sat on the 3dp floor; 0.662 does not.

Compound check vs Dialed 6M 0.0267: `0.0175 / 0.0267 ≈ 0.655`. Prefer **0.662** from Undialed (does not depend on blending 0.017 vs 0.018).

Saturation check (do **not** use §6c hazard solve): 2026-08 actual FCLS outflow ~15.8% vs undialed ~10.6%. Not a 99% drain plateau.

## File structure

| File | Role |
|---|---|
| `C:\Git\LMSimData\data\NONQM\nonqm_v1.8.0_submodel.json` | Only file that changes this job. Shock.Detail on `FCLStoD` and `FCLStoP`. |
| `R:\QR\Resi_shared\tracking\Dev\tracking_V1_8_0_NONQM_20260901.xlsx` | Iteration reports (`--dev`) |
| `R:\QR\Resi_shared\tracking\Dialed\tracking_V1_8_0_NONQM_20260901.xlsx` | Frozen baseline. Copy aside before any non-dev rebuild. |

No howard-toolbox Python changes in this plan. If someone later wants `apply_dials_inplace.py` to handle permanent pads + trailing newline, that is a separate PR.

---

## Chunk 1: Lint, apply, deploy to Howard clone

### Task 1: Pre-flight gates

**Files:** none (read-only)

- [ ] **Step 1: Reproduce current permanent strings**

```powershell
python -c "import sys; sys.path.insert(0, r'S:\QR\hzeng\howard-toolbox\dial'); from dial_utils import dial_schedule; print(repr(dial_schedule(0.017, permanent=True))); print(repr(dial_schedule(0.018, permanent=True))); print(repr(dial_schedule(0.662, permanent=True)))"
```

Expected:

```
'0.017x for 48 0.017x'
'0.018x for 48 0.018x'
'0.662x for 48 0.662x'
```

- [ ] **Step 2: Lint `HasSubModel` / `To` / current shocks**

```powershell
python -c @"
import json
from pathlib import Path
j = json.loads(Path(r'C:\Git\LMSimData\data\NONQM\nonqm_v1.8.0_submodel.json').read_text(encoding='utf-8'))
fcls = j['State']['FCLS']
print('NormalizationMethod', fcls['Attributes']['NormalizationMethod'])
for key in ('FCLStoC','FCLStoB','FCLStoP','FCLStoREO','FCLStoD','FCLStoFCLS'):
    t = fcls['Transitions'][key]
    print(key, 'HasSubModel=', t['HasSubModel'], 'To=', t.get('To'), 'IsSelfTrans=', t.get('IsSelfTrans'), 'Shock=', t.get('Shock'))
"@
```

Expected: `SOFTMAX`; `FCLStoD` and `FCLStoP` both `HasSubModel=false`, `To=D`, `IsSelfTrans=false`, Details `0.017x for 48 0.017x` and `0.018x for 48 0.018x`. Self-trans `FCLStoFCLS` has no Shock (residual — do not add one).

- [ ] **Step 3: Confirm writer convention**

`json.dumps(..., indent=2) + "\n"` reproduces `nonqm_v1.8.0_submodel.json` (file is 45349 bytes, trailing newline). If a trial dump without writing disagrees, stop — do not save.

- [ ] **Step 4: Archive the baseline workbook**

```powershell
Copy-Item "R:\QR\Resi_shared\tracking\Dialed\tracking_V1_8_0_NONQM_20260901.xlsx" `
          "R:\QR\Resi_shared\tracking\Dev\tracking_V1_8_0_NONQM_20260901_pre_fclstd_redial.xlsx"
```

### Task 2: Apply Round-1 shocks (DIAL_RUNBOOK §4)

**Files:**
- Modify: `C:\Git\LMSimData\data\NONQM\nonqm_v1.8.0_submodel.json` — `State.FCLS.Transitions.FCLStoD.Shock` and `FCLStoP.Shock` only

**Interfaces:**
- Consumes: Task 1 gates
- Produces: permanent Detail `0.662x for 48 0.662x` on both keys, `StartDate` still `20250501`

- [ ] **Step 1: Branch in LMSimData**

```powershell
cd C:\Git\LMSimData
git checkout main
git pull
git checkout -b nqm/fclstd-redial-202609
```

- [ ] **Step 2: Apply via this script — do not hand-edit JSON**

Run from any cwd. This is the DIAL_RUNBOOK §4 write with `permanent=True` (the runbook snippet omits `permanent`; NQM deep-DQ requires it).

```python
import json
import sys
from pathlib import Path

sys.path.insert(0, r"S:\QR\hzeng\howard-toolbox\dial")
from dial_utils import dial_schedule

path = Path(r"C:\Git\LMSimData\data\NONQM\nonqm_v1.8.0_submodel.json")
original = path.read_text(encoding="utf-8")
j = json.loads(original)

detail = dial_schedule(0.662, permanent=True)
assert detail == "0.662x for 48 0.662x"

for key in ("FCLStoD", "FCLStoP"):
    t = j["State"]["FCLS"]["Transitions"][key]
    assert t["HasSubModel"] is False
    assert t["To"] == "D"
    assert t["IsSelfTrans"] is False
    t["Shock"] = {"StartDate": "20250501", "Detail": detail}

updated = json.dumps(j, indent=2, ensure_ascii=False) + "\n"
if json.dumps(json.loads(original), indent=2, ensure_ascii=False) + "\n" != original:
    raise SystemExit("writer would reformat the file; abort")
path.write_text(updated, encoding="utf-8", newline="\n")
print("wrote", path)
```

- [ ] **Step 3: `git diff` gate**

Expected: **two** `Detail` lines, nothing else.

```
-          "Detail": "0.017x for 48 0.017x"
+          "Detail": "0.662x for 48 0.662x"
```

and the same for `0.018x` → `0.662x`. If Version fields, other shocks, or whitespace-only hunks appear, revert and stop.

- [ ] **Step 4: Commit on the feature branch (do not merge main yet)**

```powershell
cd C:\Git\LMSimData
git add data/NONQM/nonqm_v1.8.0_submodel.json
git commit -m "$(cat <<'EOF'
NQM FCLStoD/FCLStoP: 0.662x permanent (PD-fold actuals)

FCLStD actuals now include LP FCLS prepay (PD). Prior 0.017/0.018
were fit to liquidation-only. Same dial on both keys; both To=D.
EOF
)"
```

On PowerShell without bash HEREDOC, use:

```powershell
git commit -m "NQM FCLStoD/FCLStoP: 0.662x permanent (PD-fold actuals)"
```

- [ ] **Step 5: Push branch and pull Howard clone only**

```powershell
cd C:\Git\LMSimData
git push -u origin nqm/fclstd-redial-202609
git -C "N:\DevSimData\LMSimData_Howard" fetch
git -C "N:\DevSimData\LMSimData_Howard" checkout nqm/fclstd-redial-202609
git -C "N:\DevSimData\LMSimData_Howard" pull
```

Gate: clone HEAD == pushed commit. Parse the pulled JSON and print the two Detail strings. They must be `0.662x for 48 0.662x`.

**Do not** pull this branch into `N:\LMSimData` yet.

---

## Chunk 2: MATRIX + Dev report + probe

### Task 3: Rerun MATRIX (DIAL_RUNBOOK §6)

**Files:** none in-repo. Writes `ResiTransitionTracking` purpose `PROD`.

Ray workers read `SIM2_DATA_ROOT_DIR`. Default in `C:\Git\LMQR` is `N:\LMSimData` (prod, still 0.017x). Override so workers see the Howard clone.

- [ ] **Step 1: Confirm the override resolves to the dialed file**

```powershell
cd C:\Git\LMQR
$env:SIM2_DATA_SUBDIR = "DevSimData/LMSimData_Howard"
uv run python -c "from lmsimvectors.config import sim_config_sim2 as c; print(c.SIM2_MODEL_PATHS['NONQM_PSEUDO'])"
```

Expected path under `N:\DevSimData\LMSimData_Howard\data\NONQM\nonqm_v1.8.0_submodel.json`. Open it and confirm 0.662x.

- [ ] **Step 2: MATRIX `force_rerun`**

Always `uv run` from `C:\Git\LMQR` (`dial/RISK_RUNBOOK.md` §0). Never conda `pyprod` — Ray pip-installs the launching interpreter's `lmsim`.

```powershell
cd C:\Git\LMQR
$env:SIM2_DATA_SUBDIR = "DevSimData/LMSimData_Howard"
uv run python -m lmsimvectors.lm_sim_pub_main `
  -mode batch-ray `
  -deal_type NONQM_PSEUDO `
  -request_mode matrix `
  -purpose PROD `
  -as_of_date 20260901 `
  -num_of_workers 24 `
  -force_rerun
```

`-purpose` must be `PROD` exactly (`-p2` on the report). Never `TRACKING` (batch-ray rewrites it to `PROD` on save and you will not know which model you ran). Status sheets are MATRIX-driven; skip ECA until FCLStD has converged.

If the Ray job dies in ~30s with an empty cluster log, read `https://lmsim-ray.qr.libremax.com/api/jobs/<id>` (`lmsim==` pin mismatch).

- [ ] **Step 3: Source-table probe before trusting Excel**

```sql
SELECT purpose, dlnq_stat_next, SUM(bal) bal
FROM libremax.dbo.ResiTransitionTracking
WHERE bbg_deal_name = 'NQMFCLS ALL'
  AND model_version = 'V1_8_0_NONQM'
  AND factor_date = '2026-08-01'
  AND dlnq_stat = 'FCLS'
GROUP BY purpose, dlnq_stat_next
```

Effective D multiplier ≈ `PROD.D / PROD_UNDIALED.D`. Pre-dial this was ~0.018 (1.58mm / 88.8mm on 2026-08-01). After round 1 it must move to **~0.66**, not stay at 0.018. If it did not move: **stop dialing** (DIAL_RUNBOOK §6 / §7 — silent no-op). Do not compound a no-op.

### Task 4: Render Dev FCLS sheet and score

- [ ] **Step 1: Rebuild into Dev, not Dialed**

```powershell
cd C:\Git\LMQR
uv run python lmanalytics/tracking/transition_report.py `
  -d 20260901 -t NONQM_PSEUDO -p2 PROD --dev -r --sequential
```

Output: `R:\QR\Resi_shared\tracking\Dev\tracking_V1_8_0_NONQM_20260901.xlsx`.

- [ ] **Step 2: Read FCLS 6M ratios**

| Row | Pass if | Round-1 expectation |
|---|---|---|
| `FCLStD` | `\|ratio − 1\| ≤ 0.01` | Should jump from 0.027 toward 1. Softmax may undershoot; that is compound, not failure. |
| `FCLStC` | record only | Will likely fall below 0.95 (share stolen). |
| `FCLStREO` | record only | Same. |
| `FCLStB` | record only | Round 2 input. |

- [ ] **Step 3: Decision (DIAL_RUNBOOK §6)**

- `FCLStD` inside 1% → Round 1 done. Go to Task 5 (B) or Task 6 (promote) per Howard.
- `FCLStD` moved but off → `new_dial = 0.662 / new_6M_ratio`, still `permanent=True`, still both keys, same StartDate. Redeploy Howard clone, MATRIX, Dev report. Cap 4 rounds.
- `FCLStD` did not move → stop. Classify per §7. Do not keep multiplying.

---

## Chunk 3: Round 2 (B) and softmax cleanup

### Task 5: `FCLStoB` only after D has moved

**Files:** same submodel JSON, `FCLStoB.Shock` only

Do not pre-apply 1.807 from the current Undialed book. After Round 1, softmax will have changed B's projected mass. Compute from the **new** Dev report:

`new_B = current_B_shock / new_B_6M_ratio` with `current_B_shock = 1.097` on the first B edit.

Example only (replace with measured 6M): if post-D 6M B ratio is 0.55, `1.097 / 0.55 = 1.995` → `dial_schedule(1.995, permanent=True)` → `"1.995x for 48 1.995x"`.

Same apply snippet as Task 2, loop `("FCLStoB",)` only, `To` must stay `M270P`, `HasSubModel` false.

Then MATRIX + Dev report. If C or REO are now outside 1% **because of softmax**, compound those next, one cell at a time. Do not batch C+REO+B into one commit.

---

## Chunk 4: Promote

### Task 6: Merge to LMSimData main and official Dialed report

Only after `FCLStD` (and any Round-2 rows you touched) are inside 1% on the Dev book.

- [ ] PR / merge `nqm/fclstd-redial-202609` → `C:\Git\LMSimData` `main`
- [ ] `git -C N:\LMSimData pull` — the only permitted operation on the prod clone
- [ ] Gate: prod clone HEAD == merge commit; JSON Details match
- [ ] MATRIX again **without** `SIM2_DATA_SUBDIR` override (workers must read `N:\LMSimData`)
- [ ] Rebuild Dialed (drop `--dev`):

```powershell
cd C:\Git\LMQR
uv run python lmanalytics/tracking/transition_report.py `
  -d 20260901 -t NONQM_PSEUDO -p2 PROD -r --sequential
```

- [ ] Confirm `R:\QR\Resi_shared\tracking\Dialed\tracking_V1_8_0_NONQM_20260901.xlsx` FCLStD 6M ratio inside 1%, and that C/REO did not regress past the point Howard will accept.
- [ ] Risk / position vectors (`dial/RISK_RUNBOOK.md`) are a **separate** job after this. Purpose must not be `PROD` for an experimental risk save — pick a dedicated purpose. Not this plan.

---

## Self-review

- Spec coverage: DIAL_RUNBOOK §0–§7 instantiated; `permanent=True`; fold mapping; softmax; probe-before-compound; git-only deploy; `--dev` until done.
- Trap coverage: `apply_dials_inplace.py` / `update_dials.py` banned for this job; `TRACKING` purpose banned; `N:\` in-place edit banned; version bump banned; Dialed overwrite banned until converge.
- Numbers: 0.662 from Sep Undialed 6M 1.5109; StartDate 20250501; purpose `PROD`; as-of `20260901`.
