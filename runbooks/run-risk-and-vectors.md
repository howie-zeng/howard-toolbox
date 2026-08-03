# Runbook: Run vectors and risk (resi positions)

Two stages: **(1) generate vectors**, then **(2) run risk** off those vectors.
Always launch in **module mode from `C:\Git\LMQR_hecm`** — script mode can resolve the
stale sibling `C:\Git\LMQR` repo.

## 1. Vector run
```bash
python -m lmsimvectors.lm_sim_pub_main \
  -deal_type PositionOnly -with_position \
  -scenarios_batch default+opera \
  -purpose <PURPOSE> -d <YYYYMMDD> \
  -mode batch-ray            # or batch-local
```
- `-mode batch-ray` — distributed on the Ray cluster; **workers `pip install lmsim` from pypy at startup**, so a flaky pypy fails the run (see below).
- `-mode batch-local` — in-process on the submitter (Windows), **no Ray, no pypy** — use when pypy is down or for isolation checks. Sub-bp cross-platform noise vs Linux prod is expected (`0.0001` = 4-decimal storage granularity, not a model change).
- `-position_only` vs `-with_position`, `-bbg_deal_list "DEAL"` for a one-off deal.

## 2. Risk run
```bash
python -m RiskRun.riskrun_main \
  -d <YYYYMMDD> --save \
  --scenarioset <PROD|RATE_HEDGE> \
  --vector_purpose <PURPOSE> \
  --numprocesses 12 --sectors <CRT|MI|JUMBO2_0|HELOC|NONQM|...>
```
- **TRAP:** `--purpose` controls only where risk rows are **saved**; vector **loading** uses `--vector_purpose` (defaults to `PROD_EOD`, and it overrides `JSON_PURPOSE`). Always pass the `--vector_purpose` that matches the vectors you generated, and set `-d` = the **vector rundate** (`FETCH_EXACT` needs an exact match).
- `--scenarioset RATE_HEDGE` = rate scenarios (bull/bear/steepener/flattener/key-rate/parallel); `PROD` = the standard set. Resolved via `getattr(config, name)` in `RiskRun/prodconfig.py`.

## NQM purpose conventions (July 2026 — verify current)
- NQM position vectors → purpose **`NQM_SIM2_V3`** (position_asofdate `20260507`, `default+opera` = 37 scenarios).
- NQM risk results saved under **`NQM_SIM2_V17`**.

## pypy is down / batch-ray keeps failing
`pypy.libremax.com` flaps hard and its healthy window is often shorter than a Ray job, so some worker always lands in a down-window (no client-side retry fixes this). Options: wait for a stable window, or run **`-mode batch-local`** (immune). Never use `file://`-on-shared-drive wheel workarounds. Real fix is infra-side (stabilize the replica or bake lmsim into the worker image).

## If the risk run crashes at startup with a JSON error
`json.decoder.JSONDecodeError ... crt_deal_manager.py:1166` = a collat-mapping JSON on the N: share is malformed (usually git conflict markers deployed by the LMSimData deploy). It crashes **all** sectors. See [onboard-resi-deal](onboard-resi-deal.md) → "N: deploy failure".

## Partial-write trap
A **failed** `batch-ray` job still dribbles the few worker tasks that finished into `libremax.modeljsonresult`. Use a **fresh purpose** for a clean comparison, or clear partials first.

Related: [onboard-resi-deal](onboard-resi-deal.md), [dial-model](dial-model.md).
