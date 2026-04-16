## Learned User Preferences

- When asked to update mappings or lookup tables: ONLY APPEND new entries. Never delete existing entries unless explicitly instructed.
- Use StrReplace / edit tools directly for file modifications. Do not write Python helper scripts as workarounds for whitespace or tab-character difficulties.
- Save implementation plans to `.cursor/plans/` in the workspace so they persist across sessions.
- When translating R-to-C++ servicer mappings: R maps canonical → [variants]; C++ maps variant → canonical (inverted direction).
- C++ canonical servicer names use the no-space convention (e.g., `WELLSFARGO`, `JPMORGANCHASE`, `UNITEDWHOLESALE`).
- Do NOT add unit test files unless explicitly asked. LLPA verification is done via R tieout, not C++ gtest.
- Do NOT touch existing `LLPAManager` code when adding new LLPA GAM code. Only add new code alongside it, and prefer a generic evaluator layer (`LlpaEvaluator` / `GamLlpaEvaluator`) over NQM-specific public wrapper names unless behavior is truly product-specific.
- For NQM state-`C` SOFTMAX/shock work, keep `CtoP_Floating` as a single model; fixed `CtoP` turnover/refi should aggregate into one raw `CtoP` probability and receive one combined fixed `CtoP` shock post-SOFTMAX, while the two fixed leaves keep identical `Shock` blocks.
- For future NONQM parity work, do not reuse `_new_servicer`; add a dedicated asset field for `servicer_curr`.
- StrReplace/patch tools can silently strip UTF-8 BOM from XML `.vcxproj` files. Always verify BOM preservation after editing.
- When patching `.vcxproj.filters`, avoid duplicating existing `<ItemGroup>` blocks.

## Learned Workspace Facts

- `CRT_SERVICER_MAP` in `StacrLoader.cpp` maps raw servicer name variants to canonical names (all-caps, no spaces). The canonical name is stored in `_crt_servicer` and fed into `CategoricalVariableSelector` as a GAM model variable; the file also contains embedded literal tab characters in some servicer name string literals, so match carefully with edit tools.
- `AsOfQuarter::_getInput` needs an underscore separator between the variable name and the quarter value (e.g., `asofquarter_2020Q3`). Without it, coefficient lookups silently return 0.0.
- `LLPAManager` has known latent issues: LTV index rounding mismatch (load truncates, lookup rounds) and no bounds checking on `occ_code`/`fico_code` in the public inline overload.
- NQM LLPA implementation plans at `.cursor/plans/`: `nqm_llpa_gam_merged.plan.md` (merged, supersedes original), `nqm_1.8.0_handoff.md` (completed/pending work summary). LMSim2-specific plan at `nqm_llpa_gam_in_lmsim2_039ac43e.plan.md`. Uses a GAM model with NQM-specific scoring and time decay.
- `_upd_ltv` may differ from `_ltv` at t=0 due to HPI adjustment. Always use `orig_ltv` for `orig_llpa` and `upd_ltv` for `curr_llpa`. In LMSim2, this requires two GAM instances because `GAM::build_indices()` binds accessor pointers and fixed/varying classification at load time — one GAM can't serve both `orig_ltv` (static) and `upd_ltv` (varying). After loading, override the LTV curve's `asset_field` to `"orig_ltv"` on the orig copy and call `build_indices()` again.
- Avoid process-level singletons in Ray worker-reuse contexts — they cause silent cross-contamination between deal types. Legacy `LLPAManager::getInstance()` was fixed with `std::mutex`-guarded map keyed by CSV path; LMSim2 uses task-scoped API objects instead.
- LLPA evaluator architecture: legacy LMSim uses `LLPAGamEvaluator` base class + `NqmLLPAEvaluator` subclass. In LMSim2, keep CRT/Jumbo on `LLPAManager` but put LLPA GAM paths behind a generic `LlpaEvaluator` / `GamLlpaEvaluator` layer; reuse the built-in `GAM` engine directly, keep config key `NqmLlpaGam`, use two GAM copies for orig/curr LTV, and apply the 24-month `orig_date_num` decay outside `GAM`.
- LLPA downstream spread pipeline (`_sato_llpa_lag0`, `_incentive_spread_llpa_lag0`, `_burnout_spread_llpa_lag0`) is LLPA-source-agnostic, but `incentive_spread_llpa_lag0` for CRT/Jumbo is computed in shared `TimeDependentState.cpp` helpers, not in `LLPAManager`; any evaluator-backed NONQM path must repopulate derived spread/burnout fields after assigning `_curr_llpa`. NQM `inc_fade_period` = 60 months vs 36 for CRT/Jumbo.
- `StacrLoader.cpp` M90 delinquency path calls `Poco::strToInt(dlnq_status_code, num_pmt_owed, 10)` without the empty-string guard used in REO. An empty `current_loan_delinquency_status` throws `Poco::SyntaxException` instead of preserving the default `num_pmt_owed = 3`.
- NQM LLPA is loader-driven: the flat-file unload may emit `doc_type` as the tape alias for in-memory `doc_map`; loader also reads `doc_group` and `dscr_ratio` and computes `_orig_date_num`; `doc_detail` is NOT used by the LLPA model (PP split derived from `doc_map`). Falls back `dscr_ratio` to `1.0` when missing/nonpositive.
- LMSim2 is a greenfield C++23 rewrite of LMSim with 3-way state decomposition (`AssetData`/`TimeDependentState`/`TransitionState`), fixed/varying GAM score caching, memory-mapped file parsing, and a 4-phase pipeline (load/simulate/format/save). Currently supports CRT, Jumbo, MI; NONQM has partial code across `AssetData`, `TransitionState`, `TimeDependentState`, `FieldAccessor`, and `SeverityCalculator` but is not fully migrated. Architecture documented at `LMSim2/docs/architecture.md`.
- `foreign_national` flat-file codes map `1 -> Foreign_National`, `2 -> Perm_Resident`, `3 -> NonPerm_Resident`, else `US_Citizen`; NONQM model token `foreign_natForeign` still expects `Foreign_National` normalized to `Foreign` on the C++ side.
