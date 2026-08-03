# Candidate Submission Deep Review

**Assignment:** Loan-level one-month Non-QM prepayment model  
**Initial review:** 2026-07-17; **final intake revision:** 2026-07-20  
**Canonical candidate root:** `S:\QR\Hiring\HS_JrModeler\Test Submissions`  
**Rubric:** `interview_notes/candidate_model_evaluation_rubric.md`

> **Static-review boundary.** No candidate model was run, refit, imported, or reproduced. No candidate notebook, test, macro, binary, setup command, serialized PKL/joblib object, or external link was executed or opened. The review used static source/notebook/Office/PDF inspection and independent read-only checks of submitted CSV, JSON, and Parquet artifacts. Candidate names are used only to identify submission packages; private/contact data, protected-characteristic inferences, and authorship inferences are excluded.

**Metric evidence labels used throughout**

- **Independently verified from submitted output:** read directly from a submitted machine-readable result and arithmetically reconciled where possible; this does not mean the model was rerun.
- **Candidate-reported only:** present in a deck, memo, notebook output, or summary but not reproducible from submitted prediction-level evidence.
- **Inconsistent:** conflicting values or populations across submitted artifacts.
- **Not available:** not submitted or not calculable without running candidate code.

# 1. Executive summary

There is no unconditional advance. The highest recommendation is **Conditional interview** for Charlotte, Carlos, Qin, Peter, Daniel, Karan, and Xin. David and Thomas are discussion-only reserves; the remaining 11 submissions are rejects. The shared future-modification leak affects Charlotte, Carlos, Qin, Peter, Karan, Xin, David, Waner, Shravant, Sanskriti, and Alan.

There are **no Pass, Advance, or Strong Advance candidates**. AUCs from different windows, universes, targets, and preprocessing regimes are not directly comparable and are not used to rank candidates.

Final disposition counts: **0 Pass, 7 Conditional interview, 2 Discuss, 11 Reject** across 20 candidates.

| Rank | Candidate | Hard gate | Score | Recommendation | Decisive conclusion |
|---:|---|---|---:|---|---|
| 1 | Charlotte Liu | Fail | 80 | Conditional interview | Best overall package, but raw `mod` leaks future modification status into both final models |
| 2 | Carlos Rivas | Fail | 72 | Conditional interview | Exact target and independently auditable final predictions; modification leakage and final-period exposure |
| 3 | Qin (Allan) Dai | Fail overall | 73 | Conditional interview | Strong baseline calibration, but baseline itself uses future modification status; external blend adds revised-history/test-reuse failures |
| 4 | Peter Zhong | Fail | 71 | Conditional interview | Excellent target and auditability, but modification leakage and explicitly post-selection 2024–2026 evidence |
| 5 | Daniel Li | Fail | 71 | Conditional interview | Strong GLM/software work; future-dependent whole-loan quarantine changes earlier sample membership |
| 6 | Karan Allagh | Fail | 68 | Conditional interview | Excellent target and genuine constrained challenger; future modification, same-month HPI, and OOT reuse |
| 7 | Xin Xu | Fail | 65 | Conditional interview | Excellent target and broad feature work; future modification fields and repeated test scoring are material |
| 8 | David Shunwei Du | Fail | 73 | Discuss | Strong frozen-test evidence and engineering, but raw future modification status fails PIT |
| 9 | Thomas Kidu | Fail | 65 | Discuss | Strong traceability and exact target; PIT is unproven and final test influenced model decisions |
| 10 | Shravant Srinivas | Fail | 66 | Reject | Exact target and credible methods, but multiple foundational PIT/preprocessing/final-test failures override score |
| 11 | Waner (Arina) Zheng | Fail | 61 | Reject | Exact target and disciplined folds, but modification leakage, mixed LTV units and DTI zero/999 sentinel handling are foundational |
| 12 | Sanskriti Sarkar | Fail | 61 | Reject | Exact target, but future modification, same-month PIT, OOT selection, sentinels, and pooling defects |
| 13 | Aishwarya Ghaiwat | Fail | 58 | Reject | Exact target and rich features, but same-month PIT, OOT champion selection, contradictory versions, and broken rerun |
| 14 | Adarsh Prabhudesai | Fail | 55 | Reject | Exact response dump, but modeled population drops an entire target month plus PIT/test/reproducibility failures |
| 15 | Jarryd Scully | Fail | 45 | Reject | Event-month feature misalignment and target-loss bugs are foundational despite internally consistent predictions |
| 16 | Khush Modi | Fail | 44 | Reject | Correct positive events, but duplicate panel, full-data preprocessing, weighting, and lineage failures |
| 17 | Alan Jia | Fail | 43 | Reject | Probability-as-response, invalid denominator, full-data preprocessing, and future modification leakage |
| 18 | Sudhan Adithya | Fail | 43 | Reject | Good concepts, but deck/memo only; target, PIT, models, and metrics are unauditable |
| 19 | Shiyuan Liang | Fail | 36 | Reject | Incorrect prediction deliverable, invalid target zeros, test early stopping, and unusable weighted probabilities |
| 20 | Hardi Ramani | Fail | 34 | Reject | Defective target/dump, malformed HPI, dead LTV cleaning, and uncorrected balanced probabilities |

## Ranking and recommendation algorithm

1. Hard-gate failures override numerical score.
2. Evaluation order is: correct target/dump; PIT feature and preprocessing integrity; chronological and final-test isolation; probability calibration; economic feature/shape quality; reproducibility.
3. **Conditional interview** requires a correct, auditable target plus a bounded live-fixable defect and otherwise credible evidence. **Discuss** is reserve-only. **Reject** covers foundational, multiple, or unauditable failures.
4. Within a recommendation tier, tie-breakers are defect breadth/remediability, then score, then software/auditability. AUC is never a tie-breaker.

This ordering explains why Carlos ranks above higher-scoring Qin (Qin has broader baseline-plus-external failures), why Peter ranks above same-score Daniel, and why David is Discuss rather than Conditional despite scoring 73: PIT fails. Recommendation tier precedes score, so Shravant ranks below both Discuss candidates despite scoring 66. Within Reject, Shravant leads Waner on score; Waner leads same-score Sanskriti on remediability; Aishwarya leads Adarsh on score; Khush outranks Alan through correct binary actuals; Alan outranks same-score Sudhan through inspectable local code.

## Independent target benchmarks

The supplied panel supports two defensible exact-month conventions:

| Convention | Rows | Events | Interpretation |
|---|---:|---:|---|
| Exact-month non-absorbing current-risk | 533,016 | 6,125 | Keeps 15 later `C→C` rows from two loans after a prior `PD` |
| First-`PD` absorbing current-risk | 533,001 | 6,125 | Removes those 15 post-`PD` rows; preferred panel hygiene |

Predictor-month and event-month dating are both acceptable when exact, documented, and internally consistent. The event must still be the contiguous `C(t)→PD(t+1)` transition, and features must come from `t` or earlier.

Direct response-output audit:

- Exact non-absorbing predictor-month: Aishwarya, Carlos, David, Daniel, Qin, Thomas, Waner.
- Exact absorbing predictor-month: Adarsh, Karan, Peter, Shravant, Sanskriti, Xin.
- Exact non-absorbing event-month: Charlotte.
- Alan: 550,441 nonbinary probabilities in `response`; 423 duplicate keys.
- Hardi: 536,018 rows, 6,010 events, 413 duplicate key groups, four conflicting-response groups.
- Khush: 533,439 rows, 6,125 valid events, 402 duplicate groups plus 21 unique same-date artifacts.
- Shiyuan: 494,499-row, four-column prediction output rather than actuals.
- Sudhan: no response dump.
- Shravant: `Credit Modeling Assignment/model_response_by_loan_date.parquet`, SHA256 `7a35e3be8466142d684d0110236e5e5837151c13a321000ffd8f6bf76aeb5a3d`, exactly matches the 533,001-row/6,125-event absorbing target.
- Jarryd: submitted 522,480 rows/6,012 events; dynamic features are event-month shifted, and feature-availability filters remove canonical target rows.

# 2. Complete candidate/package inventory

## Canonical package rules

- Twenty candidates exist across 19 candidate folders and 18 root candidate ZIPs.
- Seventeen root ZIPs have matching candidate folders; Shravant Srinivas is archive-only.
- Sanskriti Sarkar and Sudhan Adithya are folder-only.
- Adarsh, Aishwarya, David, Jarryd, and Waner were added during the `2026-07-20` intake refresh. All five folder/root-ZIP pairs match exactly by relative path/hash; all root/nested ZIP CRCs pass with no traversal or encryption. Arrival timing carries no adverse inference.
- Shravant’s root archive appeared at `2026-07-17 16:28:30`, after the initial inventory. It is part of final intake and is not treated as candidate misconduct.
- Shravant’s outer ZIP has 9 files plus one directory entry; outer and inner CRC checks pass, with no unsafe paths or encryption. Five supplied assignment files match the canonical references.
- Standalone `prepayment_model_deck_shravant_srinivas.pptx` is only a PowerPoint re-save: slide body XML and media are identical to the archived deck; differences are metadata/view/master date formatting. Shravant’s conclusions are unchanged.
- Exact extraction trees are deduplicated for Daniel, Khush, Peter, Qin, Sanskriti, and Xin.
- Charlotte’s code exists only inside the nested code ZIP.
- Qin’s outer README and inner README are distinct; the extracted inner tree overwrote the outer README at folder root, so both archive members must remain separate.
- Root compilation/summary PDFs, `Thumbs.db`, `.DS_Store`, AppleDouble, `__MACOSX`, and similar filesystem metadata are excluded.
- Candidate PKL/joblib files remain opaque and were never deserialized.

| Candidate | Canonical package | Nested/duplicate handling | Key candidate artifacts | Important inventory issue |
|---|---|---|---|---|
| Adarsh Prabhudesai | Folder/root ZIP exact pair; outer 469,375,106 bytes | Nested `LB_Adarsh_Assignment.zip` ~487.8MB, 84,830 entries/1.346GB; exclude venv, executables/compiled files, symlinks, `__MACOSX`; 22 substantive files | Five notebooks, exact actuals, feature/model frames, three prediction Parquets, 15-slide PPTX/PDF, requirements | Full venv/42k Mac entries; no README; referenced `build_deck.py` absent; no standalone metrics |
| Aishwarya Ghaiwat | Folder/root ZIP exact pair; 10-file package | Nested code ZIP has 9 Python files plus docs/requirements | 19-slide PPTX/PDF, exact actuals, source/docs | Claimed predictions/metrics/model frames/figures absent; v1/v2/v3 contradictions |
| Alan Jia | `Alan Jia.zip`, 11 entries | Ignore five Mac metadata files | `libremax.py`, README, 11-page PDF deck, probability Parquet | Deck exists; prior triage incorrectly said absent |
| Carlos Rivas | `Carlos Rivas.zip`, 58 files | Root PPTX and technical-summary PDF duplicate `presentation/` copies | Notebook, 9 Python files, 5 Parquets, 17 CSVs, 12 PNGs, PPTX/PDF | Notebook and modular outputs differ slightly; final predictions are present |
| Charlotte Liu | `Charlotte Liu.zip`, 8 files | Code is nested-ZIP-only; six inner members | Actuals Parquet, 15-page deck PDF, code ZIP | No prediction-level, fitted-model, generated-analysis, or deck-source artifacts |
| Daniel Li | `Daniel Li.zip`, 3 outer files | `code.zip` is canonical; `code/` and `code/code/` are extraction duplicates | 37 logical source/config/test files, actuals Parquet, 14-page PDF | Generated metrics, predictions, figures, and model state are absent |
| David Shunwei Du | Folder/root ZIP exact pair; 28-file package | Outputs relocated but complete; opaque joblib not loaded | Executed notebook, 11-page Keynote/PDF deck, memo, exact actuals, frozen predictions, 10+ metric CSV/JSON, requirements | Strong frozen-output lineage; no explicit COVID slice |
| Hardi Ramani | `Hardi Ramani.zip`, 8 files | No duplicate candidate tree | One notebook, response Parquet, 13-slide PPTX | Only modeling source is notebook; generated metrics/predictions omitted |
| Karan Allagh | `Karan Allagh.zip`, 6 files | One nested code ZIP and one extracted tree | Six scripts, target test, metrics/coefficients/importance, seven PNGs, actuals, deck/memo | Model frame, predictions, fitted tree, best iteration, and run log absent |
| Jarryd Scully | Folder/root ZIP exact pair; modular package | Stale build copy retained | Response/feature/prediction Parquets, run metadata, 12-slide text-only PPTX | No performance metric source/table; unpinned dependencies |
| Khush Modi | `Khush Modi.zip`, 3 outer files | Complete nested tree duplicated twice; outer actuals is a third copy | Three scripts, multiple CSV/PNG generations, actuals, PPTX, three PKLs | V1/V2/V3 artifacts conflict; PKLs were not loaded |
| Peter Zhong | `Peter Zhong.zip`, 3 outer files | All 47 inner members duplicated at root and `Peter_Zhong_code/` | 15 modules, 9 tests, 14 metric artifacts, actuals, PPTX | Delivered 48-slide deck differs from expected 49-slide/hash manifest |
| Qin (Allan) Dai | `Qin (Allan) Dai.zip`, 7 outer files | Inner 25-file tree duplicated; preserve distinct outer/inner READMEs | CSV/Parquet actuals, 15-slide deck, summary, source, frozen external files, metrics | Stale filenames/output paths; no scored observations |
| Sanskriti Sarkar | Folder-only | Three notebooks each duplicated at root, subfolder, and ZIP; one copy used | Three notebooks, actuals, 12-slide PPTX, supplemental DOCX | Notebook-only workflow; no README, environment, runner, prediction file, or model frame |
| Shravant Srinivas | `Shravant Srinivas.zip`, archive-only; SHA256 `b2a9da1ee7223d7915f7977be7dcf3caa3e436d1a8caa85de39942e2669f5769` | Outer ZIP: 9 files plus directory; inner code ZIP: 68 file members/50 substantive logical files; CRC pass, no unsafe paths/encryption | Exact actuals, 12-slide deck, memo, source, machine-readable metrics/invariants/coefficients/backtest | Appeared after initial inventory; outer deck/actuals/memo match inner copies; no prediction rows/fitted models |
| Shiyuan Liang | `Shiyuan Liang.zip`, 4 files | Extracted folder omits deck and Parquet; ZIP is canonical | Notebook, 11-slide PPTX, CSV/Parquet predictions | No actual-response dump, README, environment, or tests |
| Sudhan Adithya | Folder-only | EML contributes exactly two hash-matched attachments; body/headers not read | 13-slide PPTX and one-page PDF memo | No local code, notebook, response dump, predictions, or machine-readable metrics |
| Thomas Kidu | `Thomas Kidu.zip`, 8 outer files | One extracted `src` tree matches nested `src.zip` | Six modules, response/model Parquets, JSON/CSV metrics, figures, memo, PPTX/PDF | Manual data-layout repair required; README omits `experiments.py` |
| Waner (Arina) Zheng | Folder/root ZIP exact pair; 9 files | One executed notebook plus HTML | 12-slide PPTX/PDF, exact actuals | No predictions, metric tables, memo, README, requirements, or fitted model |
| Xin Xu | `Xin Xu.zip`, 4 outer files | All 22 inner members duplicated at root and subfolder | 19 Python files, JS deck builder, actuals, 16-slide PPTX/PDF | Claimed committed outputs are entirely absent; default rerun order is broken |

# 3. Comparison matrix

| Candidate | Target/dump | PIT | Validation integrity | Model structure | Calibration evidence | Reproducibility | Final disposition |
|---|---|---|---|---|---|---|---|
| Charlotte | Exact event-month, 533,016/6,125; 15 post-PD zeros | `t-1` macro/HPI and train-only preprocessing, but raw future `mod` enters all models | 2024 reused for stopping/selection/calibration; later test remains selection-isolated | Economic/full logistic plus regularized HistGBM | Strong count metrics, slope and monthly chart; no UPB or prediction dump | Good source/tests/entrypoint; generated outputs absent | Conditional interview |
| Carlos | Exact non-absorbing, 533,016/6,125 | Conservative PMMS/HPI and train-only pipeline, but raw future `mod` enters final models | Final outcomes viewed during GLM convergence correction | Unpenalized GLM and fixed RF; no monotonic constraints | Final predictions allow independent metric verification; no final RF monthly chart | Strong package, but runner omits figures and yfinance is live | Conditional interview |
| Qin | Exact non-absorbing, 533,016/6,125 | Baseline `t-1` series, but `ever_modified` leaks future status; external histories also revised after test | Baseline final-test mechanics are clean; external blend uses viewed test | L2 logistic and unconstrained HGB; RPX blend | Logistic level excellent; HGB/blend hot | Good source/frozen external files; stale docs and missing scored rows | Conditional interview |
| Peter | Exact absorbing, 533,001/6,125 | Conservative lags, but raw future modification flag enters GLM/GBM | 2024–2026 explicitly post-selection; group holdout nonnested | True hinge GLM; unconstrained HistGBM | Excellent count/UPB/monthly tracking; raw levels hot; trailing intercept recalibration | Strong code/tests/lineage controls; delivered deck mismatch | Conditional interview |
| Daniel | Exact raw non-absorbing dump; final 513,419/5,984 | Features are PIT; sample eligibility is future-dependent | Full-history loan quarantine alters prior train/validation membership | Six 3-df cubic-spline GLM features; no tree | Good candidate-reported aggregate calibration; no PR, monthly, UPB, slope/intercept | Excellent package/tests/CI; generated evidence absent | Conditional interview |
| Karan | Exact absorbing, 533,001/6,125 | Raw future modification flag plus same-month non-vintage HPI | 2024+ used for ablation/champion; invalid “ceiling” | Strong hinge GLM; genuinely monotone LightGBM challenger | Good metrics and count/UPB views; no slope/intercept | Compact, tested target; missing model/prediction artifacts and bad default path | Conditional interview |
| Xin | Exact absorbing, 533,001/6,125 | Future modification fields leak into 2,038 risk rows | Six rounds repeatedly score 2025–26; no pristine lockbox | Final spline GLM + unconstrained CatBoost; constrained HGBs rejected | Broad candidate-reported metrics only | Broken clean rerun; no outputs despite README claim | Conditional interview |
| David | Exact nonabsorbing, 533,016/6,125; frozen test predictions exact | Future modification, same-month HPI, malformed post-filter S&P lags, age-cap distortion | Expanding 2021–23, 2024 selection, apparently frozen 2025+ test | Hinge GLM and broad LightGBM; raw incentive only monotone | Strong frozen count/UPB/bootstrap outputs; monthly underprediction | Complete 28-file output package; opaque joblib not loaded | Discuss |
| Thomas | Exact non-absorbing, 533,016/6,125; 15 post-PD zeros | Same-month HPI/unemployment availability unproven | 2024+ influenced weighting/regularization choices | Linear L2 logistic and unconstrained LightGBM | Both models hot; no monthly model tracking or UPB/slope/intercept | Strong artifact traceability; manual layout repair | Discuss |
| Shravant | Exact absorbing, 533,001/6,125 | Future modification, full-sample/future imputation, same-month HPI/PMMS | Test unemployment ablation; inner XGB tuning otherwise chronological | Spline GLM and unconstrained XGB | Machine-readable metrics/backtest; no prediction rows or predicted-UPB calibration | Clear scripts/modules/lineage; no tests/runner/lock/input hashes | Reject |
| Waner | Exact nonabsorbing, 533,016/6,125 | Future raw modification; mixed LTV units; DTI zero/999 defects; one-month macro/HPI lag | Expanding 2022/23/24 and final 2025+ holdout; no visible test fitting | Single L2 logistic; all continuous terms linear | Candidate-reported count metrics only; no monthly/UPB/slope/intercept | Executed notebook/deck/actuals; no requirements, predictions, metric tables, or model | Reject |
| Sanskriti | Exact absorbing, 533,001/6,125 | Future modification, same-month macro/HPI, sentinels, and full-data pooling | OOT chooses champion; tracking populations differ | Linear GLM and unconstrained LightGBM | Brier/deciles only; no log loss/slope/intercept/UPB | Good notebook/deck lineage, weak local rerun | Reject |
| Aishwarya | Exact nonabsorbing, 533,016/6,125 | Same-month macro/HPI; final v2 excludes modification; otherwise train-only pipeline | Final OOT selects v3 champion and blend weight | L2 linear GLM and constrained LightGBM | Candidate-reported only; promised outputs absent | Source/docs present, but clean run/deck/version lineage broken | Reject |
| Adarsh | Exact dump 533,001/6,125; modeled frame 517,429/5,943, final predictions 194,888/1,989 | Same-month HPI, full-panel FICO median, future unemployment interpolation | Final test informs features/HistGB/ensemble architecture | Hinge GLM, XGB, HistGB, two ensembles | Submitted predictions permit independent metrics on shortened Jan-2025–Mar-2026 window | Entire Apr-2026 target month omitted; huge venv package, no README/metrics table/deck builder | Reject |
| Jarryd | Submitted 522,480/6,012; positives valid but canonical target incomplete | Dynamic features attached to event month; full-test medians; false DQ history | One holdout used for comparison; no validation/final separation | Main-effects L2 logistic and weakly specified LightGBM | Metrics independently calculated from predictions but no metric artifacts | Modular source/metadata; stale build/unpinned dependencies | Reject |
| Khush | Valid positives but 423 same-date artifacts | Full-data medians/dummies; mixed units/sentinels | OOT selects champion; random validation unused | Balanced LR and weighted unconstrained XGB | Severe uncorrected overprediction; conflicting generations | Hard-coded paths, missing inputs/environment, stale artifacts | Reject |
| Alan | Invalid denominator; probability-as-response | Full-data preprocessing, unproven series timing, and raw future modification flag | Sole test used for interpretation/selection | Balanced LR; unweighted unconstrained HGB final | No Brier/log loss/calibration/monthly tracking | One script; no lock/tests/actuals/metric artifacts | Reject |
| Sudhan | No dump; reported 550,424 rows numerically consistent with an uncensored denominator | Claimed only; not auditable | 2024+ reused for model/feature/recalibration | Claimed logistic and HGB; specifications absent | Candidate-reported only AUC/lift/ratios; no proper scoring rules | No code/notebook/actuals | Reject |
| Shiyuan | 550,441 raw current rows; output is predictions | Full-data FICO; mixed units; same-month series | Test drives XGB early stopping | Balanced L1 LR and weighted unconstrained XGB | Mean scores ~43%/~40% versus ~1% | Colab-only notebook, no environment/tests/actuals | Reject |
| Hardi | 536,018/6,010; terminal zeros and conflicts | Malformed HPI; mixed LTV remains; PIT unproven | Test likely informs narrative; mixed windows | Balanced logistic and unconstrained balanced LightGBM | Brier catastrophically poor; no corrected probabilities | Notebook-only source; outputs omitted; deck drift | Reject |

# 4. Ranked shortlist and recommended interview order

## Interview slate

1. **Charlotte Liu — Conditional interview.** Require immediate recognition and point-in-time gating of future modification status, then test first-PD absorption and validation reuse.
2. **Carlos Rivas — Conditional interview.** Require a point-in-time modification rebuild and precise chronology of final-period exposure, then add final RF monthly count/UPB tracking.
3. **Qin (Allan) Dai — Conditional interview.** Interview the baseline after removing future modification status; separately require a vintage-safe external-data redesign.
4. **Peter Zhong — Conditional interview.** Use as a model-governance/ownership test: derive the low-balance hinge effect, redesign the nested entity holdout, and reserve an untouched final period.
5. **Daniel Li — Conditional interview.** Require repair of future-dependent sample quarantine and a PIT-safe penalty-expiry design.
6. **Karan Allagh — Conditional interview.** Test modification/HPI availability, final-test governance, fixed-cohort survival validation, and consistency between GLM signs and tree priors.
7. **Xin Xu — Conditional interview.** Require immediate identification/removal of future modification leakage, a clean lockbox protocol, and a working full rerun.
8. **David Shunwei Du — Discuss.** Proceed only if the live review repairs modification/HPI timing and demonstrates ownership of frozen-test governance.
9. **Thomas Kidu — Discuss/reserve.** Proceed only if capacity permits and the live exercise centers on PIT joins, untouched final validation, and probability recalibration.
10. **Shravant Srinivas — Reject.** Strong target and methods do not override modification leakage, full-sample/future imputation, same-month HPI, and final-test feature selection.
11. **Waner (Arina) Zheng — Reject.** Exact target and final-holdout mechanics do not override modification leakage, mixed LTV units and DTI zero/999 sentinel handling, and insufficient audit artifacts.

Do not spend interview time on Shravant, Waner, Sanskriti, Aishwarya, Adarsh, Jarryd, Khush, Alan, Sudhan, Shiyuan, or Hardi unless the process specifically seeks a remediation/learning-potential signal.

# 5. Hard-gate failures

Eight gates are used consistently:

1. **G1 Target event:** response one only for genuine `C(t)→PD(t+1)`.
2. **G2 Risk-set integrity:** unique exact-month rows; terminal/gapped/post-terminal handling is valid.
3. **G3 PIT predictors/preprocessing:** features and learned transforms are available by prediction date.
4. **G4 Calendar validation:** principal validation respects time.
5. **G5 Untouched final evidence:** no final-test stopping, tuning, selection, recalibration, or later development after exposure.
6. **G6 Actual-response/model agreement:** submitted binary dump agrees with the modeled target/population.
7. **G7 Auditable local implementation:** inspectable code and a credible regeneration path exist.
8. **G8 Probability correction:** class weighting/undersampling/positive scaling is absent or corrected before probabilities are treated as levels.

`P` = Pass, `F` = Fail, `U` = Unclear, `N/A` = not triggered.

| Candidate | G1 | G2 | G3 | G4 | G5 | G6 | G7 | G8 | Overall |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| Charlotte | P | P, 15-row hygiene caveat | F: future modification status | P | P | P | P | N/A | **Fail** |
| Carlos | P | P, 15-row caveat | F: future modification status | P | F | P | P with figure/external gaps | N/A | **Fail** |
| Qin | P | P, 15-row caveat | F: future modification status; external blend also revised | P | Baseline P / blend F | P | P with packaging gaps | N/A | **Fail overall** |
| Peter | P | P | F: future modification status; vintage caveat | P | F | P | P with deck-lineage defect | N/A | **Fail** |
| Daniel | P | P with 15-row caveat | F: future sample eligibility | F overall | U | F/partial: raw dump ≠ final sample | P statically | N/A | **Fail** |
| Karan | P | P | F: future modification status and same-month HPI | P | F | U: model/prediction rows omitted | P with path/output gaps | N/A | **Fail** |
| Xin | P | P | F: future modification data | P | F | P | F/unclear clean rerun | N/A | **Fail** |
| David | P | P | F: future modification and same-month HPI | P | P statically; procedural lock unknown | P | P/partial | N/A | **Fail** |
| Thomas | P | P with 15-row caveat | F/U under strict PIT standard | P | F | P | P after layout repair | N/A | **Fail** |
| Shravant | P | P | F: modification, full-sample/future imputation, same-month HPI | P | F: test feature ablation | P | P with score-audit reservations | N/A | **Fail** |
| Waner | P | P | F: modification, mixed LTV, DTI zero/999 | P | P statically | P | Partial | N/A | **Fail** |
| Sanskriti | P | P, but target cell not self-guarding | F: future modification plus same-month series | P | F | P | U/partial | N/A | **Fail** |
| Aishwarya | P | P | U/F strict same-month series | P | F: OOT champion/blend selection | P | F: broken/contradictory run | N/A | **Fail** |
| Adarsh | P | P | F: same-month HPI, full-panel median, future interpolation | P | F: repeated test feature/ensemble design | F/partial: exact dump ≠ model population | F: package/run lineage | N/A | **Fail** |
| Jarryd | P for positives | F | F: event-month features and test medians | P | F | P with canonical-population caveat | F | N/A | **Fail** |
| Khush | P for positives | F | F | P | F | F/partial due duplicate panel | F operationally | F | **Fail** |
| Alan | P for positives | F | F: future modification and full-data preprocessing | P | F | F | Partial | F for LR | **Fail** |
| Sudhan | U | U | U | U/claimed | F | F | F | N/A, claimed unweighted | **Fail** |
| Shiyuan | P for positives | F | F/U | Partial | F | F | U/partial | F | **Fail** |
| Hardi | P for realized positives | F | U/F feature integrity | P structurally | F/U | F | Partial | F | **Fail** |

# 6. Model and metric comparison

The following values are descriptive evidence within each candidate’s own universe. They are **not a leaderboard**. Different candidates use different outcome-date conventions, absorbing rules, row exclusions, windows, target defects, weights, and selection histories.

| Candidate | Window/model | ROC / PR | Proper scoring | Level/calibration | Evidence |
|---|---|---|---|---|---|
| Charlotte | Later test, calibrated HistGBM | .6771 / .0251 | log loss .05471; Brier .010027 | predicted .9808% vs actual 1.0196%; O:P 1.040; slope .989 | Candidate-reported only for model metrics; Independently verified from submitted output for actual count |
| Carlos | 2025-01–2026-04 GLM / RF | .6670/.02158; .6886/.03265 | GLM .05581/.010171; RF .05498/.010126 | .9070%/.9477% vs 1.0315%; both cold | Independently verified from submitted output |
| Qin | 2025-01–2026-04 logistic | .6562 / .0321 | .05558; .010106 | 1.0320% vs 1.0315%; O:P .999 | Independently verified from submitted output |
| Qin | Same HGB / final external blend | .6883/.0291; .6930/.0327 | HGB .05532/.010148; blend .05493/.010114 | HGB 1.3374%, blend 1.2464% vs 1.0315%; materially hot | Independently verified from submitted output; blend final evidence fails additional PIT/test gates |
| Peter | 2024-01–2026-04 raw GLM / GBM | .6701/.02584; .6787/.02560 | .05225/.009358; .05275/.009471 | prediction/actual 1.338/1.443; trailing count-dial GLM 1.006 | Independently verified from submitted output; raw prediction rows absent |
| Daniel | 2025-07–2026-04 selected GLM | .670 / PR N/A | .059851; .011119 | 1.1346% vs 1.1309%, O:P .997 | Candidate-reported only |
| Karan | 2024-01–2026-04 non-holdout GLM / LGBM | .6810/.0220; .6824/.0261 | GLM .05136/.009294; LGBM .05134/**.009301** | GLM 1.059% vs .943%, O:P .890; balance-weighted level closer for LGBM | Independently verified from submitted output |
| Xin | 2025-01–2026-04 blend | .703 / .038 | .0543 / .0101 | count O:P .99; UPB O:P 1.09; slope 1.09 | Candidate-reported only; no predictions/metrics artifacts |
| David | Frozen 2025+ GLM / LGBM | .682483/.023389; .705568/.038096 | .055316/.010157; .054447/.010071 | GLM 1.0388%, LGBM .8495% vs actual 1.0315%; UPB SMM 1.1196/.8940 vs 1.2275 | Independently verified from submitted output |
| Thomas | 2024-01–2026-04 GLM / LGBM | .6401/.0168; .6577/.0172 | .05433/.009443; .05249/.009370 | GLM 1.6529%, GBM 1.2229% vs .9478%; O:P .573/.775 | Independently verified from submitted output |
| Shravant | 2024–2026 GLM / XGB | .683553/.025343; .691708/.027043 | GLM .051486/.009332; XGB .051187/.009336 | SMM A:E .859049/.926031; actual CPR 10.7996%, predicted CPR 12.4658%/11.6143% | Independently verified from submitted output |
| Waner | Final 2025+ L2 logistic | .6814/.0274 | Brier .0101; log loss .0551 | 1.0602% predicted vs 1.0315% actual; lift 2.9018 | Candidate-reported only |
| Sanskriti | 2024-07–2026-04 GLM / LGBM | .6821/.0248; .6793/.0253 | Brier×100 .9907/.9917; log loss N/A | 1.12%/1.24% vs 1.01%; O:P .902/.815 | Candidate-reported only |
| Aishwarya | Final OOT baseline/GLM/enhanced | .699/.697/.705; PR ~.04 | GLM Brier .0105; enhanced .0106 | Enhanced CPR 11.2% vs actual 12.2008% | Candidate-reported only |
| Adarsh | Shortened Jan-2025–Mar-2026 GLM/XGB/HistGB/equal average | .6918/.0276; .6958/.0249; .6966/.0322; .7023/.0325 | Brier .010034/.010040/.010007/.010005; log loss .054529/.054426/.054273/.054047 | CPR 13.69/11.02/10.67/11.80 vs 11.58%; equal-average **UPB-weighted CPR predicted/actual 12.24%/13.65%** | Independently verified from submitted output; Apr-2026 omitted |
| Jarryd | Holdout logistic / GBM | .668186/.019391; .659952/.017991 | .055463/.0100969; .056542/.0102588 | 1.0337%/1.2456% vs actual 1.0238%; prior-UPB SMM actual 1.2133%, logistic 1.0589%, GBM 1.2695% | Independently verified from submitted output; no submitted metric table |
| Khush | Nov-2025–May-2026 LR / XGB | .6393/.0203; .6753/.0314 | current log loss/Brier N/A | Severe overprediction shown; current means/O:P absent | Independently verified from submitted output; other generations Inconsistent |
| Alan | Short late holdout LR / HGB | .681/.019; .703/.029 | log loss/Brier N/A | Actual dump absent; no O:P or calibration | Candidate-reported only; target denominator invalid |
| Sudhan | 2024+ logistic / HGB | approximately .67 | log loss/Brier/PR N/A | raw logistic P/A approximately 1.3; HGB approximately 1.5; recalibration not later tested | Candidate-reported only |
| Shiyuan | 2024-01–2026-03 LR / XGB | .6598/.0194; .6761/.0230 | log loss/Brier N/A | submitted means 43.13%/40.16% versus reported .93% test rate | Independently verified from submitted output for means; other model metrics Candidate-reported only |
| Hardi | 2024-01–2026-05 GLM / LGBM | .6289/.0163; .5445/.0125 | Brier .3063/.1823 | GLM mean approximately 54.1% vs .911%; severe weighted-prior distortion | Candidate-reported only for model metrics; Independently verified from submitted output for defective-target actual rate/count |

# 7. Feature-engineering comparison

| Candidate | Strongest feature work | Main missing or defective feature work |
|---|---|---|
| Charlotte | PIT incentive, balance factor, current LTV/HPA, prior ITM interaction, active/expired penalty states | Future raw modification status; no penalty remaining-term ramp, current CLTV, direct curtailment, or UPB framework |
| Carlos | Exact lagged incentive, balance-adjusted current LTV, transparent common feature set | Future raw modification status; no DSCR/doc/occupancy/IO/foreign/seasonality/penalty timing; static penalty |
| Qin | Incentive, age quadratic, balance factor, HPA/current LTV, penalty active, broad controls | Future cumulative modification status; no cumulative ITM burnout, penalty expiry, current CLTV; category aliases/redundancy |
| Peter | Incentive/age/balance hinges, MTM LTV, burnout, DQ/mod, active penalty, count/UPB reporting | Future raw modification status; no penalty-expiry clock; low-balance interpretation error |
| Daniel | PIT incentive/SATO/history, balance spline, HPI growth, delinquency history, DSCR | No penalty structure, current LTV/CLTV, balance factor/paydown, product/doc/mod/foreign |
| Karan | Incentive hinges/interactions, SATO, burnout, current LTV/HPA, genuine expiry buckets | Future raw modification status; unknown penalty treated as no penalty; no DQ history/product/foreign/current-balance path |
| Xin | Broadest feature library: attainable rate, payment savings, burnout, penalty/event clocks, equity, DQ, balance paths | Future modification leakage; IO schedule/payment approximations; `cltv_est` is only subject-lien LTV |
| David | Broad economic/status feature set, balance-adjusted current LTV, hinge GLM, frozen predictions | Future raw modification, same-month HPI, malformed row-lag S&P features, duplicate/constant features, age-cap distortion |
| Thomas | Simple incentive, max incentive, age, HPA/approximate LTV, macro and categories | Omits balances/paydown, penalty, modification, DQ, product, foreign, numeric DSCR |
| Waner | Intended current LTV, pool factor, HPA, IO remaining, penalty categories, expanding folds | Future raw modification; 187,790 mixed-unit LTV rows; DTI zero/999 defects; all linear effects; count-only validation |
| Shravant | Natural-spline incentive/age/current LTV/FICO; capped pool factor; clustered GLM; chronological XGB tuning | Future `is_mod`, full-sample medians, HPI/PMMS timing; current LTV omits paydown; no predicted-UPB/COVID slice |
| Sanskriti | Incentive, SATO, burnout, balance, current LTV/HPA, active/expiry penalty | Future raw modification status; sentinels, aliases, full-data pooling; no DQ history, product, foreign, current-balance path |
| Adarsh | Strong hinge GLM, curtailment/current-LTV interactions, XGB/HistGB ensembles, submitted probability frames | Model population drops Apr-2026; same-month HPI, full-panel median/future interpolation, test-designed ensemble, unsupported claims |
| Aishwarya | Rich incentive/SATO/burnout/HPA/current-LTV/penalty/category feature set and constrained LightGBM | Same-month series, fragmented categories, missing momentum, final-v2/v3 contradictions and absent outputs |
| Jarryd | Modular feature frame and interpretable logistic baseline | One-month-late dynamics, terminal shift bug, target rows conditioned on HPI, false cross-loan DQ, current LTV omits paydown |
| Khush | Event-month lagging, incentive, current-CLTV attempt, broad category inputs | Mixed units, 50.9% CLTV imputation, sentinels, constant-zero penalty, accidental feature capture |
| Alan | Incentive, quadratic age, log balances, approximate LTV, FICO, IO/mod/penalty flags | Future raw modification status; no burnout, DSCR/doc/occupancy/property/product/foreign, penalty expiry; LTV omits paydown |
| Sudhan | Strong conceptual list: incentive, burnout, equity, penalty expiry, turnover/refi | Exact formulas, model membership, availability dates, and transformations absent |
| Shiyuan | Incentive, quadratic age/burnout, current-LTV attempt | Mixed units, full-data FICO median, DTI sentinel cap, permanent penalty, no DSCR/doc/product/mod/DQ |
| Hardi | Basic rate, age, balance, FICO/LTV/DTI and HPI attempt | No incentive, malformed HPI, mixed LTV, no burnout/penalty/current equity/DSCR/doc/IO/mod/DQ/product |

## Shared future-modification leakage

The deduplicated panel contains **3,807 rows** where `mod='Y'` while `mod_ft_pay_dt > r_dt`. The exact eligible risk set contains **2,038 rows across 153 loans**, all response zero; the effective-date lead is 1–99 months with median 18 months. Predictor-date split counts are 1,549 before 2024, 333 in 2024, and 156 in 2025+. The same 2,038 rows appear under both absorbing and nonabsorbing exact targets.

Candidate-specific timing:

- Charlotte outcome-date splits: 1,514 train, 352 validation, 172 test.
- Sanskriti broad date split before its OOL partition: 1,741 through 2024-06 and 297 later.

Affected final submissions:

- Charlotte: `CATEGORICAL_FEATURES` includes `mod_clean`, mapped from raw `mod`; both logistic and HistGBM consume all features. `Charlotte_Liu_LibreMax_Prepayment_Code.zip::src/prepayment_pipeline.py:61-82,369-383,498-608`.
- Carlos: final categoricals include raw `mod`; submitted GLM coefficient −0.7050, OR .4941. `src/libremax_prepayment/config.py:36-46`.
- Qin: `ever_modified=cummax(mod!='N')` enters the final numeric list; coefficient −0.0861, OR .9175. `model_prepayment.py:52-55,120-124`.
- Peter: raw `mod` becomes `mod_flag` and enters GLM/GBM; submitted OR .4700. `cleaning.py:130-135`; `dataset.py:310-316`; `models.py:204-210,234-240`.
- Karan: `mod_flag=(mod=='Y')` enters GLM/LightGBM; submitted OR .4130. `clean_features.py:101-104,220-226`; `train_models.py:86-90,145-150`.
- Xin: already models both the raw flag and future-date clock without gating.
- David: final GLM/LightGBM include raw `mod_flag`; 2,038 affected rows, with GLM coefficient −.4542.
- Waner: final logistic includes raw `mod`; 1,882 training and 156 test rows are pre-effective, with coefficient −.421545, OR .656.
- Shravant: final `is_mod` ignores `mod_ft_pay_dt`; submitted OR .467105, p=6.53e-05. `Shravant Srinivas.zip::Credit Modeling Assignment/prepayment_model_code.zip::prepayment_model_code/src/prepay/clean.py:243-251`; `Shravant Srinivas.zip::Credit Modeling Assignment/prepayment_model_code.zip::prepayment_model_code/outputs/tables/glm_coefficients.csv:64`.
- Sanskriti: `is_mod=(mod=='Y')` enters the final binary list; submitted OR .4221. Notebook 02 cell 20 line 7; notebook 03 cell 5 lines 1-6,24-38.
- Alan: final HistGB uses `mod_clean=(mod=='Y')`. `libremax.py:191-193,219-225`.

Adarsh’s final models exclude modification; Aishwarya’s final v2 excludes it despite legacy v1 usage; Jarryd omits it. Thomas, Daniel, Hardi, Khush, and Shiyuan also omit modification; Sudhan is unauditable. No submission identified the forward-availability defect. Xin alone explicitly engineered the modification date, but still failed to gate it by effective date. Eleven final submissions are affected; the strong negative fitted effects show that the defect is not negligible.

Cross-candidate economic conclusions:

- Refinance incentive is the most consistently useful feature, but only Peter and Karan implement clearly auditable prespecified hinge systems; Charlotte and Xin also provide flexible spline/hinge treatments.
- Prepayment-penalty timing is a major separator. Karan models expiry buckets well; Xin develops event clocks but final-feature documentation conflicts; most others reduce penalty to a static flag or omit it.
- Burnout is commonly mislabeled. Age is not burnout; a cumulative maximum is not cumulative ITM duration; panel-entry histories are left-truncated.
- Current LTV should combine original leverage, current/original balance, and lagged HPI. Alan, Thomas, and Shravant omit paydown; Shiyuan/Khush suffer mixed-unit defects; Xin labels a first-lien estimate as CLTV.
- Missingness and category normalization materially affect Non-QM variables. Sanskriti, Khush, Shiyuan, and Hardi leave important sentinels or aliases untreated; Shravant learns medians from the full sample.

# 8. Logistic nonlinear-shape comparison

| Candidate | Continuous GLM treatment | Exact principal shapes | Assessment |
|---|---|---|---|
| Charlotte | L2 logistic; mostly straight lines | Incentive hinges at 0 and +1pp; log balance; age plus `log1p(age)`; one incentive×log-ITM interaction | Good incentive basis; age/LTV/penalty expiry remain too rigid |
| Carlos | Unpenalized logistic | Every continuous variable straight after training imputation/scaling; no logs except none in GLM, no hinges/splines/interactions | Misses its own RF age/incentive/LTV/balance nonlinearities |
| Qin | L2 logistic | Age + age²/1000; log original/current balance; balance factor capped [0,1.5]; current LTV capped [0,300]; incentive straight; penalty active binary | Transparent but rigid incentive/LTV; no burnout/expiry shape |
| Peter | Unweighted GLM | Incentive hinges −1/0/+1/+2pp; age hinges 12/24/48m; `log(balance)` with descending hinges at log 11/10; burnout cap 36; MTM LTV straight; active penalty binary | Strongest auditable shape system; no expiry clock |
| Daniel | Statsmodels GLM | Degree-3, df-3 cubic B-splines for incentive, age, log balance, FICO, original CLTV, unemployment; Formulaic learned edges, no explicit knots/caps; remaining features straight | Flexible but unconstrained; exact learned knots absent |
| Karan | Unweighted GLM | Incentive hinges 0/+2pp with penalty and log-balance interactions; age hinges 12/36m; expiry buckets [−3,0), [0,6), [6,12); log balance; LTV line + ≤80 flag | Strong domain structure; some hard cliffs and sign inconsistencies |
| Xin | Final GLM-v4 | `SplineTransformer(n_knots=6, degree=3)` for rate gap, age, estimated current LTV; log balance; many straight lines, interactions, penalty/DQ buckets | Rich shape library; final transformed audit artifact absent |
| David | L2 logistic with engineered hinges | Incentive knots −1/0/+1/+2pp; age 12/24/60 months; current LTV 70/90; broad main effects | More flexible than straight-line GLM, but duplicate/constant predictors and PIT defects remain |
| Thomas | L2 logistic | All continuous terms straight; age capped at 60 | Too rigid for submitted seasoning/incentive evidence |
| Waner | L2 logistic `C=.5` | Every continuous term linear after clipping/engineering; IO remaining has raw expiry hinge; penalty categorical | Transparent but no spline/polynomial/interaction treatment |
| Shravant | Unpenalized clustered logit | Natural cubic splines: incentive df5, age df5, current-LTV proxy df4, FICO df3; log original balance; capped pool factor | Strong flexible baseline; age partial peak ~42m conflicts with observed 12–18m bucket peak |
| Sanskriti | Unregularized logit | All continuous terms straight; current LTV capped 150; months-to-expiry clipped [−24,60] but linear | Cannot express claimed S-curve, age ramp/decline, or expiry cliff |
| Adarsh | Unweighted unpenalized logit | Incentive hinge 0; age hinges 12/30/60; current-LTV hinge 80; log original balance; capped curtailment; incentive×LTV/log-balance | Strong prespecified hinge system; no splines |
| Aishwarya | L2 logistic `C=1` | All numeric terms linear after transforms; positive-incentive hinge and interactions; ordinal-linear month | Rich engineering but weak age/seasonality shape and no splines |
| Jarryd | L2 logistic | All continuous variables linear; no hinges, splines, polynomials, interactions, or seasonality | Too rigid and built on one-month-late features |
| Khush | Balanced L2 logistic | Every continuous/ordinal term straight; no standardization, cap, log, spline, hinge, or interactions | Economically and numerically weak; exact redundancies remain |
| Alan | Balanced L2 logistic | Age quadratic; log original balance; incentive/current LTV/FICO straight | Reasonable basic age shape; no explicit burnout or penalty expiry |
| Sudhan | Claimed regularized pooled logistic | `inc_pos/inc_neg`, seasoning hump, penalty ramp, and interactions are described but formulas/knots/degrees unavailable | Shape claims unauditable |
| Shiyuan | Balanced L1 logistic | Quadratic age and burnout; current LTV cap [0,150]; DTI cap 65; log original balance; others straight | Some useful flexibility, overwhelmed by unit/sentinel/weighting defects |
| Hardi | Balanced logistic | Every continuous variable straight; no logs/caps/polynomials/hinges/splines/interactions | Core incentive absent; occupancy incorrectly continuous |

# 9. Tree monotonicity-constraint comparison

Regularization is not monotonicity. Depth, leaves, minimum leaf size, shrinkage, L1/L2, feature/row subsampling, and early stopping control capacity or variance; they do not guarantee an economic response direction.

| Candidate | Tree | Actual monotonic constraints | Status |
|---|---|---|---|
| Charlotte | `HistGradientBoostingClassifier` | None; “constrained” is inaccurate | Final calibrated tree |
| Carlos | `RandomForestClassifier` | None | Final ranking champion |
| Qin | `HistGradientBoostingClassifier` | None; “constrained” is inaccurate | Baseline ranking champion; final blend uses it |
| Peter | `HistGradientBoostingClassifier` | None | Challenger |
| Daniel | None | N/A | GLM-only |
| Karan | LightGBM | `rate_incentive +1`, `log_o_bal +1`, `cur_ltv −1`, `burnout −1`, `pen_months_left −1`; all others 0 | Genuine constrained challenger |
| Xin | HistGBM challengers | `rate_gap +1`, `rate_gap_pos +1`, `incentive_dollar +1`; rejected two-stage adds `p_turn_logit +1` (`experiments.py:42,183-188`; `experiments_round3.py:56-62,158-161`) | Constrained challengers rejected |
| Xin | Final CatBoost | None | Final tree component is unconstrained |
| David | LightGBM | Raw incentive +1 only; related transforms unconstrained, so aggregate incentive monotonicity is not guaranteed | Final ranking champion |
| Thomas | LightGBM | None | Ranking model/challenger |
| Waner | None | N/A | Logistic-only submission |
| Shravant | XGBoost | None; eta .05, depth 3, min child weight 20, row/column .8, lambda 10, hist/native categoricals, 420 rounds | Final challenger; no class weighting |
| Sanskriti | LightGBM | None | Challenger |
| Adarsh | XGBoost / HistGBM | None; XGB depth2/LR .05/min child 200/539 rounds; HistGB LR .05/7 leaves/min leaf200/150 iterations | Both enter test-designed ensembles |
| Aishwarya | LightGBM | Real constraints on selected features, but unconstrained related transforms/products mean aggregate incentive direction is not guaranteed | Enhanced claimed champion; outputs absent |
| Jarryd | LightGBM | None; 200 trees/depth5, other key settings unspecified | Challenger; logistic primary |
| Khush | XGBoost | None | Selected apparent champion |
| Alan | `HistGradientBoostingClassifier` | None | Final tree |
| Sudhan | Claimed histogram GBM | None documented; monotonicity appears only as future work | Challenger/claimed comparison |
| Shiyuan | XGBoost | None | Co-submitted model |
| Hardi | LightGBM | None | Optional nonlinear benchmark |

# 10. Validation-integrity comparison

| Candidate | Main windows | What is clean | What breaks integrity |
|---|---|---|---|
| Charlotte | Train outcomes through 2023; validation 2024; final outcomes 2025-01–2026-05 | Chronology, train-only preprocessing, no test-dependent predicate | 2,038 future-modification rows include 1,514/352/172 by outcome split; validation also reused three ways |
| Carlos | Expanding 2022, 2023, 2024 folds; final 2025-01–2026-04 | Strong development chronology and exact final predictions | Future modification status enters models; final period viewed before convergence correction |
| Qin | Train through 2023; validation 2024; test 2025-01–2026-04 | Calendar mechanics and train-only learned preprocessing | Future modification status affects baseline; external histories add revised-data and viewed-test failures |
| Peter | Fit through 2023; 2023 GBM selection; 2024-01–2026-04 backtest | Good temporal mechanics and replay diagnostics | Future modification status; backtest changed low-balance form/champion; group check nonnested |
| Daniel | Train through 2024-12; validation 2025-H1; test 2025-07–2026-04 | Clean split/formula refit mechanics | Later impossible transitions remove earlier rows; test provenance unavailable |
| Karan | Fit non-holdout loans through 2023; 2023 tree validation; 2024-01–2026-04 OOT; 20% loan holdout | Loan-aware and calendar-aware development | Future modification and same-month HPI; OOT ablation/champion; contemporaneous “ceiling” |
| Xin | Train through 2023; validation 2024; test 2025-01–2026-04 | Chronological, train-only transforms, rolling descriptive diagnostics | Test repeatedly scored across six rounds; future modification fields |
| David | Expanding 2021–23; 2024 selection; frozen 2025+ test | Strong frozen predictions and no direct test tuning found | Future modification/HPI; malformed S&P lags and age cap; procedural lock not provable |
| Thomas | Fit through 2023; 2023 round selection; 2024-01–2026-04 reported OOT | Correct chronology and refit pattern | OOT results influence class-weight and regularization decisions |
| Waner | Expanding 2022/23/24; final 2025+ | No visible final-test fitting or selection | Future modification, mixed-unit LTV, DTI zero/999; no monthly/UPB/slope/COVID |
| Shravant | Full training before 2024; final test 2024–2026; inner XGB fit pre-2023/validate 2023 | Exact target and chronological inner XGB tuning | Future modification; full-sample medians/features before split; test unemployment ablation; walk-forward only descriptive |
| Sanskriti | Core through 2024-06; OOT 2024-07–2026-04; OOL loan holdout | Chronological OOT and loan-level OOL | 1,741/297 future-modification rows by broad date; OOT selection, pooling, tracking mismatch |
| Adarsh | Chronological development/validation/final test | Exact response dump; submitted final predictions reconcile to shortened model frame | Entire Apr-2026 month omitted; same-month/future PIT; test-designed features/ensemble; no rolling/COVID |
| Aishwarya | Chronological training/OOT with train-only learned pipeline | Exact target and sound internal transforms | Same-month series; OOT ranks champion and optimizes blend; versions conflict |
| Jarryd | One chronological holdout | Internal prediction/actual agreement | Event-month feature leakage; target losses; test medians; no validation/final separation |
| Khush | Pre-OOT through 2025-10; OOT 2025-11–2026-05; random internal split unused | Nominal chronological holdout | Full-data preprocessing; OOT selects champion; seven months mislabeled as six |
| Alan | Train effectively through 2025-10; test 2025-11–2026-05 | Chronological cut | Future modification status; terminal May labels, full-data preprocessing, sole test reuse |
| Sudhan | Claimed train pre-2024/test 2024+ | Calendar idea only | Same holdout used for model/features/importance/recalibration; implementation absent |
| Shiyuan | Train through 2023; test 2024-01–2026-03 | Chronological principal split | Test is XGB early-stopping set; LR CV is row-stratified; full-data FICO median |
| Hardi | Train through 2022; validation 2023; test 2024-01–2026-05 | Chronological structural split | Target defects contaminate test; deck narrative appears test-informed; repeated test review |

# 11. Calibration and calendar-stability comparison

Best evidence:

- Peter supplies the strongest count/UPB/monthly framework and a leakage-free trailing six-month intercept adjustment, but the overall 2024–2026 backtest is post-selection and raw models are materially hot.
- Carlos supplies auditable final prediction rows and exact metric reproduction. A development GLM monthly routine exists, correcting the prior triage, but final RF calendar tracking is absent and pooled final levels are cold.
- Charlotte supplies log loss, Brier, slope, deciles, lift/capture, and monthly tracking, but only count weighting and no prediction-level artifact.
- Qin’s baseline logistic is nearly exact in aggregate; HGB and blend are hot and should be treated as ranking signals unless recalibrated.
- Karan reports count and aggregate balance-weighted CPR, but no slope/intercept and its cumulative “share prepaid” is invalid for an open panel.
- Xin reports a broad model-risk suite, but every model metric is candidate-reported only because the package omits outputs.
- David supplies frozen count/UPB predictions, monthly diagnostics, and a 300-draw bootstrap; LightGBM ranks better but materially underpredicts count and UPB speed, while GLM calibrates better.
- Shravant provides machine-readable ranking/proper-scoring/CPR and walk-forward tables, but no loan-level predictions, predicted-UPB calibration, or COVID slice; the 2021–2026 walk-forward results show regime instability and are descriptive after model development.
- Adarsh supplies model-level prediction Parquets and reconciled ensemble formulas, but no rolling/COVID evidence; the rank-weighted ensemble is not a probability.

Weak evidence:

- Thomas and Sanskriti report Brier/decile-style evidence but omit slope/intercept, UPB, and valid aligned monthly tracking.
- Waner reports only notebook/deck count metrics; there is no monthly/UPB/slope/intercept/uncertainty evidence.
- Aishwarya’s metrics are candidate-reported only because claimed outputs were not delivered.
- Jarryd’s metrics can be independently calculated from prediction files, but no submitted metric table or provenance artifact exists.
- Alan omits proper scoring and calibration entirely.
- Khush supplies severe calibration plots but no current mean prediction/O:P or calibrated model.
- Sudhan supplies ratios and plots only, with no underlying values or post-calibration test.
- Shiyuan and Hardi produce probability levels tens of times the event rate because class weighting is not corrected.

# 12. Code and reproducibility comparison

| Candidate | Entrypoint/layout | Tests/controls | Reproducibility conclusion |
|---|---|---|---|
| Charlotte | One CLI; six-file code package | Focused target/calibration tests; pinned requirements | Good static reproducibility; missing generated outputs/model/deck source |
| Carlos | One script entrypoint plus package/notebook | Assertions, no automated tests | Strong output evidence; runner omits figure generation; live yfinance unfrozen |
| Qin | Several scripts, no single orchestration command | No tests; frozen external manifests/hashes | Auditable but stale docs/paths and destructive external refresh instructions |
| Peter | `run_all.py`, staged modules, atomic publication | Nine tests, manifests, package checks | Strongest engineering, but over-scoped and delivered deck fails own manifest/test |
| Daniel | One CLI, 20 modules, lock, CI | Nine unit tests, Ruff/Pyrefly/pre-commit | Strong static engineering; some CLI defects and no generated evidence |
| Karan | Six manual scripts | One meaningful target test; validator checks totals only | Compact and readable; bad default path and omitted intermediate/fitted artifacts |
| Xin | Broken default `data→model→figs`; many experiment scripts | No tests/CI | Cannot regenerate cleanly; outputs absent; experiment surface overgrown |
| David | Sequential executed notebook plus frozen outputs and requirements | No code execution; prediction/metric/deck lineage is strong | Outputs relocated but complete; opaque joblib intentionally not loaded |
| Thomas | Five documented scripts, sixth omitted | No tests; strong result/figure traceability | Manual layout repair and incomplete run order, otherwise clear lineage |
| Waner | One executed notebook plus HTML and deck | No README/requirements/tests/predictions/metric tables | Understandable analysis, weak independent score/reproduction audit |
| Shravant | Clear `01→03` scripts and small modules with relative paths/seeds/invariants | No tests/one-command runner/deck builder/lock/input hash; broad minimum dependencies and warning suppression | Strong target/table/deck lineage; score audit limited by absent prediction rows/fitted models |
| Sanskriti | Three numbered notebooks | Notebook assertions only | Good visual lineage; hard-coded Colab paths and no environment/runner |
| Adarsh | Five notebooks and rich Parquet outputs | No README; missing referenced deck builder | 487.8MB nested ZIP ships full venv/42k Mac entries; source/output timestamps stale |
| Aishwarya | Nested code ZIP with nine Python files/docs | README/run paths and versions conflict; claimed outputs absent | Clean run/deck generation broken; v1/v2/v3 champion lineage unresolved |
| Jarryd | Modular package with run metadata | No submitted metric source; stale build copy and unpinned deps | Internal artifacts reconcile, but canonical target and external reproducibility fail |
| Khush | Three scripts with absolute Ubuntu paths | No tests/assertions/pipeline | Not rerunnable; stale versions and unsafe PKL-dependent visualization |
| Alan | One top-level script | No functions/tests/assertions/main guard | Easy to read, weakly reproducible and missing actuals/metrics/chart |
| Sudhan | No implementation | None | No reproducibility credit |
| Shiyuan | One Colab notebook | No tests; unpinned installs | Environment-specific and manually drifted deck |
| Hardi | One sequential notebook | No tests/assertions/environment | Locally understandable but output/target/deck lineage is unreliable |

# 13. Detailed candidate reviews

Each candidate section states the revised final rank explicitly; the physical section order reflects the audit compilation sequence, not recommendation order.

## Charlotte Liu
**Final rank: 1.**
### 1. Submission inventory

The canonical outer ZIP has eight members in order: supplied loan panel; dictionary; `Charlotte_Liu_LibreMax_Prepayment_Actuals.parquet`; 15-page deck PDF; assignment DOCX; supplied macro; supplied HPI; and `Charlotte_Liu_LibreMax_Prepayment_Code.zip`. The extracted outer members are byte-identical. The inner code ZIP contains, in order, `README.md`, `requirements.txt`, `run_pipeline.py`, `src/prepayment_pipeline.py`, `tests/test_pipeline.py`, and the reporting notebook.

Documented execution is environment setup → tests → `run_pipeline.py --bootstrap 200` → notebook. The notebook reads generated analysis outputs rather than fitting models. Missing artifacts are loan-level predictions, generated analysis CSV/JSON, fitted model, editable deck source, and a locked source/output manifest. Deck/notebook/actuals counts agree. Evidence: `Charlotte Liu.zip::Charlotte_Liu_LibreMax_Prepayment_Code.zip::README.md:18-36`; `run_pipeline.py:33-70`; notebook cells 1–2.

### 2. Target and panel construction

The source locates duplicate loan-date keys, retains one exact copy, fails on conflicting duplicates, parses and sorts dates, shifts next date/status within loan, and requires `next_date == r_dt + MonthBegin(1)`. The risk set is `status=="C" & has_next_month`; response is `next_status=="PD"`. Feature month is retained internally and submitted `date` is the event month. Assertions cover key uniqueness, exact one-month horizon, and one event per loan. Evidence: `Charlotte Liu.zip::Charlotte_Liu_LibreMax_Prepayment_Code.zip::Charlotte_Liu_LibreMax_Prepayment_Code/src/prepayment_pipeline.py:132-176,437-448`; `tests/test_pipeline.py:19-55`.

Binary audit of `Charlotte_Liu_LibreMax_Prepayment_Actuals.parquet`:

- 533,016 rows, 6,125 events, 24,412 loans.
- Exact columns `loan,date,response`; binary `int8`; zero nulls or duplicate keys.
- Event-month range 2015-08 through 2026-05.
- Exact match to an independent non-absorbing event-month reconstruction.
- 17,002 terminal current observations excluded; zero current rows followed by a genuine date gap.
- 15 later `C→C` rows from two loans remain after an earlier `PD`; absorbing truncation gives 533,001/6,125.
- Competing exact-month exits are valid cause-specific zeros, including 5,827 `C→M30`.

The 15 rows are a real hygiene defect but do not alter event correctness or the overall target gate.

### 3. Data cleaning and point-in-time handling

Macro and current HPI are requested at feature month `t-1`; origination HPI uses origination month. Prior ITM and delinquency counts exclude the current observation. LTV/CLTV values `<=1.5` are multiplied by 100; nonpositive coupon, FICO `>=9000`, and DTI `<=0`/`>=900` become missing; categories are stripped/uppercased and NA-like tokens mapped to missing. GLM medians, missing flags, scaling, frequency pooling, and one-hot encoding are fit inside training pipelines; tree category retention also uses training counts only. Evidence: `prepayment_pipeline.py:107-125,199-234,237-350,498-563`.

Current HPI uses exact `(geo,t-1)` lookup with exact state fallback: 521,354 primary, 7,696 fallback, 3,966 missing. One October-2025 unemployment value is forward-filled from September; 14,342 November feature rows are effectively two months stale although `macro_age_months` records one. This is older information, not leakage, but the deck understates staleness. No retrospective outcome filter was found beyond the missing first-PD absorption rule.

The final feature set also leaks future modification status. `CATEGORICAL_FEATURES` contains `mod_clean`; `text_map["mod_clean"]="mod"`; both logistic and HistGBM consume all listed features. The shared 2,038-row risk cohort contributes **1,514 train, 352 validation, and 172 test rows** under Charlotte’s outcome-date split, all response zero. Evidence: `Charlotte_Liu_LibreMax_Prepayment_Code.zip::src/prepayment_pipeline.py:61-82,369-383,498-608`. This fails G3 and is decision-changing.

### 4. Feature engineering

| Feature | Formula | Sources | Rationale | Available | Missing | Shape | Final? | Expected | Observed | Concern |
|---|---|---|---|---|---|---|---|---|---|---|
| Incentive family | `coupon_t-PMMS30_(t-1)`; positive hinge; over-1pp hinge | Coupon, PMMS | Refi option | `t/t-1` | Pipeline median/flag | Line + hinges 0/1 | Both | Rising, saturating | Deck profile rises .516%→1.647% | Unconstrained tail |
| SATO | Not constructed | Original coupon, no origination market-rate alignment | Origination pricing | Origination | N/A | Not used | Unused | Context-specific | N/A | Current incentive is not SATO |
| Burnout/ITM | `log1p(prior months incentive>.5)` and positive-incentive interaction | Historical incentive | Missed refi opportunities | Through `t-1` | Starts zero | Log + interaction | Both | Attenuation after exposure | No clean decline reported | Left-truncated; current-status months only |
| Age | `age` and `log1p(age)` | Age | Seasoning | `t` | None | Line + log | Both | Ramp then fade | Cohort peak 13–24m | Limited flexibility |
| Balances/paydown | `log1p(bal)`; `bal/o_bal` | Balances | Dollar savings, survivor state | `t` | None | Log + line | Both | Nonlinear/hump | Balance factor is top importance; hump | No direct curtailment |
| LTV/CLTV/HPA | Current LTV=`orig_ltv*bal/o_bal*hpi_orig/hpi_(t-1)`; YoY and origination HPA | LTV, balances, HPI | Equity/refi access | HPI `t-1` | Native/median+flags | Straight GLM; tree | Both | Higher LTV slower; HPA faster | Importance only | Original CLTV computed then unused; no current CLTV |
| FICO/DTI/DSCR | Clean numeric levels | `ofico,dti,dscr_ratio` | Qualification | Origination | Median+flag/native | Straight | Both | FICO/DSCR +, DTI − | Directions not supplied | DSCR 63.7% structurally missing |
| Doc/occ/purpose/property | Normalized categories | Static fields | Product/turnover mix | Origination | Missing/rare pooling | Categorical | Both | Level-specific | Importance only | Raw code semantics not fully labeled |
| IO/mod/DQ/foreign/product | IO state NONE/ACTIVE/EXPIRED; `mod_clean` directly from raw `mod`; prior DQ count; foreign 0–3; product/lien | Contract/history fields | Contract/segment behavior | `t` or origination | Explicit categories | Categorical/line | Both | Heterogeneous | Modification direction not submitted | 2,038 future-effective modification rows; no IO-expiry clock |
| Calendar/rates | Month category; PMMS level; unemployment | Date/macro | Seasonality/regime | `t/t-1` | Required/filled | Category + lines | Both | Regime-specific | Not shown | `macro_age_months` constant |
| Penalty | NONE/ACTIVE/EXPIRED/UNKNOWN from flag, term, age | Penalty fields | Contract friction | `t` | Unknown category | Fixed states | Both | Active lower; expiry release | Not shown | No months remaining or post-expiry duration |
| Missing indicators | Ten GLM numeric indicators | Missing numeric fields | Preserve missingness signal | `t` | Training-defined | Binary | GLM | Data-dependent | Coefficients absent | Tree uses native missing |
| Reporting/unused | Incentive/age/LTV bands; vintage; seen-loan flag; SP500 | Derived/supplied | Diagnostics | Evaluation | Various | Fixed buckets | No | N/A | Cohort charts | Bands are not model nonlinearities |

Final feature lists are defined at `prepayment_pipeline.py:38-82`; formulas at `:313-410`.

### 5. Logistic/GLM feature shape

| Continuous group | Classification | Exact treatment |
|---|---|---|
| Incentive | Straight + degree-1 hinges | Raw line, `max(x,0)`, `max(x-1,0)`; no cap |
| Balance | Log | `log1p(max(bal,0))` |
| Age | Straight + log | `age` and `log1p(max(age,0))`; no knots/cap |
| Balance factor, PMMS, unemployment, FICO, DTI, LTV, HPA, DQ, DSCR | Straight | Training median/scale where applicable; no economic knots |
| Prior ITM | Log | `log1p(count)` |
| Incentive burnout | Interaction | `max(incentive,0)*log1p(prior_itm)` |
| Penalty expiry | Not used continuously | Only categorical state |

There are no quadratics, cubic B-splines, or fixed continuous model buckets. Reporting edges (incentive −1/0/.5/1.5; age 6/12/24/36/60/120; LTV 50/70/80/90/100) are diagnostics only. Evidence: `prepayment_pipeline.py:389-409,498-542`.

### 6. Tree models and constraints

| Algorithm | Hyperparameters | Role/regularization | Weights/stopping/tuning | Monotonic constraints | Final |
|---|---|---|---|---|---|
| `HistGradientBoostingClassifier` | log loss; LR .05; max 500; max leaves 15; min leaf 500; L2 5; feature subsample .85; seed 42 | Nonlinear challenger selected as base | No class/sample weights; explicit 2024 validation early stopping, patience 30; fixed config | **None** | Validation-intercept-calibrated HistGBM |

The fitted iteration count is reported as 142. Calling this model “constrained” is incorrect: capacity controls are regularization, not `monotonic_cst`. Evidence: `prepayment_pipeline.py:545-608`; `README.md:47-51`.

### 7. Model specification and selection

Models are a constant hazard, three-variable economic logistic, full L2 logistic (`C=.1`), fixed HistGBM, and validation-intercept-calibrated HistGBM. The selection predicate requires 2024 HistGBM PR-AUC at least 5% above logistic and log loss no more than 2% worse; it reads validation metrics only. The same 2024 window also determines early stopping and calibration, increasing adaptivity but leaving the later test untouched in code. Evidence: `run_pipeline.py:68-93`; `prepayment_pipeline.py:566-688`.

The deck and notebook consistently identify calibrated HistGBM as champion. Test metrics are computed before the predicate executes, which weakens procedural precommit control but does not create a code path from test performance into selection.

### 8. Validation and leakage review

| Split | Outcome dates | Feature dates | Rows/events |
|---|---|---|---:|
| Train | 2015-08–2023-12 | 2015-07–2023-11 | 208,248 / 3,081 |
| Validation | 2024-01–2024-12 | 2023-12–2024-11 | 104,193 / 795 |
| Test | 2025-01–2026-05 | 2024-12–2026-04 | 220,575 / 2,249 |

Chronology, train-only learned preprocessing, same-loan forward scoring, and `t-1` macro/HPI history are otherwise strong. G3 fails because 1,514/352/172 future-modification rows enter train/validation/test. No final-test stopping, selection, or calibration dependency was found, so G5 remains Pass. The same validation year is triple-used. COVID/rate regimes are discussed but not separately tested; metrics are count-weighted only. Evidence: `prepayment_pipeline.py:31-37,61-82,369-383,489-608,761-795,841-862`.

### 9. Metrics and calibration

| Metric | Result | Evidence |
|---|---|---|
| ROC / PR-AUC | .677085 / .025131; bootstrap CIs reported | Candidate-reported only |
| Log loss / Brier | .054709 / .010027 | Candidate-reported only |
| Mean predicted / actual / O:P | .9808% / 1.0196% / 1.040 | Candidate-reported only for prediction/O:P; Independently verified from submitted output for actual |
| Lift / capture | 2.5255× / 568 of 2,249 = 25.26% | Candidate-reported only |
| Slope / intercept | Slope .989; test intercept numeric value absent | Candidate-reported only / Not available |
| Monthly | Jan-2025–May-2026 chart; early-2026 underprediction | Candidate-reported only |
| Count/UPB | Count only; UPB not available | Candidate-reported only / Not available |
| SMM/CPR | Hazard described as SMM-like; CPR absent | Not available |
| Train deterioration | Training metrics computed but not presented | Not available |

Metric implementation is at `prepayment_pipeline.py:641-758`; notebook cell 8 omits training output.

### 10. Economic interpretation

Incentive, seasoning, balance factor, equity, and documentation/property importance are coherent predictive signals. Modification effects cannot be trusted until raw `mod` is gated by its effective date; all affected rows are future-flagged non-events. The deck appropriately distinguishes association from causation and states that the output is a current-loan one-month hazard, not a complete cash-flow engine. The coarse penalty state cannot express the expiry ramp; balance-factor PDPs require joint accounting consistency; count calibration does not establish pool-level principal timing.

### 11. Code and software engineering

Strengths are one configurable CLI, relative paths, exact pins, fixed seeds, compact auditable target logic, type hints, runtime assertions, and focused tests. Weaknesses are a 971-line core module, no CI/type/lint config, no end-to-end test, constant/dead fields, absent model/prediction/analysis outputs, a notebook dependent on missing generated files, manual deck production, Unix-oriented README commands, and bootstrap-default mismatch. Evidence: `run_pipeline.py:33-49`; `requirements.txt:1-9`; `tests/test_pipeline.py:18-88`.

### 12. Demonstrable defects and concerns

| Severity | Classification | Evidence | Why / gate effect | Correction |
|---|---|---|---|---|
| Material | Verified defect | `prepayment_pipeline.py:61-82,369-383,498-608`; shared row audit | Raw `mod` identifies future modifications in 1,514/352/172 split rows, all non-events; G3 fails | Gate modification at an auditable effective/availability date or remove it |
| Moderate | Verified defect | `prepayment_pipeline.py:155-175`; binary audit | 15 post-PD rows; hygiene caveat, no event error | Truncate after first PD; add re-entry test |
| Moderate | Verified defect | `README.md:47-51`; `prepayment_pipeline.py:589-602` | “Constrained” tree has no monotonic constraints | Rename or add explicit constraints |
| Moderate | Strong concern | `run_pipeline.py:68-80` | Test computed before selection; precommit control weak | Select first, unlock test second |
| Moderate | Strong concern | `prepayment_pipeline.py:589-608,671-688` | One validation year used three ways | Split/cross-fit stopping, selection, calibration |
| Moderate | Packaging issue | README/inner manifest | Missing probabilities, generated tables, model, deck source | Submit compact auditable outputs and hashes |
| Moderate | Missing evidence | Notebook cell 8 | No training-performance presentation | Report train/validation/test together |
| Moderate | Strong concern | `prepayment_pipeline.py:353-367` | Penalty timing collapsed to state | Add remaining/post-expiry shape |
| Minor | Verified defect | `prepayment_pipeline.py:205-225` | Unemployment staleness understated | Preserve variable-level source date |
| Moderate | Missing evidence | `prepayment_pipeline.py:691-758` | No UPB SMM/CPR | Add monthly count/UPB speed tracking |

### 13. Candidate verdict

**Hard gate: Fail—future modification status. Score: 80/100. Confidence: high for target/code and the PIT defect; moderate for model scores. Recommendation: Conditional interview.**

| Target | Validation | Method | Features | Communication | Reproducibility | Judgment | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 19 | 14 | 14 | 13 | 9 | 7 | 4 | 80 |

Top positives: exact target/dump; isolated later test and otherwise disciplined preprocessing; strong probability and economic communication.  
Top concerns: future modification status enters both final models; 15 post-PD rows and inaccurate constraint terminology; missing prediction/generated-output lineage.

Live questions:

1. Why is `mod_clean` positive before `mod_ft_pay_dt`, and when was the flag operationally knowable?
2. Where exactly should first-PD absorption enter target construction?
3. Redesign the 2024 stopping/selection/calibration workflow.
4. Distinguish regularization from monotonic constraints and name defensible directions.
5. Explain intercept calibration versus slope, then design penalty-expiry features.

Live code modification: gate/remove `mod_clean` before its point-in-time effective date, assert zero future-dated modification features, and report affected split counts.

## Qin (Allan) Dai
**Final rank: 3.**
### 1. Submission inventory

The outer ZIP has seven members: distinct outer README, CSV and Parquet actuals, 15-slide PPTX, nested code ZIP, one-page DOCX summary, and external-data disclosure. The nested ZIP has 25 logical members: four source files, requirements and documentation, dictionary, seven frozen external raw files plus manifest, and seven reference-output files. Root and `Loan_Prepayment_Code/` copies are exact duplicates. The outer 1,455-byte README differs from the inner 2,279-byte README; the extracted folder root contains the inner version and must not replace the outer manifest.

Claims of `REPORT.md`, a 12-slide differently named deck, scored observations, diagnostics image, and complete output trees are stale. The delivered deck has 15 slides and requires a manual rename/finishing step. Reproduction instructions can overwrite frozen external inputs with revised histories. Evidence: `Qin (Allan) Dai.zip::README.md:3-25`; `Loan_Prepayment_Code/README.md:16-38`; `create_deck.py:258-260`.

### 2. Target and panel construction

The source trims IDs, drops exact duplicates, parses/sorts dates, shifts next status/date, requires exact next month, restricts to current rows, and writes predictor-month `loan,date,response`. Evidence: `Loan_Prepayment_Code/model_prepayment.py:32-50,104-115,201-210`.

CSV/Parquet audit:

- Identical 533,016 rows, 6,125 events, 24,412 eligible loans.
- Binary, no nulls or duplicate keys; date range 2015-07–2026-04.
- Exact independent non-absorbing reconstruction.
- 17,002 terminal current rows excluded; zero gapped current rows.
- 15 post-PD `C→C` zeros from two loans remain.
- 520,898 `C→C` and 5,993 competing exits are valid cause-specific zeros.

The target/dump gate passes with the same minor first-PD hygiene caveat as Charlotte.

### 3. Data cleaning and point-in-time handling

FICO outside 300–850, DTI outside 0–100, note rates outside .5–25, and LTV/CLTV outside 0–200 become missing. Balance factor is capped [0,1.5]; estimated current LTV [0,300]. Numeric imputation, standardization, rare grouping, and encoding are fit in training pipelines. `prior_noncurrent_months` uses prior history only. Evidence: `model_prepayment.py:52-100,160-182`.

Supplied macro/current HPI are shifted one month; origination HPI joins origination month. Those series are internally conservative, but the baseline is not PIT-clean: `ever_modified = cummax(mod != "N")` uses raw modification status that is already positive before `mod_ft_pay_dt`, and `ever_modified` enters the final numeric list. The shared affected cohort is 1,549 train, 333 validation, and 156 test rows, all non-events. Evidence: `model_prepayment.py:52-55,120-124`.

External series are aggregated and assigned with a two-month lag, but all seven files were retrieved in July 2026 after the test and are cumulative/revised, not as-released vintages. The submission explicitly acknowledges this. Evidence: `model_prepayment.py:57-78`; `model_prepayment_external.py:39-85`; `External_Data_Sources_and_Experiment.md:37-42`.

Category aliases remain: five purpose-missing aliases and six IO representations. Product/lien are perfectly redundant; one FTB level aliases an occupancy level; borrower count/HAMP are constants. These weaken coefficient interpretation.

### 4. Feature engineering

| Feature | Formula | Sources | Rationale | Available | Missing | Shape | Final? | Expected | Observed | Concern |
|---|---|---|---|---|---|---|---|---|---|---|
| Incentive | `coupon-PMMS_(t-1)` | Coupon, PMMS | Refi option | `t/t-1` | Median+flag | Straight logistic/tree splits | Baseline both | Positive/S-shaped | Logistic +.780 standardized; top tree importance | No logistic hinge |
| SATO/burnout | Neither true SATO nor cumulative ITM; balance factor/proxy history only | Rates/balances | Pricing and survivor selection | Historical | Various | Not used/proxy | Weak/unused | Context-dependent | N/A | Major omitted economic structure |
| Age | `age`, `age²/1000` | Age | Seasoning | `t` | None | Quadratic | Both | Hump | +linear/−square | Rigid global quadratic |
| Balances/paydown | `log1p(o_bal)`, `log1p(bal)`, `clip(bal/o_bal,0,1.5)` | Balances | Dollar economics/paydown | `t` | None | Logs + line | Both | Larger/factor effects | Mixed conditional coefficients | Redundant system; curtailment absent |
| LTV/CLTV/HPA | `orig_ltv*factor/(1+HPA)`; `HPA=HPI_(t-1)/HPI_orig-1` | Leverage, balance, HPI | Equity | `t-1` | Median+flag | Capped straight lines/tree | Both | LTV −, HPA + | LTV −, HPA + | Current CLTV absent |
| FICO/DTI/DSCR | Clean levels | Static underwriting | Access/capacity | Origination | Median+flags | Straight | Both | FICO/DSCR +, DTI − | Tiny mixed coefficients | Structural DSCR missingness |
| Doc/occ/purpose/property/IO | Normalized then one-hot/native category | Static fields | Segment behavior | Origination | Explicit missing | Categorical | Both | Level-specific | Mixed | Aliases and full one-hot/intercept interpretation |
| Mod/DQ/foreign/product | `ever_modified=cummax(mod!="N")`; prior noncurrent count; foreign category; product/lien | History/static | Refi friction/segment | Purportedly through `t` | Categories | Binary/line/category | Both | Heterogeneous | Modification coefficient −.0861, OR .9175 | 2,038 future-effective modification rows; product/lien duplicate |
| Calendar/rates | Month/year categories; unemployment changes; SP500 return | Date/macro | Regime | `t/t-1` | Median | Buckets/lines | Both | Regime-specific | Mixed | High-dimensional proxies |
| Penalty | `active = flag & age<term` | Penalty, term, age | Contract friction | `t` | Missing term→inactive | Binary | Both | Negative | Logistic negative | No remaining/expiry/post-expiry |
| External RPX | Monthly RPX families and interactions | Freddie files, incentive/equity | Refi application pipeline | Revised history lagged two months | Median | Lines/interactions/tree | Final blend challenger | Positive | Blend ranking improves | Interaction named “all RPX” actually uses cash-out |
| Missing/unused | Missing indicators; no IO/mod clocks, current CLTV, curtailment, penalty expiry | Various | Data quality | `t` | Explicit/absent | Binary/not used | Mixed | N/A | N/A | Gaps above |

Evidence: `model_prepayment.py:88-129,166-182`; `model_prepayment_external.py:120-150`.

### 5. Logistic/GLM feature shape

| Group | Classification | Exact treatment |
|---|---|---|
| Age | Quadratic polynomial | `age`, `age²/1000`; no cap |
| Balances | Log | `log1p(max(balance,0))` |
| Balance factor | Cap-floor + straight | [0,1.5] |
| Estimated current LTV | Cap-floor + straight | [0,300] |
| Incentive, FICO, LTV/CLTV, DTI, DSCR, HPA, macro, DQ, term/units | Straight | Clean/median/standardize; no knots |
| Penalty | Fixed binary | Active/inactive only |
| RPX interactions | Degree-1 hinge + interaction | Positive incentive hinge at 0; equity hinge at LTV 100 |
| Calendar | Fixed category | Month and origination year |

No cubic B-splines or baseline continuous interactions. Evidence: `model_prepayment.py:88-129`; external shapes at `model_prepayment_external.py:120-150`.

### 6. Tree models and constraints

| Algorithm | Hyperparameters | Role | Weights/stopping/tuning | Monotonic constraints | Final |
|---|---|---|---|---|---|
| `HistGradientBoostingClassifier` | LR .06; max 250; leaves 15; min leaf 100; L2 2; seed 42 | Baseline and external-family tree comparisons | No weights; internal early stopping with library defaults; family selection on 2024 | **None** | Baseline HGB; 75/25 HGB/RPX-logistic final ranking blend |

No `monotonic_cst` exists. “Constrained” refers only to capacity regularization and is inaccurate terminology. Evidence: `model_prepayment.py:175-184`; `model_prepayment_external.py:89-106`.

### 7. Model specification and selection

Baseline logistic is L2, `C=.25`, liblinear, max 500. Baseline HGB is selected on 2024 PR-AUC. External logistic/tree families and blend weights are selected on 2024 ROC-AUC; the final blend is 75% baseline HGB and 25% RPX logistic. No class weighting or resampling is used. Evidence: `model_prepayment.py:151-198`; `model_prepayment_external.py:137-210`.

The baseline selection path is mechanically validation-only, but the baseline predictors fail PIT because of `ever_modified`. The final external recommendation adds revised histories unavailable in real time and a previously viewed broad test. The all-refi RPX selector requires `"adj_cnt"`; the decisive submitted all-refi header is `WK_RPX_CNT`, which lacks that token, so the interaction selects cash-out adjusted count instead. Evidence: `data_external/freddie_rpx_all.csv:1`; `model_prepayment_external.py:120-127`.

### 8. Validation and leakage review

| Split | Dates | Rows/events |
|---|---|---:|
| Train | 2015-07–2023-12 | 215,757 / 3,118 |
| Validation | 2024-01–2024-12 | 106,784 / 836 |
| Test | 2025-01–2026-04 | 210,475 / 2,171 |

Calendar chronology, train-only learned preprocessing, no weighting, and `t-1` supplied economic series are otherwise sound. G3 fails because 1,549/333/156 future-modification rows enter train/validation/test. Same-loan overlap is deployment-consistent, though uncertainty is not clustered. External selection is validation-only inside code, but revised data and admitted test reuse add a separate failure. No rolling-origin, UPB, dedicated COVID/rate-regime, or confidence-interval analysis is supplied.

### 9. Metrics and calibration

| Metric | Logistic | HGB | Final blend | Evidence |
|---|---:|---:|---:|---|
| ROC-AUC | .6562 | .6883 | .6930 | Independently verified from submitted output |
| PR-AUC | .0321 | .0291 | .0327 | Independently verified from submitted output |
| Log loss | .05558 | .05532 | .05493 | Independently verified from submitted output |
| Brier | .010106 | .010148 | .010114 | Independently verified from submitted output |
| Predicted / actual | 1.0320% / 1.0315% | 1.3374% / 1.0315% | 1.2464% / 1.0315% | Independently verified from submitted output |
| O:P | .999 | .771 | .828 | Independently verified from submitted output |
| Top-decile lift | 2.395× | 2.727× | N/A | Independently verified from submitted output / Not available |
| Slope/intercept | N/A | N/A | N/A | Not available |
| Monthly | N/A | Overpredicts all 16 test months | N/A | Independently verified from submitted output |
| UPB/SMM/CPR | None | None | None | Not available |

The logistic is the usable level model; HGB/blend are ranking signals until recalibrated.

### 10. Economic interpretation

Incentive, active penalty, age curvature, HPA/current LTV, and foreign/product differences are directionally plausible. The negative modification estimate is contaminated by future-known non-events and cannot support an economic conclusion until rebuilt PIT. Original/current balance and factor coefficients are highly conditioned and should not be read separately. Full one-hot categorical blocks plus intercept/L2 mean individual dummy odds ratios are not simple omitted-reference comparisons. The external blend may improve rank but is not a deployable probability vector.

### 11. Code and software engineering

Strengths: relative paths, compact functions, pinned dependencies, main guards, static AST validity, frozen external hashes, and no unnecessary framework. Weaknesses: no one-command orchestration, no tests/CI/Python version, stale READMEs/output names, hardcoded deck cards, absent scored rows, undocumented early-stop temporal behavior, and downloader instructions that overwrite frozen inputs.

### 12. Demonstrable defects and concerns

| Severity | Classification | Evidence | Why / gate effect | Correction |
|---|---|---|---|---|
| Material | Verified defect | `model_prepayment.py:52-55,120-124`; shared row audit | `ever_modified` exposes 1,549/333/156 future-modification rows, all non-events; G3 fails | Gate raw modification by effective/availability date or remove it |
| Material | Strong concern | `External_Data_Sources_and_Experiment.md:37-43` | Revised post-test histories + viewed test; final blend fails PIT/final evidence | Treat exploratory; use as-released vintages and new holdout |
| Moderate | Verified defect | `model_prepayment.py:175-182` | “Constrained” HGB has no constraints | Rename/add actual `monotonic_cst` |
| Moderate | Verified defect | `model_prepayment_external.py:120-133` | RPX interaction selects cash-out series | Select explicit all-refi field and rename |
| Moderate | Verified defect | `model_prepayment.py:160-170`; coefficient CSV | Aliases/constants/redundancies damage interpretation | Canonicalize and remove duplicates/constants |
| Moderate | Strong concern | Baseline feature lists | No cumulative ITM or penalty expiry; rigid incentive | Add prespecified targeted shapes |
| Moderate | Missing evidence | README/output manifest | Scored rows/diagnostics absent | Submit predictions and compact run manifest |
| Moderate | Packaging issue | Outer/inner READMEs and deck generator | Paths/names/slide counts disagree | One canonical manifest/orchestrator |
| Minor | Verified defect | `model_prepayment.py:43-55` | 15 post-PD current rows | First-PD truncation |

### 13. Candidate verdict

**Hard gate: Fail overall—baseline modification leakage; external blend adds revised-history and test-reuse failures. Score: 73/100. Confidence: high on target/code and the PIT defect; moderate-high on score. Recommendation: Conditional interview.**

| Target | Validation | Method | Features | Communication | Reproducibility | Judgment | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | 13 | 12 | 9 | 9 | 6 | 4 | 73 |

Top positives: exact auditable target; strong baseline calendar mechanics and calibration; candid ranking-versus-level and revised-data disclosure.  
Top concerns: future modification status contaminates the baseline; final blend has no PIT-vintage untouched test; inaccurate constraint terminology/RPX bug and stale packaging.

Live questions:

1. Why is `ever_modified` positive before `mod_ft_pay_dt`, and how would you gate it?
2. Why does a two-month lag not solve revision-vintage leakage?
3. Which model should drive cash-flow level and why?
4. Identify the exact RPX series used by the interaction and repair the selector.
5. Explain full one-hot contrasts, then design a new external-data lockbox.

Live code modification: rebuild `ever_modified` from point-in-time-effective modification history, assert no future-dated flags, and report changed split counts.

## Carlos Rivas
**Final rank: 2.**
### 1. Submission inventory

The canonical ZIP has 58 files and 56 unique payloads after deduplicating the root PPTX and technical-summary PDF against `presentation/` copies. It includes the supplied data, one notebook, one script entrypoint, eight package modules, five Parquets, 17 CSVs, 12 PNGs, PPTX/PDF deliverables, README/configuration, and metadata. All extracted files hash-match ZIP members; deck images hash-match submitted figures. The notebook predates modular outputs and contains slightly different RF results. Missing artifacts include fitted models, development predictions, frozen S&P data, bootstrap replicates, tests, and deck-generation source. Evidence: `Carlos Rivas/README.md:3-5,402-420,459-463`.

### 2. Target and panel construction

`data_preparation.py` drops 600 exact duplicates, sorts by loan/date, shifts next date/status, requires exact next calendar month, restricts to current rows, and sets response from next status `PD`. Evidence: `src/libremax_prepayment/data_preparation.py:19-48`; notebook cell 23.

Audit of `outputs/loan_date_response.parquet`:

- 533,016 rows, 6,125 events, 24,412 loans; predictor months 2015-07–2026-04.
- Exact `loan_id,r_dt,response`; binary `int8`; no nulls, duplicates, extras, omissions, or label mismatches.
- 17,002 terminal current rows excluded; zero gapped current rows.
- Exact non-absorbing target, including 15 post-PD `C→C` zeros.

The target and dump pass. The 15 rows are minor panel hygiene and do not alter the event count.

### 3. Data cleaning and point-in-time handling

Fractional LTV/CLTV and rates are normalized; zero/invalid coupons are repaired or nulled; FICO 9999 and DTI 0/999 become missing; penalties normalize to No/Yes/Unknown. The DTI zero rule turns 241,029 rows into missing and requires live defense. PMMS and S&P use `t-1`; current HPI uses `t-3`; learned preprocessing is fit within each training pipeline. Evidence: `data_preparation.py:51-128`; `feature_engineering.py:54-121,212-308`; `modeling.py:60-92`.

For 5,783 age-0–2 rows, `t-3` HPI predates origination; the candidate discloses this. It is not look-ahead, but current-LTV/HPA semantics are defective for those rows. S&P is downloaded live through yfinance and not frozen. Static-field audit found no within-loan changes.

The final categorical list includes raw `mod`. The shared affected risk cohort contributes 1,549 pre-2024, 333 in 2024, and 156 in 2025+; all are non-events. Submitted GLM coefficient is −0.7050, OR .4941, so the leaked feature has a large fitted effect. Evidence: `src/libremax_prepayment/config.py:36-46`. G3 fails.

### 4. Feature engineering

| Feature | Formula | Sources | Rationale | Available | Missing | Shape | Final? | Expected | Observed | Concern |
|---|---|---|---|---|---|---|---|---|---|---|
| Incentive | `coupon_t-PMMS_(t-1)` | Current rate, PMMS | Refi economics | `t/t-1` | None | Straight GLM/tree | Both | Positive, nonlinear | GLM OR 1.236/+100bp; RF rises near +1–2pp | GLM rigid |
| SATO/burnout | Not constructed | Origination/historical rates | Pricing/opportunity history | Historical | N/A | Not used | Unused | Context/negative burnout | N/A | Age is not burnout |
| Age | Raw age | Age | Seasoning | `t` | None | Straight GLM/tree | Both | Hump | GLM negative; RF peaks near 34m | GLM misspecified |
| Balances/paydown | Raw `bal`; `o_bal` only in current-LTV | Balances | Dollar benefit/equity | `t` | None | Straight GLM/tree | Current balance both | Positive/nonlinear | GLM OR 1.033/+$100k; RF dip then rise | No log, factor, or curtailment |
| LTV/CLTV/HPA | `orig_ltv*(bal/o_bal)*hpi_orig/hpi_(t-3)` | LTV, balances, HPI | Current equity | `t-3` HPI | 3,966 + flag | Straight/tree | Current LTV both | Higher slower | GLM OR .875/+10 | Young-loan HPI; CLTV omitted |
| FICO/DTI/DSCR | Clean FICO/DTI; DSCR unused | Underwriting | Refi qualification | Origination | Median+flags | Straight | FICO/DTI both | FICO +, DTI − | Weak/non-significant | DTI zero assumption; DSCR omitted |
| Doc/occ/purpose/property | Purpose/property modeled; doc/occ omitted | Static fields | Segment behavior | Origination | Unknown/one-hot | Categorical | Purpose/property both | Level-specific | Mixed | Major Non-QM omissions |
| IO/mod/DQ/foreign/product | Raw `mod` and product used; IO/DQ/foreign unused | Static/history | Contract/segment | Purportedly `t`/origination | Categories | One-hot/tree | Partial | Heterogeneous | Modification coefficient −.7050, OR .4941 | 2,038 future-effective modification rows; no DQ history or IO timing |
| Calendar/rates | PMMS and S&P; no seasonality/year | Macro/date | Regime | `t-1` | S&P live | Straight/tree | Both | Regime-specific | PMMS OR .833; S&P null | No calendar controls; unfrozen source |
| Penalty | Static normalized flag | Flag | Contract friction | Origination | Unknown category | One-hot/tree | Both | Negative while active | Yes OR .858 | 30,852 yes rows at/past expiry |
| Missing flags | DTI/FICO/HPI | Cleaned fields | Data quality | `t` | Explicit | Binary | Both | Data-dependent | DTI-missing OR .840 | No penalty/HPI-age distinction |
| Unused/reporting | Original CLTV, DSCR, doc, occupancy, IO, foreign, units, penalty expiry, calendar, HPA | Supplied fields | Economic candidates | Various | N/A | Not used | No | N/A | N/A | Important untested families |

Final lists are in `config.py:18-46`; formulas in `feature_engineering.py:212-348`.

### 5. Logistic/GLM feature shape

All nine continuous GLM variables are training-imputed/scaled straight lines: age, balance, original term, FICO, DTI, incentive, current LTV, PMMS, and S&P return. There are no logs, caps, quadratics, fixed buckets, degree-1 hinges, splines, or interactions. Missing indicators are binary. Evidence: `modeling.py:60-110`; `outputs/glm_continuous_effects.csv:2-10`.

This conflicts with RF evidence of nonlinear incentive, age, balance, and LTV. A prespecified low-df hinge/spline baseline would be more economically faithful.

### 6. Tree models and constraints

| Algorithm | Hyperparameters | Role/regularization | Weights/stopping/tuning | Monotonic constraints | Final |
|---|---|---|---|---|---|
| `RandomForestClassifier` | 300 trees; depth 12; min leaf 100; `max_features=sqrt`; seed 42; all cores | Nonlinear challenger selected as champion | No weights; no early stopping; fixed spec compared on 2022/23/24 folds; no search output | **None** | RF champion |

Depth, leaf size, and feature sampling are regularization only. PDPs use 20,000 fixed training rows; importance uses the 2024 development fold, not final test. Evidence: `modeling.py:114-167`; `evaluation.py:885-981`.

### 7. Model specification and selection

The GLM is an unpenalized logistic probability baseline; RF uses the same features and rows. RF wins submitted development PR-AUC, ROC, Brier, and log loss in 2022, 2023, and 2024. Development calibration mappings were rejected as unstable. No weighting/resampling is used.

The final period was examined before the specification was fully frozen. The notebook states that it was viewed during correction of a GLM convergence defect; tolerance changed to `1e-10`, from about 22 iterations to 163. There is no evidence of final-outcome RF tuning, but the period cannot be called pristine. Evidence: notebook cells 70, 82, 125, 197.

### 8. Validation and leakage review

| Fold | Train | Test | Train rows/events | Test rows/events |
|---|---|---|---:|---:|
| 2022 | through 2021-12 | 2022 | 82,427/1,988 | 53,341/637 |
| 2023 | through 2022-12 | 2023 | 135,768/2,625 | 79,989/493 |
| 2024 | through 2023-12 | 2024 | 215,757/3,118 | 106,784/836 |
| Final | through 2024-12 | 2025-01–2026-04 | 322,541/3,954 | 210,475/2,171 |

Chronology, same-loan forward scoring, training-only learned preprocessing, and market/HPI lags are otherwise sound. G3 fails because raw modification status exposes 1,549/333/156 future-effective rows across pre-2024/2024/2025+. A 36-month 2022–2024 GLM monthly actual/predicted routine exists; prior triage was wrong to say there was none. What is missing is final-period RF monthly/calendar tracking, UPB weighting, training metrics, and a pristine post-freeze holdout.

### 9. Metrics and calibration

Final values were independently recomputed from `outputs/final_test_predictions.parquet`:

| Model | ROC / PR | Log loss / Brier | Predicted / actual / O:P | Top-10 capture/lift | Evidence |
|---|---|---|---|---|---|
| GLM | .666998 / .021577 | .055812 / .010171 | .9070% / 1.0315% / 1.137 | 27.04% / 2.704× | Independently verified from submitted output |
| RF | .688596 / .032654 | .054983 / .010126 | .9477% / 1.0315% / 1.088 | 27.54% / 2.754× | Independently verified from submitted output |

Calibration deciles reconcile exactly. Final RF monthly table, slope/intercept, UPB weighting, SMM/CPR, and training metrics are not available. Technical Summary says 601 top-decile RF events/27.68%/2.77×; canonical predictions and CSV give 598/27.5449%/2.7544×—**Inconsistent**.

### 10. Economic interpretation

Incentive, current LTV, balance, and the age hump are plausible. The strong negative modification effect is not interpretable until future-effective flags are removed. Static penalty treatment is materially wrong after expiry. PMMS’s isolated coefficient is conditioned on an incentive identity. Weak FICO/DTI/term/S&P fields are retained without incremental-evidence tables. The RF is useful for ranking but its cold final level and absent calendar tracking preclude direct cash-flow use.

### 11. Code and software engineering

Strengths: clear package/entrypoint, relative paths, deterministic seeds, short target logic, sklearn pipelines, output assertions, and syntax-clean modules. Weaknesses: no tests; pipeline never calls `export_all_figures`; deck is not regenerated; importance is mislabeled as final-test; local-project self-reference in lock; stale egg-info; Colab notebook drift; live yfinance; and no run manifest. Evidence: `scripts/run_pipeline.py:22-29,136-142`; `visualization.py:824-886`.

### 12. Demonstrable defects and concerns

| Severity | Classification | Evidence | Why / gate effect | Correction |
|---|---|---|---|---|
| Material | Verified defect | `config.py:36-46`; shared row audit | Raw `mod` exposes 1,549/333/156 future-effective rows and has OR .4941; G3 fails | Gate modification by effective/availability date or remove it |
| Material | Verified defect | Notebook cells 70/82/125/197; deck PDF extracted text lines 113-126 | Final period viewed before freeze; strict G5 fail | Treat as validation; reserve new holdout |
| Material | Strong concern | `config.py:36-44`; penalty counts | Static flag keeps ~30,852 expired rows active | Add active/remaining/expiry/post-expiry |
| Moderate | Verified defect | `run_pipeline.py:22-29,136-142` | Runner omits figures; stale-output risk | Call and validate figure export |
| Moderate | Verified defect | `evaluation.py:885-909`; `visualization.py:563-569` | 2024 importance labeled final test | Correct sample label |
| Moderate | Packaging issue | Summary PDF vs `final_operating_metrics.csv:6` | 601 versus canonical 598 events | Generate narrative from canonical CSV |
| Moderate | Strong concern | `modeling.py:60-110` | All GLM shapes straight | Add prespecified hinges/splines |
| Moderate | Strong concern | `feature_engineering.py:9-49` | Live yfinance input is unfrozen and weak | Freeze/checksum or remove |
| Moderate | Interview question | `data_preparation.py:109-111` | 241,029 DTI zeros made missing | Defend/test alternative on development only |
| Moderate | Missing evidence | Final outputs | No final RF calendar/UPB/slope/intercept | Export monthly count/UPB diagnostics |

### 13. Candidate verdict

**Hard gate: Fail—future modification status and non-pristine final period. Score: 72/100. Confidence: high on target/output/PIT defect; moderate on decision chronology. Recommendation: Conditional interview.**

| Target | Validation | Method | Features | Communication | Reproducibility | Judgment | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | 11 | 13 | 9 | 8 | 7 | 4 | 72 |

Top positives: exact target and independently auditable final metrics; strong expanding-window development; clear rare-event analysis.  
Top concerns: future modification status has a large fitted effect; final period is not pristine; static penalty and broken figure/external-data lineage.

Live questions:

1. Why is raw `mod` positive before `mod_ft_pay_dt`, and how would you rebuild it PIT?
2. What final outcomes were visible before `tol=1e-10`?
3. Why are DTI zeros missing, and why retain live S&P return?
4. Distinguish RF regularization from monotonicity.
5. Add final RF monthly count/UPB O:P and active-penalty timing.

Live code modification: point-in-time gate/remove `mod`, assert no future-effective modification features, and recompute the affected split counts without fitting.

## Peter Zhong
**Final rank: 4.**
### 1. Submission inventory

The outer ZIP has a PPTX, nested 47-file code ZIP, and response Parquet. Root and `Peter_Zhong_code/` trees are exact duplicates. The inner package contains 15 modules, nine tests, documentation/model card/memo, `run_all.py`, manifests, actuals, and 14 metric artifacts. Raw inputs, model dataset, row-level predictions, fitted bundle, and figures are deliberately excluded. Execution order is explicit at `run_all.py:40-59`.

The delivered deck has 48 slides/notes and SHA256 `572b398a…`; source/tests expect 49 and manifest hash `f6c32360…`. The missing expected executive-thesis slide and hash mismatch are packaging/lineage defects, not proof of metric falsity. Evidence: `README.md:10-14`; `tests/test_deliverables.py:172-211`; `SUBMISSION_MANIFEST.json:7`.

### 2. Target and panel construction

Cleaning drops exact duplicates, fails on conflicting keys, validates dates/age, and censors after first PD. Dataset code shifts next status/date, requires current status and exact next month, and writes predictor-month actuals. Evidence: `src/prepay/cleaning.py:71-98,181-189`; `src/prepay/dataset.py:129-139`; `src/prepay/pipeline.py:375-392`.

Audit:

- Exact absorbing 533,001 rows, 6,125 events, 24,411 loans.
- Binary `loan_id,date,response`; no nulls, duplicate keys, gaps, or terminal zeros.
- Date range 2015-07–2026-04; exact independent match.
- Absorbing convention removes 15 post-PD zeros and no events.
- 411 delinquency/foreclosure-to-PD and 186 loans first observed as PD are properly excluded.

### 3. Data cleaning and point-in-time handling

FICO 9999 and DTI 0/999 become missing; fractional LTV/rates normalize; invalid current rates are forward-filled within loan then fall back to valid original rate. Categories normalize centrally. GLM medians and missing flags are fit on training; GBM categorical levels are training-locked. PMMS is month `t`; unemployment is lagged one month; current HPI uses `t-2`; HPI ratio is capped [.5,3], balance ratio ≤2, MTM LTV [5,150], balance floor $1,000. Evidence: `cleaning.py:100-179`; `dataset.py:35-57,194-275`; `models.py:92-118,245-271`.

Most direct look-ahead controls pass; final-vintage revision leakage remains acknowledged. Modification does not: `mod_flag` is cleaned directly from raw `mod` and enters both GLM and GBM. The shared affected cohort contributes 1,549 pre-2024, 333 in 2024, and 156 in 2025+; all are non-events. Submitted modification OR is .4700. Evidence: `cleaning.py:130-135`; `dataset.py:310-316`; `models.py:204-210,234-240`.

### 4. Feature engineering

| Feature | Formula | Sources | Rationale | Available | Missing | Shape | Final? | Expected | Observed | Concern |
|---|---|---|---|---|---|---|---|---|---|---|
| Incentive | `coupon-PMMS_t` | Coupon, PMMS | Refi moneyness | `t` | Median/native | Hinges −1/0/1/2 | GLM+GBM | Rising/saturating | Monotone; flattens >2pp | Generic PMMS |
| SATO | `o_coupon-PMMS_orig` | Origination rate/macro | Pricing selection | Origination | Median/native | Straight/tree | Both | Context | Weak positive/null | Invalid-rate missing flag absent |
| Burnout | Prior count of current months incentive>1pp, cap 36 | History | Unexercised opportunity | Through `t-1` | Starts zero | Capped line/tree | Both | Negative | GLM positive significant | Left-truncated/specification-conditioned |
| Age | Source age | Age | Seasoning | `t` | None | Hinges 12/24/48 | Both | Ramp/fade | Peak ~24–30m | No cohort interaction |
| Balance/paydown | `ln(max(bal,1000))`, hinges log 11/10; factor inside MTM LTV | Balances | Dollar economics/tiny-balance payoff | `t` | Floor | Log+hinges | Both | U-shape | Sharp sub-$22k rise | Total effect misreported |
| LTV/CLTV/HPA | MTM=`factor*orig_ltv/HPIratio`; orig CLTV/HPA tree-only | Leverage, balances, HPI | Equity | HPI `t-2` | Flag/native | Line/tree | Both/GBM | LTV − | GLM OR .960/10 pts | No current CLTV |
| FICO/DTI/DSCR | Clean levels | Underwriting | Access/capacity | Origination | Flags/native | Lines/tree | Both; DSCR GBM | FICO/DSCR +, DTI − | Mostly weak | High DTI missingness |
| Doc/occ/purpose/property | Pooled/normalized categories | Static | Segment behavior | Origination | Explicit missing | One-hot/tree | Both/GBM | Level-specific | Mixed | Code labels opaque |
| IO/mod/DQ/foreign/product | IO flag; raw-derived `mod_flag`; prior DQ; foreign/product tree fields | Contract/history | Segment/friction | Purportedly through `t` | Native/flags | Binary/category | Both/GBM | Heterogeneous | Modification OR .4700 | 2,038 future-effective modification rows; no IO expiry |
| Calendar/rates | Annual sine/cosine; unemployment; incentive PMMS | Date/macro | Seasonality/regime | `t/t-1` | Prior-fill | Harmonic/line/tree | Both | Cyclic | Weak seasonality | No explicit year interaction |
| Penalty | `flag & age<term` | Flag, term, age | Contract friction | `t` | Missing flag | Binary | Both | Negative | OR .804 | No remaining/expiry clock |
| Missing indicators | FICO, DTI, MTM-LTV, penalty | Fields | Missingness | `t` | Explicit | Binary | GLM | Data-dependent | Nonsignificant | SATO missing not flagged |
| Reporting/unused | Monthly CPR, rolling replays, state, first-time buyer, original balance direct | Various | Diagnostics | Evaluation | Various | Reporting | No/GBM | N/A | Rich diagnostics | FTB dead column |

Evidence: `dataset.py:214-326`; `models.py:38-146,190-242`.

### 5. Logistic/GLM feature shape

| Group | Classification | Exact treatment |
|---|---|---|
| Incentive | Degree-1 hinges | Knots −1,0,1,2pp; net slopes .3768,.2624,.4727,.5521,.0851 |
| Age | Degree-1 hinges | Knots 12,24,48 months; annual slopes +1.177,+.266,−.156,−.052 |
| Balance | Log + descending hinges | `ln(max(bal,1000))`; log knots 11 (~$59.9k), 10 (~$22.0k) |
| Burnout | Cap + straight | Cap 36, divide 12 |
| MTM LTV/FICO/DTI/SATO/unemployment | Straight | Scaling by 10/20 points or 1pp as documented |
| Calendar | Fixed cyclic | Sine/cosine annual harmonic |
| Penalty | Fixed binary | Active only; no expiry |

Below log balance 10, total local slope is `0.245732-(-0.369921)-1.860926=-1.245273`; a one-log-unit **decline** has OR `exp(1.245273)=3.47`, not the hinge-only 6.43. Evidence: `models.py:38-43`; `outputs/metrics/glm_coefficients.csv:12-18`.

### 6. Tree models and constraints

| Algorithm | Hyperparameters | Role/regularization | Weights/stopping/tuning | Monotonic constraints | Final |
|---|---|---|---|---|---|
| `HistGradientBoostingClassifier` | LR .05; leaves 15; min leaf 100; 400 iterations; library-default other controls | Full/matched/group/replay challengers | No weights; early stopping false; five-config 2023 log-loss grid | **None** | Challenger |

Matched-information, whole-loan, and yearly replays reuse the selected configuration. No monotonic constraints are supplied. Evidence: `config.py:97-132`; `models.py:290-350`.

### 7. Model specification and selection

Champion is the nonlinear GLM with trailing-six-month count-level intercept recalibration; GBM is challenger. The GBM edge is concentrated below $60k; matched-feature GBM adds little; GLM has better raw Brier/calibration and interpretability. Evidence: `model_comparisons.csv:2-7`; `deck_main.py:257-275`.

The champion decision and low-balance hinges were informed by 2024–2026. The candidate discloses this. Disclosure improves judgment but does not restore final-test independence.

### 8. Validation and leakage review

- Fit through 2023-12: 215,757 rows/3,118 events.
- GBM tuning fit through 2022; validation 2023.
- Backtest 2024-01–2026-04: 317,244/3,007.
- Rolling replays: train through 2020/21/22, test 2021/22/23.
- Secondary 20% loan holdout: 107,225/1,223.

Calendar mechanics, training-fitted learned preprocessing, no weighting, monthly count/UPB diagnostics, and COVID/refi-wave retention are strong. G3 fails because future modification status enters both final models. The backtest is post-selection. The whole-loan GBM reuses hyperparameters selected before the group split, so held-out loans influenced selection; it is not nested independent evidence. Evidence: `config.py:38-58`; `cleaning.py:130-135`; `models.py:204-210,234-240`; `pipeline.py:451-502`.

### 9. Metrics and calibration

| Metric | GLM | GBM | Count-dial GLM | Evidence |
|---|---:|---:|---:|---|
| ROC / PR | .67008/.02584 | .67870/.02560 | Same rank | Independently verified from submitted output |
| Log loss / Brier | .05225/.009358 | .05275/.009471 | N/A/.009339 | Independently verified from submitted output |
| Predicted/actual | 1.2682%/.94785% | 1.3679%/.94785% | .9538%/.94785% | Independently verified from submitted output |
| O:P | .747 | .693 | .994 | Independently verified from submitted output |
| Monthly top-20 capture | 40.74% | 41.24% | Rank unchanged | Independently verified from submitted output |
| UPB P/A | 1.285 | N/A | .967 | Independently verified from submitted output |
| Slope/intercept | Not reported | Not reported | Intercept shift implemented, deltas absent | Not available |
| Monthly SMM MAE | 31.39bp raw | N/A | 10.24bp | Independently verified from submitted output |
| CPR | Exact `1-(1-SMM)^12` proxy | Same | Same | Independently verified from submitted output |

The recalibration at `evaluation.py:402-416` uses only prior realized months, so it is leakage-free month by month. It fixes level, not slope or segment error.

### 10. Economic interpretation

Incentive, age, MTM LTV, active penalty, and tiny-balance payoff channels are coherent. The strong negative modification effect is contaminated by future-known non-events and cannot be interpreted economically. Burnout is positive, not classical burnout; the candidate reports rather than forces the expected story. The low-balance effect may reflect maturity, cleanup, turnover, or curtailment and cannot identify cause. Cash-flow use is limited to full-payoff count/UPB speed, not total CPR, scheduled principal, curtailment, WAL, or P&L.

### 11. Code and software engineering

Strengths: clear staged entrypoint, centralized paths/config, exact pins/seed, target tests, atomic publication, manifests, stale-stage checks, broad tests, and no hidden notebook. Weaknesses: nearly 10,000 source lines and 48 slides are disproportionate; deck cannot be regenerated exactly; no CI/lint/type config; predictions intentionally absent; deterministic-build claim is weakened by random UUID/current timestamps.

### 12. Demonstrable defects and concerns

| Severity | Classification | Evidence | Why / gate effect | Correction |
|---|---|---|---|---|
| Material | Verified defect | `cleaning.py:130-135`; `dataset.py:310-316`; `models.py:204-210,234-240` | Raw modification flag exposes 1,549/333/156 future-effective rows; OR .4700; G3 fails | Gate modification by effective/availability date or remove it |
| Material | Verified defect | `README.md:95-109`; `deck_main.py:229-240` | 2024–26 changes form/champion; G5 fail | Reserve a later untouched period |
| Moderate | Packaging issue | manifest/tests/PPTX XML | 48 delivered vs 49 expected/hash mismatch | Align source/tests/manifest/deck |
| Moderate | Verified defect | `models.py:129-137`; coefficient CSV | Hinge-only OR 6.43 misread; total ~3.47 | Compute cumulative local slopes |
| Moderate | Strong concern | `pipeline.py:489-502` | Whole-loan holdout nonnested | Split groups before tuning |
| Moderate | Missing evidence | `evaluation.py:42-87` | No global slope/intercept | Report on untouched data |
| Moderate | Missing evidence | `dataset.py:35-57,194-209` | Final-vintage revision caveat | Use vintages/sensitivity |
| Minor | Interview question | `models.py:290-296` | No GBM monotonicity | Test constrained incentive challenger |
| Minor | Verified defect | `pipeline.py:306-340` | Rebuild not byte-deterministic | Stable content-derived IDs |
| Moderate | Strong concern | README/deck source | Over-scoped artifact surface | Reduce primary deck/code layers |

### 13. Candidate verdict

**Hard gate: Fail—future modification status and post-selection 2024–2026 evidence. Score: 71/100. Confidence: high. Recommendation: Conditional interview.**

| Target | Validation | Method | Features | Communication | Reproducibility | Judgment | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | 10 | 12 | 11 | 7 | 7 | 4 | 71 |

Top positives: exact absorbing target; strong count/UPB/model-risk engineering; candid limitations and true GLM nonlinearities.  
Top concerns: future modification status with a large fitted effect; no untouched final test; deck/low-balance/entity-holdout interpretation defects.

Live questions:

1. Why is `mod_flag` positive before `mod_ft_pay_dt`, and how would you gate it?
2. List every post-2024–2026 specification change.
3. Derive the net below-$22k balance slope.
4. Redesign the whole-loan holdout nested within training.
5. Add calibration slope/intercept and explain count versus UPB dials.

Live code modification: rebuild `mod_flag` point-in-time, assert no future-effective modification features, and report changed model rows before any refit.

## Karan Allagh
**Final rank: 6.**
### 1. Submission inventory

The six-member outer ZIP contains memo PDF, code ZIP, deck PDF/PPTX, response dump, and memo Markdown. The nested code has six scripts, one target test, README/model card/requirements, metrics/coefficients/importance, and seven PNGs. Extracted files hash-match archives; stray `Thumbs.db` is excluded. PPTX has 15 slides.

Run order is target → features → models → charts → deck → validation, but there is no single entrypoint. Missing `model_data.parquet`, predictions, fitted LightGBM, preprocessing state, selected iteration, and run log prevent full lineage. Default `DATA_DIR` resolves to an extra nested `Karan Allagh` directory. Evidence: `code/README.md:6-32,46-52`; `code/build_target.py:30-35`.

### 2. Target and panel construction

The code parses dates, drops exact duplicates, sorts, truncates at first PD, shifts next status/date, restricts to current rows with a successor, asserts exact month adjacency, and writes predictor-month actuals. Evidence: `build_target.py:38-82`.

Audit:

- Exact absorbing 533,001 rows, 6,125 events, 24,411 loans.
- Binary three-column dump, zero nulls/duplicates/gaps/terminal zeros.
- Exact independent row/label match.
- 17,000 terminal current rows correctly censored.
- Removing absorption would add 15 post-PD zeros.

Target tests cover event alignment, final censoring, distressed payoff exclusion, absorption, and gaps. `tests/test_target.py:33-107`.

### 3. Data cleaning and point-in-time handling

LTV units, invalid FICO/DTI, purpose/doc/IO/penalty flags, note-rate fallback, and age are normalized. PMMS uses `t-1`; GLM imputation uses training medians; IDs are not features. Evidence: `clean_features.py:59-145`; `train_models.py:103-106`.

`hpi_now` joins same-month `r_dt`; HPA and current LTV consume it. The HPI file has no release/availability/vintage field. Under a strict production PIT rule, availability is not established and the gate fails. `clean_features.py:181-196`.

Blank penalty flags become no-penalty. `pp_penalty_unknown` is created but omitted from both models; this affects 109,615 target rows, 2,960 loans, and 1,493 events. Evidence: `clean_features.py:88-91,219-230`.

Modification also fails PIT. `mod_flag=(mod=="Y")` is included in the GLM and LightGBM without gating by `mod_ft_pay_dt`. The shared affected cohort is 1,549 pre-2024, 333 in 2024, and 156 in 2025+, all non-events; submitted modification OR is .4130. Evidence: `clean_features.py:101-104,220-226`; `train_models.py:86-90,145-150`.

### 4. Feature engineering

| Feature | Formula | Sources | Rationale | Available | Missing | Shape | Final? | Expected | Observed | Concern |
|---|---|---|---|---|---|---|---|---|---|---|
| Incentive | `coupon-PMMS_(t-1)` | Rates | Refi option | `t/t-1` | Fallback/ffill | Hinges 0/2 + interactions | Both | Rising, flatter deep ITM | Slopes +.346,+.518,+.161 | Agency PMMS proxy |
| SATO | `o_coupon-PMMS_orig` | Orig rate/macro | Pricing | Origination | Train median | Straight/tree | Both | Context | Near null | Generic rate |
| Burnout | `cummax(incentive)-current incentive`, floor 0 | History | Forgone opportunities | Through `t` | None | Straight/tree constrained − | Both | Negative | GLM positive/null | Left-truncated; sign conflict |
| Age | Date/source age | Age | Seasoning | `t` | Backfill | Hinges 12/36 | Both | Ramp/fade | Strong first year, later decline | Uncapped to 309m |
| Balance/paydown | `log(max(o_bal,1000))`; factor only in current LTV | Balances | Dollar economics | Origination/`t` | Median | Log+interaction/tree | Both | Larger more responsive | Positive ITM interaction | No direct current balance/curtailment |
| LTV/CLTV/HPA | `orig_ltv*clip(bal/o_bal,0,1.5)/(HPI_t/HPI_orig)`; HPA12 | Leverage/balance/HPI | Equity | Same-month HPI | Train median | Line+≤80 flag/tree | Both | LTV −, HPA + | Correct signs | PIT failure; CLTV unused |
| FICO/DTI/DSCR | Clean FICO/DTI; DSCR indicator/tree ratio | Static | Access/capacity | Origination | Median+flags/native | Lines/tree | Both | Mixed | Mostly null | Raw DSCR omitted from GLM |
| Doc/occ/purpose/property | Normalized categories | Static | Segment behavior | Origination | Missing/OTHER | One-hot/native | Both/tree | Level-specific | Full doc positive | Some code semantics opaque |
| IO/mod/DQ/foreign/product | IO and raw-derived `mod_flag`; no DQ/foreign/product | Contract/history | Segment/friction | Purportedly `t`/origination | Defaults | Binary | Partial | Heterogeneous | Modification OR .4130 | 2,038 future-effective modification rows; important omitted groups |
| Calendar/rates | Sine/cosine month; PMMS through incentive | Date/macro | Seasonality/regime | `t/t-1` | Ffill | Cyclic | Both | Cyclic | Sine positive | No explicit year/regime |
| Penalty | Active gate; months left; expiry buckets | Flag/term/age | Friction and expiry | `t` | Unknown→no penalty | Interactions + buckets | Both | Active −; expiry lift | ORs 1.66/1.48/1.49 around expiry | Unknown handling; hard cliffs |
| Missing | FICO/DTI flags; penalty unknown unused | Fields | Data quality | `t` | Explicit | Binary | Partial | Data-dependent | Null | Major unknown cohort collapsed |
| Reporting/unused | Current balance path, CLTV, foreign, product, DQ, vintage, cumulative open-panel chart | Various | Diagnostics | Evaluation | Various | Reporting | No | N/A | N/A | Open-panel cumulative chart invalid |

Evidence: `clean_features.py:98-216`; `train_models.py:46-100,144-189`.

### 5. Logistic/GLM feature shape

| Group | Classification | Exact treatment |
|---|---|---|
| Incentive | Degree-1 hinges + interactions | `min(x,0)`, `clip(x,0,2)`, `max(x-2,0)`; interact with active penalty; positive segment interacts with log balance |
| Age | Degree-1 hinges | Knots 12/36; segment scaling /12,/24,/60 |
| Penalty event time | Fixed buckets | [−3,0), [0,6), [6,12) months relative expiry |
| Original balance | Log + interaction | `log(max(o_bal,1000))-12.5` |
| Current LTV | Cap [0,200] + line + threshold | `/100` plus `LTV<=80` indicator |
| Burnout | Floor 0 + straight | No upper cap |
| HPA/SATO/FICO/DTI | Straight after cleaning | FICO valid 300–850; DTI 0–100 |
| Calendar | Cyclic fixed basis | sine/cosine annual |

No cubic splines or quadratics. The penalty differential can reverse for sufficiently OTM loans, and burnout’s GLM sign opposes the imposed tree prior; both require defense.

### 6. Tree models and constraints

| Algorithm | Hyperparameters | Role/regularization | Weights/stopping/tuning | Monotonic constraints | Final |
|---|---|---|---|---|---|
| LightGBM | objective binary; LR .05; leaves 31; min leaf 500; feature/bagging .8; bag every round; L2 5; max 2,000; seed 7 | Flexible challenger | No weights; early stopping 100 on 2023, fit through 2022; refit through 2023 | Incentive +1; log original balance +1; current LTV −1; burnout −1; penalty months left −1 | Challenger |
| “Ceiling” LightGBM | Same broad controls; 600 rounds | Contemporaneous diagnostic | Trains non-holdout loans through 2024–26, scores holdout same period | None | Not a candidate model |

The main constraints are genuine. The “ceiling” is not an upper bound and exceeding it would not imply leakage. Evidence: `train_models.py:144-189,289-330`.

### 7. Model specification and selection

Champion is unweighted statsmodels Binomial GLM with loan-clustered covariance; constrained LightGBM is challenger. Tree lift collapses OOT, supporting GLM transparency. Submitted AUCs are GLM/LGBM .7305/.8499 in-sample, .7351/.7389 pre-2024 loan holdout, .6810/.6824 OOT non-holdout, and .6845/.6852 OOT loan holdout.

The “honest test” is also used for nested feature-family ablation and champion justification. Evidence: `train_models.py:251-286,387-433`; `memo.md:42-52`. It is development/OOT evidence, not untouched final evidence.

### 8. Validation and leakage review

- Fit: random 80% loan group, through 2023-12.
- Tree early-stop fit: through 2022; validation 2023.
- OOT: 2024-01–2026-04.
- Loan holdout: random 20% of loan IDs, reported pre-2024 and 2024+.
- No rolling-origin validation.

Chronology, loan-group split, training medians, no class balancing, and count/balance reporting are strengths. Future modification status, same-month HPI, and final-window ablation fail strict gates. COVID/refi-boom behavior is narrated but not isolated. Evaluation is mostly count weighted; balance weighting is aggregate only.

The cumulative chart compounds monthly cross-sectional means over a changing open panel. January 2024 has 7,610 loans; April 2026 has 15,572; only 4,289 appear in all 28 months. It is a synthetic hazard index, not realized fixed-book prepaid share. Evidence: `make_charts.py:267-295`.

### 9. Metrics and calibration

| Metric | GLM | LGBM | Evidence |
|---|---:|---:|---|
| OOT ROC / PR | .6810/.0220 | .6824/.0261 | Independently verified from submitted output |
| OOT log loss / Brier | .05136/.009294 | .05134/**.009301** | Independently verified from submitted output |
| Predicted / actual / O:P | 1.059%/.943%/.890 | Level closer balance-weighted | Independently verified from submitted output |
| Top-10 capture/lift | 28.1%/2.81× | Similar ranking | Independently verified from submitted output |
| Count CPR | 12.0% predicted vs 10.8% actual | N/A | Independently verified from submitted output |
| Balance CPR | 13.06% GLM; 12.55% LGBM vs 12.34% actual | — | Independently verified from submitted output |
| Slope/intercept | N/A | N/A | Not available |
| Monthly | Chart 2018–2026; table/predictions absent | Same | Candidate-reported only |
| Cumulative share | 25.2% GLM vs 22.5% “actual” | — | Invalid construction |

The LightGBM Brier value `.009301` is the decimal conversion of machine-readable `brier_x100=.9301` in `Karan Allagh/output/metrics.json`.

### 10. Economic interpretation

Incentive, seasoning, leverage, HPA, size interaction, and penalty expiry are strong concepts. The very negative modification effect is contaminated by future-known non-events and cannot support interpretation. Full-doc “agency graduation” and 2023-vintage diagnoses are hypotheses, not causal findings. Burnout’s GLM sign conflicts with the narrative and tree prior. Rate shocks hold burnout fixed, so they are partial derivatives, not coherent full scenarios. The current open-panel chart is not a pool-factor tie-out.

### 11. Code and software engineering

Strengths: compact modular scripts, exact pins, fixed seeds, meaningful target tests, month/event assertions, loan-clustered covariance, no unsafe dependencies, proportionate complexity. Weaknesses: six manual commands, ambiguous default path, import-time deck writing, assertions removable under `-O`, incomplete tests, total-only response/model validator, missing fitted/prediction artifacts, hardcoded deck metrics, and no CI/version/checksum/run log.

### 12. Demonstrable defects and concerns

| Severity | Classification | Evidence | Why / gate effect | Correction |
|---|---|---|---|---|
| Material | Verified defect | `clean_features.py:101-104,220-226`; `train_models.py:86-90,145-150` | Raw modification flag exposes 1,549/333/156 future-effective rows; OR .4130; G3 fails | Gate modification by effective/availability date or remove it |
| Material | Verified defect | `train_models.py:251-286,387-433` | OOT used for ablation/champion; G5 fail | Later untouched window/nested walk-forward |
| Material | Strong concern | `clean_features.py:181-196` | Same-month HPI availability unproven; G3 fail strict | Availability-date/vintage join |
| Material | Verified defect | `make_charts.py:267-295` | Open-panel cumulative share invalid | Fixed-cohort survival/pool factor |
| Moderate | Verified defect | `train_models.py:289-330` | “Ceiling” not upper bound | Rename contemporaneous benchmark |
| Moderate | Verified defect | `clean_features.py:199-205` | Burnout begins at panel entry | Rename/reconstruct full history |
| Moderate | Strong concern | `clean_features.py:88-91`; feature lists | Unknown penalty becomes no penalty | Explicit unknown category |
| Moderate | Missing evidence | `validate_outputs.py:35-48` | Model/prediction row agreement not auditable | Exact key/hash reconciliation |
| Moderate | Interview question | Coefficients/deck | Burnout/penalty claims overstate signs | Conditional curves with clustered CIs |
| Minor | Packaging issue | `make_deck.py`; validator | Hardcoded deck/output lineage | Populate/validate from one result artifact |

### 13. Candidate verdict

**Hard gate: Fail—future modification, same-month HPI, and OOT reuse. Score: 68/100. Confidence: high. Recommendation: Conditional interview.**

| Target | Validation | Method | Features | Communication | Reproducibility | Judgment | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | 9 | 12 | 9 | 8 | 7 | 3 | 68 |

Top positives: exact/tested absorbing target; economically strong GLM and genuinely constrained challenger; candid calibration miss.  
Top concerns: future modification and same-month HPI PIT failures; no untouched final test; invalid cumulative/ceiling claims and unknown-penalty handling.

Live questions:

1. Why is `mod_flag` positive before `mod_ft_pay_dt`, and how would you gate it?
2. Prove which HPI observation was available in January 2024.
3. State when every knot/bucket/feature/champion choice was frozen.
4. Rebuild the cumulative chart as a fixed-cohort survival test.
5. Explain positive burnout, the OTM penalty reversal, and immutable lineage.

Live code modification: gate/remove modification before its effective date, assert no future-effective flags, and report changed train/OOT rows without refitting.

## Daniel Li
**Final rank: 5.**
### 1. Submission inventory

The canonical outer ZIP contains `code.zip`, `loan_date_response.parquet`, and 14-page `Slides.pdf`. `code.zip` has 37 logical files: project/lock/pre-commit/Python-version metadata, README, methodology documentation, CI, 20 package modules, and nine unit tests. Extracted `code/` and `code/code/` are byte-identical extraction duplicates; Mac metadata is excluded.

One CLI defines the complete stage order. Dependencies are locked; CI runs static checks/tests. Generated summaries, metrics, predictions, spline state, figures, fitted models, editable deck source, and deck-build code are absent despite README references, preventing model-result reconciliation. Evidence: `Daniel Li.zip::code.zip::code/libremodel/cli.py:28-109,184-199`; `code/README.md:92-137`.

### 2. Target and panel construction

The target trims IDs, full-row deduplicates, sorts, shifts lead status/date, computes month gap, retains current rows with an exact one-month successor, and sets response from lead `PD`. The dump validates unique keys, non-null fields, and binary values. Evidence: `code/libremodel/target.py:29-82`.

Audit:

- Submitted raw target exactly matches the non-absorbing benchmark: 533,016 rows, 6,125 events, 24,412 loans, 2015-07–2026-04.
- Zero nulls, duplicate keys, extras, omissions, or label mismatches.
- Fifteen post-first-PD zeros across two loans remain in the dump; the later model sample removes them.
- Final model sample is 513,419 rows/5,984 events: train 310,196/3,853; validation 64,921/567; test 138,302/1,564.
- Full-row `.unique()` is fragile for conflicting same-key records, though the submitted 600 duplicate groups are exact.

The raw target is exact; the dump is not the final modeled population.

### 3. Data cleaning and point-in-time handling

Rates/LTV/CLTV in `(0,1]` are scaled; DTI zero/999 becomes missing with a flag; categories normalize; invalid core fields trigger whole-loan exclusion. Train-only medians/scaling/Formulaic state are used; final refit uses train+validation only. Incentive and unemployment use `t-1`; report HPI uses `t-1`, HPI12 uses `t-13`, and origination rates/HPI use origination month. Evidence: `cleaning.py:12-98,106-137`; `preprocessing.py:98-189,259-294`; `features.py:76-202`.

The decisive defect is whole-loan impossible-transition quarantine:

```text
loan_has_impossible_transition = max(flag over complete future history)
```

It excludes every row of that loan. Evidence: `sample_selection.py:61-88,99-116`; `docs/modeling_pipeline.md:191-208`.

Independent reconciliation:

- 266 flags across 213 loans.
- Exclusive rows removed because a later split contains the first flag: **1,180 train** and **172 validation**; gross counts 1,207/178 include rows also failing core eligibility.
- All 3,331 pre-flag removed rows are non-events; 3,234 would otherwise be eligible.
- Future-aware core-field whole-loan scanning has **no incremental effect in this panel** because the selected core fields are constant within loan; row-level and whole-loan invalidity remove the same rows.

The impossible-transition rule is a real PIT/sample-selection failure even though removed pre-flag rows are all non-events; that fact identifies the bias direction rather than curing it.

### 4. Feature engineering

| Feature | Formula | Sources | Rationale | Available | Missing | Shape | Final? | Expected | Observed | Concern |
|---|---|---|---|---|---|---|---|---|---|---|
| Current incentive | `coupon_t-PMMS_(t-1)` | Rates | Refi option | `t/t-1` | None | Cubic B-spline | Yes | Rising/nonlinear | .36%→3.05%; significant | Unconstrained extrapolation |
| SATO proxy | `o_coupon-PMMS_orig` | Origination rate/macro | Pricing selection | Origination | None | Straight | Yes | Context | Weak negative/null | Generic PMMS |
| Burnout/history | Cummax incentive; months incentive>.5 | Historical incentive | Opportunity exposure | Through `t` | Missing=false | Straight | Yes | Saturation/negative interaction | Max weak; months positive | No area/fade/current interaction |
| Age | Source age | Age | Seasoning/burnout | `t` | None | Cubic spline | Yes | Hump | Peak ~57m | Penalty expiry omitted |
| Balances/paydown | `log(bal)` | Current balance | Dollar economics | `t` | Nonpositive null | Cubic spline | Yes | U-shape | Reported U-shape | No original balance/factor/curtailment |
| LTV/CLTV/HPA | Original CLTV spline; HPI growth lines | CLTV/HPI | Leverage/equity | Origination/`t-1` | Train medians/flag | Spline + lines | Yes | CLTV −, HPA + | CLTV rising/null; HPA12 positive | No current LTV/CLTV |
| FICO/DTI/DSCR | FICO spline; DTI/DSCR lines + availability flags | Underwriting | Access/capacity | Origination | Exclude/median/flags | Spline/lines | Yes | Mixed | Mostly weak; DTI-missing significant | FICO ceiling 899; zero current rates remain |
| Doc/occ/purpose/property | Purpose/occupancy only | Static | Segment behavior | Origination | Unknown | One-hot | Yes/unused | Level-specific | Group tests weak | Doc/property omitted |
| IO/mod/DQ/foreign/product | Longest DQ and months since DQ; others unused | History/static | Friction/segment | Through `t` | Median/flags | Ordinal/line | DQ yes | DQ − | Weak | IO/mod/foreign/product omitted |
| Calendar/rates | Month categorical; unemployment spline | Date/macro | Seasonality/regime | `t/t-1` | Past-fill | Category/spline | Yes | Regime-specific | Unemployment hump | No explicit absolute-rate regime |
| Penalty | None in model | Penalty flag/term/age | Contract friction | `t` | Structurally complete among yes loans | Not used | No | Active −; expiry lift | Unadjusted active event rate .637% vs 1.326% after term | Discarded for wrong missingness rationale |
| Missing | DTI, DSCR, DQ, HPI flags | Fields | Data quality | `t` | Explicit | Binary | Yes | Data-dependent | Mostly weak | Combined HPI failure flag |
| Challenger | Incentive×FICO; unemployment×incentive; df-5 splines | Final inputs | Flexible interactions | Same | Same | Spline interactions | No | Context | D best validation metrics | Selection threshold subjective |
| Reporting/unused | Original balance, balance factor, current leverage, penalty, doc/property/IO/mod/foreign/product/SP500 | Supplied fields | Economic candidates | Various | N/A | Not used | No | N/A | N/A | Material omissions |

Evidence: `features.py:52-202`; `preprocessing.py:18-107`; `modeling.py:70-107`.

### 5. Logistic/GLM feature shape

The final six spline variables use Formulaic `bs(feature, df=3, degree=3, extrapolation="extend")`; no explicit knots/bounds/caps are provided and serialized spline state is absent.

| Group | Classification | Exact treatment |
|---|---|---|
| Current incentive, age, log balance, FICO, original CLTV, unemployment | Cubic B-spline | Degree 3, df 3, learned fit-sample edges, extend extrapolation |
| Current balance | Log + spline | `log(bal)` then standardize/spline |
| Origination incentive, maximum incentive, months ITM, DTI, DSCR, DQ variables, HPI growth | Straight | Median/standardize where needed |
| Longest delinquency | Fixed-bucket-derived ordinal + line | Status map 0/30/.../270, cumulative max |
| Challenger C | Spline interactions | 3×3 basis products for incentive×FICO and unemployment×incentive |
| Challenger D | Cubic B-splines | Degree 3, df 5 for same six variables |
| Penalty expiry/current LTV/paydown | Not used | No shape |

Evidence: `preprocessing.py:18-90`.

### 6. Tree models and constraints

No tree model was submitted.

| Algorithm | Hyperparameters | Role | Weights/stopping | Monotonic constraints | Final |
|---|---|---|---|---|---|
| None | N/A | GLM-only submission | No weighting/resampling | None | N/A |

### 7. Model specification and selection

All candidates are unweighted Statsmodels binomial-logit GLMs fitted by Newton with max 200 and loan-clustered covariance for inference. Variants:

| Variant | Shape | Interactions | Validation log loss / AUC | Status |
|---|---|---|---|---|
| A | All lines | None | .04947 / .624 | Baseline |
| B | Six df-3 splines | None | .04895 / .635 | Selected |
| C | B | Incentive×FICO; unemployment×incentive | .04894 / .634 | Rejected |
| D | Six df-5 splines | None | .04890 / .640 | Rejected |

B is chosen as the simplest material improvement, although D wins both reported validation metrics and no predeclared tolerance/uncertainty rule is supplied. Evidence: `modeling.py:70-107,446-525`; `Slides.pdf` extracted text lines 141-166.

### 8. Validation and leakage review

| Set | Predictor dates | Raw target | Final sample |
|---|---|---:|---:|
| Train | 2015-07–2024-12 | 322,541/3,954 | 310,196/3,853 |
| Validation | 2025-01–2025-06 | 67,344/581 | 64,921/567 |
| Test | 2025-07–2026-04 | 143,131/1,590 | 138,302/1,564 |

Split mechanics, train-only preprocessing, final refit, and same-loan chronology are sound. Whole-loan future quarantine makes the population prospectively unavailable and therefore fails PIT/chronology overall. No rolling-origin, monthly O:P, COVID/rate-regime, UPB, segment, or deal validation is supplied. Test-tuning provenance is unclear because generated artifacts/commit history are absent.

### 9. Metrics and calibration

| Metric | Result | Evidence |
|---|---|---|
| ROC-AUC | Train+validation .709; test .670 | Candidate-reported only |
| PR-AUC | Not available | Not available |
| Log loss | .060305 fit; .059851 test | Candidate-reported only; slide rounding inconsistency |
| Brier | .011119 test | Candidate-reported only |
| Predicted / actual / O:P | 1.1346% / 1.1309% / .997 | Candidate-reported only |
| Lift/capture | Fit 3.34×/33.4%; test 2.41×/24.1% | Candidate-reported only |
| Slope/intercept | None | Not available |
| Monthly/UPB/CPR | None | Not available |
| Deterioration | AUC −.039; lift −.93×; capture −9.3pp | Candidate-reported only |

The aggregate test mean is strong, but no prediction artifact, monthly series, or slope/intercept allows independent or temporal calibration assessment.

### 10. Economic interpretation

Incentive, balance U-shape, and HPI-growth effects are coherent. The 57-month age peak cannot be attributed cleanly to burnout when penalty expiry is omitted. Positive DTI/CLTV curves are weak conditional estimates and should be investigated rather than declared wrong. Close pooled calibration does not establish pool cash-flow accuracy without monthly/UPB evidence.

### 11. Code and software engineering

Strengths: clear package/CLI, relative paths, exact lock, focused tests, CI/lint/type/pre-commit, detailed docs, and no hidden notebook. Weaknesses: no full-pipeline integration test, generated artifacts absent, `.env` workflow awkward, one CLI command falls through to a greeting, redundant design-matrix paths, and somewhat excessive infrastructure. Evidence: `cli.py:139-146,177-181`; README/CI.

### 12. Demonstrable defects and concerns

| Severity | Classification | Evidence | Why / gate effect | Correction |
|---|---|---|---|---|
| Material | Verified defect | `sample_selection.py:61-88,99-116` | Future transitions alter prior membership; G3/G4 fail | Exclude affected row and later only |
| Moderate | Verified defect | `target.py:98-103`; sample code | Raw dump has 15 post-PD rows and differs from model sample | Separate/align raw and final actuals |
| Material | Strong concern | `docs/modeling_pipeline.md:104-106` | Penalty term structurally complete among yes loans but omitted | Active/remaining/expiry/post-expiry features |
| Moderate | Verified defect/packaging | `Slides.pdf` extracted text lines 407-410; `feature_analysis.py:310-342` | Deck claims shared axes/95% bands absent from source | Make code generate exact figure/table |
| Moderate | Missing evidence | README artifact list | Metrics/predictions absent | Submit compact outputs/manifest |
| Moderate | Missing evidence | `validation.py:55-77` | No PR/slope/monthly/UPB/CPR | Add model-risk suite |
| Minor | Interview question | `cleaning.py:36-45` | 19 zero current rates retained | Audit/treat as missing |
| Moderate | Interview question | Variant table | D wins but B chosen without rule | Predeclare complexity-performance rule |
| Minor | Strong concern | `target.py:29-38` | Full-row dedup fragile on conflicting keys | Explicit conflict assertion |

### 13. Candidate verdict

**Hard gate: Fail—future-dependent whole-loan sample quarantine. Score: 71/100. Confidence: high on factual findings; moderate on score. Recommendation: Conditional interview.**

| Target | Validation | Method | Features | Communication | Reproducibility | Judgment | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 18 | 11 | 14 | 11 | 6 | 8 | 3 | 71 |

Top positives: exact raw target; transparent nonlinear GLM and honest deterioration; excellent static engineering.  
Top concerns: future-dependent sample population; raw dump/final-sample mismatch; structural penalty omission and missing model-result lineage.

Live questions:

1. Why is removing an early row due to a later anomaly invalid prospectively?
2. Reconcile 533,016 raw actuals with 513,419 modeled rows.
3. State the rule that selects B over D.
4. Build and interpret penalty-expiry features.
5. Explain operational label timing at split boundaries.

Live code modification: replace whole-loan impossible-transition quarantine with point-in-time row-and-forward exclusion and a cross-split regression test.

## Xin Xu
**Final rank: 7.**
### 1. Submission inventory

The outer ZIP contains `prepayment_actuals.parquet`, matching 16-slide PPTX/PDF, and a 22-file code ZIP. Root and `xin_xu_prepayment_code/` trees duplicate the inner ZIP exactly. Logical files include `run_pipeline.py`, README/memo, two requirements files, four core modules, 12 experiment/final/reporting modules, and a JS deck builder.

The intended order spans data, baseline, rounds 2–6, final model, deck data, plots, and Node deck. The default entrypoint instead runs data → model → figures, while figures immediately require final artifacts produced only by later stages. No `outputs/` directory is submitted despite README claims; missing artifacts include predictions, metrics, manifests, coefficients, backtests, importance/PDP tables, and figure sources. Evidence: `run_pipeline.py:20-31`; `src/plots.py:367-391`; `README.md:24-26,89-105`.

### 2. Target and panel construction

The source full-row deduplicates, strips IDs with collision assertion, parses/sorts, truncates after first PD, asserts consecutive months, shifts next status/date, restricts to current exact-next-month rows, and exports predictor-month actuals. Evidence: `src/data_prep.py:49-124,133-170`.

Audit:

- Exact absorbing 533,001 rows, 6,125 events, 24,411 loans.
- Three columns `loan,date,response`, binary, zero nulls/duplicates/gaps/terminal zeros.
- Exact independent match; 17,000 terminal current rows censored and 15 post-PD risk rows prevented.

Target/dump gates pass fully.

### 3. Data cleaning and point-in-time handling

Dates/categories/booleans/sentinels/units are normalized centrally; macro uses `t-1`, HPI `t-2`, with geography/state/prior fallback and young-loan suppression. GLM transforms are train-fitted; CatBoost uses native missing; IDs/future target fields are excluded. Evidence: `data_prep.py:34-107,177-248`; `modeling.py:70-83`.

Material modification leakage:

- Code uses current `mod` and `mod_seasoning = r_dt-mod_ft_pay_dt` without gating future dates. `data_prep.py:84-86,357-361`.
- 3,807 panel rows have `mod_ft_pay_dt>r_dt`; every row already says `mod=Y`. Leads span 1–99 months; the exact risk-set median is 18 months.
- 2,038 enter risk set: **1,549 train / 333 validation / 156 test**, zero events.
- Final GLM uses `mod_flag`; final CatBoost uses `mod_flag` and `mod_seasoning`.

This is direct PIT failure. HPI vintage revision, zero/missing rate handling, and occupancy normalization are secondary concerns.

### 4. Feature engineering

| Feature | Formula | Sources | Rationale | Available | Missing | Shape | Final? | Expected | Observed | Concern |
|---|---|---|---|---|---|---|---|---|---|---|
| Incentive | `rate_gap=coupon-PMMS_(t-1)`; positive gap; `bal*gap_pos/100` | Rates/balance | Refi option/dollars | `t/t-1` | Median/native | Spline/hinge/tree | Both | Rising S-curve | Kink near +1pp reported | Final CB unconstrained |
| SATO/attainable rate | Orig SATO; own/rolling attainable gaps | Orig/current rates, PMMS | Borrower-specific rate | Historical/`t-1` | Median/native | Lines/tree | Both | Positive gap | Positive profile | Approximate static SATO |
| Payment saving | Annuity payment ratio, rem term [12,480] | Rates/term | Monthly savings | `t` | Median/native | Nonlinear formula | Both | Increasing | Reported monotone | IO payment approximated incorrectly |
| Burnout/history | Cumulative ITM/area/max/EWMAs/run length | Incentive history | Prior opportunity | Through `t` | Various | Lines/tree | Both | Attenuation | Slow burnout reported | Final coefficients absent |
| Age/term | Age spline; remaining term | Dates/term | Seasoning | `t` | Median/native | Cubic spline/tree | Both | Hump | 13–24m ramp | No final knots artifact |
| Balances/paydown | `log1p(bal)`, factor, 1m/3m paydown, scheduled curtailment | Balance history | Dollar/path behavior | Through `t` | Median/native | Log/ratios/caps | Both | Curtailment + | Reported positive | Post-IO schedule error |
| LTV/CLTV/HPA | `100*bal/(orig_value*HPIratio)`, cap [0,250]; HPA/YoY | Leverage/balance/HPI | Equity | HPI `t-2` | Flags/native | Spline/tree | Both | LTV − | Low LTV faster | Misnamed CLTV; other liens absent |
| FICO/DTI/DSCR | Clean levels | Underwriting | Access/capacity | Origination | Flags/median/native | Lines/tree | Both | Mixed | Not shown | Final coefficients absent |
| Doc/occ/purpose/property | Normalized categories | Static | Segment behavior | Origination | Unknown/native | One-hot/tree | Both/CB | Level-specific | Importance only | Occupancy not common-normalized |
| IO | Flag, months to expiry, expiring-6m | IO fields/age | Payment reset | `t` | Flags/native | Clock/binary/tree | Both | Event-time | Not shown | Payment/schedule approximation |
| Modification | Flag, seasoning, recent-12m | Mod fields | Post-mod behavior | Should be PIT | No gating | Flag/clock/tree | Both | Often slower | Affected rows zero-event | Direct future leakage |
| DQ | Ever DQ, months since, spell count, buckets | Status history | Refi friction | Through `t` | Buckets/native | Flags/lines/tree | Both | Recent DQ − | Not shown | Final constants conflict with documentation describing these features as rejected |
| Foreign/product | Foreign category; lien flag; product dropped | Static | Segment/product | Origination | Unknown/native | Category/binary | CB/both | Heterogeneous | Not shown | Product rationale undocumented |
| Calendar/rates | Month/quarter; PMMS level/changes/min36; unemployment | Date/macro | Regime | `t/t-1` | Required | Categories/lines/tree | Both | Regime-specific | Large annual instability | Only ~130 macro months |
| Penalty | Months to expiry; active; buckets; event flags/interactions | Penalty/term/age | Contract clock | `t` | Unknown bucket | Buckets/lines/tree | Both | Active −; expiry lift | Baseline OR .49; recent expiry 1.11 | Event dummies remain despite “rejected” claim |
| Missing | DTI/FICO/DSCR/LTV/HPI flags | Fields | Data quality | `t` | Explicit | Binary/native | GLM/CB | Data-dependent | Not shown | Rate/SATO flags absent |
| Reporting/unused | Vintage, baseline bins, service transfers, HAMP/disaster/MI, product | Various | Diagnostics | Evaluation | Various | Reporting/not used | No | N/A | N/A | Spec documentation conflicts |

Evidence: `data_prep.py:254-383`; `experiments.py:42-110`; rounds 2/5/6.

### 5. Logistic/GLM feature shape

| Group | Classification | Exact treatment |
|---|---|---|
| Rate gap, age, estimated current LTV | Cubic B-spline | sklearn `SplineTransformer(n_knots=6, include_bias=False)`; default degree 3, uniform fit-range knots, constant extrapolation; seven columns each |
| FICO, DTI, DSCR, HPI, SATO, burnout, macro, payment saving, book/rolling/balance-path fields | Straight after standardization | No additional knots |
| Balance | Log + straight | `log1p(bal)` |
| Incentive interactions | Degree-1 hinge + interactions | `max(gap,0)` multiplied by log balance, active penalty, LTV, expiring/post-expiry flags |
| Penalty/DQ/calendar | Fixed buckets | Penalty windows; DQ recency groups; quarter |
| Curtailment/factors/payment | Cap-floor/nonlinear formula | Curtailment [−1,1], factor [0,2], LTV [0,250], payment term [12,480] |
| Baseline only | Fixed buckets | Gap edges −∞,−2,−1,−.5,0,.5,1,1.5,2,3,∞; age 6,12,18,24,36,48,60,84,120 |

No final transformed names/knots/coefficients are submitted. Evidence: `experiments.py:46-49,95-110`; `modeling.py:32-83`.

### 6. Tree models and constraints

| Family | Hyperparameters/role | Weights/stopping/tuning | Actual monotonic constraints | Final |
|---|---|---|---|---|
| Baseline HistGBM | Grid LR .05/.10, 200/400 iterations, 31/63 leaves; pick .05/200/31; min leaf 100, L2 1 | Unweighted, no early stop; select 2024 log loss | None | Baseline |
| Constrained HistGBM variants | Same base plus feature blocks | Some time-decay/balance weights; select 2024 | `rate_gap +1`, `rate_gap_pos +1`, `incentive_dollar +1`; rejected two-stage adds `p_turn_logit +1` | Rejected/intermediate |
| CatBoost | 400 iterations, LR .05, depth 6, L2 3, Logloss, seed 42, `has_time=True` | No class weights or early stopping; evaluated on 2024 | **None** | Final tree component |

`has_time=True` does not by itself prove the deck’s “ordered boosting” wording. The constrained HistGBM challenger directions are defined at `experiments.py:42,183-188` and `experiments_round3.py:56-62,158-161`; round-6 HGB-v4 applies them at `experiments_round6.py:131-140`. Final CatBoost and spline GLM have no enforced monotonicity. CatBoost `has_time` and fitting evidence: `experiments_round6.py:48-50,143-167`.

### 7. Model specification and selection

Final model is 50/50 log-odds blend of GLM-v4 and CatBoost; no calibration overlay. Feature/model adoption uses 2024 validation log-loss margins, with later blend weight fixed. Evidence: `final_model.py:1-13`; `README.md:108-121`.

Rounds 2–4 often score test candidates before validation selection. Later selectors use validation expressions, but subsequent rounds were designed after test exposure. The 2025–2026 test is repeatedly viewed and cannot be a lockbox. Memo admits reuse.

Specification documentation conflicts:

- Deck calls final GLM binned; final GLM uses splines.
- DQ-history and penalty-event features are called rejected but remain in final constants.
- Baseline tree is called unregularized despite min-leaf/L2 controls.
- Final CatBoost is unconstrained despite monotonicity language.

### 8. Validation and leakage review

| Split | Dates | Rows/events |
|---|---|---:|
| Train | 2015-07–2023-12 | 215,757/3,118 |
| Validation | 2024 | 106,784/836 |
| Test | 2025-01–2026-04 | 210,460/2,171 |

Chronology, train-only preprocessing, no class balancing, same-loan deployment interpretation, count/UPB views, and annual descriptive replays are strengths. PIT fails on modification fields. Test isolation fails through repeated scoring. Rolling results are ex-post diagnostics of an ex-post-selected specification, not prospective lockbox evidence. COVID is not separately assessed.

### 9. Metrics and calibration

No model metric is independently verified because predictions/metrics are absent.

| Metric | Reported final blend | Evidence |
|---|---:|---|
| ROC / PR | .703 / .038 | Candidate-reported only |
| Log loss / Brier | .0543 / .0101 | Candidate-reported only |
| Count O:P / UPB O:P | .99 / 1.09 | Candidate-reported only |
| Slope / intercept | 1.09 / not shown | Candidate-reported only / Not available |
| Top-10 capture/lift | 28.8% / ~2.9× | Candidate-reported only |
| Monthly gap | Count ~.08pp; UPB ~.2pp | Candidate-reported only |
| CPR | Count 11.5%/11.6%; UPB 13.3%/12.4% actual/predicted | Candidate-reported only |
| Stability | Annual AUC .57–.72; O:P .23 in 2020, 1.35 in 2021 | Candidate-reported only |
| Uncertainty | AUC CI .69–.71; blend−CB CI −.002 to .003 | Candidate-reported only |

The pooled UPB O:P 1.09 versus ratio of average monthly CPR near 1.07 can reflect aggregation order rather than contradiction.

### 10. Economic interpretation

Incentive, payment saving, penalty suppression/expiry, seasoning/burnout, current equity, curtailment, and regime effects are strong concepts. The model is a plausible shadow-validation candidate, not production-ready: no pristine test, UPB level miss remains, annual O:P is unstable, no submitted cash-flow tieout, and turnover/refi/cash-out are not separated.

### 11. Code and software engineering

Strengths: centralized relative paths, modular layers, fixed seeds, auditable target, explicit exceptions/join validation, data-driven deck source. Weaknesses: broken default pipeline, no outputs, no tests/CI, unpinned Node dependency, bloated lock, repeated experiment orchestration, assertions removable under optimization, hardcoded final dispatch, missing final manifest/features/knots/coefficients, and excessive experiment surface for the time box.

### 12. Demonstrable defects and concerns

| Severity | Classification | Evidence | Why / gate effect | Correction |
|---|---|---|---|---|
| Material | Verified defect | `data_prep.py:84-86,357-361`; final lists | Future modification data; G3 fail | Remove/gate before effective date; test |
| Material | Verified defect/concern | Memo; rounds 2/4 | Repeated test scoring; G5 fail | Separate inaccessible lockbox command |
| Material | Verified defect/packaging | `run_pipeline.py:20-31`; `plots.py:367-391` | Clean rerun cannot build final artifacts; G7 fail | One dependency-aware full entrypoint |
| Material | Missing evidence | README vs inner manifest | All outputs omitted | Submit predictions/metrics/manifests/tables |
| Moderate | Verified defect | Memo/deck vs final constants | “Rejected” DQ/penalty features remain | Generate inventory from final spec |
| Moderate | Strong concern | Constrained challengers vs final CB | Final monotonicity implied, not enforced | Constrain or correct wording |
| Moderate | Missing evidence | `deck_data.py:21-23,129-148` | No final GLM audit artifact | Export names/knots/coefficients/contrasts |
| Moderate | Strong concern | IO/payment/LTV formulas | Post-IO schedule/payment and CLTV approximations | IO-aware schedule; rename LTV |
| Minor | Missing evidence | Deck vs data checks | Static-constancy claim not coded | Add per-loan invariant check |
| Moderate | Packaging issue | Manifest/README | No tests; unpinned Node | Add regression tests/pins |

### 13. Candidate verdict

**Hard gate: Fail—future modification fields and reused test. Score: 65/100. Confidence: high on target/PIT/source; moderate on performance. Recommendation: Conditional interview.**

| Target | Validation | Method | Features | Communication | Reproducibility | Judgment | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | 9 | 12 | 10 | 7 | 4 | 3 | 65 |

Top positives: exact absorbing target; broad economically literate feature development; candid shadow-model/regime framing.  
Top concerns: future modification leakage; no pristine lockbox; broken rerun/omitted outputs/final-spec contradictions.

Live questions:

1. Locate and explain every future-dated modification row.
2. Enumerate exact final GLM/CatBoost features.
3. Explain repeated test exposure and redesign governance.
4. Derive correct IO balance/payment formulas.
5. Reconcile “rejected” features with final constants.

Live code modification: gate/remove all modification fields before their point-in-time effective date and add a regression assertion/count report without refitting.

## David Shunwei Du
**Final rank: 8.**
### 1. Submission inventory

The folder/root-ZIP pair is exact by relative path and hash. The 28-file package contains one sequential executed notebook, an 11-page Keynote/PDF deck, memo, exact actuals, frozen prediction Parquet, more than ten metric CSV/JSON artifacts, an opaque joblib object, and requirements. The joblib was not loaded. Outputs were relocated but are complete.

The frozen prediction file contains 210,475 rows and 2,171 events and matches the final exact-target subset. Deck, memo, prediction, and metric artifacts provide strong static lineage. There is no explicit COVID analysis; the model object remains opaque by design.

### 2. Target and panel construction

The submission builds the exact nonabsorbing predictor-month target:

- Sorted loan/date histories.
- Exact next-calendar-month eligibility.
- Current-only risk set.
- Terminal current rows excluded.
- `C(t)→PD(t+1)` events only.

The actuals dump exactly matches the 533,016-row/6,125-event canonical nonabsorbing target, with zero nulls, duplicate keys, omissions, or label mismatches. Frozen final predictions exactly match the 210,475-row/2,171-event final subset. G1, G2, and G6 pass. Evidence: notebook cells 5 and 8; independent full-file audits of `prepayment_actuals.parquet` and the frozen prediction Parquet.

### 3. Data cleaning and point-in-time handling

Material PIT defects:

- Final GLM and LightGBM include raw `mod_flag`; the shared 2,038 pre-effective modification rows enter: 1,549 pre-2024, 333 in 2024, and 156 final-test rows, all response zero. Submitted GLM coefficient is −.4542. Evidence: notebook cells 13 and 15; `logit_coefficients.csv:2-8`; independent full-file feature audit.
- Current-month final-vintage HPI is not release-vintage. Evidence: notebook cell 11.
- Correct macro-table S&P returns exist, but separately engineered `sp500_3m_change`/`sp500_12m_change` are calculated after risk filtering with row lags rather than calendar lags; 9,628/16,239 observations are wrong. Evidence: notebook cell 13; independent full-file feature audit.
- Age is capped at 240 before remaining term is calculated, distorting 6,258 rows across 223 loans. Evidence: notebook cell 13; independent full-file feature audit.

Current LTV correctly includes `bal/o_bal`; this report does **not** treat it as an omission. No class weighting is used.

### 4. Feature engineering

| Feature | Formula | Sources | Rationale | Available | Missing | Shape | Final? | Expected | Observed | Concern |
|---|---|---|---|---|---|---|---|---|---|---|
| Incentive/savings | Rate incentive; positive savings; monthly savings | Coupon, market rate, balance | Refi option/dollar benefit | `t`, subject to market timing | Model handling | Hinges −1/0/+1/+2pp; lines/tree | Both | Increasing | Dominant signal | Monthly savings duplicates positive savings; incentive is rescaled savings/100k |
| SATO/burnout | Origination spread and historical opportunity controls | Rates/history | Pricing and burnout | Historical | Model handling | Lines/tree | Both | Context/attenuation | Not fully isolated | Duplicated history terms |
| Age/term | Age and remaining term | Age/original term | Seasoning/maturity | `t` | None | Hinges 12/24/60 months; tree | Both | Ramp then fade | Useful | Age cap 240 distorts remaining term |
| Balances/paydown | Balance factor and dollar savings | Current/original balance | Dollar economics/equity | `t` | Model handling | Lines/tree | Both | Nonlinear | Useful | Duplicate savings transforms |
| Current LTV/HPA | Includes `bal/o_bal` and HPI ratio | LTV, balances, HPI | Current equity | Current-month HPI | Model handling | Hinges 70/90; tree | Both | Higher LTV slower | Plausible | Final-vintage HPI |
| FICO/DTI/DSCR | Credit/capacity controls | Static underwriting | Refi access | Origination | Model handling | Lines/tree | Both | Mixed | Not central | No explicit stability table |
| Documentation/occupancy/purpose/property | Broad categorical controls | Static fields | Segment behavior | Origination | Category handling | One-hot/native | Both | Level-specific | Included | Interpretation mainly predictive |
| IO/penalty/product/foreign | Contract/product controls | Static fields | Contract friction | Origination/`t` | Model handling | Binary/category/tree | Both | Heterogeneous | Included | No comprehensive segment calibration |
| Modification | Raw `mod_flag` | `mod`, `mod_ft_pay_dt` | Modified-loan behavior | Should begin at effective date | No gating | Binary | Both | Often slower | GLM coefficient −.4542 | 2,038 future-effective rows |
| Delinquency history | Prior noncurrent counts and related fields | Status history | Refi friction | Through `t-1` | Defaults | Lines/tree | Both | Negative | Included | Duplicate prior-noncurrent counts |
| Calendar/macro | PMMS, unemployment, S&P changes | Macro/date | Regime | HPI current month; macro mixed | Model handling | Lines/tree | Both | Regime-specific | Variation by month | Post-filter row-lag S&P features are wrong |
| Missing/constant | Missing flags and engineered transforms | Various | Data quality | Various | Explicit/native | Binary | Both | Data-dependent | Included | `savings_neg_amount` constant zero |

### 5. Logistic/GLM feature shape

The logistic model is L2-regularized and uses economically motivated hinges.

| Continuous group | Classification | Exact treatment |
|---|---|---|
| Incentive/savings | Degree-1 hinges | Exact knots −1/0/+1/+2 percentage points |
| Age | Degree-1 hinges | Exact knots 12/24/60 months |
| Current LTV | Degree-1 hinges | Exact knots 70/90 |
| Balance/savings | Straight/interactions | Dollar and balance-factor effects |
| Credit/macro | Straight | FICO, DTI, macro controls |
| Categories/missing | One-hot/binary | Fixed intercept shifts |

No class weighting is used. Duplicate and constant feature transforms weaken coefficient interpretation. Evidence: notebook cell 19 and `logit_coefficients.csv:2-52`.

### 6. Tree models and constraints

| Algorithm | Hyperparameters | Role/regularization | Weights/stopping/tuning | Monotonic constraints | Final |
|---|---|---|---|---|---|
| LightGBM | Broad economic/status feature set; submitted fixed seed/configuration | Ranking champion | No class weights; expanding folds and 2024 selection | Raw incentive +1 only; related incentive transforms unconstrained | Frozen 2025+ champion |

The raw incentive constraint does not guarantee global monotonicity because related unconstrained transforms can offset it.

### 7. Model specification and selection

Development uses expanding 2021–2023 folds, with 2024 as the model-selection period. The 2025–2026 final predictions appear frozen statically; no direct final-test tuning is found, although procedural untouched status cannot be proven without development history. Evidence: notebook cells 15, 18, 21, 23, and 27; `run_summary.json:5-24`.

The GLM remains a valuable calibration benchmark; LightGBM ranks better. The correct deployment conclusion depends on use:

- LightGBM for ranking/concentration.
- GLM for better aggregate probability level.

### 8. Validation and leakage review

- Expanding development folds: 2021, 2022, 2023.
- 2024 model selection.
- Frozen final test: 2025–2026, 210,475 rows/2,171 events.
- Same-loan chronology is compatible with live-book scoring.
- No class weighting.
- G5 passes statically; procedural lock is unproven.
- G3 fails from raw modification and current-month final-vintage HPI.
- No explicit COVID slice.
- Monthly performance shows underprediction and regime variation.

### 9. Metrics and calibration

Frozen prediction and submitted metric artifacts permit independent calculation:

| Metric | GLM | LightGBM | Evidence |
|---|---:|---:|---|
| ROC-AUC | .682483 | .705568 | Independently verified from submitted output |
| PR-AUC | .023389 | .038096 | Independently verified from submitted output |
| Brier | .010157 | .010071 | Independently verified from submitted output |
| Log loss | .055316 | .054447 | Independently verified from submitted output |
| Mean predicted / actual | 1.0388% / 1.0315% | .8495% / 1.0315% | Independently verified from submitted output |
| Top-decile event capture | Lower than LGBM | 31.23% | Independently verified from submitted output |
| Top-decile UPB capture | Lower than LGBM | 36.75% | Independently verified from submitted output |
| UPB actual/predicted SMM | 1.2275% / 1.1196% | 1.2275% / .8940% | Independently verified from submitted output |
| Bootstrap | 300 draws; model delta confirmed | 300 draws | Independently verified from submitted output |
| Monthly/COVID | Monthly regime variation; no explicit COVID slice | Same | Independently verified from submitted output / Not available |

### 10. Economic interpretation

The model captures incentive, equity, balance, seasoning, credit, contract, and status-history channels. The raw modification coefficient cannot be interpreted because all affected pre-effective rows are non-events. Current LTV is balance-adjusted and should not be criticized for omitting paydown.

The main cash-flow conclusion is calibration-specific: LightGBM concentrates payoff events and UPB but underpredicts aggregate count and UPB SMM; GLM calibrates materially better.

### 11. Code and software engineering

Strengths:

- Exact folder/ZIP match and complete 28-file package.
- Sequential executed notebook, frozen predictions, 10+ machine-readable metric artifacts, memo, deck, and requirements.
- Clear seeds and strong artifact reconciliation.

Weaknesses:

- Opaque joblib remains unaudited.
- Outputs were relocated, though complete.
- Duplicate/constant features and incorrect row-lag S&P features.
- No explicit COVID validation.

G7 is partial/pass.

### 12. Demonstrable defects and concerns

| Severity | Classification | Evidence | Why / hard-gate effect | Correction |
|---|---|---|---|---|
| Material | Verified defect | Notebook cells 13/15; `logit_coefficients.csv:2-8`; independent full-file feature audit | 2,038 pre-effective rows, all zero; GLM coefficient −.4542; G3 fails | Gate modification by effective date |
| Material | Strong concern | Notebook cell 11; independent HPI-date audit | Final-vintage observation month is not release-vintage PIT; G3 fails | Lag to release date/use vintages |
| Moderate | Verified defect | Notebook cell 13; independent full-file feature audit | Row lags miscompute 9,628/16,239 observations | Compute on unique calendar macro table |
| Moderate | Verified defect | Notebook cell 13; independent full-file feature audit | Age cap distorts 6,258 rows/223 loans | Derive remaining term before cap |
| Moderate | Verified defect | Notebook cells 13/15; `feature_importance.csv:52,73-83` | Duplicate prior-DQ counts and savings transforms; one constant feature | Remove exact duplicates/constants |
| Moderate | Missing evidence | `monthly_cpr.csv:2-17`; no COVID output | No explicit COVID slice | Add COVID/regime table |
| Minor | Interview question | Notebook cells 21/23/27; `run_summary.json:5-24` | Frozen final test appears clean but procedural lock is unprovable | Provide immutable run manifest/history |

### 13. Candidate verdict

**Hard gate: Fail—future modification and current-month HPI. Score: 73/100. Confidence: high. Recommendation: Discuss.**

| Target | Validation | Method | Features | Communication | Reproducibility | Judgment | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 17 | 18 | 12 | 9 | 7 | 7 | 3 | 73 |

Top positives: exact target/dump and frozen predictions; strong GLM/chronological inner validation/clustered evidence; clear code/output/deck lineage.  
Top concerns: future modification leakage; current-month HPI and malformed S&P features; LightGBM probability underprediction and no COVID slice.

Live questions:

1. How would you gate `mod_flag` by `mod_ft_pay_dt`?
2. What HPI vintage was available on each scoring date?
3. Prove the final test was inaccessible during feature/model selection.
4. Rebuild the S&P 3m/12m changes on the macro calendar.
5. Explain why current LTV is correct while remaining term is distorted.

Live code modification: point-in-time gate `mod_flag`, assert zero pre-effective rows, and define a new frozen evaluation protocol before rerunning.

## Thomas Kidu
**Final rank: 9.**
### 1. Submission inventory

The outer ZIP has supplied HPI, PPTX, dictionary, nested `src.zip`, assignment, panel, PDF, and macro. `src.zip` contains six source modules, README/requirements, response and model-feature Parquets, metrics/experiments JSON, coefficient/importance CSVs, memo Markdown/PDF, and nine figures. All 26 substantive inner files match the extracted tree; PPTX/PDF have 12 matching slides/pages, and embedded figures/rounded numbers reconcile to outputs.

Code expects raw data under `data/`, but outer Parquets sit beside `src.zip`; output directories must pre-exist. README run order omits `experiments.py`. Manual repair is required, but traceability is otherwise strong. Evidence: `Thomas Kidu/src/README.md:3-34`; `src/prep.py:25,69-70`.

### 2. Target and panel construction

The implementation strips IDs, drops exact duplicates, parses/sorts, shifts next status, drops each loan’s final observation, restricts to current rows, and sets `y=next_status=="PD"`. Separate validation asserts key uniqueness, strict date order, exact one-month adjacency, and positive C→PD transitions. Evidence: `src/prep.py:69-90,128-131`; `src/target.py:22-86`.

Audit:

- Exact non-absorbing 533,016 rows, 6,125 events, 24,412 loans.
- Binary `loan_id,date,response`; no nulls, duplicates, terminal observations, date gaps, or disagreement with `model_features.parquet`.
- Date range 2015-07–2026-04.
- Fifteen post-PD `C→C` zeros from two loans; absorbing version is 533,001/6,125.

The response is not materially wrong; first-PD truncation is a minor hygiene correction.

### 3. Data cleaning and point-in-time handling

Fractional LTV/CLTV normalizes; FICO 9999, DTI 999, and nonpositive original coupon become missing; categories/booleans normalize. GLM imputation/scaling/encoding is train-fitted; LightGBM uses native missing/categories. Evidence: `src/prep.py:42-131`; `src/model.py:45-64,90-99,231-246`.

Macro and HPI join the same calendar month as `r_dt`, with no release date, availability date, or vintage. This proves same-month use but not definitively future leakage from the supplied schema. Under a strict PIT gate it is unproven/fail. Evidence: `src/features.py:56-67,88-95`.

HPI fallback leaves 3,966 unresolved observations. Historical burnout is PIT but includes current incentive and is a cumulative maximum rather than duration/dose. No future balance/status predictor appears.

### 4. Feature engineering

| Feature | Formula | Sources | Rationale | Available | Missing | Shape | Final? | Expected | Observed | Concern |
|---|---|---|---|---|---|---|---|---|---|---|
| Incentive | `coupon-PMMS_t` | Rates | Refi economics | Same month | Median/native | Straight/tree | Both | Positive nonlinear | GLM OR 1.846; top GBM gain | PIT unproven; GLM rigid |
| SATO | Not built | Orig rate/market rate | Pricing selection | Origination | N/A | Not used | No | Context | N/A | Missing |
| Burnout | `cummax(incentive through t)` | History | Prior opportunity | Through `t` | Median/native | Straight/tree | Both | Negative conditional | Slight positive; GBM rank 5 | Includes current; not cumulative ITM |
| Age | `min(age,60)` | Age | Seasoning | `t` | None | Cap+line/tree | Both | Ramp/peak/fade | GLM OR .967; observed peak 15–20m | GLM cannot represent peak |
| Balances/paydown | None | `bal,o_bal` | Dollar/equity path | `t` | N/A | Not used | No | Nonlinear | N/A | Major omission |
| LTV/CLTV/HPA | `orig_ltv*HPI_orig/HPI_now`; HPA ratio | Orig leverage/HPI | Equity | Same-month HPI | Median/native | Straight/tree | Both | LTV −, HPA + | LTV OR .724; HPA OR .832 | “MTM LTV” omits `bal/o_bal` |
| FICO/DTI/DSCR | FICO/DTI lines; numeric DSCR omitted | Static | Qualification | Origination | Median/native | Straight | FICO/DTI both | FICO +, DTI − | OR 1.147/1.087 | Coarse DSCR document dummy remains |
| Doc/occ/purpose/property | Raw categories | Static | Segment behavior | Origination | Missing category | Full one-hot/native | Both | Level-specific | Mixed | No omitted reference |
| IO/mod/DQ/foreign/product | IO category only | Static/history | Contract/segment | Origination/`t` | Category | Categorical | IO yes | Heterogeneous | Mixed | Mod/DQ/foreign/product omitted |
| Calendar/rates | Unemployment, raw SP500, month | Macro/date | Regime/seasonality | Same month | Median/native | Lines/category | Both | Regime-specific | Unemployment/SP500 + | PIT and nonstationary level |
| Penalty | None | Flag/term/age | Contract friction | `t` | N/A | Not used | No | Active −, expiry lift | N/A | Major omission |
| Missing flags | None | Nullable fields | Missingness | `t` | Median/native | Not used | No | Data-dependent | N/A | GLM erases missing-state distinction |
| Reporting | Incentive bins [−6,−2,−1,0,.5,1,1.5,2,3,6]; age curve | Actuals | Diagnostics | Full sample | Out-of-range dropped | Buckets | No | N/A | Monotone incentive, age peak | Not model effects |

Feature lists/formulas: `src/features.py:50-109`; `src/model.py:31-36`.

### 5. Logistic/GLM feature shape

The L2 logistic uses train-median numeric imputation and standardization. Every continuous feature is straight except age’s upper cap:

| Group | Classification | Exact treatment |
|---|---|---|
| Incentive, max incentive, HPA, approximate LTV, FICO, original LTV/CLTV, DTI, unemployment, SP500 | Straight | No knots/logs/polynomials/interactions |
| Age | Cap-floor + straight | Upper cap 60 |
| Penalty expiry/balance/paydown/DSCR ratio | Not used | No shape |
| Categories | Full one-hot | Not nonlinear continuous treatment |

There are no logs, quadratics, hinges, splines, or continuous interactions. Evidence: `src/model.py:31-64`.

### 6. Tree models and constraints

| Algorithm | Hyperparameters | Role/regularization | Weights/stopping/tuning | Monotonic constraints | Final |
|---|---|---|---|---|---|
| LightGBM | LR .03; leaves 15; min leaf 300; feature/bagging .7; L2 5; max 1,000; seed 42 | Ranking model | No weights; early stop 50 on 2023 after fit through 2022; selected 99 rounds; refit through 2023 | **None** | Preferred ranking model/challenger wording varies |
| Loose/regularized experiments | Loose: LR .05, leaves 31, min leaf 20, 300 rounds; regularized recreates selector | Overfit diagnostic | No weights; 2024+ evaluated | None | Non-final |

There is no random forest. Regularization is not monotonicity. Evidence: `src/model.py:72-147`; `src/experiments.py:58-99`.

### 7. Model specification and selection

Final models are unweighted L2 logistic and LightGBM. The 2023 slice honestly selects tree rounds. The 2024+ period is later used to justify removing class weighting and tightening GBM regularization; deck language that test never influenced selection is too broad. Evidence: `src/model.py:107-121`; `src/experiments.py:27-99`; deck slides 5 and 10.

No calibrated champion is declared. Practical use is ranking-only because both raw probability levels are hot.

### 8. Validation and leakage review

| Role | Dates | Rows/events |
|---|---|---:|
| Tree selection fit | 2015-07–2022-12 | 135,768/2,625 |
| Tree validation | 2023 | 79,989/493 |
| Final fit | 2015-07–2023-12 | 215,757/3,118 |
| Reported OOT | 2024-01–2026-04 | 317,259/3,007 |

Chronology, train-fitted preprocessing, and fixed-round refit pass. Final OOT reuse fails. Same-month PIT is unproven. No rolling origin, loan holdout, monthly model tracking, UPB, slope/intercept, penalty/product/doc/vintage stability, or COVID-specific analysis.

### 9. Metrics and calibration

| Metric | GLM | GBM | Evidence |
|---|---:|---:|---|
| Train/OOT ROC | .7030/.6401 | .7547/.6577 | Independently verified from submitted output |
| Train/OOT PR | .03182/.01680 | .04810/.01718 | Independently verified from submitted output |
| OOT log loss/Brier | .05433/.009443 | .05249/.009370 | Independently verified from submitted output |
| Predicted/actual/O:P | 1.6529%/.9478%/.573 | 1.2229%/.9478%/.775 | Independently verified from submitted output |
| Top-decile capture/lift | 23.38%/2.338× | 22.75%/2.275× | Independently verified from submitted output |
| Slope/intercept | N/A | N/A | Not available |
| Monthly/UPB/SMM/CPR | N/A | N/A | Not available |
| Deterioration | ROC −.063 | −.097 | Independently verified from submitted output |

Every submitted OOT decile overpredicts. Final models are unweighted, so the issue is regime/level calibration, not weighting-prior distortion.

### 10. Economic interpretation

Incentive and lower approximate leverage are coherent. `mtm_ltv` is misnamed because it omits paydown. Seasoning and burnout claims rely on unadjusted curves or a weak proxy. HPA’s conditioned negative coefficient need not be “wrong” given mechanical overlap with LTV. Raw SP500 may be a time trend. No penalty, balance, DQ, modification, product, foreign, or numeric DSCR effects support Non-QM cash-flow interpretation.

### 11. Code and software engineering

Strengths: small modules, relative paths, pinned dependencies, clear assertions, strong artifact traceability, and no framework overengineering. Weaknesses: no single entrypoint/tests/CI/Python version; data layout mismatch; POSIX-only setup; output dirs assumed; `interpret.py` refits rather than loading exact final objects; experiments omitted from run order; dead helper; no model/prediction/manifest.

### 12. Demonstrable defects and concerns

| Severity | Classification | Evidence | Why / gate effect | Correction |
|---|---|---|---|---|
| Material | Verified defect | `model.py:115-121`; `experiments.py:27-99` | Final OOT influenced choices; G5 fail | New untouched holdout |
| Material | Strong concern | `features.py:56-67,88-95` | Same-month HPI/macro availability unproven; G3 strict fail | Availability/vintage joins |
| Material | Strong concern | Metrics/experiments outputs | GLM 74% hot, GBM 29% hot | Validation-fitted calibration + new test |
| Moderate | Verified defect | `features.py:88-95` | Current LTV omits paydown | Include `bal/o_bal`; rename |
| Moderate | Verified defect | `model.py:45-64`; OR CSV | Full one-hot + intercept lacks simple reference ORs | Drop reference/effects coding/report contrasts |
| Moderate | Missing evidence | Feature lists | Penalty timing absent | Active/remaining/expiry features |
| Moderate | Strong concern | `features.py:103-109` | Balances/mod/DQ/product/foreign omitted | PIT-safe incremental challengers |
| Moderate | Missing evidence | Tree source | No monotonicity or shape diagnostics | PDP/ICE and selective constraints |
| Minor | Verified defect | Target code/binary audit | 15 post-PD zeros | First-PD truncation |
| Moderate | Packaging issue | README/layout | Manual repair required | Configurable paths/one command |

### 13. Candidate verdict

**Hard gate: Fail—PIT unproven and final-test reuse. Score: 65/100. Confidence: high on artifacts/target/modeling; moderate-high on PIT. Recommendation: Discuss.**

| Target | Validation | Method | Features | Communication | Reproducibility | Judgment | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 18 | 11 | 11 | 8 | 8 | 6 | 3 | 65 |

Top positives: exact response/dump; clear modular code and artifact traceability; candid calibration/overfit discussion.  
Top concerns: same-month PIT unproven; final period influenced decisions; probabilities hot and key Non-QM features omitted.

Live questions:

1. Reconcile deck’s untouched-test claim with experiment code.
2. Define real-time availability dates for HPI/unemployment.
3. Explain full-one-hot OR contrasts.
4. Derive balance-adjusted current LTV and penalty expiry.
5. Choose/calibrate a champion for cash-flow use.

Live code modification: isolate all model/feature decisions from an inaccessible final-test object and evaluate it once after freeze.

## Waner (Arina) Zheng
**Final rank: 11.**
### 1. Submission inventory

The folder/root-ZIP pair matches exactly by relative path/hash. The nine-file submission contains one executed notebook plus HTML export, 12-slide PPTX/PDF, and exact actuals. There are no delivered predictions, metric tables, memo, README, requirements, or fitted model.

Notebook and deck provide a readable analysis path, but model metrics cannot be independently recomputed from row-level predictions. The package is proportionate but incomplete for score lineage.

### 2. Target and panel construction

The submitted target exactly matches the nonabsorbing predictor-month benchmark:

- 533,016 rows and 6,125 events.
- Zero nulls or duplicate keys.
- Exact next-calendar-month `C→PD` positives.
- Terminal rows excluded.
- Exact independent row/label reconciliation.

G1, G2, and G6 pass.

### 3. Data cleaning and point-in-time handling

Strengths:

- Macro/HPI are lagged one month.
- Train-only learned preprocessing is otherwise sound.

Defects:

- Final GLM uses raw `mod`; 2,038 future-effective rows across 153 loans are all zero. Waner’s split has 1,882 training and 156 test affected rows. Submitted `mod_Y` coefficient is −.421545, OR .656. Evidence: notebook cells 10–16 and independent full-file panel audit.
- After exact key/dedup alignment, 187,790 modeled rows retain fraction-style `orig_ltv<=2`; remaining rows use percentage scale. Cell 6 clips to `[0,200]` but never multiplies fractions by 100, corrupting both `orig_ltv` and derived `current_ltv`. Evidence: notebook cell 6 lines 16,26-30; cell 9 final numeric list; independent full-file model-frame audit.
- 241,029 modeled rows retain `DTI=0` as real zero; `DTI=999` is clipped to 100. This is structural/missing coding, not valid zero affordability. Evidence: notebook cell 6 lines 26-30; independent full-file audit.
- FICO `9999` is clipped to 850 on 7,741 rows instead of treated as missing. Evidence: notebook cell 6 lines 26-30.
- IO and purpose aliases remain fragmented.
- Origination HPI remains a final-vintage caveat.

G3 fails on modification timing and unit/sentinel integrity.

### 4. Feature engineering

| Feature | Formula | Sources | Rationale | Available | Missing | Shape | Final? | Expected | Observed | Concern |
|---|---|---|---|---|---|---|---|---|---|---|
| Incentive | Coupon minus lagged market rate | Current rate, macro | Refi option | `t/t-1` | Train processing | Straight | Yes | Positive | Positive signal | No nonlinear threshold |
| SATO/burnout | Limited/unclear final treatment | Origination/current rates, history | Pricing/opportunity | Historical | Various | Straight/unused | Partial | Context/attenuation | Not central | Underdeveloped |
| Age/term | Age, remaining term | Age/term | Seasoning/maturity | `t` | None | Straight | Yes | Hump/decline | Linear conditional effect | No age shape |
| Balances/pool factor | Current/original balance ratio | Balances | Paydown/equity | `t` | Model handling | Straight | Yes | Nonlinear | Included | No path/curtailment |
| Current LTV/HPA | Intended balance-adjusted current LTV and HPA | LTV, balance factor, HPI | Equity/refi access | HPI `t-1` | Train handling | Straight | Yes | Higher LTV slower | Not auditable economically | 187,790 fraction-style original-LTV rows corrupt current LTV |
| FICO/DTI/DSCR | Clipped credit controls | Static underwriting | Qualification | Origination | Clipped sentinels; DTI0 retained | Straight | Yes | Mixed | Included | FICO9999→850; DTI999→100; 241,029 DTI zeros retained |
| Doc/occ/purpose/property | Categorical controls | Static fields | Segment behavior | Origination | Alias categories | One-hot | Yes | Level-specific | Mixed | Fragmented aliases |
| IO | IO flag and remaining term | IO fields, age | Recast timing | `t` | Category handling | Straight clock/hinge | Yes | Expiry effect | Included | Raw hinge only |
| Modification | Raw `mod` | Modification fields | Modified-loan behavior | Should begin at effective date | No gating | Binary | Yes | Often slower | Coef −.421545, OR .656 | 2,038 future-effective rows |
| Penalty | Penalty categorical/state | Penalty fields | Contract friction | `t` | Category handling | Categorical | Yes | Active slower | Included | Limited timing evidence |
| Calendar/macro | Lagged macro/HPI; no final calendar-month predictor | Economic series | Regime | `t-1` | Model handling | Straight | Yes | Regime-specific | Included | No seasonality predictor, monthly tracking, or COVID slice |
| Missing/unused | Missing flags; no UPB/slope/intercept outputs | Various | Data quality | Various | Various | Binary/reporting | Partial | N/A | N/A | Audit gaps |

### 5. Logistic/GLM feature shape

The only model is L2 logistic regression with `C=.5`.

| Continuous group | Classification | Exact treatment |
|---|---|---|
| Incentive, age, balance factor, HPA/current LTV, credit, macro | Straight | Linear after clipping/engineering; LTV units and DTI coding are corrupted |
| IO remaining | Degree-1 hinge/clock | Raw hinge around IO expiry |
| Penalty/categories | Fixed categorical | One-hot intercept shifts |
| Missing indicators | Binary | Fixed shifts |

There are no splines, polynomials, or explicit continuous interactions.

No final calendar-month predictor is present.

### 6. Tree models and constraints

No tree/challenger model is submitted.

| Algorithm | Hyperparameters | Role | Weighting/stopping | Monotonic constraints | Final |
|---|---|---|---|---|---|
| None | N/A | Logistic-only | No class weights | N/A | L2 logistic |

### 7. Model specification and selection

The single L2 logistic is evaluated through expanding 2022, 2023, and 2024 folds, followed by a 2025+ final holdout. There is no visible final-test fitting or selection. No challenger comparison exists.

The simple specification supports transparency but leaves nonlinear economic shapes and robustness untested.

### 8. Validation and leakage review

- Expanding 2022/2023/2024 folds.
- Final 2025+ holdout.
- No visible final-test model selection; G5 passes statically.
- G3 fails because raw modification status includes 1,882 training and 156 test future-effective rows, 187,790 LTV rows remain fraction-scaled, and DTI zero/999 coding is invalid.
- No monthly tracking, UPB validation, calibration slope/intercept, uncertainty intervals, rolling-origin table, or COVID slice.

### 9. Metrics and calibration

All model metrics are stored notebook/deck outputs and therefore **Candidate-reported only**:

| Metric | Test result | Evidence |
|---|---:|---|
| ROC-AUC | .6814 | Candidate-reported only |
| PR-AUC | .0274 | Candidate-reported only |
| Brier | .0101 | Candidate-reported only |
| Log loss | .0551 | Candidate-reported only |
| Mean predicted / actual | 1.0602% / 1.0315% | Candidate-reported only |
| Lift | 2.9018× | Candidate-reported only |
| Deciles | Not strictly monotone | Candidate-reported only |
| Slope/intercept | Not supplied | Not available |
| Monthly/UPB/COVID | Not supplied | Not available |

### 10. Economic interpretation

The model intends to cover incentive, equity, balance factor, credit, IO timing, penalty, and borrower/product categories. Current-LTV economics cannot be trusted because `orig_ltv` mixes fraction and percent scales. Future modification status contaminates a strongly negative coefficient, and FICO/DTI sentinels/structural zeros are converted into valid numeric extremes.

The model is a transparent count-risk prototype, not a demonstrated cash-flow engine.

### 11. Code and software engineering

Strengths:

- Exact folder/ZIP pair.
- One sequential executed notebook plus HTML.
- Concise 12-slide deck and exact actuals.
- Deterministic final specification.

Weaknesses:

- No README, requirements, predictions, metric tables, memo, fitted model, or tests.
- Score and decile results cannot be independently recomputed.
- No reusable runner or deployment artifact.

G7 is partial.

### 12. Demonstrable defects and concerns

| Severity | Classification | Evidence | Why / hard-gate effect | Correction |
|---|---|---|---|---|
| Material | Verified defect | Notebook cells 10–16; independent full-file panel audit | 2,038 pre-effective rows; coefficient −.421545; G3 fails | Gate by `mod_ft_pay_dt` |
| Material | Verified defect | Notebook cell 6 lines 16,26-30; cell 9 final list; independent full-file model audit | 187,790 fraction-style LTV rows corrupt original/current LTV | Normalize fraction values before clipping |
| Material | Verified defect | Notebook cell 6 lines 26-30; independent full-file audit | 241,029 DTI zeros retained; DTI999 clipped100 | Treat structural/sentinel coding as missing + flags |
| Moderate | Verified defect | Notebook cell 6 lines 26-30 | FICO9999→850 on 7,741 rows | Treat sentinel as missing + flag |
| Moderate | Strong concern | Model design | All continuous effects linear; no challenger | Add prespecified nonlinear challenger |
| Moderate | Missing evidence | Package inventory | No predictions/metrics tables/model | Submit auditable outputs |
| Moderate | Missing evidence | Evaluation | No monthly/UPB/slope/COVID/uncertainty | Add model-risk suite |

### 13. Candidate verdict

**Hard gate: Fail—future modification plus LTV/DTI unit and sentinel defects. Score: 61/100. Confidence: high. Recommendation: Reject.**

| Target | Validation | Method | Features | Communication | Reproducibility | Judgment | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 18 | 13 | 10 | 5 | 7 | 6 | 2 | 61 |

Top positives: exact target/dump; expanding folds and statically clean final holdout; transparent single-model design.  
Top concerns: future modification leakage; mixed LTV units and DTI zero/999 coding; no auditable predictions/monthly/UPB evidence.

Live questions:

1. Why is `mod_Y` positive before `mod_ft_pay_dt`?
2. Why were 187,790 fraction-style LTV rows not multiplied by 100?
3. Why are 241,029 DTI zeros treated as affordability observations?
4. Show evidence that final 2025+ data were inaccessible during model design.
5. Design nonlinear, monthly/UPB, and COVID validation after unit repair.

Live code modification: gate raw `mod`, normalize LTV units, convert DTI structural/sentinel codes to missing with flags, assert corrected distributions, and document a future untouched evaluation.

## Shravant Srinivas
**Final rank: 10.**
### 1. Submission inventory

Shravant is archive-only. `Shravant Srinivas.zip` appeared at the submission root at `2026-07-17 16:28:30`, after the initial inventory; the late filesystem appearance is an intake fact, not candidate misconduct. Outer SHA256 is `b2a9da1ee7223d7915f7977be7dcf3caa3e436d1a8caa85de39942e2669f5769`.

The outer ZIP has nine files plus one directory entry, passes CRC, and has no unsafe paths or encryption. Candidate deliverables are under `Credit Modeling Assignment/`. The inner `prepayment_model_code.zip` has 68 file members representing 50 substantive logical files. The 12-slide deck, actuals, and memo have matching outer/inner copies. Five supplied assignment files match the canonical references.

The later standalone `prepayment_model_deck_shravant_srinivas.pptx` is only a PowerPoint re-save: slide body XML and media are identical to the archived deck; differences are limited to metadata, view settings, and master date formatting. It does not change any modeling conclusion.

Machine-readable evidence includes `outputs/tables/metrics_summary.csv`, `outputs/tables/target_invariants.json`, `outputs/tables/glm_coefficients.csv`, and `outputs/tables/walk_forward_backtest.csv`. Loan-level predictions, scored frame, and fitted models are absent. Outer/nested CRC and artifact matching establish strong package lineage but do not independently reproduce model fits.

### 2. Target and panel construction

The submitted target is excellent:

- Exact duplicate rows are removed.
- Histories are truncated after first `PD`.
- Only current rows with an exact next-calendar-month observation enter the risk set.
- Terminal current rows are excluded rather than labeled zero.
- Response one is reserved for exact `C(t)→PD(t+1)`.
- The submitted date is predictor month.

Full audit of `Shravant Srinivas.zip::Credit Modeling Assignment/model_response_by_loan_date.parquet`:

- SHA256 `7a35e3be8466142d684d0110236e5e5837151c13a321000ffd8f6bf76aeb5a3d`.
- Exact columns `loan,date,response`.
- 533,001 rows and 6,125 events.
- Zero nulls, duplicate rows, or duplicate loan-date keys.
- Predictor dates July 2015–April 2026.
- Exact row/label match to the canonical first-PD absorbing target.

Machine invariants are also submitted at `Shravant Srinivas.zip::Credit Modeling Assignment/prepayment_model_code.zip::prepayment_model_code/outputs/tables/target_invariants.json`. G1, G2, and G6 pass.

### 3. Data cleaning and point-in-time handling

The decisive PIT defects are:

1. **Future modification status.** Raw `mod` is an ever-modified field. Final `is_mod` ignores `mod_ft_pay_dt`; 2,038 eligible pre-effective rows across 153 loans enter modeling, all response zero. Counts are 1,549 full-training and 489 final-test rows; 428 inner-validation rows are a subset of the 1,549. Submitted GLM OR is .467105, p=`6.53e-05`. Evidence: `Shravant Srinivas.zip::Credit Modeling Assignment/prepayment_model_code.zip::prepayment_model_code/src/prepay/clean.py:243-251`; `Shravant Srinivas.zip::Credit Modeling Assignment/prepayment_model_code.zip::prepayment_model_code/outputs/tables/glm_coefficients.csv:64`.
2. **Full-sample learned preprocessing.** Features are built before the split; FICO/DTI medians use all data. FICO full median is 741 versus train-only 734, filling 5,790 training and 8,150 test rows. DTI median is 36.9 under both populations by coincidence. Evidence: `Shravant Srinivas.zip::Credit Modeling Assignment/prepayment_model_code.zip::prepayment_model_code/src/prepay/features.py:243-263`; split occurs later at `Shravant Srinivas.zip::Credit Modeling Assignment/prepayment_model_code.zip::prepayment_model_code/scripts/02_fit_models.py:38-41`.
3. **Prospectively unsafe within-loan rate fill.** The full-loan median may use later observations for 19 modeled rows. An independent check found that the selected value equals the contemporaneously available `o_noterate` for all 19, with zero events and no observed numerical feature change. The implementation is unsafe even though it has zero measured effect here. Evidence: `Shravant Srinivas.zip::Credit Modeling Assignment/prepayment_model_code.zip::prepayment_model_code/src/prepay/clean.py:174-194`.
4. **Economic-series availability.** Same-month HPI and PMMS are joined without release-date or historical-vintage controls; HPI is the clearer strict PIT failure. Evidence: `Shravant Srinivas.zip::Credit Modeling Assignment/prepayment_model_code.zip::prepayment_model_code/src/prepay/features.py:30-45,110-149`.

These are distinct from model-result leakage: they affect the predictor values/population supplied to otherwise chronological fits.

### 4. Feature engineering

| Feature | Formula | Sources | Rationale | Available | Missing | Shape | Final? | Expected | Observed | Concern |
|---|---|---|---|---|---|---|---|---|---|---|
| Incentive | Current coupon minus market rate | Coupon, PMMS | Refinance option | Same-month series | Full-sample transforms | Natural cubic spline, df5 | GLM+XGB | Rising/S-shaped | Useful ranking signal | Same-month PMMS; no vintages |
| SATO | `o_noterate-pmms30_orig` | Original coupon, origination PMMS | Origination pricing/risk proxy | Origination | Complete after rate handling | Straight/tree | Both | Context-dependent | OR 1.02167, nonsignificant | Agency PMMS is a rough Non-QM benchmark |
| Burnout | Cumulative months through `t` with incentive >.5pp | Incentive history | Persistent non-response | Through `t` | Starts zero | Straight/tree | Both | Negative/attenuating | OR 1.009775, p=.000208, opposite expected | Confounded with sustained incentive |
| Age | Source age | Age | Seasoning/turnover | `t` | None | Natural cubic spline, df5 | GLM+XGB | Ramp then fade | Partial effect peaks ~42m; observed bucket 12–18m | Model/observed shape mismatch |
| Balances/paydown | `log(o_bal)`; capped pool factor separately | Original/current balance | Dollar economics/survival | `t`/origination | Model handling | Log + capped line/tree | Both | Nonlinear | Effects submitted | Pool factor does not repair LTV interaction |
| Current LTV/HPA | `orig_ltv/(1+HPA)` | Original LTV, HPI | Current equity/refi access | Same-month HPI | Model handling | Natural cubic spline, df4 | Both | Higher LTV slower | Shape modeled | Omits `bal/o_bal`; not true current LTV |
| Original LTV/CLTV | Original leverage fields | LTV/CLTV | Origination selection | Origination | Model handling | Tree/controls | XGB/controls | Higher leverage slower | Not separately emphasized | Current CLTV unavailable |
| FICO | Cleaned origination FICO | `ofico` | Refinance access | Origination | **Full-sample median 741** | Natural cubic spline, df3 | Both | Positive/saturating | Modeled | Train-only median should be 734 |
| DTI/DSCR | Cleaned DTI; DSCR indicator plus filled ratio, with non-DSCR ratio set to zero | Static fields | Qualification/investor underwriting | Origination | Full-sample DTI median 36.9; structural DSCR missingness encoded | Lines + indicator/tree | Both | Higher DTI slower; DSCR nonlinear | DTI/DSCR terms weak in submitted GLM | Full-sample fitting; documentation and DSCR overlap |
| Modification | `is_mod` directly from raw ever-modified flag | `mod`, `mod_ft_pay_dt` | Modified-loan behavior | Should begin at effective date | No PIT gating | Binary | Both | Often slower conditional | OR .467105, significant | 2,038 future-effective zero-event rows |
| Penalty | Active/penalty indicators and pooled comparison | Penalty flag/term/age | Contract friction | `t` | Model handling | Binary/tree | Both | Active slower | Pooled effect reported | Not a same-borrower experiment; only 2,210/9,521 penalty loans appear both sides |
| Doc/occ/purpose/property/IO/product/foreign | Normalized categorical controls | Static contract/borrower fields | Segment behavior | Origination | Category handling | Dummies/native tree | Both | Level-specific | Not all directions submitted | No full segment stability table |
| Calendar/macro | Unemployment and same-month market/HPI series | Date/macro | Regime | Observation month | Full-sample feature build | Lines/tree | Both/challenger | Regime-dependent | Unemployment removed after test ablation | Final-test feature selection |
| Missing/unused | Missing flags; no predicted-UPB calibration or COVID slice | Derived/supplied | Data quality/stability | Various | Various | Binary/reporting | Partial | N/A | Walk-forward drift | Audit gaps remain |

Feature/preprocessing evidence: `Shravant Srinivas.zip::Credit Modeling Assignment/prepayment_model_code.zip::prepayment_model_code/src/prepay/features.py:155-280`; modification evidence: `Shravant Srinivas.zip::Credit Modeling Assignment/prepayment_model_code.zip::prepayment_model_code/src/prepay/clean.py:243-251`.

### 5. Logistic/GLM feature shape

The champion GLM is an unpenalized logit with loan-clustered standard errors and no class weighting.

| Continuous group | Classification | Exact treatment |
|---|---|---|
| Refinance incentive | Natural cubic spline | df5 |
| Age | Natural cubic spline | df5; fitted partial peak ~42 months |
| Current-LTV proxy | Natural cubic spline | df4; formula omits balance factor |
| FICO | Natural cubic spline | df3 |
| Original balance | Log + straight | Natural log of original balance |
| Pool factor | Cap-floor + straight | Capped separately from current-LTV proxy |
| SATO, burnout, DTI, DSCR, HPA, HPI momentum | Straight | DSCR also has an indicator; no weighting |
| Other numeric controls | Straight or categorical controls | Exact complete fitted basis not recoverable from absent model object |
| Modification/penalty/missing states | Binary | Fixed intercept shifts |

The observed age bucket peak is 12–18 months, materially earlier than the fitted age partial-effect peak near 42 months. The spline itself is flexible, but the discrepancy requires a joint-effect/cohort explanation.

### 6. Tree models and constraints

| Algorithm | Hyperparameters | Role/regularization | Weights/stopping/tuning | Monotonic constraints | Final |
|---|---|---|---|---|---|
| XGBoost | eta .05; depth 3; min child weight 20; row subsample .8; column subsample .8; lambda 10; `hist`; native categoricals; selected iteration 420 | Nonlinear challenger/final comparator | No class weighting; tuning on pre-2023 fit/2023 validation is chronological | **None** | Submitted final XGB comparator |

Depth, child weight, subsampling, lambda, and histogram construction are regularization, not monotonic constraints. No fitted model/tree dump was submitted, so exact split thresholds are unavailable.

### 7. Model specification and selection

The unweighted spline GLM provides the interpretable probability baseline with clustered inference. XGB uses chronological inner tuning: pre-2023 fit and 2023 validation, selecting 420 iterations. That inner tree tuning is methodologically sound.

The final feature set is not isolated from test:

- `study_time_proxy_ablation.py` explicitly scores unemployment variants on 2024–2026.
- Those test results are used to remove unemployment from the final specification.
- Evidence: `Shravant Srinivas.zip::Credit Modeling Assignment/prepayment_model_code.zip::prepayment_model_code/study_time_proxy_ablation.py:50-72,85-97`.

Thus G5 fails even though the inner XGB hyperparameter tuning is chronological.

### 8. Validation and leakage review

- Full model training is pre-2024; final test is 2024–2026.
- Inner XGB fit/validation is pre-2023/2023.
- Future modification rows: 1,549 full-training and 489 final-test; 428 inner-validation rows are included within the 1,549 training count.
- Full-sample FICO/DTI medians and features are created before the split.
- Nineteen rate fills use a future-aware method, but all equal the contemporaneous `o_noterate`; no numerical feature value or event changes in this panel.
- Same-month HPI/PMMS lack release/vintage controls.
- Final-test unemployment ablation changes the model.
- Walk-forward 2021–2026 is useful descriptive evidence but does not become a pristine prospective test after specification development.
- No dedicated COVID slice, predicted-UPB calibration, or loan-level score file is supplied.

Chronological split mechanics pass; PIT and final-test isolation fail.

### 9. Metrics and calibration

The following values come from submitted machine-readable CSVs and are **Independently verified from submitted output** as table values; no model was rerun.

| Metric | GLM | XGB | Evidence |
|---|---:|---:|---|
| Test ROC-AUC | .683553 | .691708 | Independently verified from submitted output |
| Test PR-AUC | .025343 | .027043 | Independently verified from submitted output |
| Log loss | .051486 | .051187 | Independently verified from submitted output |
| Brier | .009332 | .009336 | Independently verified from submitted output |
| Actual CPR | 10.7996% | 10.7996% | Independently verified from submitted output |
| Predicted CPR | 12.4658% | 11.6143% | Independently verified from submitted output |
| SMM actual/predicted (A:E) | .859049 | .926031 | Independently verified from submitted output |
| Calibration slope/intercept | Not supplied | Not supplied | Not available |
| Predicted-UPB calibration | Not supplied | Not supplied | Not available |
| Walk-forward 2021–2026 | Regime instability | Regime instability | Independently verified from submitted output; descriptive only |
| COVID slice | Not supplied | Not supplied | Not available |

Metric sources: `Shravant Srinivas.zip::Credit Modeling Assignment/prepayment_model_code.zip::prepayment_model_code/outputs/tables/metrics_summary.csv`; walk-forward source: `Shravant Srinivas.zip::Credit Modeling Assignment/prepayment_model_code.zip::prepayment_model_code/outputs/tables/walk_forward_backtest.csv`.

### 10. Economic interpretation

Incentive, flexible seasoning, leverage/equity, balance, and penalty are economically relevant. The interpretation has four material limits:

1. Modification OR .467105 is contaminated by future-known non-events.
2. `orig_ltv/(1+HPA)` is not current LTV because it omits `bal/o_bal`; a separate pool-factor term does not repair the missing interaction.
3. The penalty pooled comparison is not a same-borrower natural experiment: only 2,210 of 9,521 penalty loans appear on both sides of expiry.
4. No predicted-UPB calibration or COVID-period slice supports production cash-flow claims.

The model can support conditional ranking and count-level diagnostics, but not a production pool-speed conclusion without a PIT rebuild and untouched validation.

### 11. Code and software engineering

Strengths:

- Clear `01→03` scripts, small modules, relative paths, deterministic seeds, and target invariants.
- Strong target/output/deck/table lineage; outer deck/actuals/memo match inner copies.
- Machine-readable metrics, coefficients, target invariants, and walk-forward tables.

Weaknesses:

- No tests, one-command runner, deck builder, environment lock, or input-hash manifest.
- Broad minimum dependencies and global warning suppression.
- Stale documentation and OS artifacts.
- No loan-level predictions, scored frame, fitted model, or tree dump, limiting independent score audit.

G7 passes with score-audit reservations.

### 12. Demonstrable defects and concerns

| Severity | Classification | Evidence | Why / hard-gate effect | Correction |
|---|---|---|---|---|
| Material | Verified defect | `Shravant Srinivas.zip::Credit Modeling Assignment/prepayment_model_code.zip::prepayment_model_code/src/prepay/clean.py:243-251`; `Shravant Srinivas.zip::Credit Modeling Assignment/prepayment_model_code.zip::prepayment_model_code/outputs/tables/glm_coefficients.csv:64` | `is_mod` leaks 2,038 future-effective zero-event rows; OR .467105; G3 fails | Gate modification by effective/availability date or remove it |
| Material | Verified defect | `Shravant Srinivas.zip::Credit Modeling Assignment/prepayment_model_code.zip::prepayment_model_code/src/prepay/features.py:243-263`; `Shravant Srinivas.zip::Credit Modeling Assignment/prepayment_model_code.zip::prepayment_model_code/scripts/02_fit_models.py:38-41` | Full-sample FICO/DTI medians before split; test informs training features; G3 fails | Fit all learned preprocessing on training only |
| Minor | Verified defect | `Shravant Srinivas.zip::Credit Modeling Assignment/prepayment_model_code.zip::prepayment_model_code/src/prepay/clean.py:174-194` | Nineteen rows use a prospectively unsafe fill method, but all match contemporaneous `o_noterate` and have zero observed numerical effect | Restrict fills to values available at or before row date |
| Material | Strong concern | `Shravant Srinivas.zip::Credit Modeling Assignment/prepayment_model_code.zip::prepayment_model_code/src/prepay/features.py:30-45,110-149` | HPI observation month is not availability/vintage date; G3 fails strict PIT | Lag to documented release date and preserve vintages |
| Material | Verified defect | `study_time_proxy_ablation.py:50-72,85-97` | 2024–2026 test selects unemployment exclusion; G5 fails | Use validation-only ablation and reserve a new untouched test |
| Moderate | Verified defect | Current-LTV formula | Omits `bal/o_bal`; separate pool factor cannot reproduce interaction | Build balance-adjusted current LTV and validate ranges |
| Moderate | Strong concern | Penalty pooled analysis | Only 2,210/9,521 loans span both sides; not same-borrower experiment | Use within-loan/event-time design with appropriate controls |
| Moderate | Missing evidence | Package manifest | No predictions/scored frame/fitted models | Submit compact prediction and model-specification artifacts |
| Moderate | Missing evidence | Evaluation outputs | No predicted-UPB calibration or COVID slice | Add monthly/segment count and UPB diagnostics |
| Moderate | Packaging issue | Inner manifest/docs | No tests/runner/lock/input hashes; warnings suppressed | Add reproducible orchestration and focused regression tests |

### 13. Candidate verdict

**Hard gate: Fail—future modification, full-sample/future imputation, same-month HPI, and final-test feature selection. Score: 66/100. Confidence: high. Recommendation: Reject.**

| Target | Validation | Method | Features | Communication | Reproducibility | Judgment | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | 8 | 13 | 9 | 7 | 7 | 2 | 66 |

Top positives: exact target/dump; strong GLM and chronological inner tree tuning with clustered inference; clear code/output/deck lineage.  
Top concerns: future modification leakage; final-test feature selection; full-sample imputation and same-month HPI plus missing UPB/COVID/auditable score rows.

Live questions:

1. Why is `is_mod` positive before `mod_ft_pay_dt`, and how would you reconstruct it PIT?
2. Why does scoring unemployment ablation on 2024–2026 consume the final test?
3. Redesign train/validation/final windows so all feature and tree choices are frozen before test.
4. Quantify how train-only FICO imputation changes the 5,790 training and 8,150 test fills.
5. Derive a balance-adjusted current-LTV formula and explain why a separate pool-factor term is insufficient.

Live modification: implement point-in-time `is_mod` with an assertion that no row precedes its modification effective date, then specify a new untouched evaluation plan before any model rerun.

## Sanskriti Sarkar
**Final rank: 12.**
### 1. Submission inventory

The folder has three unique notebooks, each triplicated at root, `Libremax_code/`, and ZIP; one 12-slide PPTX, exact response Parquet, and supplemental DOCX. The notebook copies are byte-identical. Execution order is `01_eda` → `02_target_joins_features` → `03_models_validation_drivers`. There is no README, environment/requirements, runner, model frame, predictions, metrics CSV, coefficients, figures, or fitted model.

Deck image hashes match notebook outputs; native chart caches and tables reconcile to stored notebook metrics. Lineage is visually strong but local rerun is weak.

### 2. Target and panel construction

Notebook 02 parses dates, sorts, drops exact duplicates with conflict assertion, truncates after first PD, shifts next status, restricts to current rows with a successor, and exports actuals. Exact adjacency is checked only in prior EDA, not carried/asserted in the target cell. Evidence: `02_target_joins_features_v3 (2).ipynb` cells 4,6,7,11; `01_eda_ (1).ipynb` cell 23.

Audit:

- Exact absorbing 533,001 rows, 6,125 events, 24,411 loans.
- Binary `loan_id,r_dt,response`; zero nulls/duplicates/gaps/terminal zeros.
- Exact independent key/label match; date range 2015-07–2026-04.
- Target implementation is not self-guarding, but the submitted panel happens to be contiguous.

### 3. Data cleaning and point-in-time handling

Dates/LTV/current coupon/penalty flags are partly cleaned; HPI uses backward as-of with state fallback; GLM numeric medians are training-only. Evidence: notebook 02 cells 8,9,15,18; notebook 03 cell 6.

Material defects:

- Same-month PMMS/unemployment and HPI with no release/vintage lag; strict PIT fails.
- `ofico=9999`: 7,741 risk rows; `dti=999`: 27,235; `o_noterate=0`: 989. They enter models.
- Documentation aliases (`FULL`/` full `, etc.) and purpose missing aliases remain separate.
- Rare-level pooling is calculated on the full frame before split. Example: property `MH` has 1,498 full rows but 357 training rows, changing whether it is pooled.
- `is_mod=(mod=="Y")` enters the final binary list without gating by `mod_ft_pay_dt`. Before the OOL partition, the affected cohort has **1,741 rows through 2024-06 and 297 later**, all response zero. Submitted modification OR is .4221.

Evidence: notebook 02 cells 13,15,17,20 line 7,21; notebook 03 cell 5 lines 1-6,24-38 and cell 6.

### 4. Feature engineering

| Feature | Formula | Sources | Rationale | Available | Missing | Shape | Final? | Expected | Observed | Concern |
|---|---|---|---|---|---|---|---|---|---|---|
| Incentive | Clean current coupon − same-month PMMS | Rates | Refi moneyness | Claimed `t` | Median/native | Straight/tree | Both | S-curve | GLM OR 1.366; tree S-curve claimed | Same-month PIT; GLM rigid |
| SATO | Original coupon − orig-month PMMS | Rates | Pricing selection | Origination | None | Straight/tree | Both | Usually negative | OR .935 | 989 zero coupons |
| Burnout | Prior count incentive>.5, excluding current | History | Opportunity selection | Through `t-1` | Starts zero | Straight/tree | Both | Negative | OR 1.013 positive | Crude count/no interaction |
| Age | Raw age | Age | Seasoning | `t` | None | Straight/tree | Both | Ramp/fade | GLM OR .9895; GBM peak claimed | GLM rigid |
| Balances/paydown | `ln(o_bal)`; `bal/o_bal` only in LTV | Balances | Size/equity path | `t` | None | Log/indirect | Both/indirect | Size + | OR 1.320/log unit | No current-balance/path feature |
| LTV/CLTV/HPA | Current LTV=`orig_ltv*bal/o_bal/HPIratio`, cap150; HPI ratio; orig LTV | Leverage/balance/HPI | Equity | Same-month HPI | Median+flag/native | Lines/tree | Both | LTV − | Current LTV negative | Collinearity/PIT; CLTV omitted |
| FICO/DTI/DSCR | Raw FICO; DTI zero→NA; DSCR + indicator | Static | Access/capacity | Origination | Median/native | Lines/tree | Both | Mixed | Not fully shown | 9999/999 sentinels remain |
| Doc/occ/purpose/property | Raw categories with rare pooling | Static | Segment behavior | Origination | Various | One-hot/native | Both | Level-specific | Exact FULL OR 1.804; purpose N/A 2.053 | Aliases/missing codes |
| IO/mod/DQ/foreign/product | IO, raw-derived `is_mod`, second lien; no DQ/foreign/product | Static/history | Contract/segment | Purportedly `t`/origination | Binary | Binary | Partial | Heterogeneous | Modification OR .4221 | 1,741/297 future-effective rows before OOL; important omissions |
| Calendar/rates | Month category; same-month unemployment | Date/macro | Seasonality/regime | `t` claimed | Ffill/median | Category/line | Both | Regime-specific | Importance only | PIT; no year/regime |
| Penalty | Has, active, months-to-expiry clipped [−24,60], unknown | Flag/term/age | Friction/expiry | `t` | Unknown explicit | Binary+straight/tree | Both | Active −, release | Active OR .653; remaining OR .989 | Linear expiry too rigid |
| Missing | DTI, DSCR, HPI, penalty flags | Fields | Missingness | `t` | Explicit partial | Binary | Both | Data-dependent | Not shown | No FICO/coupon flag |
| Reporting/unused | CLTV, DQ, foreign, product, units, rate regime, monthly tracking | Various | Diagnostics | Evaluation | Various | Reporting/not used | No | N/A | N/A | Population mismatch in tracking |

### 5. Logistic/GLM feature shape

The unregularized statsmodels Logit has 69 columns plus intercept.

| Group | Classification | Exact treatment |
|---|---|---|
| Incentive, SATO, age, burnout, FICO, DTI, DSCR, HPI ratio, original LTV, unemployment | Straight | No knots/polynomials/interactions |
| Original balance | Log + straight | Natural log |
| Current LTV | Cap + straight | Upper cap 150 |
| Months to penalty expiry | Cap-floor + straight | Clip [−24,60]; no-penalty→0; separate active flag |
| Calendar month | Fixed categorical | 12 levels |
| Penalty active/unknown/missing flags | Binary | Fixed steps |

No hinges, cubic splines, quadratics, or continuous interactions. This cannot express the candidate’s own tree S-curve, age ramp/decline, or penalty cliff. Evidence: notebook 03 cells 6 and 10.

### 6. Tree models and constraints

| Algorithm | Hyperparameters | Role/regularization | Weights/stopping/tuning | Monotonic constraints | Final |
|---|---|---|---|---|---|
| LightGBM `LGBMClassifier` | 2,000 max trees; LR .03; leaves 31; min child 200; subsample/column .8; L2 5; seed 42 | Nonlinear challenger | No weights; AUC early stop 100; fit 2015-07–2023-05, validate 2023-06–2024-06; best 28; refit core | **None** | Challenger |

The “last 12 months” validation is 13 inclusive months. `subsample=.8` may not activate row bagging without nonzero bagging frequency. Importance uses default split count, not gain. Evidence: notebook 03 cells 12–13,18–19.

### 7. Model specification and selection

GLM is selected because OOT AUC roughly ties GBM and GLM level is closer: 1.12% versus 1.24% against 1.01% actual. The OOT result itself determines the champion; no later untouched period exists. Evidence: `Supplemental_Modeling_Notes_v2.docx` extracted text lines 9-22; deck slide 8.

### 8. Validation and leakage review

| Segment | Dates | Rows/events |
|---|---|---:|
| Core train | 2015-07–2024-06 | 212,016/2,770 |
| GBM fit | 2015-07–2023-05 | 132,967/2,279 |
| GBM validation | 2023-06–2024-06 | 79,049/491 |
| OOT | 2024-07–2026-04 | 213,986/2,153 |
| OOL pre-cutoff | through 2024-06 | 53,312/663 |
| OOT×OOL omitted | 2024-07–2026-04 | 53,687/539 |

Chronological OOT, loan-level OOL, training medians, and unweighted models are strengths. G3 fails from both future modification status and same-month economic series. OOT selects champion; category pooling uses final covariates; no rolling origin/COVID/UPB. Monthly chart computes actuals on all OOT rows but predictions only where not NaN, so every month compares different populations.

### 9. Metrics and calibration

| Metric | GLM | GBM | Evidence |
|---|---:|---:|---|
| Train/OOL/OOT ROC | .7241/.7226/.6821 | .7654/.7403/.6793 | Candidate-reported only |
| Train/OOL/OOT PR | .0379/.0337/.0248 | .0550/.0387/.0253 | Candidate-reported only |
| OOT Brier×100 | .9907 | .9917 | Candidate-reported only |
| Predicted/actual/O:P | 1.12%/1.01%/.902 | 1.24%/1.01%/.815 | Candidate-reported only |
| OOT top-decile lift | 2.8936 | 2.7403 | Candidate-reported only |
| Log loss/slope/intercept | N/A | N/A | Not available |
| Monthly | Population-mismatched GBM chart | — | Candidate-reported only; invalid as coded |
| UPB/SMM/CPR | None beyond rough 1.15%→13% narrative | — | Not available / Candidate-reported only |

### 10. Economic interpretation

Incentive, SATO, equity, seasoning, balance, penalty activity/expiry are coherent. The strong negative modification estimate is contaminated by future-known non-events. Exact raw category coefficients do not represent normalized economic groups. HPI/original/current LTV terms are mechanically related. Positive burnout remains in the selected GLM despite being omitted from the preferred story. OOT overprediction, no UPB, no survival/competing-risk integration, and rigid shapes prevent production cash-flow use.

### 11. Code and software engineering

Strengths: clear numbered notebook flow, fixed seeds, useful assertions, modest helpers, and excellent deck/notebook image lineage. Weaknesses: hard-coded `/content` paths, no README/environment/runner/tests/CI/types, null execution counts, absent generated outputs, full-data category pooling, tracking bug, physical triplication/manual version naming, and unauditable supplemental claims.

### 12. Demonstrable defects and concerns

| Severity | Classification | Evidence | Why / gate effect | Correction |
|---|---|---|---|---|
| Material | Verified defect | Notebook 02 cell 20 line 7; notebook 03 cell 5 lines 1-6,24-38 | Raw modification flag exposes 1,741/297 future-effective rows before OOL; OR .4221; G3 fails | Gate modification by effective/availability date or remove it |
| Material | Verified defect | Supplemental note/deck slide 8 | OOT chooses champion; G5 fail | Select internally, lock, score OOT once |
| Material | Strong concern | Notebook 02 cells 13/15/17 | Same-month macro/HPI; G3 fail strict | Availability-date lags/vintages |
| Material | Verified defect | Notebook 02 cleaning/model cells | FICO9999/DTI999/zero orig coupon | Convert to missing + flags |
| Moderate | Verified defect | Notebook 03 cell 6 | Full-frame rare pooling | Train-only vocabulary |
| Moderate | Verified defect | Category outputs | Alias/missing categories split | Canonical normalization |
| Moderate | Strong concern | GLM source/deck PDP | Central shapes linear | Prespecified hinges/splines |
| Moderate | Verified defect | Notebook 03 cell 17 | Monthly actual/prediction populations differ | Common scored-row mask/assertion |
| Moderate | Verified defect | Notebook 03 cell 20 | Penalty PDP creates invalid combinations | Restrict to penalty loans |
| Moderate | Missing evidence | Metrics cells | No log loss/slope/intercept/UPB/recalibration | Full probability suite |
| Moderate | Packaging issue | Notebook paths/manifest | Local rerun incomplete | README, pins, runner, outputs |

### 13. Candidate verdict

**Hard gate: Fail—future modification, same-month PIT, and OOT champion selection. Score: 61/100. Confidence: high. Recommendation: Reject.**

| Target | Validation | Method | Features | Communication | Reproducibility | Judgment | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 18 | 8 | 11 | 9 | 8 | 4 | 3 | 61 |

Top positives: exact absorbing target; genuine OOT/OOL concepts and unweighted probabilities; strong economic/deck lineage.  
Top concerns: future modification and same-month PIT failures; final-test selection; sentinel/category and tracking/reproducibility defects.

Live questions:

1. Why is `is_mod` positive before `mod_ft_pay_dt`, and how would you gate it?
2. Explain why OOT champion selection consumes the final test.
3. Make target self-guarding and repair sentinels/category aliases train-only.
4. Define publication-date-safe macro/HPI joins.
5. Align monthly populations and add UPB SMM/CPR.

Live code modification: point-in-time gate/remove `is_mod`, assert no future-effective flags, and report corrected broad-date/OOL counts.

## Adarsh Prabhudesai
**Final rank: 14.**
### 1. Submission inventory

The folder/root-ZIP pair matches exactly. The 469,375,106-byte outer ZIP contains nested `LB_Adarsh_Assignment.zip`, approximately 487.8MB with 84,830 entries and 1.346GB uncompressed because it includes a full virtual environment and roughly 42,000 Mac metadata entries.

Excluded from substantive review: virtual environment, compiled/executable files, symlinks, and `__MACOSX`. Twenty-two substantive files remain: five notebooks, exact actuals, model/final feature frames, model/validation/final prediction Parquets, 15-slide PPTX/PDF, and requirements.

No README is supplied. `build_deck.py` is referenced in requirements/workflow material but absent. There is no standalone metrics table. Model/ensemble timestamps and notebook execution order are stale, although submitted probability formulas reconcile numerically.

### 2. Target and panel construction

The submitted actuals exactly match the absorbing predictor-month target:

- 533,001 rows and 6,125 events.
- Zero nulls or duplicate keys.
- Exact first-PD truncation.
- Exact next-calendar-month eligibility.
- Terminal current rows excluded.
- Independent exact row/label match.

However, the exact dump does not agree with the modeled population:

- `response_dump.parquet` and `model_frame.parquet`: 533,001 rows/6,125 events through 2026-04.
- `final_features.parquet`: 517,429 rows/5,943 events through 2026-03.
- `final_predictions.parquet`: 194,888 rows/1,989 events, January 2025–March 2026.
- The entire April 2026 exact-target month—15,572 rows and 182 events—is excluded because final features require macro/HPI availability.

G1 and G2 pass. G6 is **Fail/partial: exact actual dump ≠ modeled population**. Evidence: `Target_and_relationships.ipynb` cell 3 lines 1-26; independent full-file audits of `response_dump.parquet`, `model_frame.parquet`, `final_features.parquet`, and `final_predictions.parquet`.

### 3. Data cleaning and point-in-time handling

Material failures:

- Same-month HPI drives all 517,429 model rows. The candidate acknowledges a lag is needed; G3 fails. Evidence: `Ensemble.ipynb` cell 12 lines 41-47; independent full-file `final_features.parquet` audit.
- FICO median is computed on the full panel: 742 versus train-only 737. Evidence: `Data_cleaning.ipynb` cells 11 and 15-24; independent train/all-data audit.
- October 2025 unemployment is two-sided interpolated using future November value 4.5, affecting 13,739 test rows and 144 events. Evidence: `Data_cleaning.ipynb` cell 29 lines 11-14; independent full-file feature audit.
- Final test evidence is cited during feature decisions, HistGB addition, ensemble design, and multiple model comparisons. Evidence: `Modelling.ipynb` cell 0 lines 25 and 37 and cells 22-24; `Ensemble.ipynb` cell 0 lines 3-6.

Final models exclude `mod`, so Adarsh is not part of the shared modification leak.

### 4. Feature engineering

| Feature | Formula | Sources | Rationale | Available | Missing | Shape | Final? | Expected | Observed | Concern |
|---|---|---|---|---|---|---|---|---|---|---|
| Incentive | Coupon-market spread with positive hinge | Current rate, market rate | Refi option | Same-month market context | Model handling | Hinge 0/tree | All | Positive | Strong | Same-month rate/HPI ecosystem |
| SATO/burnout | Historical rate/path controls | Origination/current rates | Pricing/opportunity | Historical | Model handling | Lines/tree | All | Context/attenuation | Included | Exact history design not fully documented |
| Age | Piecewise age | Age | Seasoning | `t` | None | Hinges 12/30/60 | GLM+trees | Ramp/fade | Useful | Test-informed architecture risk |
| Balances/curtailment | Log original balance, capped curtailment | Balances | Dollar economics/paydown | `t` | Model handling | Log+line/cap | All | Nonlinear | Useful | No independent scheduled balance audit |
| Current LTV/HPA | Current-LTV hinge80; HPA and balance inputs | LTV, balances, HPI | Equity/refi access | Same-month HPI | Model handling | Hinge/tree | All | Higher LTV slower | Useful | Same-month HPI |
| FICO/DTI/DSCR | Credit/capacity controls | Static underwriting | Qualification | Origination | FICO full-panel median | Lines/tree | All | Mixed | Included | FICO median leakage |
| Doc/occ/purpose/property | Categorical controls | Static fields | Segment behavior | Origination | Category handling | One-hot/tree | All | Level-specific | Included | No detailed segment calibration |
| IO/penalty/product/foreign | Contract/product controls | Static fields | Refi friction | Origination/`t` | Model handling | Binary/category/tree | All | Heterogeneous | Included | Claims exceed supplied model evidence |
| Modification | Excluded | Modification fields | Modified-loan behavior | N/A | N/A | Not used | No | N/A | N/A | Correctly avoids shared leak |
| DQ/status history | Status-history controls | Prior statuses | Refi friction | Through `t-1` | Defaults | Lines/tree | All | Negative | Included | Limited audit detail |
| Calendar/macro | Unemployment and HPI | Macro/date | Regime | HPI same month; unemployment interpolated | Future interpolation | Lines/tree | All | Regime-specific | Included | Future November value used in October |
| Missing/ensembles | Missing flags; rank and probability ensembles | Various/predictions | Robustness | Evaluation | Various | Rank/probability combinations | Final | N/A | Rank blend/high AUC | Rank score is not a probability |

### 5. Logistic/GLM feature shape

The GLM is unweighted and unpenalized.

| Continuous group | Classification | Exact treatment |
|---|---|---|
| Incentive | Degree-1 hinge | Knot 0 |
| Age | Degree-1 hinges | Knots 12, 30, 60 months |
| Current LTV | Degree-1 hinge | Knot 80 |
| Original balance | Log + straight | Natural log |
| Curtailment | Cap-floor + straight | Capped continuous term |
| Positive incentive×LTV | Interaction | Explicit |
| Positive incentive×log balance | Interaction | Explicit |
| Credit/macro | Straight | No splines/polynomials |

There are no cubic splines.

### 6. Tree models and constraints

| Algorithm | Hyperparameters | Role | Weighting/stopping/tuning | Monotonic constraints | Final |
|---|---|---|---|---|---|
| XGBoost | depth 2; LR .05; min child 200; selected 539 rounds | Challenger | No weighting stated; test comparisons influence architecture | None | Ensemble component |
| HistGradientBoosting | LR .05; 7 leaves; min leaf 200; 150 iterations | Dominant rank-ensemble component | No constraints; test-informed addition | None | Ensemble component |

The validation-rank ensemble weights are `.25/.10/.65` GLM/XGB/HistGB. A separate equal probability average is also submitted. Rank score is not a probability and must not be evaluated as calibrated level.

### 7. Model specification and selection

The package compares GLM, XGB, HistGB, validation-rank ensemble, and equal probability average. The final test is repeatedly cited during:

- Feature decisions.
- Addition of HistGB.
- Ensemble architecture/weight choice.
- Multiple model comparisons.

Thus G5 fails. Claims of 4,095-model sweeps, Bayesian search, monotonic constraints, and regularization are unsupported by submitted source/output. GLM evidence: `Modelling.ipynb` cell 5 lines 18-30 and cell 15; XGB: cell 18; HistGB: `Ensemble.ipynb` cell 3.

### 8. Validation and leakage review

- Chronological training/validation/final split exists.
- Exact response/model-frame target artifacts reconcile, but `final_features`/`final_predictions` omit 15,572 April-2026 rows and 182 events.
- G3 fails from same-month HPI, full-panel FICO median, and future unemployment interpolation.
- G5 fails because test results shape features and ensemble architecture.
- No rolling-origin or COVID slice.
- Ensemble/model timestamps and notebook execution order are stale.
- Final `mod` exclusion avoids the shared modification leak.

### 9. Metrics and calibration

Metrics are independently calculated from submitted final prediction Parquets, but only on the shortened January 2025–March 2026 window:

| Metric | GLM | XGB | HistGB | Equal probability average | Evidence |
|---|---:|---:|---:|---:|---|
| ROC-AUC | .6918 | .6958 | .6966 | .7023 | Independently verified from submitted output |
| PR-AUC | .0276 | .0249 | .0322 | .0325 | Independently verified from submitted output |
| Brier | .010034 | .010040 | .010007 | .010005 | Independently verified from submitted output |
| Log loss | .054529 | .054426 | .054273 | .054047 | Independently verified from submitted output |
| Predicted CPR | 13.69% | 11.02% | 10.67% | 11.80% | Independently verified from submitted output |
| Actual CPR | 11.58% | 11.58% | 11.58% | 11.58% | Independently verified from submitted output |
| UPB-weighted CPR predicted/actual | N/A | N/A | N/A | 12.24% / 13.65% | Independently verified from submitted output |

The validation-rank ensemble is a rank score, not a calibrated probability. No rolling/COVID metrics are supplied. These metrics must not be described as a complete January 2025–April 2026 final test.

### 10. Economic interpretation

The GLM hinge design is economically thoughtful: incentive threshold, seasoning segments, LTV threshold, log balance, curtailment, and incentive interactions. HistGB/equal average improve rank/proper scoring on the submitted test.

Interpretation is weakened by same-month HPI, future unemployment interpolation, full-panel FICO imputation, and test-designed ensemble architecture. Deck language conflates rank AUC with probability calibration.

### 11. Code and software engineering

Strengths:

- Exact actuals and multiple model/prediction frames.
- Five notebooks with auditable outputs.
- Submitted model/validation/final predictions and reconciled formulas.

Weaknesses:

- Nested ZIP includes a full virtual environment, compiled/executable files, symlinks, and ~42k Mac entries.
- No README or standalone metrics.
- Referenced `build_deck.py` absent.
- Stale model/ensemble timestamps and notebook order.
- Unsupported broad search/constraint claims.

G7 fails operationally despite rich artifacts.

### 12. Demonstrable defects and concerns

| Severity | Classification | Evidence | Why / hard-gate effect | Correction |
|---|---|---|---|---|
| Material | Verified defect | Independent full-file audits of `response_dump.parquet`, `model_frame.parquet`, `final_features.parquet`, `final_predictions.parquet` | Model population omits all Apr-2026: 15,572 rows/182 events; G6 fails/partial | Align features/predictions to exact target or explicitly censor before defining test |
| Material | Verified defect | `Ensemble.ipynb` cell 12 lines 41-47; `final_features.parquet` audit | Same-month HPI affects 517,429 rows; G3 fails | Apply documented publication lag/vintage |
| Material | Verified defect | `Data_cleaning.ipynb` cells 11,15-24; independent train/all-data audit | Full-panel FICO median 742 vs train 737 | Fit imputer on training only |
| Material | Verified defect | `Data_cleaning.ipynb` cell 29 lines 11-14; independent feature audit | October 2025 uses future November unemployment for 13,739 rows/144 events | Past-only fill or missing flag |
| Material | Verified defect | `Modelling.ipynb` cell 0 lines 25/37 and cells 22-24; `Ensemble.ipynb` cell 0 lines 3-6 | Final test informs features/HistGB/ensemble; G5 fails | Validation-only architecture; new final test |
| Moderate | Missing evidence | Claimed search/constraints | 4,095-model/Bayesian/constraint/regularization claims unsupported | Remove or submit exact artifacts |
| Moderate | Communication issue | Deck ensemble discussion | Rank score conflated with probability calibration | Separate ranking and level metrics |
| Material | Packaging issue | Nested archive manifest | Full venv/compiled files/symlinks/Mac entries; missing README/deck builder | Submit source-only deterministic archive |
| Moderate | Missing evidence | Validation outputs | No rolling/COVID slice | Add prospective stability tables |

### 13. Candidate verdict

**Hard gate: Fail—model-population mismatch, same-month/future PIT, test-designed architecture, and operational reproducibility. Score: 55/100. Confidence: high. Recommendation: Reject.**

| Target | Validation | Method | Features | Communication | Reproducibility | Judgment | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 17 | 7 | 10 | 11 | 5 | 3 | 2 | 55 |

Top positives: exact response dump; strong hinge GLM and submitted prediction artifacts; reconciled ensemble probability formulas on the modeled subset.  
Top concerns: modeled population omits Apr-2026; same-month/future PIT and test-designed ensemble; huge venv packaging and unsupported lineage claims.

Live questions:

1. Why do final features/predictions omit all 15,572 April-2026 target rows?
2. Why is same-month HPI unavailable for a month-start score?
3. Rebuild October 2025 unemployment without future November information.
4. List every decision made after viewing final-test metrics.
5. Explain rank versus probability averaging and defend the 4,095-model claims.

Live code modification: align the modeled population to the exact target, rebuild HPI/unemployment/FICO preprocessing PIT and train-only, then specify a new untouched test.

## Aishwarya Ghaiwat
**Final rank: 13.**
### 1. Submission inventory

The folder/root-ZIP pair matches exactly. The 10-file package contains a nested code ZIP with nine Python files plus documentation/requirements, a 19-slide PPTX/PDF, and exact actuals.

Despite README/source claims, the package omits delivered predictions, metrics JSON, model frames, decile CSVs, figures, and fitted model. Version names v1/v2/v3 conflict. The data path requires nesting/manual moves; `build_deck` depends on legacy outputs not produced by the documented run path.

### 2. Target and panel construction

The target code enforces exact adjacency and produces the exact nonabsorbing predictor-month target:

- 533,016 rows and 6,125 events.
- Zero nulls/duplicate keys.
- Exact independent row/label match.
- Terminal rows excluded.

G1, G2, and G6 pass.

### 3. Data cleaning and point-in-time handling

Strengths:

- Learned preprocessing is fitted on training data.
- Final v2 excludes `mod_flag`; legacy v1 includes raw future modification, but the final v2 is not marked as modification-leaked.
- Rich cleaning/feature pipeline.

Concerns:

- Same-month macro/HPI lack release-date/vintage controls; strict G3 is Unclear/Fail. Evidence: nested `src/data_prep.py:90-101,104-131`.
- State/document cleaning leaves 194/30 fragmented variants.
- Housing momentum is approximately 45% missing.

### 4. Feature engineering

| Feature | Formula | Sources | Rationale | Available | Missing | Shape | Final? | Expected | Observed | Concern |
|---|---|---|---|---|---|---|---|---|---|---|
| Incentive | Coupon-market spread plus positive hinge | Rates | Refi option | Same-month macro | Train pipeline | Line+hinge/tree | Both | Positive | Strong | Same-month release/vintage |
| Dollar/size interactions | Positive incentive×balance/size | Rates/balances | Dollar economics | `t` | Model handling | Interactions | Both | Positive | Included | Aggregate monotonicity complex |
| SATO/burnout/momentum | Origination spread and backward-looking history | Rates/history | Pricing/opportunity | Historical | Momentum ~45% missing | Lines/tree | Both | Context/attenuation | Rich feature block | High missingness |
| Age | Raw age | Age | Seasoning | `t` | None | Straight/tree | Both | Hump | Tree can flex | GLM linear |
| Balances/current LTV/HPA | Balance and HPI-derived equity | Balances/LTV/HPI | Refi access | Same-month HPI | Model handling | Lines/tree | Both | LTV negative | Included | PIT timing |
| FICO/DTI/DSCR | Credit/capacity | Static | Qualification | Origination | Pipeline | Lines/tree | Both | Mixed | Included | No delivered effect table |
| Penalty | Active indicator/term features | Penalty fields/age | Contract friction | `t` | Category handling | Binary/tree | Both | Negative active | Included | Exact outputs absent |
| Doc/occ/purpose/property | Cleaned categories | Static | Segment behavior | Origination | Fragmented variants remain | Dummies/native | Both | Level-specific | Included | 194/30 variants |
| IO/product/foreign | Product/contract categories | Static | Segment behavior | Origination | Model handling | Dummies/tree | Both | Heterogeneous | Included | No delivered segment table |
| Modification | Excluded from final v2 | Modification fields | Modified-loan behavior | N/A | N/A | Not used final | No final | N/A | Legacy v1 only | Version confusion |
| Calendar/macro | Month and economic variables | Date/macro | Regime | Same month | Momentum missing | Ordinal line/tree | Both | Cyclic/regime | Included | Month treated ordinal-linear in GLM |
| Missing/unused | Missing flags and v3 calibration claims | Various | Data quality | Various | Explicit/absent | Binary/reporting | Mixed | N/A | Claimed isotonic | Outputs absent |

### 5. Logistic/GLM feature shape

Final logistic is L2-penalized with `C=1`.

| Continuous group | Classification | Exact treatment |
|---|---|---|
| Numeric features | Straight | Linear after transforms |
| Positive incentive | Degree-1 hinge | Knot 0 |
| Incentive×size/dollar fields | Interaction | Explicit |
| Calendar month | Ordinal straight | 1–12 numeric; not cyclic |
| Age | Straight | No hinge/spline/polynomial |
| Categories | One-hot | Fixed shifts |

No splines or polynomials.

### 6. Tree models and constraints

| Algorithm | Hyperparameters | Role | Weighting/tuning | Monotonic constraints | Final |
|---|---|---|---|---|---|
| Enhanced LightGBM | Regularized boosted tree; exact output config absent | Claimed champion | Claimed 18-configuration sweep absent | Real constraints on selected features; unconstrained related transforms/products mean aggregate incentive monotonicity is not guaranteed | v2/v3 status contradictory |

The package lacks machine-readable model outputs needed to audit constraints, tuning, and realized champion.

### 7. Model specification and selection

Candidate materials report baseline, L2 GLM, and enhanced LightGBM. Final v3 ranks models by final OOT AUC, and Nomura blend weight is optimized on that same OOT. No later untouched test remains; G5 fails. Evidence: nested `src/train_v3.py:94-105`; `src/nomura_model.py:129-142`.

Version lineage conflicts:

- v1/v2/v3 names coexist.
- v3 claims isotonic calibration adopted.
- Deck remains v2.
- Final champion is contradictory.
- Claimed 18-configuration sweep is absent.

### 8. Validation and leakage review

- Chronological principal holdout exists.
- Train-only learned processing is otherwise sound.
- Same-month macro/HPI is not strict PIT.
- OOT selects champion and blend weight.
- No later final test.
- No delivered prediction/metric/model-frame outputs.
- No clear rolling/COVID stability evidence.

### 9. Metrics and calibration

All values are notebook/deck claims and therefore **Candidate-reported only**:

| Metric | Baseline | GLM | Enhanced | Evidence |
|---|---:|---:|---:|---|
| ROC-AUC | .699 | .697 | .705 | Candidate-reported only |
| PR-AUC | ~.04 | ~.04 | ~.04 | Candidate-reported only |
| Brier | N/A | .0105 | .0106 | Candidate-reported only |
| Predicted CPR | N/A | N/A | 11.2% | Candidate-reported only |
| Actual OOT CPR | 12.2008% | 12.2008% | 12.2008% | Candidate-reported only |
| Log loss/slope/intercept | N/A | N/A | N/A | Not available |
| Monthly/UPB/COVID | N/A | N/A | N/A | Not available |

### 10. Economic interpretation

The feature set is unusually rich for the assignment: incentive, dollar interactions, SATO, backward burnout, age, balance/equity, penalty, and broad categories. The GLM remains too linear for seasoning and calendar effects. Constrained LightGBM directions are only partial because related transforms and interactions remain unconstrained.

Without delivered outputs, champion/calibration claims cannot support cash-flow use.

### 11. Code and software engineering

Strengths:

- Exact folder/ZIP pair.
- Multiple source modules, docs, and requirements.
- Exact target and train-only learned pipeline.

Weaknesses:

- Data path nesting/manual moves.
- README/run path does not produce deck-required legacy outputs.
- v1/v2/v3 and champion/calibration contradictions.
- Claimed predictions, metrics, frames, figures, and model absent.
- No clean end-to-end reproducible run.

### 12. Demonstrable defects and concerns

| Severity | Classification | Evidence | Why / hard-gate effect | Correction |
|---|---|---|---|---|
| Material | Strong concern | Nested `src/data_prep.py:90-101,104-131` | Release/vintage availability unproven; G3 strict fail | Lag to availability/vintage |
| Material | Verified defect | Nested `src/train_v3.py:94-105`; `src/nomura_model.py:129-142` | Final OOT ranks champion and blend weight; G5 fails | Validation-only selection + new final test |
| Material | Packaging issue | Nested ZIP manifest; `README.md`, `run_all.py`, `build_deck.py` source audit | Claimed outputs absent and run/deck paths conflict; G7 fails | Deliver deterministic outputs/manifest |
| Moderate | Verified defect | Category audit | 194/30 state/doc variants remain fragmented | Canonical normalization |
| Moderate | Strong concern | Feature frame | Housing momentum ~45% missing | Missing flags/sensitivity |
| Moderate | Contradiction | `SUMMARY.md:80-84`; v1/v2/v3/deck manifest audit | Final champion and isotonic adoption disagree | One canonical version |
| Moderate | Missing evidence | Claimed sweep | 18-config sweep absent | Submit search table or remove claim |
| Moderate | Strong concern | GLM design | Age/month effects linear | Add prespecified nonlinear/cyclic terms |

### 13. Candidate verdict

**Hard gate: Fail—strict PIT uncertainty, final-OOT selection, and broken reproducibility. Score: 58/100. Confidence: high. Recommendation: Reject.**

| Target | Validation | Method | Features | Communication | Reproducibility | Judgment | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 18 | 12 | 9 | 10 | 6 | 2 | 1 | 58 |

Top positives: exact target/dump; rich economic features and train-only learned preprocessing; real partial LightGBM constraints.  
Top concerns: final OOT selects model/blend; same-month PIT and category fragmentation; contradictory versions and absent outputs/broken run.

Live questions:

1. Define the actual final v2/v3 champion.
2. Explain why OOT-based blend optimization consumes the final test.
3. Prove same-month HPI/macro availability.
4. Show the claimed 18-configuration sweep and constraints.
5. Repair category normalization and the clean run path.

Live code modification: create one canonical run that selects/calibrates on validation only, emits all claimed outputs, and reserves a new final test.

## Jarryd Scully
**Final rank: 15.**
### 1. Submission inventory

The folder/root-ZIP pair matches exactly. The modular package includes a 522,480-row response dump, feature frame, 216,547-row logistic/GBM prediction artifacts, run metadata, and a 12-slide text-only PPTX.

There is no submitted performance metric source/table. A stale build copy and unpinned dependencies weaken lineage. Internal prediction/actual agreement is exact, but the modeled population is not the canonical target.

### 2. Target and panel construction

The intended positives are valid C→PD transitions, but construction is materially wrong:

- Response and dynamic features are attached to event month `t+1`, not predictor month `t`.
- A non-grouped `groupby(...).cumsum().shift(1)` terminal bug removes 6,597 rows and 67 events.
- HPI availability filtering removes another 3,924 rows and 46 events.
- Submitted actuals contain 522,480 rows/6,012 events versus the absorbing canonical 533,001/6,125.
- The response dump depends on feature availability.

G1 passes for realized positives; G2 fails. G6 is **Pass with canonical-population caveat**: predictions/actuals agree exactly inside the submitted 522,480-row population, but that population omits canonical target rows/events.

### 3. Data cleaning and point-in-time handling

The fatal timing error is universal: all 522,480 dynamic feature rows are one month late because event-month rows receive predictor-month concepts. Evidence: `Jarryd Scully.zip::submission/prepayment-model-submission.zip::prepayment-model-submission/prepayment-model/src/pipeline/feature_table.py:20-89,118-157`; independent full-file feature audit.

Additional defects:

- Logistic medians are learned from the test distribution.
- A non-grouped ever-delinquent operation creates false cross-loan history on 3,166 rows/17 events.
- Current LTV omits `bal/o_bal` and is deterministic with original LTV/HPA.
- HPI availability filtering changes the target population.

Target/terminal evidence: `Jarryd Scully.zip::submission/prepayment-model-submission.zip::prepayment-model-submission/prepayment-model/src/pipeline/loan_panel.py:126-141`; feature evidence: `Jarryd Scully.zip::submission/prepayment-model-submission.zip::prepayment-model-submission/prepayment-model/src/pipeline/feature_table.py:20-89,118-157`.

### 4. Feature engineering

| Feature | Formula | Sources | Rationale | Available | Missing | Shape | Final? | Expected | Observed | Concern |
|---|---|---|---|---|---|---|---|---|---|---|
| Incentive | Coupon-market spread | Rates | Refi option | Should be predictor month | Test-median handling | Straight/tree | Both | Positive | Signal present | Attached one month late |
| SATO/burnout | Limited historical controls | Rates/history | Pricing/opportunity | Should be prior history | Model handling | Straight/tree | Partial | Context | Weak | Timing/history bugs |
| Age | Raw age | Age | Seasoning | Predictor month | None | Straight/tree | Both | Nonlinear | Main effect | One month late; no shape |
| Balances/paydown | Balance controls | Balances | Dollar economics | Predictor month | Model handling | Straight/tree | Both | Nonlinear | Included | No path/curtailment |
| Current LTV/HPA | `orig_ltv/(1+HPA)` | Orig LTV/HPI | Equity | Event-month-attached | Model handling | Straight/tree | Both | LTV negative | Included | Omits `bal/o_bal`; deterministic collinearity |
| FICO/DTI/DSCR | Credit/capacity controls | Static | Qualification | Origination | Test medians for logistic | Straight/tree | Both | Mixed | Included | Test distribution leakage |
| Doc/occ/purpose/property | Categorical controls | Static | Segment behavior | Origination | Category handling | One-hot/tree | Both | Level-specific | Included | No nonlinear interactions |
| IO/penalty/product/foreign | Contract/product controls | Static | Friction/segment | Origination/`t` | Model handling | Binary/category | Both | Heterogeneous | Included | Dynamic clocks one month late |
| Modification | Omitted | Modification fields | Modified behavior | N/A | N/A | Not used | No | N/A | N/A | Avoids shared mod leak |
| Delinquency history | Ever-delinquent | Status history | Refi friction | Prior history | Defaults | Binary | Both | Negative | Included | Non-grouped shift crosses loans |
| Calendar/macro | HPI/macro fields | Economic/date | Regime | Feature availability filter | Missing rows dropped | Straight/tree | Both | Regime-specific | Included | Target depends on HPI availability |
| Missing/unused | Missing flags; no seasonality/interactions | Various | Data quality | Various | Test medians | Binary/none | Partial | N/A | N/A | Weak feature governance |

### 5. Logistic/GLM feature shape

The primary logistic is L2-regularized with main effects only.

| Continuous group | Classification | Exact treatment |
|---|---|---|
| Incentive, age, balances, LTV/HPA, credit, macro | Straight | One global slope each |
| Categories/missing | One-hot/binary | Fixed shifts |

There are no hinges, splines, polynomials, continuous interactions, or seasonality terms.

### 6. Tree models and constraints

| Algorithm | Hyperparameters | Role | Weighting/stopping/tuning | Monotonic constraints | Final |
|---|---|---|---|---|---|
| LightGBM | 200 trees; depth 5; learning rate/leaves/min leaf/regularization/seed/stopping unspecified | Challenger | No documented tuning | None | Logistic selected primary |

The tree specification is insufficiently pinned for reproducibility.

### 7. Model specification and selection

L2 logistic is primary; LightGBM is compared on the same single holdout. There is no separate validation/model-selection period and no final untouched test. G5 fails.

No class weighting is used, so G8 is not triggered.

### 8. Validation and leakage review

- One chronological holdout exists.
- No separate validation/final hierarchy.
- Every dynamic feature is one month late.
- Test medians contaminate logistic preprocessing.
- Target loses rows/events through terminal and HPI filters.
- False cross-loan delinquency affects 3,166 rows/17 events.
- No rolling-origin, COVID, monthly calibration, or robust UPB framework.

### 9. Metrics and calibration

Metrics are independently recalculated from submitted predictions; no submitted metric table exists:

| Metric | Logistic | GBM | Evidence |
|---|---:|---:|---|
| ROC-AUC | .668186 | .659952 | Independently verified from submitted output |
| PR-AUC | .019391 | .017991 | Independently verified from submitted output |
| Brier | .0100969 | .0102588 | Independently verified from submitted output |
| Log loss | .055463 | .056542 | Independently verified from submitted output |
| Mean predicted / actual | 1.0337% / 1.0238% | 1.2456% / 1.0238% | Independently verified from submitted output |
| Prior-month-UPB SMM actual/predicted | 1.2133% / 1.0589% | 1.2133% / 1.2695% | Independently verified from submitted output |
| Slope/intercept/monthly/COVID | N/A | N/A | Not available |

These metrics describe the candidate’s internally filtered, one-month-late population, not the canonical target.

### 10. Economic interpretation

The logistic’s aggregate probability level is close on its own population, but feature timing invalidates economic interpretation. Current LTV omits paydown and is mechanically linked to original LTV/HPA. The false cross-loan delinquency flag can create spurious credit effects.

The simple logistic outperforms the underspecified GBM on submitted ranking/proper-scoring metrics, supporting the candidate’s primary-model choice but not validating the data construction.

### 11. Code and software engineering

Strengths:

- Modular package with response, feature, predictions, and run metadata.
- Internal prediction/actual agreement.
- Clear primary/challenger comparison.

Weaknesses:

- Fundamental grouped-shift and event-month alignment bugs.
- No submitted metric source/table.
- Stale build copy and unpinned dependencies.
- Weakly specified LightGBM and no test hierarchy.

G7 fails because canonical regeneration is not reliable.

### 12. Demonstrable defects and concerns

| Severity | Classification | Evidence | Why / hard-gate effect | Correction |
|---|---|---|---|---|
| Material | Verified defect | `Jarryd Scully.zip::submission/prepayment-model-submission.zip::prepayment-model-submission/prepayment-model/src/pipeline/feature_table.py:20-89,118-157`; independent full-file feature audit | All 522,480 dynamic rows attached to event month; G3 fails | Keep features at predictor month |
| Material | Verified defect | `Jarryd Scully.zip::submission/prepayment-model-submission.zip::prepayment-model-submission/prepayment-model/src/pipeline/loan_panel.py:126-141`; response/model Parquet audit | Non-grouped shift removes 6,597 rows/67 events; G2 fails | Shift within each loan |
| Material | Verified defect | `Jarryd Scully.zip::submission/prepayment-model-submission.zip::prepayment-model-submission/prepayment-model/src/pipeline/feature_table.py:20-89,118-157`; Parquet audit | Removes 3,924 rows/46 events; target depends on features | Build target before feature availability |
| Material | Verified defect | `Jarryd Scully.zip::submission/prepayment-model-submission.zip::prepayment-model-submission/prepayment-model/src/models/logistic/model.py:32-55`; independent train/test transform audit | Test medians used; G3 fails | Fit medians on training only |
| Material | Verified defect | `Jarryd Scully.zip::submission/prepayment-model-submission.zip::prepayment-model-submission/prepayment-model/src/pipeline/feature_table.py:118-157`; independent full-file feature audit | False cross-loan ever-DQ on 3,166 rows/17 events | Group every shift/cumulative transform |
| Moderate | Verified defect | `Jarryd Scully.zip::submission/prepayment-model-submission.zip::prepayment-model-submission/prepayment-model/src/pipeline/feature_table.py:20-89`; independent formula audit | Omits `bal/o_bal`; deterministic collinearity | Balance-adjust formula |
| Material | Strong concern | `Jarryd Scully.zip::submission/prepayment-model-submission.zip::prepayment-model-submission/prepayment-model/src/models/logistic/model.py:22-76`; `.../src/models/gbm/model.py:17-64`; `.../config/logistic.yaml`; `.../config/gbm.yaml`; `Jarryd Scully.zip::submission/run_meta_logistic.json`; `.../run_meta_gbm.json` | One holdout used for model comparison; G5 fails | Train/validation/final hierarchy |
| Moderate | Packaging issue | Package inventory | No metric source; stale build/unpinned deps | Pin and submit metrics/manifest |

### 13. Candidate verdict

**Hard gate: Fail—canonical target loss, one-month-late features, preprocessing leakage, and no final-test isolation. Score: 45/100. Confidence: high. Recommendation: Reject.**

| Target | Validation | Method | Features | Communication | Reproducibility | Judgment | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 6 | 10 | 9 | 6 | 6 | 6 | 2 | 45 |

Top positives: modular package and internally consistent predictions; simple logistic beats challenger; reasonable aggregate level on submitted population.  
Top concerns: dynamic features one month late; terminal/HPI filters remove canonical rows/events; test medians and false cross-loan DQ.

Live questions:

1. Show why event-month feature attachment is leakage.
2. Repair the non-grouped terminal/DQ shifts.
3. Reconstruct the canonical target before HPI filtering.
4. Move all imputation to training only.
5. Design separate validation and final-test periods.

Live code modification: rebuild target/features on predictor month with grouped shifts and train-only preprocessing, then define a new untouched evaluation.

## Alan Jia
**Final rank: 17.**
### 1. Submission inventory

The canonical ZIP contains four substantive artifacts: 423-line `libremax.py`, README, 11-page `libremax_case_study.pdf`, and `output_predictions.parquet`; Mac metadata is excluded. All substantive files match extracted copies. The deck **does exist**, correcting prior triage. The README gives a one-script order but claims an absent `validation_charts.png`. There is no lockfile, metric table/log, fitted model/scaler, deck source, or binary actual-response dump. Evidence: `Alan Jia.zip::Libremax Submission/README.txt:4-31`; `libremax.py:268-376`.

### 2. Target and panel construction

The code sorts by loan/date, shifts next observed status, restricts to current rows, and defines positives as next status PD. It does not deduplicate, shift/check next date, censor terminal rows, or truncate after first PD. Evidence: `libremax.py:32-42`.

Independent panel audit:

- Raw current rows: 550,441; valid exact-month benchmark 533,016; events remain 6,125.
- Invalid zeros: **17,002 terminal + 423 same-date duplicate transitions**; no genuine post-dedup forward gaps.
- 16,079 invalid rows are in test; removing them changes test rate from 1.0082% to 1.1866%.
- Seventeen post-PD current rows remain.

Submitted Parquet audit:

- 550,441 rows, 24,419 loans, 2015-07–2026-05.
- Three columns `loan_id,date,response`, but all 550,441 `response` values are nonbinary probabilities, range .0008478–.7756277; mean .0113379.
- 423 duplicate loan-date groups; zero nulls.
- Code explicitly assigns `gb.predict_proba` to `response`. `libremax.py:379-394`.

Both risk-set and response-dump gates fail.

### 3. Data cleaning and point-in-time handling

FICO 9999/0 and DTI 999/0 become missing with flags; mixed LTV units and IO/penalty flags normalize; dates parse. However, FICO and HPI medians and servicer frequency/category coding are learned on all data before the chronological split. Evidence: `libremax.py:51-113,183-189,233-256`.

Same-month PMMS/HPI joins lack release/vintage dates, so PIT is unproven. HPI uses global geography-dependent index medians with no missing flag. No range assertions/caps or static-field checks exist. IDs are not predictors.

The final HistGB feature list also includes `mod_clean=(mod=="Y")` without gating by `mod_ft_pay_dt`. The same 1,549/333/156 predictor-date rows are future-effective modification non-events. Evidence: `libremax.py:191-193,219-225`. This adds a confirmed shared G3 failure.

### 4. Feature engineering

| Feature | Formula | Sources | Rationale | Available | Missing | Shape | Final? | Expected | Observed | Concern |
|---|---|---|---|---|---|---|---|---|---|---|
| Incentive | `coupon-PMMS_t` | Rates | Refi option | Same month | None | Straight LR/tree | Both | Positive | LR +.685 | PIT; no hinge/cap |
| SATO/burnout | Not constructed; age mislabeled burnout | Rates/history | Pricing/opportunity | Historical | N/A | Not used | No | Context/negative burnout | N/A | Explicit omission |
| Age | Age + age² | Age | Seasoning | `t` | None | Quadratic LR/tree | Both | Hump | +.555/−.655 | Peak/scaler absent |
| Balances/paydown | `log1p(o_bal)` LR; `log1p(bal)` tree | Balances | Dollar benefit | `t` | None | Logs | Both/tree | Positive/nonlinear | Orig balance +.159 | No factor/curtailment |
| LTV/CLTV/HPA | `orig_ltv/(HPI_t/HPI_orig)` | LTV/HPI | Equity | Same month | Global medians | Straight/tree | Both | LTV − | LR −.154 | Omits `bal/o_bal`; no CLTV |
| FICO/DTI/DSCR | FICO clean; DTI engineered but level unused; DSCR absent | Static | Access/capacity | Origination | Global medians/flags | Straight/unused | FICO both | FICO + | +.055 | Full-data leakage; key omissions |
| Doc/occ/purpose/property | Purpose engineered then unused; others absent | Static | Segment behavior | Origination | Unknown | One-hot/none | No | Level-specific | N/A | Major Non-QM omissions |
| IO/mod/DQ/foreign/product | IO both; `mod_clean=(mod=="Y")` in final tree; others absent | Static/history | Contract/segment | Purportedly `t`/origination | Baseline values | Binary/tree | Partial | Heterogeneous | Modification claimed negative | 2,038 future-effective modification rows; no timing/history |
| Calendar/rates | Vintage year tree; PMMS through incentive | Dates/macro | Regime | `t` | None | Numeric/tree | Tree | Nonmonotone | Not shown | No seasonality/COVID |
| Penalty | Static binary | Flag | Contract friction | Origination | Blank→0 | Binary | Both | Negative while active | LR −.121 | 32,865 current rows at/after term |
| Missing/servicer | FICO/DTI flags; full-data rare servicer integer code | Fields/servicer | Data quality/operations | `t` | Flags/code −1 | Binary/ordinal tree | Both/tree | Heterogeneous | Not shown | Test-informed arbitrary ordering |
| Unused/reporting | Current CLTV, HPA direct, balance factor, DSCR/doc/occ/property/DQ/foreign/product/penalty expiry | Supplied | Economic candidates | Various | N/A | Not used | No | N/A | N/A | Broad gaps |

Evidence: `libremax.py:121-225`.

### 5. Logistic/GLM feature shape

| Group | Classification | Exact treatment |
|---|---|---|
| Incentive, current LTV, FICO | Straight | No cap/knots/interactions |
| Age | Quadratic polynomial | Age and age², separately standardized |
| Original balance | Log + straight | `log1p(o_bal)` |
| Current balance/vintage/servicer | Not used in LR | Tree only |
| Penalty/IO/missing flags | Binary | Fixed steps |
| SATO/burnout/expiry/current CLTV | Not used | No shape |

No fixed continuous buckets, hinges, cubic splines, or interactions. Evidence: `libremax.py:248-280`.

### 6. Tree models and constraints

| Algorithm | Hyperparameters | Role/regularization | Weights/stopping/tuning | Monotonic constraints | Final |
|---|---|---|---|---|---|
| `HistGradientBoostingClassifier` | max 200 iterations; LR .05; depth 4; seed 17 | Primary final model | No weights; early stopping left to unpinned sklearn default; deck claims depth optimized but no search/validation trace | **None** | Yes; probabilities populate dump |

Test permutation importance is used for narrative. Depth/LR are not monotonic constraints. Evidence: `libremax.py:296-323`; `libremax_case_study.pdf` extracted text lines 131-140 and 225-227.

### 7. Model specification and selection

Balanced L2 logistic is the interpretable baseline; unweighted HistGB is selected on the sole test’s reported ROC/AP. There is no separate validation set, no documented depth search, and no final refit. Test effectively begins November 2025, not October as deck states. Purpose/unemployment exclusion claims lack submitted experiment code; top-decile statistics are not generated by source. Evidence: `libremax.py:199-317`; `libremax_case_study.pdf` extracted text lines 118-121 and 225-230.

### 8. Validation and leakage review

- Train: 2015-07–2025-10, 443,514 rows.
- Test: 2025-11–2026-05, 106,927 rows.
- No validation/rolling/final lockbox.
- 13,862 loans overlap; acceptable for live-book scoring, but use case is unstated.
- Full-data preprocessing contaminates training.
- Future-effective modification status enters the final HistGB.
- May 2026 is unobservable and dominates terminal zeros.
- Sole test drives champion/importance; default internal tree stopping may be random.
- No monthly, UPB, COVID, or regime validation.

### 9. Metrics and calibration

| Metric | LR | HGB | Evidence |
|---|---:|---:|---|
| Train/test ROC | .693/.681 | .753/.703 | Candidate-reported only |
| Test PR/AP | .019 | .029 | Candidate-reported only |
| Log loss/Brier | N/A | N/A | Not available |
| Mean prediction | N/A | Pooled all-row .0113379 | Independently verified from submitted output |
| Actual/O:P | Invalid test rate claim; no actual dump | Same | Inconsistent / Not available |
| Lift/capture | N/A | 2.8×/28.5% | Candidate-reported only; source absent |
| Slope/intercept/deciles/monthly | N/A | N/A | Not available |
| UPB/SMM/CPR | N/A | N/A | Not available |

Balanced LR probabilities are uncorrected, though final HGB is unweighted. Neither model is calibrated with proper scoring evidence.

### 10. Economic interpretation

LR signs for incentive, LTV, FICO, balance, age hump, and penalty are plausible. Final-tree direction is unavailable because permutation importance has no sign, and its modification input leaks future-known non-events. Current LTV omits paydown; static penalty persists after expiry; age is not burnout; servicer causal stories and an April-2024 in-sample case are unsupported. The probability output cannot support cash-flow projection.

### 11. Code and software engineering

Positive: one concise relative-path entrypoint, readable ordering, fixed seeds, proportionate scope. Weaknesses: unpinned dependencies, global warning suppression, no functions/main guard/tests/CI/schema assertions, import executes pipeline, dead preprocessing/features, manual deck, absent claimed chart, and output “validation” does not validate actuals/keys/adjacency.

### 12. Demonstrable defects and concerns

| Severity | Classification | Evidence | Why / gate effect | Correction |
|---|---|---|---|---|
| Material | Verified defect | `libremax.py:32-42`; panel audit | 17,002 terminal +423 same-date invalid zeros; G2 fail | Dedup/exact-month censoring |
| Material | Verified defect | `libremax.py:379-394`; Parquet audit | Probability-as-response; G6 fail | Export binary actuals |
| Material | Verified defect | `libremax.py:191-193,219-225`; shared row audit | Final tree consumes 1,549/333/156 future-effective modification rows; G3 fails | Gate modification by effective/availability date or remove it |
| Material | Verified defect | `libremax.py:54-62,111-113,183-189` | Full-data preprocessing; G3 fail | Train-only pipeline |
| Material | Strong concern | Test importance/deck depth claim | Sole test selection/tuning; G5 fail | Train/validation/final |
| Material | Verified defect | `libremax.py:262-270` | Balanced LR raw probabilities | Remove weighting or prior-correct/calibrate |
| Moderate | Verified defect | `libremax.py:137-140` | Permanent penalty flag | Active/expiry/post-expiry |
| Moderate | Verified defect | `libremax.py:126-132` | LTV omits balance factor | Balance-adjusted proxy |
| Moderate | Verified defect | `libremax.py:183-189` | Arbitrary ordinal servicer code | Train-only categorical handling |
| Material | Missing evidence | Metric source | No proper scoring/monthly/UPB | Full probability suite |
| Moderate | Packaging issue | README/manifest | Missing chart/lock/metrics/model | Compact reproducible package |

### 13. Candidate verdict

**Hard gate: Fail. Score: 43/100. Confidence: high. Recommendation: Reject.**

| Target | Validation | Method | Features | Communication | Reproducibility | Judgment | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 7 | 8 | 8 | 8 | 6 | 4 | 2 | 43 |

Top positives: correct positive-event definition; chronological cut and simple baseline/tree comparison; concise core economic intuition.  
Top concerns: invalid zero denominator and probability-as-response; future modification/full-data preprocessing; test-selected and uncalibrated workflow.

Live questions:

1. Why is `mod_clean` positive before `mod_ft_pay_dt`, and how would you gate it?
2. Rewrite target handling for duplicates, terminal rows, exact month, and post-PD.
3. Explain why the submitted response is wrong and reconcile May censoring.
4. Explain class-weight probability correction.
5. Redesign current LTV, active penalty, and servicer encoding.

Live code modification: remove/gate future-effective `mod_clean`, assert zero such rows, and report changed train/test counts.

## Khush Modi
**Final rank: 16.**
### 1. Submission inventory

The outer ZIP has nested `final_submission_v3.zip`, 12-slide PPTX, and outer actuals. The inner ZIP has README, three scripts, duplicate actuals, four CSV tables, 12 PNGs, and three PKLs. Complete inner trees are duplicated under two extraction paths; actuals has a third copy. PKLs were never loaded.

V1/V2/V3 metrics, calibration, importance, validation curves, and model files coexist without manifest. Current deck metrics match `comparison_table.csv`; `model_results_v2.csv` differs and `model_results.csv` reports implausibly high stale values. README claims absent requirements and HTML deck. Scripts use hard-coded Ubuntu paths and expect absent processed data. Evidence: `README.md:6-16`; three result CSVs.

### 2. Target and panel construction

The candidate uses an event-month convention: sort by loan/date, shift previous observed status, set event when previous status C and current status PD, retain rows whose previous observed status is C. Evidence: `process_data_v3.py:10-34`.

Audit of `actuals_v2.parquet`/outer copy:

- 533,439 rows, 6,125 events, 24,412 loans; August 2015–May 2026.
- Binary `loan,date,response`; no nulls.
- All positives are genuine exact-next-month C→PD.
- 402 duplicate loan-date groups (804 rows).
- Against deduplicated exact-month panel, 423 invalid same-date rows: 402 duplicate extras + **21 unique same-date artifacts**.
- Correct non-absorbing event-month benchmark is 533,016/6,125.
- Terminal current rows are excluded, not labeled zero.

The event-month convention is acceptable; lack of deduplication/exact adjacency is not.

### 3. Data cleaning and point-in-time handling

Dynamic fields are shifted to T−1 and macro/HPI keyed to T−1, but preprocessing is not train-safe:

- Numeric coercion/full-data medians and dummy discovery occur before OOT split. `train_model_v3.py:24-47`.
- 186,766 modeled rows (35.0%) have decimal LTV; 345,505 use percentage scale.
- DTI999: 27,255; FICO9999: 7,745; zero original rate: 990; zero units: 69,929.
- Current CLTV is missing on 271,560 rows (50.9%), primarily due to 265,930 missing origination dates.
- Final OOT macro gaps: 15,581 May-2026 rows missing PMMS; 29,331 Nov-2025/May-2026 rows missing unemployment.
- Categories are not normalized.
- Penalty code tests `== "TRUE"` against source 0/1/blank, making the flag constant zero. `process_data_v3.py:74-75`.
- Publication lags/vintages remain unproven.

### 4. Feature engineering

| Feature | Formula | Sources | Rationale | Available | Missing | Shape | Final? | Expected | Observed | Concern |
|---|---|---|---|---|---|---|---|---|---|---|
| Incentive | `coupon_(T-1)-PMMS_(T-1)` plus components | Rates | Refi option | T−1 | Full-data median | Straight/tree | Both | Positive | LR +.179; XGB positive then tail down | Exact linear redundancy |
| SATO/burnout | Neither; age proxy only | Rates/history | Pricing/opportunity | Historical | N/A | Not used | No | Context/negative | N/A | Missing |
| Age | Shifted prior age | Age | Seasoning | Prior observed row | None | Straight/tree | Both | Nonlinear | LR negative | Duplicate same-month lag; rigid |
| Balances/paydown | Raw prior balance; original balance intermediate | Balances | Dollar/path economics | T−1 | None | Straight/tree | Current both | Nonlinear | Tiny LR + | No log/factor/curtailment |
| LTV/CLTV/HPA | Raw mixed orig LTV; derived current CLTV from balance/HPI | Leverage/balance/HPI | Equity | T−1 | CLTV 50.9% median | Straight/tree | Both | CLTV − | LR CLTV − | Mixed units/missing HPI/orig dates |
| FICO/DTI/DSCR | Raw sentinel-contaminated fields; DSCR duplicated | Static | Qualification | Origination | Full-data median | Straight/tree | Both accidentally | Mixed | Small coefficients | 9999/999; duplicate columns |
| Doc/occ/purpose/property | Occ/purpose/property categories; doc unused | Static | Segment | Origination | Noisy aliases | Dummies/tree | Both | Level-specific | Mixed | Missing aliases and opaque codes |
| IO/mod/DQ/foreign/product | IO encodings/term and foreign accidentally selected; mod omitted; no DQ/product | Static/history | Contract/segment | Origination/T−1 | Median/baselines | Dummies/ordinal | Partial | Heterogeneous | Dirty SHAP inputs | Substring `"io"` captures `ratio`/foreign |
| Calendar/rates | Linear month, PMMS, unemployment | Date/macro | Seasonality/regime | T−1 | Full-data median | Straight/tree | Both | Cyclic/regime | Month line; unemployment + | Month not cyclic; macro gaps |
| Penalty | Wrong `TRUE` test | Flag | Contract friction | Origination | Constant zero | Absent | Intended only | Negative active | None | Core feature nonfunctional |
| Expiry | Not built | Term/age | Release | T−1 | N/A | Not used | No | Nonlinear | N/A | Major omission |
| Missing flags | None | All incomplete fields | Data quality | T−1 | Median | Not used | No | Data-dependent | N/A | Missing cohorts hidden |
| Reporting/stale | Incentive/month plots, old validation/calibration/importance | Outputs | Diagnostics | Mixed | Unknown | Plots | No | N/A | Contradictory generations | Generating code absent |

Evidence: `process_data_v3.py:24-78`; `train_model_v3.py:19-35`; `lr_coefficients.csv`.

### 5. Logistic/GLM feature shape

Every numeric/ordinal input is a straight line without standardization: original/current rates, FICO, LTV, DTI, borrower/unit counts, age, balance, PMMS, unemployment, CLTV, incentive, month, DSCR, foreign code, IO term. There are no logs, caps, quadratics, fixed buckets, hinges, splines, or continuous interactions. Categories are one-hot.

Exact redundancies include incentive with coupon/PMMS and raw/lagged static DSCR. Month is incorrectly linear January→December; foreign code is incorrectly ordinal. Evidence: `train_model_v3.py:19-55`.

### 6. Tree models and constraints

| Algorithm | Hyperparameters | Role/regularization | Weights/stopping/tuning | Monotonic constraints | Final |
|---|---|---|---|---|---|
| `XGBClassifier` | 300 trees; depth 5; LR .05; row/column .8; logloss metric; seed 42 | Apparent champion | `scale_pos_weight=neg/pos`; no early stopping; no search; random validation unused | **None** | Serialized V3 apparent champion |

Depth/subsampling are regularization, not monotonicity. No probability correction follows weighting. Evidence: `train_model_v3.py:57-70`.

### 7. Model specification and selection

Balanced logistic and weighted XGB are compared on final OOT; XGB is declared superior. The random internal validation sample is created but never used. No simple empirical/economic baseline or final refit exists. Selection is therefore final-test selection. Evidence: `train_model_v3.py:37-107`; README/deck.

### 8. Validation and leakage review

- Pre-OOT: 2015-08–2025-10, 428,768/4,903.
- Random internal 80/20 row split: 343,014/85,754; validation unused.
- OOT: **2025-11–2026-05**, 104,671/1,222, seven inclusive months.
- Deck incorrectly says January–June 2026.
- 13,228 loans cross pre-OOT/OOT; not inherently leakage.

Chronological holdout exists, but full-data preprocessing and OOT champion selection fail. No rolling/COVID/train-vs-test/UPB stability; two OOT months have macro gaps.

### 9. Metrics and calibration

| Metric | Logistic | XGB | Evidence |
|---|---:|---:|---|
| ROC / PR | .639257/.020305 | .675288/.031419 | Independently verified from submitted output; older artifacts Inconsistent |
| Precision/recall/F1 | .0191/.5262/.0369 | .0229/.4959/.0439 | Independently verified from submitted output |
| Log loss | N/A | N/A | Not available |
| Brier | Conflicting V1/V2; V3 absent | Same | Inconsistent |
| Actual | 1.1675% OOT | Same | Independently verified from submitted output |
| Mean prediction/O:P | N/A | N/A | Not available |
| Calibration | Severe overprediction plot | Severe overprediction plot | Candidate-reported only |
| Lift/capture/slope/intercept | N/A | N/A | Not available |
| Monthly | Plot only, source absent | Plot only | Candidate-reported only |
| UPB/SMM/CPR | None | None | Not available |

Confusion matrices show 32.10% LR and 25.23% XGB rows above .5 against 1.17% events, rigorously establishing severe miscalibration even without exact means.

### 10. Economic interpretation

Incentive and current equity likely contain rank signal; PMMS and age directions are plausible. Coefficients are not interpretable due to exact redundancy, unscaled units, mixed LTV, duplicated DSCR, ordinal foreign codes, and 50.9% CLTV imputation. Penalty narrative has no functioning feature. The models can support rough ranking only, not cash-flow probabilities.

### 11. Code and software engineering

Positive: small three-script layout, deterministic seeds, locally visible target formula, current deck metrics align with current comparison CSV. Weaknesses: absolute paths, no dependency manifest/entrypoint/tests/assertions/CI/types/logging/schema checks, absent processed data/actuals generator, detached preprocessing, substring feature selection, dead validation variables, unsafe PKL-dependent visualization, stale outputs, and no source for key plots.

### 12. Demonstrable defects and concerns

| Severity | Classification | Evidence | Why / gate effect | Correction |
|---|---|---|---|---|
| Moderate | Verified defect | `process_data_v3.py:16-31`; actuals audit | 423 same-date artifacts; G2 fail | Dedup/exact adjacency |
| Material | Verified defect | `train_model_v3.py:24-47` | Full-data preprocessing; G3 fail | Train-fitted pipeline |
| Material | Verified defect | `train_model_v3.py:52-70` | Uncorrected class-balanced probabilities; G8 fail | Prior correction/calibration |
| Material | Verified defect | OOT evaluation code | OOT selects champion; G5 fail | Chronological validation then final |
| Material | Verified defect | LTV/sentinel audit | Mixed units and 9999/999 | Normalize/flag |
| Material | Verified defect | CLTV/macro joins | 50.9% CLTV missing and OOT macro gaps | Repair/flag/train-impute |
| Moderate | Verified defect | `process_data_v3.py:74-75` | Penalty constant zero | Normalize and derive expiry |
| Moderate | Verified defect | Substring selector/coefficients | Accidental/redundant features | Explicit schema/remove duplicates |
| Moderate | Verified defect | Split code/deck | OOT dates misstated | Generate labels from split metadata |
| Moderate | Packaging issue | README/results files | Conflicting generations/not rerunnable | One clean manifest/output |
| Moderate | Strong concern | Release joins | HPI/macro vintages unaddressed | Availability-date joins |

### 13. Candidate verdict

**Hard gate: Fail. Score: 44/100. Confidence: high. Recommendation: Reject.**

| Target | Validation | Method | Features | Communication | Reproducibility | Judgment | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 15 | 6 | 5 | 7 | 6 | 3 | 2 | 44 |

Top positives: all 6,125 positives are genuine exact-month events; chronological holdout concept/simple models; incentive/equity intuition and candid calibration warning.  
Top concerns: uncorrected weighted probabilities/OOT selection; full-data preprocessing and severe input defects; stale nonreproducible package.

Live questions:

1. Explain 402 duplicate groups plus 21 unique same-date artifacts.
2. Explain weighted-prior probability correction.
3. Redesign train/validation/final dates.
4. Repair LTV/sentinels/HPI/origination gaps.
5. Replace substring feature selection with an explicit schema.

Live code modification: implement unique exact-month target construction and direct validated actuals export.

## Sudhan Adithya
**Final rank: 18.**
### 1. Submission inventory

The folder contains an EML envelope and exactly two logical attachments: 13-slide `prepayment_deck.pptx` and one-page `prepayment_memo.pdf`; MIME attachment hashes match extracted files. The EML body/headers were not inspected. PPTX contains eight raster images but no chart data, notes, comments, code, macros, or external relationships.

No notebook, script, repository, response dump, prediction table, model artifact, environment, or machine-readable metrics were submitted. This contradicts references to an “accompanying notebook.” All model results are candidate-reported only and were not reproduced.

### 2. Target and panel construction

The deck/memo describe a current-month hazard whose next monthly record is PD, first-payoff truncation, and delinquency/default censoring. This is conceptually plausible, but sorting, deduplication, exact calendar adjacency, terminal handling, competing-exit coding, and export cannot be audited.

Reported panel is 550,424 at-risk rows and 6,125 events. That denominator is numerically consistent with an uncensored current-row denominator (~550,441) and roughly 17,400 above exact benchmarks 533,001–533,016, consistent with terminal/same-date zeros. It is a strong concern, not proof without code/dump.

### 3. Data cleaning and point-in-time handling

Candidate claims mixed-unit LTV repair, first-transition reduction, FICO9999/DTI0/999 missing flags, IO normalization, mixed-date parsing, strictly as-of macro/HPI, state HPI fallback, ~2% unmatched HPI, and two rate months forward-filled. Exact thresholds, mappings, unmatched handling, duplicate/static/balance/rate checks, train-only preprocessing, and release/vintage dates are absent.

The PIT gate is unverified. Observation-month labels do not establish information availability.

### 4. Feature engineering

| Feature | Formula | Sources | Rationale | Available | Missing | Shape | Final? | Expected | Observed | Concern |
|---|---|---|---|---|---|---|---|---|---|---|
| Incentive | Claimed `inc_pos/inc_neg`; exact sign/market series absent | Current rate/mortgage rate | Refi option | Claimed as-of | Rate tail ffilled | Possible zero hinge | Claimed both | Positive ITM/lockout OTM | Inference OR 1.36/pp | Champion formula absent |
| SATO | Missing formula | Original/market rate | Pricing selection | Origination | Unknown | Claimed line | Claimed full | Context | OR .91 inference model | Not champion evidence |
| Burnout | Missing window/aggregation | Incentive history | Missed opportunities | Through `t` claimed | Unknown | Path transform unknown | Claimed full | Negative | Not reported | Leakage/window unauditable |
| Age | Missing formula | Age | Seasoning | `t` | Unknown | Claimed hump | Claimed both | Peak/fade | Peak 12–18m claimed | Basis/knots absent |
| Balances/paydown | Size×incentive interaction claimed | Balances | Dollar option | `t` | Unknown | Interaction unknown | Claimed full | Larger response | Not reported | Current/original balance membership unclear |
| LTV/CLTV/HPA | Updated LTV/underwater/HPA claimed | Balance, original LTV, HPI | Equity | Claimed as-of | Fallback/~2% miss | Ratio/binary unknown | Claimed | LTV − | OR .99/unit inference | Formula/units/PIT absent |
| FICO/DTI/DSCR | Missing formulas; DSCR/investor combined | Static | Qualification | Origination | Claimed flags | Unknown | Claimed | Mixed | DSCR/investor OR .87 | Concepts conflated |
| Doc/occ/purpose/property | Seven categoricals claimed; not enumerated | Static | Segment behavior | Origination | Unknown | Dummies/native claimed | Claimed | Level-specific | Not reported | References/pooling absent |
| IO/mod/DQ/foreign/product | IO cleaned; final membership largely absent | Static/history | Contract/segment | Various | Unknown | Unknown | Unclear | Heterogeneous | Not reported | Insufficient evidence |
| Calendar/rates | Cyclical month, 3m momentum, unemployment | Date/macro | Seasonality/regime | Claimed as-of | Rate ffill | Unknown | Claimed | Regime-specific | Deterioration reported | Lags/formulas absent |
| Penalty | Active and expiry ramp claimed | Flag/term/age | Contract friction | `t` | Unknown | Indicator+ramp unknown | Claimed core | Active −, release | OR .61 inference | Knots/buckets absent |
| Missing/external | Missing flags claimed; no added external beyond assignment | Fields | Data quality | Various | Claimed | Binary | Claimed | Data-dependent | Not shown | Train fitting unavailable |
| Reporting | CPR, calibration, grouped CV, importance | Predictions/actuals | Investment diagnostics | Evaluation | N/A | Plots | No | N/A | Candidate claims only | Raster values unavailable |

### 5. Logistic/GLM feature shape

The champion is described as a regularized pooled logistic hazard with 26 numeric, seven categorical, and interactions. `inc_pos/inc_neg`, seasoning hump, and penalty ramp are claimed, but formulas, knots, degrees, coefficients, scaling, regularization, model matrix, reference categories, and interactions are absent. Odds ratios come from a separate parsimonious inference model, not the champion. No continuous feature can be reliably classified beyond claimed-only descriptions.

| Continuous group | Classification | Exact knots/edges/degree/df/caps | Evidence status |
|---|---|---|---|
| Incentive | Claimed degree-1 hinge | `inc_pos/inc_neg` imply a possible knot at zero; formulas and coefficients absent | Candidate claim only |
| Seasoning | Claimed nonlinear hump | Basis could be polynomial, spline, hinge, or bucket; no knots/degree/df supplied | Not available |
| Penalty expiry | Claimed ramp | No clock formula, knots, buckets, cap, or post-expiry treatment supplied | Not available |
| Updated LTV, FICO, DTI, SATO, unemployment, rate momentum | Likely straight terms in the separate inference model | “Per natural unit” OR language only; champion treatment unknown | Candidate claim only |
| Balance × incentive | Claimed interaction | Exact balance transform and interaction formula absent | Not available |
| Calendar month | Claimed cyclic | Sine/cosine versus month dummies unknown | Not available |
| Burnout | Claimed path-dependent | Window, dose, cap, fade, and interaction unknown | Not available |
| Original/current balance, HPA, DSCR, remaining IO, other continuous controls | Unknown/not established | No complete champion model matrix | Not available |

### 6. Tree models and constraints

| Algorithm | Hyperparameters | Role/regularization | Weights/stopping/tuning | Monotonic constraints | Final |
|---|---|---|---|---|---|
| Claimed histogram gradient boosting | No learning rate/depth/leaves/iterations/L1/L2/subsample/seed supplied | Challenger | No rebalancing claimed; early stopping/tuning unknown | None documented; monotonicity is future work | Logistic reportedly selected |

Regularization claims do not establish monotonicity.

### 7. Model specification and selection

Logistic and GBM are compared; no class rebalancing is claimed. The only disclosed calendar split is train before 2024/test 2024+. That same period supports model comparison, feature/lean-model comparison, importance, champion choice, and recalibration. No later test follows. Model specifications and tuning samples are unavailable.

### 8. Validation and leakage review

Chronological intent and grouped K-fold are positives. Grouped CV is not a substitute for calendar transfer. Final isolation fails; preprocessing/PIT/same-loan handling are unknown; no walk-forward, COVID, year/month table, uncertainty, or post-calibration test. “Regime risk, not instability” is stronger than one cutoff can establish.

### 9. Metrics and calibration

| Metric | Reported | Evidence |
|---|---:|---|
| At-risk/events/rate | 550,424 / 6,125 / 1.1128% | Candidate-reported counts; arithmetic verified |
| Logistic/GBM in-sample AUC | .72/.82 | Candidate-reported only |
| 2024+ AUC | ~.67 both | Candidate-reported only |
| Grouped-CV AUC | ~.73 | Candidate-reported only |
| Lift/capture | 2.7×/27% | Candidate-reported only; arithmetic relation valid |
| Full/lean OOT AUC | .670/.659 | Candidate-reported only |
| Raw logistic/GBM P:A | ~1.3/~1.5 | Candidate-reported only |
| Balance P:A | 1.37 | Candidate-reported only |
| Recalibrated ratio | .92 or “~1.0” | Inconsistent/candidate-reported |
| Log loss/Brier/PR/slope/intercept | N/A | Not available |
| Monthly/segment values/uncertainty | N/A | Not available |

Recalibration evaluated on its fitting/reused period does not establish future calibration.

### 10. Economic interpretation

Incentive, penalty, equity, seasoning, burnout, turnover/refi, balance-weighted calibration, and competing exits are strong concepts. Weaknesses: explanation-model ORs are attributed too broadly; OR .61 means 39% lower odds, not 37% suppression or probability; updated-LTV unit is unstated; DSCR/investor are conflated; balance-weighted relative error does not prove large loans prepay faster; one cutoff does not establish an AUC ceiling; “ready to price with” is unsupported.

### 11. Code and software engineering

No auditable implementation exists. Entrypoint, paths, versions, seeds, target assertions, preprocessing, model design, tree parameters, calibration, regeneration, and model/dump agreement cannot be assessed. Code/reproducibility receives zero.

### 12. Demonstrable defects and concerns

| Severity | Classification | Evidence | Why / gate effect | Correction |
|---|---|---|---|---|
| Material | Packaging issue | MIME inventory vs deck/memo notebook references | No implementation; G7 fail | Supply local source/environment/run order |
| Material | Missing evidence | No actual-response file | G6 fail; target unauditable | Three-column binary dump/audits |
| Material | Verified defect | Slides 5,8,10–13 | 2024+ reused for selection/recalibration; G5 fail | Separate tuning/calibration/final |
| Material | Strong concern | Slide 3/memo | “Next record” not exact month | Add adjacency/censoring guard |
| Material | Missing evidence | “Strictly as-of” claims | PIT/train-only transforms unknown | Availability dates/vintages |
| Moderate | Strong concern | Separate inference-model disclosure | ORs are not champion effects | Submit both specs/champion effects |
| Moderate | Missing evidence | Tree claims | Parameters/stopping/constraints absent | Full tree specification |
| Moderate | Missing evidence | Metric set | No proper scoring/uncertainty/monthly values | Complete untouched metric suite |
| Minor | Verified defect | OR .61 narrative | Odds arithmetic wrong | State 39% lower odds |
| Moderate | Strong concern | Slides 12–13 | Ceiling/readiness claims exceed evidence | Walk-forward/prospective validation |

### 13. Candidate verdict

**Hard gate: Fail. Score: 43/100. Confidence: high for package decision, moderate for underlying model. Recommendation: Reject.**

| Target | Validation | Method | Features | Communication | Reproducibility | Judgment | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 6 | 8 | 8 | 10 | 8 | 0 | 3 | 43 |

Top positives: good hazard concept; chronological/imbalance awareness; coherent economic narrative.  
Top concerns: no code/actuals; reused only holdout; exact target/PIT/specifications/metrics unsupported.

Live questions:

1. Show exact target code for gap/terminal/duplicate cases.
2. Enumerate every train/tune/calibrate/test date.
3. Derive incentive, burnout, updated LTV, and penalty expiry.
4. Separate champion effects from inference-model ORs.
5. State tree parameters and explain why .67 is not a ceiling.

Live code modification: add exact-month target eligibility and export a validated binary actuals file.

## Shiyuan Liang
**Final rank: 19.**
### 1. Submission inventory

The canonical ZIP contains one 47-cell Colab notebook, 11-slide PPTX, and CSV/Parquet prediction copies. Extracted notebook/CSV match archive; extracted folder omits deck/Parquet, so ZIP is canonical. CSV/Parquet have identical logical rows; XGB differs only by float32 serialization.

No README, local CLI, pinned environment, tests, model artifact, deck-build path, or actual-response dump. Deck train/test/AUC/PR and LR coefficients match notebook; XGB gain rankings match but magnitudes differ from notebook output.

### 2. Target and panel construction

The notebook strips IDs, parses dates, sorts, detects but retains 600 duplicate keys, shifts next observed status, retains all current rows, and sets `prepaid=next_status=="PD"`. It never shifts/checks next date or censors terminal rows. Evidence: notebook cells 12,17,23,26.

Independent target audit:

- Raw candidate risk set: 550,441 current rows/6,125 events.
- Correct unique exact-month non-absorbing target: 533,016/6,125.
- Excess: **17,002 terminal zeros + 423 retained same-date duplicate zeros**; no genuine post-dedup forward calendar gaps.
- Complete-case modeling: 494,499 rows/5,681 events.

Delivered CSV/Parquet are 494,499×4 predictions: `loan_id,date,lr_prepay_prob,xgb_prepay_prob`; no actual response. They have 389 duplicate keys and no nulls. Evidence: `prepayment_predictions.csv:1-5`; notebook cells 46–47.

### 3. Data cleaning and point-in-time handling

Reasonable: IDs/dates normalize; HPI uses supplied geography; IO/penalty/purpose/foreign encodings are attempted; LR scaler is train-fitted; burnout is lagged.

Defects:

- FICO median 737 is calculated on full panel before split; 19,981 values are imputed.
- LTV mixing is material: 272,693/773,046 panel rows (35.3%) and 193,864/550,441 current rows use fraction-style values; formulas assume percentages.
- Rate-unit anomalies exist but are sparse: only 31 current rows have `0<c_noterate<1`; not globally material.
- DTI clipping affects 38,905 rows, including 38,854 exact 999 sentinels, converting them to 65.
- Missing-purpose/IO/penalty/foreign values collapse to baselines without flags.
- Same-month macro/S&P/HPI lacks release/vintage control.
- Listwise deletion removes 55,942 risk rows without selection analysis.

Evidence: notebook cells 13–14,21,28,35.

### 4. Feature engineering

| Feature | Formula | Sources | Rationale | Available | Missing | Shape | Final? | Expected | Observed | Concern |
|---|---|---|---|---|---|---|---|---|---|---|
| Incentive | `coupon-PMMS_t` | Rates | Refi option | Same month | Complete-case | Straight/tree | Both | Positive | LR +.620; XGB rank 1 | Same-month PIT; sparse rate units |
| SATO | Not built | Orig/market rates | Pricing | Origination | N/A | Not used | No | Context | N/A | Missing |
| Burnout | Lagged cumulative prior ITM count; square LR | Incentive history | Missed opportunities | Prior observed row | Missing incentive=false | Quadratic/tree | Both | Hump/attenuation | +linear/−square | Duplicates/gaps/no magnitude/fade |
| Age | Age + age² | Age | Seasoning | `t` | Complete-case | Quadratic/tree | Both | Hump | +linear/−square | Turning point unavailable |
| Balances/paydown | `log1p(o_bal)`; current balance only inside LTV | Balances | Dollar/equity path | `t` | Complete-case | Log/indirect | Both/indirect | Positive | Orig balance + | No factor/curtailment |
| LTV/CLTV/HPA | Orig LTV raw; current LTV formula cap [0,150]; exact `ltv_change=orig-current` | Leverage/balance/HPI | Equity | Same-month HPI | Complete-case | Lines/cap/tree | Both | LTV − | Current −, change + | Material mixed units; exact collinearity |
| FICO/DTI/DSCR | Full-data-median FICO; DTI cap65; DSCR unused | Static | Qualification | Origination | Median/cap | Lines/tree | FICO/DTI | FICO +, DTI − | Small signs | Leakage/sentinel distortion; DSCR omitted |
| Doc/occ/purpose/property | Purpose/occupancy only | Static | Segment | Origination | Missing→baseline | Dummies/tree | Partial | Level-specific | Mixed | Documentation/property omitted |
| IO/mod/DQ/foreign/product | IO and foreign flags; no mod/DQ/product | Static/history | Contract/segment | Origination | Unknown→baseline | Binary/tree | Partial | Heterogeneous | Small negatives | Codes collapsed; no timing |
| Calendar/rates | Unemployment and SP500 YoY; no calendar term | Macro/date | Regime | Same month | SP500 missing→0 | Lines/tree | Both | Regime-specific | Unemployment + | PIT/no seasonality |
| Penalty | Permanent static `pp_flag` | Flag | Friction | Origination | Blank→0 | Binary/tree | Both | Negative active only | LR −.0745 | 198,818 flagged current rows; 30,584 strictly expired remain active |
| Expiry/missing | No expiry or missing flags | Term/age/fields | Contract/data quality | `t` | Baselines/deletion | Not used | No | Expiry release | N/A | Major omission |
| Reporting | Quarterly AUC, gains, coefficients | Outputs | Diagnostics | Evaluation | N/A | Plots | No | N/A | Deck drift | No calibration |

### 5. Logistic/GLM feature shape

| Group | Classification | Exact treatment |
|---|---|---|
| Age, burnout | Quadratic polynomial | Raw and square separately standardized |
| Current LTV | Cap-floor + straight | Clip [0,150] |
| DTI | Cap-floor + straight | Upper cap 65; sentinel becomes cap |
| Original balance | Log + straight | `log1p(o_bal)` |
| Incentive, LTV change, FICO, original LTV, unemployment, SP500 | Straight | No knots/interactions |
| Penalty/IO/purpose/occupancy/foreign/channel | Binary categories | Fixed indicators |
| SATO/expiry/CLTV/DSCR/mod/DQ/product/calendar | Not used | No shape |

No hinges or splines. XGB learns implicit piecewise-constant splits; exact thresholds unavailable.

### 6. Tree models and constraints

| Algorithm | Hyperparameters | Role/regularization | Weights/stopping/tuning | Monotonic constraints | Final |
|---|---|---|---|---|---|
| `XGBClassifier` | max 500; best iteration 83; LR .05; depth 5; row/column .8; AUC; patience 30; seed 42 | Co-submitted/better rank | `scale_pos_weight=68.4`; **final test is eval_set** | **None** | Unclear champion |

The final test selects iteration 83, so headline XGB evidence is tuned. Evidence: notebook cell 40.

### 7. Model specification and selection

LR is L1 `LogisticRegressionCV`, liblinear, ten Cs, three default stratified row folds, balanced weights; best C≈166.81 and all coefficients nonzero. Comments incorrectly say 20 Cs/five folds. XGB uses weighted test early stopping. No explicit champion, operational threshold, or untouched final window exists. Evidence: notebook cells 38,40,42.

### 8. Validation and leakage review

- Train: 2015-07–2023-12, 211,296/3,044.
- Test: 2024-01–2026-03, 283,203/2,637.
- No separate temporal validation/final holdout.
- Chronological principal split passes in form.
- LR CV is stratified row-level, not chronological/grouped.
- Full-data FICO imputation leaks.
- XGB test early stopping and cross-model comparison fail G5.
- Same-loan deployment interpretation, COVID-specific analysis, monthly calibration, segment/UPB validation are absent.

### 9. Metrics and calibration

| Metric | LR | XGB | Evidence |
|---|---:|---:|---|
| Test ROC / PR | .6598/.0194 | .6761/.0230 | Candidate-reported only |
| Log loss/Brier | N/A | N/A | Not available |
| Mean prediction, all rows | **43.1334%** | **40.1634%** | Independently verified from submitted output |
| Reported test actual | .931% | .931% | Candidate-reported only |
| Approximate O:P | .0216 | .0232 | Mixed evidence; actuals absent |
| Lift/capture/slope/intercept | N/A | N/A | Not available |
| Monthly calibration/UPB/SMM/CPR | N/A | N/A | Not available |
| Deterioration | ROC gap .052 | .115 | Candidate-reported only |

Class weighting/positive scaling is not prior-corrected or calibrated. The ~40% levels against ~1% events are unusable probabilities.

### 10. Economic interpretation

Incentive, quadratic seasoning/burnout, equity, balance, and FICO/DTI directions are broadly plausible. Individual LTV coefficients are unstable due exact linear dependence and unit errors. XGB gain has no direction. Permanent penalty and IO flags ignore expiry/recast. No calibrated monthly SMM/CPR or UPB evidence supports cash-flow use.

### 11. Code and software engineering

Positive: one visible notebook, proportionate scope, deterministic seeds, visible target/features. Weaknesses: Colab mount/hardcoded paths, unpinned runtime installs/upgrades, warning suppression, no assertions/tests/README/environment, duplicates only printed, no actuals export, no model/scaler/tree dump, manual deck drift, stale gain block, comments/code mismatch.

### 12. Demonstrable defects and concerns

| Severity | Classification | Evidence | Why / gate effect | Correction |
|---|---|---|---|---|
| Material | Verified defect | Notebook cell 26 | Positive events satisfy G1, but terminal/same-date zeros fail G2 | Shift date/status, exact-month censor |
| Material | Verified defect | Cell 17; deck slide 4 | Duplicates retained while deck says dropped | Resolve/assert before target |
| Material | Verified defect | Cells 46–47/output header | Predictions replace actuals; G6 fail | Binary three-column output |
| Material | Verified defect | Cells 38/40/47 | Weighted probabilities uncorrected; G8 fail | Unweighted/prior correction+calibration |
| Material | Verified defect | Cell 40 | Final test early stopping; G5 fail | Temporal validation |
| Material | Verified defect | Cell 21 | Full-data FICO median; G3 fail | Train-only imputer |
| Material | Verified defect | Unit audit/cell 28 | LTV units materially corrupt features | Normalize/flag/assert |
| Moderate | Strong concern | Cells 13–14 | Same-month macro/HPI PIT | Availability lags/vintages |
| Material | Verified defect | Penalty source/model | Permanent penalty beyond expiry | Active/remaining/post-expiry |
| Moderate | Verified defect | LTV formulas | Exact collinearity | Independent equity variables |
| Moderate | Packaging issue | Gain chart/notebook | Deck metric drift | Programmatic source table |
| Moderate | Packaging issue | Cell 2 | Colab/unpinned rerun | Local pinned runner |

### 13. Candidate verdict

**Hard gate: Fail. Score: 36/100. Confidence: high. Recommendation: Reject.**

| Target | Validation | Method | Features | Communication | Reproducibility | Judgment | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 7 | 8 | 6 | 6 | 5 | 3 | 1 | 36 |

Top positives: correct high-level current-loan hazard concept; chronological cutoff and simple LR/XGB comparison; relevant incentive/equity intuition.  
Top concerns: wrong target/deliverable; unusable weighted probabilities and test stopping; material units/sentinels/permanent penalty and weak reproducibility.

Live questions:

1. Trace terminal, two-month-gap, and duplicate rows through `shift(-1)`.
2. Produce the required actuals schema.
3. Explain weighted-probability correction.
4. Redesign exact train/validation/test dates.
5. Repair LTV/rate units and DTI sentinels.

Live code modification: replace target block with unique exact-month eligibility/censoring and validated actuals export.

## Hardi Ramani
**Final rank: 20.**
### 1. Submission inventory

The eight-member ZIP contains supplied HPI/assignment/dictionary/macro/panel, one 45-cell notebook, `loan_response.parquet`, and 13-slide PPTX. Extracted files exactly match archive; no stale candidate copies. Notebook code cells execute sequentially with no saved exceptions.

Only modeling source is the notebook. No README, environment, requirements, metrics/coefficient/prediction outputs, fitted model, or deck source is submitted. Deck slide 9 embeds training curves; slide 11 mixes model/windows; slide 3 contains placeholders.

### 2. Target and panel construction

The notebook deletes invalid FICO rows before target, parses/renames date, counts but does not resolve duplicates, sorts, shifts next status only, sets response for all current rows, exports, and only later deduplicates exact rows for modeling. It never checks next date or censors terminal rows. Evidence: notebook cells 7,13,15,21.

Audit of `loan_response.parquet`:

- 536,018 rows, 6,010 events, 23,789 loans, 2015-07–2026-05.
- Three columns, binary `int8`, zero nulls.
- **16,537 terminal zeros** (16,529 unique keys; eight duplicate rows).
- **413 duplicate key groups**, all pairs; **four conflicting `{0,1}` groups**.
- Model split total 535,621, 397 fewer than dump; 16 duplicate-key extras remain in model.
- 17 post-PD current rows, all zero.
- Candidate deletes 115 valid events via pre-target FICO filtering.

The realized positives are exact adjacent C→PD, but risk set/dump fail.

### 3. Data cleaning and point-in-time handling

FICO invalids are deleted, not imputed/flagged. LTV conversion is applied to `eligible` **after** train/validation/test `.copy()` objects are created; models retain mixed 0–1/0–100 units. Train has 47,287/132,419 rows LTV≤1; validation 27,168/77,990; test 113,633/325,212. DTI zeros/999 and zero note rates remain. Occupancy is modeled as continuous. Evidence: notebook cells 7,27,29,31,33.

`hpi_growth_12m` applies `pct_change(12)` after HPI is replicated across loan rows, so “12” means loan observations, not months. Independent comparison on 458,934 rows: 70.7% differ >1pp, 24.9% >5pp; median absolute error 2.44pp; sign differs 47.5%; correlation .422. Same-month HPI availability is also unproven.

### 4. Feature engineering

| Feature | Formula | Sources | Rationale | Available | Missing | Shape | Final? | Expected | Observed | Concern |
|---|---|---|---|---|---|---|---|---|---|---|
| Incentive | Intended generic names absent | Coupon/PMMS | Refi option | `t` | N/A | Not created | Deck-only | Positive | N/A | Actual fields not matched |
| SATO/burnout | None | Rates/history | Pricing/opportunity | Historical | N/A | Not used | No | Context/negative | N/A | Missing |
| Age | Raw age | Age | Seasoning | `t` | Median | Straight | Both | Nonlinear | Logistic −.168 | Deck says positive |
| Balances/paydown | Raw current balance; intended factor names absent | Balances | Dollar/path | `t` | Median | Straight | Current balance both | Positive/nonlinear | +.139 | No original/factor/curtailment |
| LTV/CLTV/HPA | Raw mixed orig LTV/CLTV; malformed HPI growth | Leverage/HPI | Equity | Same-month HPI | Median+indicator | Straight | Both | LTV −, HPA + | Mixed small coefficients | Dead unit correction/malformed HPI |
| FICO/DTI/DSCR | Valid-FICO-selected; raw DTI; DSCR absent | Static | Qualification | Origination | Median true null only | Straight | FICO/DTI | Mixed | +FICO/−DTI | Selection, 0/999 sentinels, DSCR omitted |
| Doc/occ/purpose/property | Purpose/property/channel categories; occupancy continuous; doc absent | Static | Segment | Origination | Most-frequent | One-hot/line | Partial | Level-specific | Mixed | Missing literals/reference issue |
| IO/mod/DQ/foreign/product | All absent | Static/history | Contract/segment | Various | N/A | Not used | No | Heterogeneous | N/A | Broad omissions |
| Calendar/rates | Same-date macro joined but excluded; calendar engineered then excluded | Macro/date | Regime | Same month | N/A | Not used | No | Regime-specific | N/A | No market-rate model |
| Penalty/expiry | None | Penalty/term/age | Contract friction | `t` | N/A | Not used | No | Active −/expiry lift | N/A | Core omission |
| Missing | Automatic HPI-growth missing indicator | Numeric features | Data quality | `t` | Pipeline | Binary | Both | Data-dependent | −.139 | Sentinels not made missing |
| Reporting/deck | Rate incentive, balance ratio, macro, calendar claimed/attempted | Generic names | Narrative | N/A | N/A | Dead/deck-only | No | N/A | Claims do not match fitted list |

### 5. Logistic/GLM feature shape

All modeled numerics are affine-standardized straight lines: original/current rate, FICO, original LTV/CLTV, DTI, age, current balance, malformed HPI growth, and occupancy code. No logs, caps, polynomials, buckets, hinges, splines, or interactions. Categorical one-hot blocks retain all levels with intercept/regularization, so individual ORs are not omitted-reference comparisons.

Core shape assessment: incentive absent; age too rigid; leverage mixed-unit; burnout/penalty expiry absent; raw balance line; malformed HPI line.

### 6. Tree models and constraints

| Algorithm | Hyperparameters | Role/regularization | Weights/stopping/tuning | Monotonic constraints | Final |
|---|---|---|---|---|---|
| LightGBM `LGBMClassifier` | binary; 500 trees; LR .03; leaves 31; row/column .8; seed42 | Optional nonlinear benchmark | `class_weight="balanced"`; no early stop/search; unpinned defaults | **None** | Ambiguous |

Stored ROC deteriorates .8977 train → .5775 validation → .5445 test. No importance/PDP/SHAP/tree dump. Weighted prevalence log shows .5, so raw probabilities are not portfolio levels.

### 7. Model specification and selection

Balanced liblinear logistic uses train-median indicators/scaling and full one-hot categoricals; balanced LightGBM compares on same windows. No explicit champion or predeclared rule. Deck feature-selection improvement to .63 exactly rounds logistic test .628867, strongly suggesting test-informed narrative. Slide 11 mixes validation-like AUC with unmatched/test-like recall.

### 8. Validation and leakage review

| Sample | Dates | Rows/events |
|---|---|---:|
| Train | 2015-07–2022-12 | 132,419/2,569 |
| Validation | 2023 | 77,990/477 |
| Test | 2024-01–2026-05 | 325,212/2,964 |

Chronology and train-fitted preprocessing pass structurally. Test contains 16,097 censored terminal zeros, including all May rows; both models are repeatedly reviewed on test; final purity is compromised. No later/rolling/COVID/monthly/UPB validation. Same-loan overlap is not automatically leakage.

### 9. Metrics and calibration

| Metric | Logistic | LightGBM | Evidence |
|---|---:|---:|---|
| Train/validation/test ROC | .6216/.5336/.6289 | .8977/.5775/.5445 | Candidate-reported only |
| PR | .0298/.0072/.0163 | .1783/.0157/.0125 | Candidate-reported only |
| Brier test | **.306329** | **.182306** | Candidate-reported only |
| Actual test | .9114% | Same | Independently verified from submitted output, but target defective |
| Mean predicted | ~54.12% from deciles | Exact unavailable; ≥16.27% lower bound | Candidate-reported/derived |
| O:P | ~.0168 | ≤.056 | Derived |
| Lift/capture | 2.304×/23.04% | N/A | Candidate-reported/derived |
| Log loss/slope/intercept/monthly/UPB/CPR | N/A | N/A | Not available |

Logistic Brier is 33.9× an optimal constant-rate Brier; LightGBM 20.2×. Balanced weights are not corrected or recalibrated.

### 10. Economic interpretation

Current coupon, FICO, DTI, and balance directions are superficially plausible, but coupon is not incentive, HPI is malformed, LTV mixed, age/deck signs conflict, and property/channel effects lack reference interpretation. Deck claims rate incentive/balance ratio that were never built. No calibrated SMM, penalty timing, competing-risk integration, or UPB output supports cash-flow use.

### 11. Code and software engineering

Positive: one sequential notebook, relative paths, orderly execution counts, sklearn pipelines, deterministic tree seed, short target logic. Weaknesses: no README/environment/tests/assertions/CI/types; warning suppression; duplicate processing continues; target exported before dedup; dead LTV conversion; stale generic column names; dead engineered fields; absent metrics/coefficients/predictions; manual deck/placeholder/drift; no output validation.

### 12. Demonstrable defects and concerns

| Severity | Classification | Evidence | Why / gate effect | Correction |
|---|---|---|---|---|
| Material | Verified defect | Notebook cell 15; dump audit | 16,537 terminal zeros; G2 fail | Exact-month censoring |
| Material | Verified defect | Cells 13/15/21; dump/model counts | 413 duplicate groups, 4 conflicts, dump mismatch | Dedup before target/export |
| Material | Verified defect | Cells 33/41/43 | Balanced raw probabilities; G8 fail | Unweighted/prior-correct/calibrate |
| Material | Verified defect | Cell 23 | Loan-row `pct_change(12)` malformed | Compute unique geo-month HPA |
| Material | Verified defect | Cells 27/31 | LTV conversion after split copies is dead | Normalize before split/assert |
| Material | Verified defect | Feature/deck outputs | Claimed features/signs absent/conflict | Programmatic feature/metric manifest |
| Material | Strong concern | Test .63 narrative | Test likely informed selection; G5 fail | Freeze before test |
| Moderate | Verified defect | Cleaning/model lists | Sentinels and occupancy semantics | Normalize/flag/category |
| Material | Verified defect | Slide 11/output | Mixed metric windows/stability claim | Model×window table |
| Moderate | Verified defect | Post-PD audit | 17 post-PD current rows | Absorbing rule/investigate |
| Moderate | Packaging issue | ZIP/notebook outputs | Missing environment/generated artifacts | README/pins/manifest/outputs |

### 13. Candidate verdict

**Hard gate: Fail. Score: 34/100. Confidence: high on findings; moderate on exact score. Recommendation: Reject.**

| Target | Validation | Method | Features | Communication | Reproducibility | Judgment | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 10 | 4 | 4 | 4 | 5 | 2 | 34 |

Top positives: chronological structural split; realized positives are genuine; sequential notebook and attempted model comparison.  
Top concerns: defective target/dump; unusable weighted probabilities; malformed/dead features and deck/model/window contradictions.

Live questions:

1. Why are May 2026 rows censored rather than zero?
2. Derive weighted-probability correction.
3. Reconcile deck feature list/signs with fitted model.
4. Identify data used for .63 feature selection.
5. Explain why loan-row HPI `pct_change(12)` is invalid.

Live code modification: normalize/deduplicate first, shift next date/status, enforce exact month, censor terminal/gaps, and export one unique binary actuals file.

# 14. Cross-candidate strengths and weaknesses

## Strengths that materially separate the top group

1. **Exact target construction is necessary but not sufficient.** Adarsh, Aishwarya, Charlotte, Carlos, David, Qin, Peter, Karan, Daniel, Xin, Thomas, Waner, Shravant, and Sanskriti produce exact event labels; the ranking then turns on PIT, validation isolation, calibration, and reproducibility.
2. **Chronological discipline matters more than model complexity.** Strong submissions use explicit calendar development/validation/test windows and understand why random loan-month splits are misleading.
3. **Probability quality is distinct from ranking.** Adarsh, Charlotte, Carlos, David, Qin, Peter, Karan, Daniel, Xin, Thomas, Waner, Shravant, and Sanskriti engage with Brier/log loss/calibration or level bias. Qin’s logistic-versus-HGB distinction is especially clear.
4. **Economic shape matters.** Adarsh, David, Peter, and Karan provide auditable prespecified hinges. Daniel, Xin, and Shravant use low-df splines. Charlotte has a useful incentive hinge system and burnout interaction.
5. **Penalty timing is a high-signal Non-QM concept.** Karan handles expiry most convincingly; Xin attempts a richer clock system. Static flags or total omission materially weaken many submissions.
6. **Honest limitation disclosure earns judgment credit but does not erase hard-gate failure.** Peter, Qin, Xin, Karan, and Daniel disclose meaningful caveats; their scores remain conditional because the defects still affect evidence validity.
7. **Engineering controls are valuable when they preserve lineage.** Peter and Daniel have strong test/manifest/CI structures; Charlotte, David, Thomas, and Shravant have comparatively clear static traceability.

## Repeated weaknesses

1. **Final-test reuse.** Charlotte and Waner have clear static G5 passes; David’s frozen final test appears clean but procedural lock is unproven. Most other submissions fail or cannot prove final isolation.
2. **Future modification status is a shared hidden leak.** Charlotte, Carlos, David, Qin, Peter, Karan, Xin, Waner, Shravant, Sanskriti, and Alan consume modification status before its effective date.
3. **Observation date is not availability date.** Same-month HPI/unemployment affects Adarsh, Aishwarya, David, Shravant, Sanskriti, and others without release/vintage evidence.
4. **Class weighting without probability correction.** Alan’s LR, Khush’s LR/XGB, Shiyuan’s LR/XGB, and Hardi’s LR/LGBM treat weighted scores as probabilities.
5. **Actuals versus modeled-population failures.** Alan and Shiyuan fail the required response dump outright; Sudhan supplies none; Adarsh’s exact dump does not match final features/predictions; Jarryd’s internally consistent dump is not the canonical population.
6. **Sentinel/unit/imputation failures.** Adarsh and Shravant fit medians on the full sample; Jarryd uses test medians; Waner leaves 187,790 LTV rows fraction-scaled, retains 241,029 DTI zeros, and clips DTI999/FICO9999 to maxima; Sanskriti, Khush, Shiyuan, and Hardi retain material sentinels/units.
7. **Regularization mislabeled as monotonicity.** Charlotte and Qin call HGBs constrained without monotone constraints; several others imply economic shape from depth/leaves alone.
8. **Calendar tracking is weak.** Pooled AUC and deciles often conceal regime-level level error. Peter and David are strongest; Carlos supplies auditable rows but omits final RF tracking; Shravant’s walk-forward table is descriptive and unstable.
9. **Open-panel cumulative hazards are misread as realized book runoff.** Karan’s compounded monthly means do not represent a fixed starting cohort.
10. **Packaging drift.** Adarsh’s full venv, Aishwarya’s version/output contradictions, Jarryd’s stale build, Waner’s missing audit files, Peter’s deck hash/count, Carlos’s summary count, Qin’s stale READMEs, Khush’s model generations, Sanskriti’s manual versions, Xin’s absent outputs, and Shravant’s stale docs/OS artifacts weaken lineage.
11. **Importance is not direction or causality.** Tree gain/permutation/SHAP evidence is frequently overinterpreted.

## Prior-triage reconciliation

The prior triage was materially too generous to Daniel, Karan, Peter, Qin, Sanskriti, and Xin because it underweighted future-dependent sample construction, PIT availability, final-test reuse, and missing lineage. The shared audit removed Charlotte’s prior Pass and lowered Carlos, Qin, Peter, Karan, Sanskriti, and Alan. Shravant was added after its archive appeared; Adarsh, Aishwarya, David, Jarryd, and Waner were added during the 2026-07-20 intake refresh. Arrival timing is not treated adversely. The triage was too harsh on Carlos for calendar tracking alone and incorrectly stated that Alan lacked a deck.

# 15. Candidate-specific live-defense questions and interview order

Each detailed verdict contains five questions and one code modification. The highest-value first question and modification are summarized here.

| Order | Candidate | Live-defense first question | Live modification |
|---:|---|---|---|
| 1 | Charlotte | Why is `mod_clean` positive before `mod_ft_pay_dt`? | Gate/remove future-effective modification status |
| 2 | Carlos | Why is raw `mod` future-positive, and what final information was seen before convergence correction? | Gate modification and add final RF monthly count/UPB tracking |
| 3 | Qin | How would you fix `ever_modified`, then reconstruct vintage-safe RPX inputs? | Gate modification and fix the RPX selector |
| 4 | Peter | How would you gate `mod_flag`, and what is the total sub-$22k balance OR? | Gate modification and correct cumulative hinge reporting |
| 5 | Daniel | Why can a later impossible transition not delete an earlier valid row? | Point-in-time row-and-forward quarantine |
| 6 | Karan | How would you prove both modification and HPI availability? | Gate modification and add `available_dt` PIT assertions |
| 7 | Xin | Show every future modification row and when fields were actually knowable | Gate/remove future modification fields |
| 8 | David | How would you gate modification and prove frozen-test governance? | PIT modification plus a new frozen-run manifest |
| 9 | Thomas | Reconcile the untouched-test claim with OOT-driven decisions | Make final test inaccessible until freeze |
| 10 | Shravant | How would you gate `is_mod`, isolate ablation, and rebuild current LTV? | PIT `is_mod` plus a new untouched evaluation plan |
| 11 | Waner | Why are modification, LTV units, and DTI coding all invalid? | Gate modification, normalize units, and add auditable predictions |
| 12 | Sanskriti | Why is `is_mod` future-positive, and why does OOT selection consume the test? | Gate modification and align monthly scored populations |
| 13 | Aishwarya | What is the canonical v2/v3 champion and untouched period? | One canonical validation-only run |
| 14 | Adarsh | Why does the model omit Apr-2026, and which decisions used test data? | Align model population, rebuild PIT features, and reserve a new test |
| 15 | Jarryd | Why are all dynamic features one month late? | Predictor-month rebuild with grouped shifts |
| 16 | Khush | Where should calibration occur after class weighting? | Train-only pipeline and exact-month target |
| 17 | Alan | Why are `mod_clean` and `response` both wrong for their claimed timing/meaning? | Gate modification and correct the actuals dump |
| 18 | Sudhan | Show exact target and every data window | Add adjacency/censoring and binary actuals export |
| 19 | Shiyuan | What does weighting do to a 40% score in a 1% population? | Correct target/dump and probability workflow |
| 20 | Hardi | Why is `pct_change(12)` over loan rows not 12-month HPA? | Rebuild target and geo-month HPA before modeling |

Interview decision rules:

- Charlotte, Carlos, Qin, Peter, Daniel, Karan, and Xin proceed beyond the conditional interview only if they identify the decisive defect without prompting and implement or precisely design the correction.
- David and Thomas proceed only if the reserve discussion demonstrates strong PIT and calibration ownership.
- Rejected candidates should not be rescued by headline AUC, presentation polish, or familiarity with mortgage terminology.

# 16. Evidence limitations

1. **No candidate model was run or reproduced.** Model fits, tests, notebooks, binaries, setup commands, and serialized model files were never executed/imported/deserialized.
2. Independent calculations were limited to read-only source/panel/output audits: schema, row/event counts, duplicate/null/binary checks, exact target reconciliation, arithmetic on submitted aggregate tables, and static feature/validation logic.
3. “Independently verified from submitted output” does not mean independently refit. It means a value was read from and reconciled within submitted machine-readable artifacts.
4. Prediction-level metrics could be independently recalculated only where predictions were submitted, including Carlos, David, Adarsh, and Jarryd. Many other model scores remain candidate-reported.
5. Office/PDF citations use slide/page references or clearly labeled extracted-text line ranges, plus internal package member references where needed; binary outputs are cited by full-file row/count audit, not invented line numbers.
6. Static review cannot determine live ownership, explanation quality, or whether a candidate can safely modify the work. Those are interview questions.
7. Final historical macro/HPI tables may contain revisions. Where source files lack release/vintage fields, the review distinguishes proven same-month implementation from unproven real-time availability.
8. Missing evidence is not treated as proof that a model behavior or experiment never existed. It is treated as unavailable evidence for the submitted package.
9. No allegation of fabrication, cheating, or improper authorship is made. Artifact conflicts are described as lineage, packaging, documentation, or reproducibility defects.
10. The final intake contains 20 candidates, 19 folders, and 18 root candidate ZIPs. Shravant remains archive-only; Sanskriti and Sudhan remain folder-only.
11. Adarsh, Aishwarya, David, Jarryd, and Waner were added during the 2026-07-20 intake refresh. Arrival timing carries no adverse inference.
12. Root-level candidate compilation/summary PDFs and filesystem metadata were excluded from candidate evidence.
