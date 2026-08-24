# Runbook: Dial a SIM2 model to tracking

**Canonical, agent-executable procedure: [`../dial/DIAL_RUNBOOK.md`](../dial/DIAL_RUNBOOK.md)** (13 KB, every step gated).
**After the dial converges — vectors + risk to diff: [`../dial/RISK_RUNBOOK.md`](../dial/RISK_RUNBOOK.md)** (verified commands + the flags that silently produce zero jobs).
**Tooling:** `../dial/update_dials.py` (generate-spec / apply-spec), `../dial/dial_utils.py`, `../dial/run.py` (dial-ratio Excel). See the `dial/` section of the repo README.

This page is the 60-second orientation + trap checklist. For the real steps, use `DIAL_RUNBOOK.md`.

## The loop
1. `dial = 1 / (6-month error ratio)` per status-sheet transition (from the latest `tracking_*.xlsx`).
2. Write it as a `Shock: {StartDate, Detail: dial_schedule(x)}` at `State/<From>/Transitions/<key>` in the submodel JSON (e.g. `C:\Git\LMSimData\data\NONQM\nonqm_v1.8.0_submodel.json`). `dial_utils.dial_schedule` = flat 48m + 23m ramp, 3dp. `StartDate` = 12m lookback from the last observable transition.
3. **Deploy via git only** (edit `C:\Git\LMSimData` → push → `git pull` in the deployed clone / N: fork — **never edit the deployed clone directly**).
4. Re-run MATRIX (batch-ray `force_rerun`) + render the report; iterate `new = old / new_ratio`.

## Engine traps (these fail *silently* — always verify)
- **Shock placement must match transition structure.** Plain (`HasSubModel:false`) → Shock at transition level. Composite (`HasSubModel:true`, `Detail:{Default,Zero,…}`) → Shock **nested inside each `Detail.<SubModel>`**. A transition-level shock on a composite loads with no warning and does **nothing**. **Lint every target's `HasSubModel` before dialing.**
- **Self-transitions (`IsSelfTrans:true`)** are residuals `1−Σ(others)` — shocks parse but are never consulted (e.g. `M270PtM270P` rests ~1.016, un-dialable).
- **Report rows aggregate model transitions** — cells are keyed by the `To` field, not key names; `FCLStoP` has `To=D` so its dial folds into reported `FCLStD`.
- **3dp rounding floor** — tiny dials (×0.018) need values split across co-folding transitions.
- After any change, verify the **effective multiplier from raw `ResiTransitionTracking`**, not just the workbook ratio.
- `Zero`/`gam_zero_prob` submodel branches are **functional** (encode prod's conditional zero-prob logic) — don't strip casually.

## NQM state (July 2026, permanent dials)
Deep-DQ family dials are `permanent=True` (`"<x>x for 48 <x>x"`) because the family runs on borrowed STACR GAMs (structural mismatch); M30 keeps its ramp. Purposes: `NQM_SIM2_V8` undialed, `NQM_SIM2_V9` dialed+ramped, `NQM_SIM2_V9_DIALED` dialed+permanent.

Related: [run-risk-and-vectors](run-risk-and-vectors.md), [onboard-resi-deal](onboard-resi-deal.md).
