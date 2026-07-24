# Runbook: Onboard / fix a resi deal in the vector-risk pipeline

A deal only produces vectors if it's present in the right layers. When a deal fails
the vector/risk run, identify the error and fix the matching layer.

## The 4 layers
1. **Deal registry — `lmdeallist` table** (authoritative in `lmdb`, replicated to `padb`/`libremax`). Auto-populated by `resi_deal_manager/update.py` from CoreLogic (`lps.lp_cover`), DV01 BigQuery (FIGRE/ACHM→HELOC, SCRT), STACR, CAS, MI. New deals auto-approved.
2. **Deal-list txt** — `N:/LMSimData/deal_list/{jumbo2.0,non_qm,heloc,subprime,alt_a,scrt}.txt`.
3. **Collat mapping JSON** — `N:/LMSimData/init_config/{deal_collat_mapping(CRT+SCRT),nonqm_tape_,jumbo2_0_tape_,heloc_tape_}...json`. Entry = `bbg_deal_name`, `collat.id` (=pool_id, drives flat-file lookup), optional `intex_deal_name` (Intex cashflows only — **not** needed for vectors; safe null), `collat.detail.path`.
4. **Flat files** — `N:/FlatFilesMonthly/{CRT,Jumbo2,NQM,HELOC}Monthly/{pool_id}_{YYYYMMDD}.txt`.

## Resolution order (`getCRTDeal`)
`nonqm_tape → jumbo_tape → heloc_tape → crt → pseudo → legacy Libremax..PoolGroupMap (overrides all)`.
Fallback for a deal in the txt list but not the JSON: `load_deal_from_list → data_util.getLPDealUpdateDF` (`lps.lp_dyn ⋈ lib.poolgroupmap`).
**A deal resolves iff its pool_id is in one of: the JSON, `lib.poolgroupmap`, or SQL-Server PoolGroupMap.** No name-strip fallback except SCRT.

## Failure taxonomy (`lmsimvectors/lm_sim_pub_main.py` — all graceful skips)
| log line | meaning | fix |
|---|---|---|
| `deal no mapping` (:367) | `getCRTDeal` returned None — in none of the dicts | add a collat-mapping JSON entry (or ensure it's in poolgroupmap) |
| `no collat for deal` (:386) | mapped, but no `{pool_id}_*.txt` on disk | generate the flat file |
| `no SIM2 pool files` / `Could not find pool file` (model_run.py) | no file within the **12-month lookback** from the collat date | generate a recent flat file |

## Flat-file generation per product (writes to prod N: share — never run unilaterally)
- **JUMBO2_0 / NONQM / SUBPRIME / ALT_A / HELOC(CoreLogic) / SCRT:**
  `python -m agencydata.wh_lp_update --deal_type <T> [--deal_list "DEAL"]` (Redshift unload → S3 → N:; also writes stats/trans DBs). Jenkins `quant-DailySimDataUpdateJumbo`. SCRT files go to CRTMonthly and SCRT is **not** vector-run.
- **HELOC FIGRE/ACHM (DV01-sourced — NOT in poolgroupmap):**
  `python -m lmdv01.dv01_update_platf --deal_list "FIGRE 2025-FL1,FIGRE 2025-PF1"` (DV01 BigQuery → N:, skips months already on disk unless `--force_unload`). Jenkins `quant-DailySimDataUpdateDV01`. **`wh_lp_update --deal_type HELOC` does NOT work for FIGRE/ACHM** (returns 0 rows — they're not in `lib.poolgroupmap`). In `dv01_update.py` FIGRE deals skip the flatfile step (stats only); generation lives in `dv01_update_platf.py::update_flatfile_dv01`, and the deal must be in `lmdv01/dv01_config_platf.py DV01_DEAL_NAME_LIST`. If the newest month unloads "has no loans", DV01's loan-level data for that month isn't complete yet — the prior month within the 12-mo lookback still resolves.

## N: deploy failure (why the risk run crashed July 2026)
`N:/LMSimData` is a **live git working copy**; Jenkins `quant-deploy-lmsimdata` syncs it to `main` via `git stash push init_config/*_mapping.json → restore → clean → pull → stash pop` (the stash preserves desk edits made directly on N:). **When the same mapping entry is added both directly on N: AND via a merged PR, the `stash pop` conflicts → the job exits 1 and leaves git conflict markers in the JSON on N:** → invalid JSON → `CRTDealManager.__init__` crashes at `json.loads` → the risk/vector run dies for **all** sectors.
- **Fix:** reconcile N: to `origin/main` (`git reset --hard origin/main`), recover any unique deals stranded in the stashes into `main` via PR (they're absent from both `main` and the N: working tree — `git show 'stash@{N}:<path>'` to extract), then drop redundant stashes.
- **Process rule:** mapping edits go through PRs **or** direct-on-N:, **not both** — that collision is the whole problem.
- **SMB gotchas:** git ops on the N: share are slow (index refresh; a reset can take minutes — run in background); a killed op leaves `.git/index.lock` to `rm`; use forward-slash UNC (`//lmaxquantstorage.file.core.windows.net/lmaxqr/LMSimData`) + `-c safe.directory='*'`. Never write N: without asking; destructive git on N: is gated by the safety classifier.

Related: [run-risk-and-vectors](run-risk-and-vectors.md), [release-lmsim-model](release-lmsim-model.md).
