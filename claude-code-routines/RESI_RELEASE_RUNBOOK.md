# Resi model release: unload -> vectors -> risk

How a resi model/framework change actually gets to production, written after the
2026-09-01 FIGRE rename + Jumbo/HELOC status-cohort release. Read this before running any
of it — most of the cost that day came from traps in the middle section, not from the work.

Five repos ship together: **LMQR**, **LMSimData**, **LMSim**, **DealManagerServer**,
**JenkinsJobs**.

---

## 1. Merge order, and why

```
LMSim  ->  tag v*  ->  wheel publishes  ->  LMQR pins it  ->  LMQR merge
       ->  LMSimData merge -> git pull the N: deployment
       ->  DealManagerServer merge -> restart the process
       ->  JenkinsJobs merge
```

**LMSim first** whenever LMQR needs to pin a new wheel — LMQR cannot reference a version
that does not exist. Pushing a `v*` tag is what triggers `release-python.yaml`; the job
builds on Windows and Linux runners and publishes to `pypy.libremax.com`.

**Both platform wheels must land.** `uv.lock` pins two URLs per package
(`manylinux_2_39_x86_64` and `win_amd64`); the pin bump cannot resolve until both exist.

**JenkinsJobs last, never before LMQR.** Its daily-job lines call deal types that only
exist on the new LMQR; merging it first turns the 14:20 ET job red.

**DealManagerServer needs a process restart** — the merge alone does nothing, the old
mapping stays in the cached `_deal_manager_instance`.

**The N: LMSimData clone is `git pull` only, never edit in place.** And a new unload column
is silently dropped unless the deployed `file_config/flat_file_config.json` lists it — pull
the deployment *before* re-unloading or the column never reaches the tape.

### Bumping the lmsim pin

Three places: `pyproject.toml`, and two spots in `uv.lock` (the specifier, and the version
plus both wheel URLs). Do **not** just run `uv lock --upgrade-package lmsim` and commit the
result — a uv version mismatch against whoever generated the lock also strips platform
markers off unrelated packages (`ptyprocess`, torch's deps, numpy/pillow/six), which
changes what installs on the Linux runners. Hand-edit the four lines, then confirm with
`uv run --frozen python -c "import lmsim; print(lmsim.__version__)"`.

---

## 2. Refresh the flat files

**Merge first, then unload.** The code that writes the new tapes *is* the code being
released; nothing can generate them beforehand.

```bash
cd C:/Git/LMQR
uv run --frozen python agencydata/wh_lp_update.py \
    --log --fail_on_deal_error --force_unload \
    --deal_type JUMBO2_0 --deal_list "<comma-separated deals>"
```

- **`--deal_list` restricts to the book.** The full product lists are 1,858 deals; the
  portfolio is 68. Get the held set the same way `-deal_type PositionOnly` does:
  `PortfolioLoader().loadPortfolio(pos_date, use_lmsecmaster=True, loadPlaceHolders=True)`
  then `.filterByGroupBy(["P"]).filterByNonzeroMarketValue().filterByApply(lambda p: not iu.isHedge(p))`,
  and read `p.getBloombergDealName()` off `pf.getPositions()`.
- **Leave `--max_workers` at its default (4).** Raising it to 24 was ~4.5x faster and
  produced `('HY000', 'The driver did not supply an error!')` from the Redshift driver.
- **Never pass `--unload_all_collat`.** It sweeps from `first_update_date` and marked 10 of
  35 Jumbo deals failed; the retry without it did 10 of 10.
- `--start_date` takes `YYYYMMDD`, not `YYYY-MM-DD`.

### HELOC is three passes, not one

`--deal_type` takes one product per run, and after the 2026-09-01 FIGRE rename the HELOC
family is **three** distinct deal types (`crt_deal.py:26,35,36`), each its own branch in
`wh_lp_update.py` over its own pool table:

| deal_type | source | branch | pool tables |
|---|---|---|---|
| `HELOC` | CoreLogic LP (non-FIGRE) | `:106` | LP pools |
| `HELOC_PSEUDO` | CoreLogic LP | `:97` | `lib.heloc_pseudo_pool_loanid` |
| `FIGRE_PSEUDO` | dv01 / Figure | `:84` | `lib.figre_pseudo_pool{,_loanid}` (`dv01_pseudo_config.py:3-4`) |

All three are in the supported list at `:172-174`. What used to be called `HELOC_PSEUDO`
was really FIGRE; that swap took effect with the database rename, ahead of any code merge,
so a script or query written before then means the other thing now.

**`FIGRE_PSEUDO` does come through `wh_lp_update`** despite being dv01-sourced. Only *real*
`FIGRE*` deals (`dv01_update.py:45`) and `GRADE*` (`dv01_update_platf.py:62`, plus the one
named `FIGRE 2023-HE1A2`) go through the dv01 scripts instead.

**`FIGRE_PSEUDO` is the exception to the factor-date rule below.** `resi_date_offsets.py:103`
special-cases it to the `HELOC_FIGURE` variant precisely because its source is dv01/Figure
rather than CoreLogic LP, so do not assume it shares plain HELOC's naming.

**A deal missing `he_type` is skipped, not failed.** `wh_lp_update.py:109` logs
`Skipping <deal>: deal not found or he_type missing in HELOC config` and moves on, so a
misconfigured deal leaves its old tape in place and the run still exits 0.
`--fail_on_deal_error` does not catch it. Count the tapes you expect; do not trust the exit
code.

**Deal name does not tell you which model a HELOC deal runs.** Routing is the `is_fig`
column of the HELOC deal CSV (`crt_deal_manager.py:305`, columns
`deal_name,status,he_type,is_fig`), consumed at `lm_sim_pub_main.py:432,440` as
`_heloc_df[_heloc_df.is_fig == "FIG"]`. `FIG` routes to the GRADE model; everything else
(LOC / SEQ / CES / HB) falls through to `MODEL_VERSION_HELOC`. So `GRADE 2026-HB1` is a
*treated* deal despite its name, and was among the largest movers in
`dial/RISK_RUNBOOK.md` worked example 2 -- which is also why a `-deal_type HELOC` risk run
carries its own control group for free (`V2_0_7_HE` and `V2_0_7_GRADE` should move 0.000).

### Which pipeline owns which deal

| Source | Products | Script |
|---|---|---|
| LP / CoreLogic | JUMBO2_0, NONQM, HELOC, ALT_A, SUBPRIME, and the `*_PSEUDO` pools | `agencydata/wh_lp_update.py` |
| dv01 (BigQuery) | everything in `lmdv01/dv01_config.py: DV01_DEAL_NAME_LIST` — FIGRE and ACHM | `lmdv01/dv01_update.py --deal_list "..."` |

A deal in neither list gets no tape and no watermark row, and `wh_lp_update.py` never even
counts it ("19 deals checked" when you passed 23). Before concluding the watermark is
broken, check `lib.poolgroupmap` — if the deal is not mapped to any pool there is no
upstream data and the missing watermark is a symptom, not the cause.

### The factor-date shift

`factor_date_shift_deal_types` (LMSim `FamilyConfig.h`) — CRT, STACR, CAS, MI, JUMBO2_0,
NONQM are named `asofdate = factor_date + 1 month`. HELOC, FIGURE and CES are not. So for
an August factor date, Jumbo tapes are `_20260901` and HELOC tapes are `_20260801`. A
missing `_20260801` Jumbo tape is not a failure and a present one is not success.

### Verifying an unload

Existence proves nothing — twice a file sat at the expected path and was ten days stale.
Check row counts against the pool table, and after any interrupted run check structure:
file ends in a newline, and every row has the header's column count. A tape truncated
mid-write still parses, it just has fewer loans.

---

## 3. Vectors, then risk

Both are Jenkins jobs (`quant-DailyCRTVectors`, `quant-run-risk`) but run fine locally.

```bash
# vectors
uv run --frozen python lmsimvectors/lm_sim_pub_main.py \
  -as_of_date 20260831 -mode batch-ray -request_mode forward_proj \
  -purpose PROD_EOD -scenarios_batch 'default+opera' \
  -deal_type PositionOnly -with_position -position_asofdate 20260831 \
  -ray_cluster staging

# risk -- needs both env vars, riskrun fails without them
VCMO_WRAPPER_SIM='S:\Intex\Vcmowrap\production_x64\' BLPAPI_ROOT='C:\blp\API' \
uv run --frozen python RiskRun/riskrun_main_ray.py \
  --save -m libremax-quants@libremax.com --sectors CRT --scenarioset PROD \
  --ray --ray_cluster staging --ray_strategy task --ray_task_backend eager \
  --vector_purpose PROD_EOD --purpose <TEST_PURPOSE> --date 20260831
```

Risk consumes what vectors saved under `--vector_purpose`, so gate risk on the vectors
**exit code**, not merely sequence it afterwards.

### Clusters

`lmray/config.py: CLUSTERS` — `east` (288 workers, `task_retries=3`), `staging`
(192, `task_retries=64`), `east-spot` (393, 64).

Vectors failed twice on `east` with `0/592 results`: workers were still downloading pyarrow
and numpy while the autoscaler reaped idle nodes, and 3 retries was not enough. The same run
succeeded first try on `staging`, whose config comment says outright that 192 exists to stop
Ray asking the autoscaler for an impossible shape. **Prefer staging; if a run dies with
`RaySystemError: Failed to startup worker after retrying 5 times`, that is infrastructure,
not the model — nothing in the 434-line cluster log mentioned tapes or deal types.**

**Staging skips the lmsim version check.** `lm_sim_pub_main.py` passes
`importlib.metadata.version("lmsim") if args.ray_cluster != "staging" else None`. A local /
cluster version mismatch will not raise — it will silently compute with a different engine.
Ask what the cluster runs, and match it for the run without dirtying the repo:

```bash
uv run --frozen --index "https://pypy.libremax.com/simple/" \
  --with "lmsim==2.7.3.dev16+g330f602bb" python lmsimvectors/lm_sim_pub_main.py ...
```

`--with` alone fails (`lmsim was not found in the package registry`) because it does not
inherit `[tool.uv.sources]` — the `--index` flag is required. This leaves `git status`
clean, unlike `uv add`.

### Where risk results go, and the purpose trap

`fundstudio.dbo.riskdb_hist` — note the database is **fundstudio**, not libremax, and the
date column is `as_of_date` (plus `run_date`), not `riskdate`. There is no run_id column, so
trace a run by its cusips.

**`--sectors` does not decide the save purpose.** `riskrunner.py:1104`:

```python
risk_df["purpose"] = risk_df.cusip.apply(lambda c: self._save_purpose[RiskRunner.CUSIP_SECTOR[c]])
```

The purpose comes from each cusip's *own* sector via `prodconfig.py: SAVE_PURPOSE`;
`--sectors` only chooses which cusips to load. Running `--sectors RMBS_MODEL` priced 46
GNMA HECM cusips and wrote them to `PROD_RMBS` (`SAVE_PURPOSE["HECM"]`), touching no
Jumbo/HELOC/NQM at all. `SAVE_PURPOSE["RMBS MODEL"]` is `RMBS_MODEL_TEST`, which has never
had a row — that sector is not productionised. **Resi model positions live under
`SAVE_PURPOSE["CRT"] = "QRPRODWRAPPERWITHSETTLE_CRT"`, so use `--sectors CRT`.**

**Always pass `--purpose <something>_TEST` on a validation run.** Without it, `--sectors CRT`
overwrites the prod CRT rows — destroying both production risk and the baseline you wanted
to compare against. `--purpose` overrides every sector (`riskrun_main.py:444`).

### Comparing new risk against prod

Same date, same cusips, cross purpose. Date-over-date is the wrong axis: a test purpose has
no history, and comparing prod 8/31 to prod 8/28 shows market movement rather than the
effect of the change.

```sql
DECLARE @date VARCHAR(8) = '20260831';
select r1.scenarios, r1.as_of_date, p.LmxAssetSubtype, p.Description, r1.cusip, p.couponrate
     , r1.calc_price, r1.scen_yield, r1.e_spread, r1.wal, r1.eff_dur, r1.spread_dur
     , r1.defaults, r1.cum_loss, r1.loss_severity, r1.bond_writedown
     , r2.scen_yield, r2.e_spread, r2.wal, r2.eff_dur, r2.spread_dur
     , r2.defaults, r2.cum_loss, r2.loss_severity, r2.bond_writedown
from fundstudio.dbo.riskdb_hist r1
join fundstudio.dbo.riskdb_hist r2
  on r1.as_of_date = r2.as_of_date and r1.cusip = r2.cusip and r1.scenarios = r2.scenarios
join (select distinct securityreference, description, LmxAssetSubtype, LmxAssetStructure, couponrate
      from Libremax.dbo.T_FS_portfolio where positiondate = @date) p
  on r1.cusip = p.securityreference
where r1.as_of_date = @date
  and r1.purpose = 'QRPRODWRAPPERWITHSETTLE_CRT_TEST'
  and r2.purpose = 'QRPRODWRAPPERWITHSETTLE_CRT'
  and r1.scenarios = 'BASEPRICE'
order by p.LmxAssetSubtype, p.Description;
```

Group the diffs by `LmxAssetSubtype`. A subtype the release did not touch should be a flat
zero row; if unrelated subtypes move, suspect an lmsim version mismatch before suspecting
the model change. Only promote to the prod purpose once the diff is small.

---

## 4. Traps that cost real time

**`pkill -f` does not kill anything launched with `uv run`.** Each launch is three
processes — `uv.exe`, `.venv\Scripts\python.exe`, and a uv-managed cpython under
`AppData\Roaming\uv\python\` — and the pattern reaches none of them, while `pkill` still
exits 0. On 2026-09-01 this silently stacked five concurrent `wh_lp_update.py` runs and
froze the Redshift cluster; each "stopped" report was wrong. Kill from PowerShell by PID,
loop until the count is zero (it took four rounds), and only then say it is stopped:

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='uv.exe'" |
  Where-Object { $_.CommandLine -match '<script>' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Killing the local client does **not** cancel the Ray job it submitted — that keeps running
on the cluster. Cancel Redshift sessions one statement per call (`CANCEL <pid>;`), because
`executeSQL` silently discards errors after the first statement in a batch.

**`ever_fcls` in dv01 cannot follow the CRT definition.** STACR/CAS/SCRT all derive it from
a foreclosure-referral date (`foreclosurerefdt IS NOT NULL`, spelled out in
`STACR_VARS["foreclosure_condition"]`), and copying that into dv01 looks consistent — but
`loan_foreclosure_date` is populated for **zero** FIGRE and ACHM loans, so the flag would be
identically 0. Use the status instead, and exclude REO: 4 of 6 REO loans never had
Foreclosure status, so including it flags deed-in-lieu loans that never foreclosed.

```sql
max(case when loan_status = 'Foreclosure' then 1 else 0 end)
  over (partition by dv01_id order by as_of_date rows between unbounded preceding and current row)
```

Use raw `loan_status`, not `dlq_status`: `SQL_UNLOAD_FIGURE_CORE` substitutes
`{status_mapping}`, which for FIGRE collapses `FCLS/REO/M180+` into `D180`, so `dlq_status`
is never `'FCLS'` there. FIGRE ends up 0 regardless because its `month_in_d180 < 1` filter
drops foreclosed loans from the tape entirely — which is the desired behaviour, reached
without a special case.

Adding a column to a dv01 tape takes **five** edits, not one: compute and expose it in
*both* `SQL_UNLOAD_DV01_CORE` (used by everything except FIGRE) and `SQL_UNLOAD_FIGURE_CORE`
(`deal_name.startswith("FIGRE")`), then name it in `SQL_UNLOAD_DV01`'s outer column list. A
column missing from that last list never reaches the file.

**Verify a derived column against data, not against code.** Both `ever_fcls` mistakes above
came from reasoning about consistency with the other configs; both were caught by querying
how often the field is actually populated.

**The pool table is the only non-git state.** Reverting code does not restore
`lib.heloc_pseudo_pool_loanid`; that needs `wh_nqm_pseudo_sample.py --rebuild`, which drops
both pool tables and is not resumable.
