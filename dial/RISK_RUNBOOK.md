# Runbook: Vectors + Risk for a dial change (agent-executable)

Companion to [`DIAL_RUNBOOK.md`](DIAL_RUNBOOK.md). Once a dial is applied and tracking has
converged, this is how you produce the risk numbers to diff. Every command below was run
end-to-end and verified on 2026-08-11 (STACR FCLS/REO 12M dial, as-of 20260810).

Two stages: **vectors** first, then **risk** off those vectors. The risk stage reads vectors by
`purpose`, so the two must agree.

---

## 0. Environment — get this wrong and nothing else matters

**Always `uv run` from `C:\Git\LMQR`.** Never the conda `pyprod` python.

```powershell
cd C:\Git\LMQR
uv run python -m lmsimvectors.lm_sim_pub_main ...
```

`lm_sim_pub_main.py:1268` builds the Ray runtime env as
`runtime_env["pip"] = [f"lmsim=={importlib.metadata.version('lmsim')}"]` — it pins whatever lmsim
the *launching interpreter* has. The conda env carries an lmsim that has been pulled from
`pypy.libremax.com`, so the Ray job dies ~30s after submission with
`runtime_env setup failed ... No matching distribution found for lmsim==<old>`, and the
cluster-side job log is **0 bytes**. The real error is only at
`https://lmsim-ray.qr.libremax.com/api/jobs/<raysubmit_id>` in the `message` field — read that
before touching code or paths when a job fails within a minute.

**To make the run see dialed models**, `SIM2_DATA_ROOT_DIR` must point at the clone holding the
dial branch. `C:\Git\LMQR` defaults to `N:\LMSimData` (shared prod). For a dev-clone run, edit
`lmsimvectors/config/sim_config_sim2.py:6` locally (uncommitted):

```python
SIM2_DATA_ROOT_DIR = str(paths.n_drive / "DevSimData" / "LMSimData_Howard")
```

Verify it resolves to the dialed file before spending an hour:

```powershell
uv run python -c "from lmsimvectors.config import sim_config_sim2 as c; print(c.SIM2_MODEL_PATHS['STACR_PSEUDO'])"
```

> `C:\Git\LMQR_prod` already carries this same override as an uncommitted edit.
> `C:\Git\LMQR_hecm` does **not** — it points at `N:\LMSimData`, so it will silently use prod
> (undialed) models.

---

## 1. Vector run

```powershell
uv run python -m lmsimvectors.lm_sim_pub_main `
  -as_of_date <YYYYMMDD> -mode batch-ray -request_mode forward_proj `
  -purpose <PURPOSE> -scenarios_batch "default+opera" `
  -deal_type <CRT|NONQM|JUMBO2_0|...> -position_only -position_asofdate <YYYYMMDD>
```

**`-position_asofdate` is REQUIRED.** Without it the run loads the portfolio, logs deal data, and
then exits with `ERROR: No jobs to run, check input data` — because
`_apply_position_filters` (`lm_sim_pub_main.py:939-941`) returns immediately:

```python
if args.position_asofdate is None or not (args.position_only or args.with_position or args.exclude_position):
    return deal_list, hecm_universe_df
```

and for a position run `_select_resi_deals` (`:893-897`) never populates `deal_list` itself
(`if args.deal_type != "PositionOnly"` skips the fill), so the list stays empty → zero jobs.

**Other flag notes**

- `-request_mode forward_proj` — needed for position/risk vectors. (MATRIX is the *tracking*
  mode, used by `DIAL_RUNBOOK.md` §6, not here.)
- Use `-deal_type <TYPE> -position_only`, **not** `-deal_type PositionOnly -with_position`.
- The team runbook `runbooks/run-risk-and-vectors.md` says `-d <date>`; that flag does not exist
  on the vector script. It is `-as_of_date`.
- `-num_of_workers` is ignored in ECA/MATRIX modes — `RAY_NUMBER_OF_CPUS` wins (`:379`).
- `-bbg_deal_list "A,B"` overrides deal selection entirely (`_select_resi_deals` first branch),
  use it to narrow further than `-deal_type`.

**Gate:** the run prints a deal-summary table before submitting. Read it — it is the only place
you see what is actually being run. `-deal_type CRT` is broader than STACR; a real portfolio
pulled in CAS, SCRT, and one STACR deal.

Expect `ERROR: no collat for deal: <X>` for individual deals — non-fatal, that deal is dropped.

Success looks like:

```
All deals succeeded (222/222). Overall success rate: 100.00%
LMSim Vector Process Completed Successfully
```

---

## 2. Risk run

```powershell
uv run python -m RiskRun.riskrun_main `
  -d <YYYYMMDD> --scenarioset <RATE_HEDGE|PROD> `
  -c <CUSIP,CUSIP,...> --save `
  --purpose <PURPOSE> --numprocesses 8 --vector_purpose <PURPOSE>
```

**TRAP:** `--purpose` controls only where risk rows are **saved**; vector **loading** uses
`--vector_purpose`, which defaults to `PROD_EOD` (`RiskRun/prodconfig.py:24`). Pass it
explicitly and match it to stage 1, or you will silently price against production vectors and
the diff will show nothing.

`-d` here **is** correct (`riskrun_main.py:346`) — unlike the vector script.

`--sectors <CLO|CRE|CON_ABS|CRT|RMBS_STATIC|RMBS_MODEL|PROXY|HECM|CMBS>` filters by sector
instead of `-c`; the two are alternative ways to scope the portfolio.

---

## 3. Verify before diffing

**Risk rows** land in `fundstudio.dbo.riskdb_hist` (`riskrunner.py:955,969-970`, DB from
`GALILEO_CLIENT_CONFIG.risk_database` = `lmdb.RiskDBEnum.FUND_STUDIO`) — *not* the `Libremax` DB:

```python
from lmdata import lmdb
import pandas as pd
eng = lmdb.get_conn(lmdb.RiskDBEnum.FUND_STUDIO)
pd.read_sql("SELECT purpose, cusip, COUNT(*) scen_rows FROM dbo.riskdb_hist "
            "WHERE purpose='<PURPOSE>' GROUP BY purpose, cusip ORDER BY cusip", eng)
```

**Vectors**: the practical check is that the risk stage found them. A CUSIP whose deal was not in
stage 1 fails loudly per scenario:

```
Couldn't retrieve model for <DEAL>, scen Base, on <DATE>, purpose <PURPOSE>: Model vector is empty/doesnt exist
```

followed by a cascade of `KeyError: 'BASEPRICE'` for every later scenario. That is **one** root
cause echoing ~40 times, not 40 problems. Other CUSIPs are unaffected — risk processes them
independently.

**Map CUSIPs to deals first** so you know which ones stage 1 must cover:

```python
import datetime as dt
import lmutils.instrumentutils as iu
from portfolio.portfolioloader import PortfolioLoader
pf = (PortfolioLoader().loadPortfolio(dt.date(Y, M, D), use_lmsecmaster=True, loadPlaceHolders=True)
        .filterByGroupBy(['P']).filterByNonzeroMarketValue()
        .filterByApply(lambda p: not iu.isHedge(p)).sort())
for p in pf.getPositions():                     # Portfolio is NOT iterable; use getPositions()
    print(p.getSecurityReference(), p.getBloombergDealName(), p.getDescription())
```

---

## 4. Making the diff mean something

- **Use a fresh purpose.** A *failed* batch-ray job still dribbles finished worker tasks into the
  results table, so a reused purpose can mix runs.
- **Both sides must differ only in the dial.** Running the new dial against production risk as
  baseline also folds in engine-version differences (a `uv sync` can move `lmsim`), rate data, and
  anything else that changed. For a clean read, run *both* sides here: check the deployed clone
  back to `main`, rerun stages 1–2 under a second purpose, diff those two.
- **Cohorts are broader than their names.** A dial on the STACR submodel's `CRT` cohort also moves
  Fannie CAS-shelf **SBT** deals and FNM pseudo pools — see
  [`../runbooks/dial-model.md`](../runbooks/dial-model.md) and the `stacr-crt-cohort-not-stacr-only`
  memory note. Scoping the risk run to "just STACR" hides exactly the collateral no tracking report
  watches. Keep the non-dialed cohort's deals in the run as a control: they should show ~zero
  change, and if they move, cohort isolation is not working.

---

## Worked example (2026-08-11, STACR FCLS/REO 12M dial, as-of 20260810)

```powershell
cd C:\Git\LMQR
uv run python -m lmsimvectors.lm_sim_pub_main -as_of_date 20260810 -mode batch-ray `
  -request_mode forward_proj -purpose HZ_STACR_DIAL12M -scenarios_batch "default+opera" `
  -deal_type CRT -position_only -position_asofdate 20260810

uv run python -m RiskRun.riskrun_main -d 20260810 --scenarioset RATE_HEDGE `
  -c 20754PAD2,20753VDL9,80290CBP8,20754RAJ5,20754KAJ0,20754MAL1,35564KUL1,95758BBV0 `
  --save --purpose HZ_STACR_DIAL12M --numprocesses 8 --vector_purpose HZ_STACR_DIAL12M
```

Vectors: 6 deals × 37 scenarios = 222/222 in ~12 min. Deals submitted were `CAS 2019-HRP1`,
`CAS 2020-SBT1`, `CAS 2021-R01`, `CAS 2021-R02`, `CAS 2022-R07`, `STACR 2022-HQA1`.

Risk: 7/8 CUSIPs × 33 scenarios = 231 rows in ~145s. `95758BBV0` (WAL 2022-CL4) failed — its deal
is not in the CRT position list, so it had no vectors.

Related: [`DIAL_RUNBOOK.md`](DIAL_RUNBOOK.md), [`../runbooks/dial-model.md`](../runbooks/dial-model.md),
[`../runbooks/run-risk-and-vectors.md`](../runbooks/run-risk-and-vectors.md).
