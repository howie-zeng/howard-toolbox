# Model Transition Dial Runbook (agent-executable)

Procedure for calibrating a SIM2 submodel's transition rates to tracking actuals by applying
per-transition dials. Product-agnostic; NQM (`V1_8_0_NONQM`, July 2026) is the worked example.
Written for execution by an agent: every step has a verification gate — **do not skip gates;
this process fails silently in specific, known ways.**

---

## 0. Parameters to resolve first

| Parameter | How to find it |
|---|---|
| `DEAL_TYPE` | e.g. `NONQM_PSEUDO`, `STACR_PSEUDO`, `CAS_PSEUDO`, `JUMBO2_0_PSEUDO`, `HELOC_PSEUDO` |
| `SUBMODEL_JSON` | `lmsimvectors/config/sim_config_sim2.py :: SIM2_MODEL_PATHS[DEAL_TYPE]` → path under the LMSimData data root (edit the **`C:\Git\LMSimData`** checkout of that path) |
| `TRACKING_PURPOSE` | the purpose the report reads via `-p2` (e.g. `NQM_SIM2_V7_TRACKING`). Vector `-purpose` must equal it EXACTLY. Never `TRACKING` (batch-ray rewrites it to `PROD` on save) |
| `REPORT` | latest `tracking_*_<yyyymmdd>.xlsx` for the deal type (Dev dir for dev purposes) |
| `STATUS_SHEETS` | the sheets whose transitions you're dialing (from `PROJ_TARGET_LIST_MAP[DEAL_TYPE]` in `lmanalytics/tracking/transition_report.py`) |
| `MODEL_VERSION` | `MODEL_VERSION_MAP[DEAL_TYPE]` — projections are keyed (purpose, model_version) |
| Deployed data clone | the `SIM2_DATA_ROOT_DIR` checkout Ray workers read (e.g. `N:\DevSimData\LMSimData_Howard`). **NEVER edit it directly — `git pull` only** |

## 1. Compute dials from the report

Sheet layout (all products): row 1 carries `3M Error` / `6M Error` / `12M Error` group labels;
row 2 is the header (`Ratio` follows `Abs` under each group); transitions are in column C.

- `dial = 1 / (6M Error Ratio)` per transition row. Ratio = Proj/Actual, so the dial rescales projections to actuals.
- Skip rows with `|ratio − 1| ≤ 0.001` (10bp) and rows with blank ratio (no actual flow — flag them, don't dial).

## 2. Map report rows → JSON transitions (DO NOT assume 1:1)

Report rows aggregate model transitions. Derive the mapping for your product:

1. Enumerate `State/<S>/Transitions/<key>` in the submodel JSON. Each entry has `From`, `To`,
   optional `Shock`. **The `To` field is authoritative for which OUTPUT cell a shock feeds —
   not the key name** (e.g. NQM `FCLStoP` has `To=D`).
2. Reconcile against the report's row vocabulary. Aggregation patterns seen in practice:
   - a report bucket (e.g. `M90P`) fanning out over granular states (`M90..M240`) — apply the
     same dial to every member state's transition;
   - "better/worse" report rows mapping to step-up/step-down granular moves;
   - two model transitions folding into one report cell (`FCLStoD` + `FCLStoP` → reported `D`);
   - sub-state trios sharing a `To` (self/B/W) — see the inert-transition warning below.
3. **Fail fast** if a mapped key is missing, and **flag** (never silently overwrite) any
   existing `Shock` on a target.

NQM worked example (verified):

| Report row | JSON keys |
|---|---|
| `M60t<X>` | `M60to<X>` |
| `M90Pt{C,M30,M60,P,D,FCLS}` | that target across `M90,M120,M150,M180,M210,M240` |
| `M90PtB` / `M90PtW` | the 5 step-better / 5 step-worse granular moves |
| `M90PtM270P` | `M240toM270P` |
| `M270PtM270P` | `M270PtoM270P`+`M270PtoM270PB`+`M270PtoM270PW` (all inert — see §7) |
| `FCLStD` | `FCLStoD` **and** `FCLStoP` (`To=D`) |

## 3. Dial string + StartDate

```python
sys.path.insert(0, r"S:\QR\hzeng\howard-toolbox\dial")
from dial_utils import dial_schedule       # flat x for 48m, 23m linear ramp to 1x
detail = dial_schedule(0.701)              # NOTE: rounds x to 3 DECIMALS (precision floor for tiny dials)
```

- **Permanent vs ramped**: the default schedule ramps back to 1x after 48 months (trailing
  pad `1x`). For STRUCTURAL calibrations (e.g. dials correcting borrowed-model collateral
  mismatch that will not decay), use `dial_schedule(x, permanent=True)` -> `"<x>x for 48 <x>x"`;
  the trailing `Nx` without "for" is the engine's indefinite pad/fill value (LMSim
  `State.cpp:68-76`). NQM's 63 deep-DQ family dials are permanent (`d81cd9f4`); a ramped dial
  silently reverts long-horizon forward projections to the uncalibrated model after the ramp
  (tracking never sees this — only multi-year vectors do). Verified: pad form parses and
  applies identically to the ramped form inside the flat window.
- **StartDate = 12-month lookback from the last observable transition month** (last flat file
  month has no next-month status; e.g. files through 20260701 → last transition May→Jun 2026 →
  StartDate `20250501`). Leave pre-existing shocks (other calibrations) untouched.
- **Gate:** `dial_schedule(x)` of an already-dialed transition must reproduce its existing
  `Detail` string byte-for-byte (format self-test).

## 4. Apply (scripted, never hand-edit)

```python
j["State"][S]["Transitions"][key]["Shock"] = {"StartDate": START, "Detail": dial_schedule(x)}
```

Write back with `json.dumps(j, indent=2, ensure_ascii=False) + "\n"`, re-load to validate,
then `git diff` — expect ONLY Shock-block insertions plus comma-line touches.

## 5. Deploy via git ONLY

```powershell
cd C:\Git\LMSimData
git add data/<PRODUCT>/<submodel>.json && git commit -m "..." && git push origin <branch>
git -C "<deployed-clone>" pull          # the ONLY permitted operation on the deployed clone
```

- **Gate:** deployed clone HEAD == pushed commit; parse the pulled JSON and count/verify shocks.
- If push hangs minutes: git-lfs lock verification without creds. Fix once:
  `git config "lfs.<remote-url>/info/lfs.locksverify" false`

## 6. Rerun vectors, render, validate, iterate

```powershell
# from the LMQR repo root, PYTHONPATH pinned to it
python -m lmsimvectors.lm_sim_pub_main -mode batch-ray -deal_type <DEAL_TYPE> -request_mode matrix -purpose <TRACKING_PURPOSE> -as_of_date <ASOF> -num_of_workers 24 -force_rerun
# ECA only feeds CPR/CDR tabs; status sheets are MATRIX-driven. Run ECA once after convergence.
python lmanalytics/tracking/transition_report.py -d <ASOF> -t <DEAL_TYPE> -p2 <TRACKING_PURPOSE> --dev -r --sequential
```

Archive the pre-dial workbook before the first overwrite. Then per dialed row:

- `|ratio − 1| ≤ ~1%` → done.
- Off but **moved** → compound: `new_dial = current_dial / new_ratio`; redeploy; rerun MATRIX; repeat (converges in 2–4 rounds).
- **Didn't move at all** → STOP dialing it. Verify at the source: query the raw
  `ResiTransitionTracking` cell and compute the effective multiplier vs pre-dial. If a dial
  change produces zero cell movement, the flow is engine-internal or the shock is being
  ignored (classify per §7) — no multiplier will fix it; report it as structural.

**The probe discipline (core algorithm):** treat every unexplained ratio as a measurement
problem first. One dial change = one experiment; read the raw table, compute the effective
multiplier per cell, and only then decide: responsive (iterate) / aggregated (fix the mapping)
/ inert (structural — document and move on).

## 6b. Per-submodel dials (different dials WITHIN one transition)

To dial sub-components of a composite transition differently (e.g. NQM `CtoP`'s
`CtoP_Fixed_Turnover` / `CtoP_Fixed_Refi` / `CtoP_Floating`), nest a Shock inside EACH
`Detail.<SubModel>` child. Semantics (`Simulator.cpp:334-366`):

- **Non-softmax states** (no `NormalizationMethod` on the state, e.g. NQM's C state): each
  child's shock multiplies its own component BEFORE summation — distinct dials compose
  correctly even for loans selecting multiple sub-models (e.g. in-the-money fixed loans get
  `x_turn * turnover + x_refi * refi`; the selector at `SubmodelSelector.cpp:190-203` routes
  ARM->Floating, out-of-money fixed->Turnover, in-the-money fixed->Turnover|Refi).
- **SOFTMAX states** (e.g. M270P): child shocks are applied post-normalization at the
  TRANSITION level, and if multiple selected sub-models carry shocks, **only the last one
  survives** and scales the whole summed transition — distinct per-component dials do NOT
  compose. Check the state's `NormalizationMethod` first.

Calibration note: the tracking report only shows the blended transition (e.g. total `CtP`),
so per-component dial values must come from outside evidence (refi share, S-curve analysis);
the report validates the blend.

## 7. Known engine quirk classes (verified on NQM; check for your product)

1. **Shock placement must match the transition's structure — mismatches are SILENT no-ops.**
   The engine contract (`Transition::parse`, LMSim `src/model/State.cpp:196-219`;
   `SubModel::parse`, `State.cpp:142-144`):
   - `HasSubModel: false` (plain) → Shock at **transition level** (the common case).
   - `HasSubModel: true` (composite `Detail: {Default, Zero, ...}`) → Shock **nested inside
     each `Detail.<SubModel>` child**. STACR's `M270PtoM240` is the working reference: Shock
     inside `Detail.Default`, using the cohort form
     `{"HasCohort": true, "Cohorts": [{"Cohort": "CAS", "StartDate": ..., "Detail": ...}, {"Cohort": "CRT", ...}]}`
     for per-cohort dials.
   A transition-level Shock on a composite loads WITHOUT warning and does nothing (this cost
   NQM 4 calibration rounds on `M270PtoM240` and silently ate the W dial on composite
   `M150toM180`). **Lint every dial target's `HasSubModel` first**, then either nest the Shock
   per the contract, or flatten the composite to the plain shape (also engine-supported; the
   v1.7.6-prod pattern — code-side eligibility gates like `n_pni_owed==9` at `Simulator.cpp:420`
   are preserved). Both NQM and STACR now use the composite + nested-Shock convention (NQM simple form,
   STACR cohort form). The flatten remains a valid fallback pattern (v1.7.6 precedent).
   Note: `Shock::parse` is one shared parser used at BOTH placements (`State.cpp:216-218`
   transition-level, `:142-144` submodel-level) and it supports the cohort form at either
   (`State.cpp:90-95`). Breakage comes from placement mismatch, never from the structure or
   the Shock form itself — so do NOT flatten STACR (its structure already matches its Shock
   placement, and its Zero branches are live conditional logic). NQM was later restored to
   the same composite+nested convention (`ca7d6fed`) — both files now match.
2. **Self-transitions are renormalization residuals** — `IsSelfTrans: true` is skipped and
   overwritten as `1 − Σ(others)` (`Simulator.cpp:324-328, 488-489`); its Shock parses but is
   never consulted, and same-`To` sub-states (B/W trios) fold into the same cell, so the
   self-row ratio cannot be dialed. NQM's `M270PtM270P` rests at ~1.016 for this reason.
3. **3dp rounding floor** — a ×0.018-scale dial has ~5% granularity; split across co-folding
   transitions (e.g. `FCLStoD`/`FCLStoP` at 0.017/0.018) to approximate fractional multipliers.
4. **Output decomposition** — a single config transition (NQM `FCLStoB`, `To=M270P`) may be
   decomposed by the engine into granular output cells; its one shock still scales the
   aggregate correctly. Conversely the output cell is keyed by the declared `To` field, not
   the key name (`FCLStoP` has `To=D` → folds into the reported D cell).
5. **`Zero` / `gam_zero_prob` submodel branches are FUNCTIONAL, not junk** (per the model
   owner): they encode prod's hard-coded conditional zero-probability logic through the
   submodel selector (e.g. "rate = 0 unless `n_pni_owed == 9`", or population-based
   STACR-vs-Agency zeroing). **Do not strip them casually — STACR's copies also carry the
   live cohort Shocks.** Removal/flattening is safe ONLY when the condition is provably
   enforced elsewhere (e.g. the duplicate code-side gate at `Simulator.cpp:420-424` for
   M270P's `n_pni_owed==9`) or the engine force-routes all deal types to one branch
   (`SubmodelSelector.cpp:141-146` for NQM's M150 pair) — and always verify empirically that
   the undialed base flow is unchanged after the edit (NQM check: M240 base flow stayed
   ~0.0081, moving only by the applied dial).

## 8. NQM reference state (2026-07-08, LMSimData nqm_hz @ ca7d6fed)

24/25 dialed transitions within ~1% (`M60tC`, `M270PtM240`, `M270PtFCLS`, `FCLStREO` at
exactly 1.0000). Exceptions: `FCLStD` 1.0035 (3dp floor), `M270PtM270P` 1.0156 (residual —
un-dialable by construction). Config is STACR-consistent: original composite structures with
`Zero`/`gam_zero_prob` conditional-zero branches intact; the `M270PtoM240` dial (0.460) is
NESTED in `Detail.Default`. B/W and the M150 pair carry no shocks (uncalibrated; nested
shocks there would be live and alter untracked internal dynamics).
Engine hardening suggested to the LMSim owner: warn on a `Shock` key placed where the parser
won't read it (transition level on `HasSubModel:true`, or on `IsSelfTrans:true`).
Full pipeline context: LMQR memory notes `nqm-model-dial-calibration` / `nqm-pseudo-pool-tracking-pipeline`.
