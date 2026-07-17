# Candidate Submission Triage

**Scope:** `S:\QR\Hiring\HS_JrModeler\Test Submissions`
**Assignment:** loan-level one-month prepayment model, status `C` at month `t` to `PD` at month `t+1`
**Rubric:** `interview_notes/candidate_model_evaluation_rubric.md`
**Review mode:** static review of submitted artifacts; no candidate code was executed
**Cross-check:** `HS_JrModeler_Candidate_Summaries_v8.pdf` was read after independent review

## Bottom Line

Advance the candidates who got the target right, used a forward-time validation design, reported probability-quality metrics, and gave economically coherent drivers. Do not over-weight raw AUC or NQM vocabulary. The assignment is a screen for modeling judgment, leakage discipline, and ownership.

Current recommendation:

| Category | Candidates | Count |
|---|---:|---:|
| Clear Pass | Daniel Li; Karan Allagh; Peter Zhong; Qin (Allan) Dai; Sanskriti Sarkar; Xin Xu | 6 |
| Needs Discussion | None | 0 |
| Clear Fail | Alan Jia; Carlos Rivas; Khush Modi; Shiyuan Liang; Sudhan Adithya | 5 |

Correction note: the initial inventory used an ignore-aware file search that omitted
many binary deliverables. A direct disk audit subsequently found the submitted
response dumps, decks, figures, and archives. The response dumps were then read
directly to check schema, row count, event count, duplicate keys, nulls, and binary
values. This report uses the corrected inventory.

Daniel also lacks an actual-versus-projected calendar-time chart. He remains a pass
based on the overall submission: a conservative interpretable model, excellent
aggregate held-out calibration, correct target, clean response dump, and unusually
strong software discipline. For Carlos, the same omission is decisive because his
chosen random forest's level error changes materially across validation periods.
This is an overall candidate judgment, not a claim that the chart requirement was
applied as an absolute hard gate to every submission.

## Decision Definitions

**Clear Pass** means the submission is strong enough to advance on the technical assignment. It can still have caveats, especially calibration or packaging issues.

**Needs Discussion** means there is strong signal, but a material gap prevents a clean pass/fail call from the current folder alone.

**Clear Fail** means a hard gate or required-deliverable issue makes the submission unsuitable as-is.

Hard gates used:

- Correct `C` at `t` to `PD` at `t+1` response.
- Predictors observed no later than the prediction date.
- Genuine out-of-sample validation, preferably chronological.
- Response dump consistent with the modeled actual response.
- Enough code/artifacts to audit the work.

## Clear Pass

### Daniel Li - Clear Pass

**Score estimate:** 84 / 100
**Confidence:** high
**Why pass:** Strong target definition, probability modeling, chronological
validation, held-out calibration, and software engineering. The response dump and
slide deck are physically present and valid. This is a clear pass even though the
candidate should be asked about one future-aware data-quality filter and the absence
of calendar-time actual-versus-projected tracking.

Evidence:

- `loan_date_response.parquet`: 533,016 rows, 6,125 events, exactly
  `loan_id/date/response`, no duplicate keys or nulls, and binary response.
- `Slides.pdf`: reports held-out ROC-AUC 0.6702, Brier 0.011119, log loss
  0.059851, and 1.135% mean prediction versus 1.130% actual.
- `code/libremodel/target.py`: requires current `C`, an exact consecutive next
  month, and next status `PD`.
- `code/libremodel/splits.py`: train through 2024-12, validation during 2025-H1,
  and test from 2025-07.
- `code/`: packaged CLI, focused unit tests, CI configuration, and detailed
  methodology documentation.

Concerns:

- No actual-versus-projected chart through calendar time; slide 8 is calibration
  by prediction decile.
- Daniel identified and cleaned the prepayment-penalty fields, but explicitly
  excluded `prepayment_penalty_term` because of high missingness; neither the
  penalty flag nor term appears in the selected final formula. His pass is driven
  by target, validation, calibration, and engineering discipline—not penalty-term
  insight.
- Some whole-loan sample exclusions use future panel evidence to quarantine loans
  with invalid fields or impossible transitions. The candidate should defend this
  as data-integrity filtering rather than deployment leakage.
- The submitted code tree is duplicated under `code/code/`, which is packaging
  sloppiness but not a modeling failure.

Interview follow-ups:

- Ask the candidate to explain the whole-loan exclusion rules.
- Ask them to add monthly actual-versus-projected tracking.
- Ask why the selected spline GLM is preferable to a more flexible challenger.

### Karan Allagh - Clear Pass

**Score estimate:** 84 / 100
**Confidence:** high for modeling logic, moderate for package completeness
**Why pass:** Strong modeling judgment. The code and memo show the right target, explicit PD truncation, out-of-time validation, loan-level holdout, no class rebalancing, GLM versus LightGBM comparison, feature ablation, calibration gap analysis, and a clear recommendation for the auditable GLM over the more flexible model.

Evidence:

- `code/build_target.py`: `build_response()` uses current `C` rows and next observed `PD` as the response; final observed rows are excluded.
- `code/train_models.py`: primary OOT split at 2023-12, secondary random 20% loan-level holdout, early stopping inside the training window.
- `output/metrics.json`: OOT GLM AUC 0.681, LightGBM AUC 0.6824; GLM mean prediction 1.059% versus 0.943% actual; feature ablation shows rate incentive/burnout and penalty terms matter.
- `memo.md`: candidly explains overprediction, regime shift, and why higher OOT AUC would be suspicious.

Concerns:

- `response_dump.parquet`, seven figures, and the 15-slide PPTX are physically
  present. The predictions parquet expected by `validate_outputs.py` is not in the
  extracted folder.
- `code/build_target.py` defaults `DATA_DIR` to `../Karan Allagh` relative to `code/`, which would resolve to a nested `Karan Allagh\Karan Allagh` path unless `DATA_DIR` is overridden.
- The PPTX is a structurally valid Open XML package, but the default path should
  still be fixed before relying on the advertised one-command rerun.

Interview follow-ups:

- Ask the candidate to run `validate_outputs.py` or explain the missing artifacts.
- Ask why the GLM is chosen despite LightGBM's slightly better PR-AUC.
- Ask how they would recalibrate the 2024+ level bias without overfitting.

### Peter Zhong - Clear Pass

**Score estimate:** 84 / 100
**Confidence:** high for methodology, moderate for current-folder deliverables
**Why pass:** Excellent modeling discipline and self-critique. The README, memo, model card, source package, tests, and metrics show correct response timing, no random row split, train-only preprocessing, OOS and held-out-loan checks, calibration by decile/segment, rolling-origin validation, and honest disclosure that 2024-2026 backtest results are post-selection.

Evidence:

- `README.md`: defines `outputs/response_dump.parquet` as current-month `C` rows with `t+1` `PD`; 533,001 rows and 6,125 events.
- `MEMO.md`: explicitly rejects random row validation and discloses level overprediction and post-selection use of the 2024-2026 window.
- `MODEL_CARD.md`: says validation is not a pristine final holdout and future data remain the definitive prospective test.
- `outputs/metrics/metrics_summary.csv`: OOS GLM AUC 0.6701, GBM AUC 0.6787; GLM+walk-forward recalibration fixes count level to 1.006x actual.

Concerns:

- Two valid response-dump copies and a 48-slide PPTX are physically present.
- The submitted deck's hash does not match the canonical deck hash in
  `SUBMISSION_MANIFEST.json`, and the manifest's canonical deck/archive paths are
  absent. This is a lineage/packaging inconsistency, not a missing analysis.
- Raw OOS models materially overpredict levels: GLM 1.338x actual, GBM 1.443x actual before recalibration.
- Much of the strongest framing is model-risk-governance style; interview should verify the candidate can simplify it for PMs.

Interview follow-ups:

- Ask why post-selection OOS evidence is still useful but not final.
- Ask which result matters more for a cash-flow desk: ranking AUC or count/UPB calibration.
- Ask the candidate to reproduce the response dump from `src/prepay/dataset.py`.

### Qin (Allan) Dai - Clear Pass

**Score estimate:** 82 / 100
**Confidence:** high
**Why pass:** Clean, auditable baseline. This is the safest clear pass from the current physical folder because the response dump CSV is actually present. The methodology memo defines the correct one-month hazard, uses chronological train/validation/test, reports appropriate rare-event metrics, and makes a reasonable distinction between ranking and calibration.

Evidence:

- `model_response_by_loan_date.csv`: physically present three-column actual response dump.
- `METHODOLOGY_MEMO.md`: defines response as current `C` at factor date `t` transitioning to `PD` at `t+1`; trains through 2023, validates on 2024, tests 2025-April 2026.
- `reference_outputs/metrics.json`: test logistic ROC-AUC 0.6562, PR-AUC 0.0321, Brier 0.010106, log loss 0.05558; HGB ROC-AUC 0.6883 but lower PR-AUC and worse calibration.
- `reference_outputs/monthly_test_calibration.csv`: monthly actual versus predicted rates are reported.
- `External_Data_Sources_and_Experiment.md`: external RPX experiment is separated and limitations are disclosed.

Concerns:

- `Loan_Prepayment_Modeling_Deck_Qin_Dai.pptx` and
  `model_response_by_loan_date.parquet` are physically present. `REPORT.md`
  remains absent.
- HGB overpredicts the test event level: 1.337% predicted versus 1.031% actual in `metrics.json`.
- External-data experiment uses revised public histories; production use would require vintaged data.

Interview follow-ups:

- Ask whether logistic or HGB should be champion if the use case is cash-flow level rather than rank ordering.
- Ask how RPX data should be lagged and vintaged in production.
- Ask why the actual response dump uses column name `loan` instead of `loan_id`.

### Sanskriti Sarkar - Clear Pass

**Score estimate:** 80 / 100
**Confidence:** moderate-high
**Why pass:** Strong notebook-based analysis. The notebooks construct the right target, identify data defects, use out-of-time and out-of-loan validation axes, fit GLM and LightGBM, report AUC/PR-AUC/Brier/calibration/top-decile lift, and recommend the interpretable GLM when GBM does not improve OOT performance.

Evidence:

- `02_target_joins_features_v3 (2).ipynb`: documents risk set as `status == "C"` with next status observed; event is next status `PD`; reports 533,001 risk rows and 6,125 events.
- `02_target_joins_features_v3 (2).ipynb`: writes `model_frame.parquet` and `response_dump.parquet` inside the notebook.
- `03_models_validation_drivers_final.ipynb`: OOT test after 2024-06 and OOL 20% random loan holdout; training excludes both holdouts.
- `03_models_validation_drivers_final.ipynb`: GLM OOT AUC 0.6821, PR-AUC 0.0248, Brier x100 0.9907, predicted rate 1.12% versus actual 1.01%; GBM roughly ties OOT.

Concerns:

- The three notebooks, a 12-slide deck, a valid 533,001-row response dump, and a
  code archive are physically present.
- There is still no README, requirements file, scripted runner, or separately
  submitted prediction file.
- OOT probability levels overpredict by about 11% for GLM and 23% for GBM.
- Notebook-only workflow is harder to audit than a script/package.

Interview follow-ups:

- Ask the candidate to locate the exact cell that defines `event` and explain date convention.
- Ask why the training set excludes both future months and held-out loans.
- Ask why GLM is recommended over LightGBM.

### Xin Xu - Clear Pass

**Score estimate:** 86 / 100 for modeling; 75 / 100 for current-folder delivery
**Confidence:** moderate-high
**Why pass:** The strongest modeling package conceptually. The source and memo show careful point-in-time target construction, lagged macro/HPI joins, burn-out and penalty features, chronological train/validation/test, rolling-origin backtests, operational metrics, calibration, and explicit disclosure that the 2025-2026 holdout was reused across refinement rounds.

Evidence:

- `src/data_prep.py`: `build_target()` labels only current `C` rows with a consecutive next month and sets response to next-month `PD`; `export_actuals()` enforces the three-column actuals schema.
- `README.md`: defines risk set and response convention; says final observed month is censored and post-PD rows are dropped.
- `src/modeling.py`: train/valid/test split by month, GBM tuning on validation only, final scoring on 2025-2026 test; rolling-origin backtest.
- `src/evaluation.py`: includes ROC-AUC, PR-AUC, log loss, Brier, calibration slope/intercept, UPB-weighted obs/pred, monthly AUC, and monthly top-10% capture.
- `memo.md`: explicitly discloses the holdout reuse problem and distinguishes baseline single-touch results from refinement-round gains.

Concerns:

- A rendered 16-slide PPTX, valid 533,001-row actuals dump, and code archive are
  physically present at the candidate root. The README's claim that detailed
  experiment outputs are committed under `outputs/` remains false because that
  directory is absent.
- The final blend's 2025-2026 gains are candidate-grade, not final, because the holdout was reused across refinement rounds.

Interview follow-ups:

- Ask the candidate to distinguish pristine baseline holdout evidence from post-refinement holdout evidence.
- Ask them to rebuild or show the actuals dump.
- Ask how the blend would be governed if future lockbox months contradict the current result.

## Needs Discussion

None at this time.

## Clear Fail

### Carlos Rivas - Clear Fail

**Score estimate:** 84 / 100 on the written rubric; overridden by investment-validation judgment
**Confidence:** high
**Why fail:** The mechanics are strong, but the submission never shows model
projection versus realized prepayment through calendar time. For a prepayment
model intended to inform cash-flow timing, aggregate metrics and decile calibration
are insufficient when calibration changes across rate regimes.

Evidence:

- `outputs/loan_date_response.parquet`: valid 533,016-row binary actuals dump.
- `outputs/final_test_predictions.parquet`, 12 figures, and two copies of the
  14-slide PPTX are physically present.
- The deck shows development PR-AUC, aggregate final metrics, decile reliability,
  operating lift, coefficients, and partial dependence, but no monthly or
  quarterly actual-versus-projected tracking.
- The submitted plotting code has no calendar-time actual-versus-predicted routine.
- The RF's level error is unstable: approximately 22.6% overprediction in 2022,
  45.6% overprediction in 2023, 10.0% overprediction in 2024, then 8.1%
  underprediction in the final 2025+ holdout.

Why this matters:

- The direction of level bias reverses across periods.
- Pooled AUC, Brier score, and decile calibration conceal that regime instability.
- A portfolio manager needs evidence that projected cash-flow timing tracks
  realized speeds through time.

Interview follow-ups if still considered:

- Ask the candidate to add monthly count- and UPB-weighted actual-versus-predicted
  SMM/CPR.
- Ask why the random forest is called champion when its temporal level stability
  is not shown.

### Alan Jia - Clear Fail

**Score estimate:** 45 / 100
**Confidence:** high
**Why fail:** The target construction is directionally correct, but the required output is wrong: the submitted three-column `response` is model probability, not the binary actual response. That is a hard-gate failure. The approach also uses class-weighted logistic regression without calibration correction and reports permutation importance on the test set.

Evidence:

- `libremax.py`: `prepay` is correctly defined as current `C` with `next_status == "PD"`.
- `libremax.py`: `output_df["response"] = all_prob`; this writes predicted probabilities to the response column.
- `README.txt`: describes `output_predictions.parquet` as the required three-column output.
- Direct parquet check: 550,441 rows, continuous probabilities, 423 duplicate
  loan-date keys, and non-binary `response`.

Other concerns:

- HPI and macro are joined contemporaneously to `r_dt`; no publication lag discipline.
- Missing values are filled using the full modeled data before the split.
- The time split is an 80% date quantile, not a clean deployment-period split.
- No deck or standalone write-up is present in the current folder.

Interview follow-ups if still considered:

- Ask the candidate to explain the difference between actual response dump and predicted probability output.
- Ask how class weighting affects probability calibration.

### Khush Modi - Clear Fail

**Score estimate:** 50 / 100
**Confidence:** moderate-high
**Why fail:** The work has plausible feature ideas and an OOT split, but the
submitted package has hard-gate auditability problems: current-period feature
leakage, full-sample preprocessing, conflicting metric files, and duplicate
loan-date keys in the response actuals.

Evidence:

- `process_data_v3.py`: defines event at month `T` as `status(T) == "PD"` and `status(T-1) == "C"`, then lags dynamic features; this can be interpreted as equivalent timing if clearly documented, but the date convention is less natural than the predictor-month convention.
- `train_model_v3.py`: uses final six months as OOT and a stratified random split inside the earlier window.
- `comparison_table.csv`: XGBoost OOT ROC-AUC 0.6753, PR-AUC 0.0314; logistic ROC-AUC 0.6393, PR-AUC 0.0203.
- `model_results.csv` and `model_results_v2.csv`: conflicting metric histories; the earlier `model_results.csv` reports implausibly high OOT PR-AUC around 0.665.
- Direct parquet check: response file has 533,439 rows and 6,125 events but 402
  duplicate loan-date keys.

Other concerns:

- Paths such as `/home/ubuntu/project/project/loan_panel.parquet` make the project non-portable.
- `has_pp_penalty = (pp_penalty == "TRUE")` is likely brittle given the assignment's mixed encodings.
- Class weighting and XGBoost `scale_pos_weight` are used without a clear probability calibration correction.
- A deck, figures, and actuals files are physically present; the failure is
  modeling integrity rather than missing presentation.

Interview follow-ups if still considered:

- Ask the candidate to reconcile the conflicting metric files.
- Ask why duplicate actuals were produced.
- Ask how they would rewrite the target on predictor month `t`.

### Shiyuan Liang - Clear Fail

**Score estimate:** 37 / 100
**Confidence:** high
**Why fail:** The zip-only submission fails the target, predictor-timing, OOS
validation, response-dump, and calibration gates.

Evidence:

- `Shiyuan Liang.zip` contains one notebook, one deck, and prediction CSV/parquet
  files.
- The notebook uses next observed status without enforcing an exact next calendar
  month and labels terminal/gapped current rows as zero, producing 550,441 at-risk
  rows rather than the correct 533,016.
- Macro and HPI are joined contemporaneously at `r_dt` without publication lags.
- The 2024-2026 test set is used for XGBoost early stopping and best-iteration
  selection.
- The delivered parquet has 494,499 rows and four columns:
  `loan_id/date/lr_prepay_prob/xgb_prepay_prob`. It is predictions, not the
  required binary actual response, and has 389 duplicate loan-date keys.
- Mean probabilities are roughly 43.1% and 40.2% against an event rate near 1%
  because class weighting is not corrected back to probability levels.
- No Brier score, log loss, calibration, or actual-versus-projected tracking is
  reported.

### Sudhan Adithya - Clear Fail

**Score estimate:** 42 / 100 from local files
**Confidence:** high for current-folder review
**Why fail:** The memo is coherent, but there is no local code, no notebook, no response dump, and no inspectable pipeline. The email refers to an external Colab link and embedded attachments, but the current folder does not contain a runnable local submission. That fails the reproducibility and response-dump gates.

Evidence:

- `prepayment_memo.pdf`: describes the right conceptual hazard, data-quality issues, GLM/GBM comparison, no rebalancing, and OOT AUC around 0.67.
- `.eml`: contains an email with embedded attachments and external references, but no local source code or response dump is in the folder.
- Aggregate PDF: no parquet response dump was delivered, so schema, row count, duplicate keys, and binary-response checks cannot be verified.

Other concerns:

- Calibration is weak before recalibration; the memo says raw model overpredicts speed around 1.3x OOT.
- No local code means the target definition and feature timing cannot be independently audited.
- A linked Colab is not enough for this assignment unless the files are included or exportable.

Interview follow-ups if still considered:

- Ask for the local notebook/code and response dump before spending interview time.
- Ask the candidate to rebuild the target in front of you from the source panel.

## Cross-Candidate Observations

### What Separates the Passes

- The best submissions treat the problem as a discrete-time one-month hazard, not a loan-level "ever prepaid" classifier.
- The best submissions use time-forward validation and explicitly reject random row-level splits.
- Stronger candidates discuss probability levels, not only ranking: Brier, log loss, calibration deciles, SMM/CPR, and monthly actual-versus-predicted.
- Stronger candidates are candid about regime shift. AUC around 0.67-0.70 is credible here; much higher OOS performance would be suspicious.
- The strongest candidates know when a flexible model is not worth the interpretability/calibration cost.

### Repeated Weaknesses

- Several submissions package artifacts inconsistently even when the files are
  physically present; manifests, README paths, and extracted locations do not
  always agree.
- Several submissions confuse the required response actuals with model predictions, or at least make the output hard to verify.
- Class weighting or positive-class scaling appears frequently without enough calibration discussion.
- Some candidates use OOT windows repeatedly during model iteration; good candidates disclose this, weak candidates do not.
- Notebook-only submissions can be analytically strong but are harder to reproduce.
- Calendar-time actual-versus-projected tracking is often absent even when
  aggregate discrimination and calibration are reported.

## Suggested Interview Priority

1. **Howard's top group:** Karan Allagh, Xin Xu, Daniel Li.
   - Karan and Xin stand out for recognizing that the prepayment-penalty term is
     not merely a static flag: remaining term and expiry timing directly shape
     the prepayment curve.
   - Daniel ranks in the group for his model discipline and engineering, but he
     did not carry penalty term/expiry into the final model.
2. **Also worth interviewing:** Qin (Allan) Dai, Peter Zhong, Sanskriti Sarkar.
3. **Do not advance on current submission:** Alan Jia, Carlos Rivas, Khush Modi,
   Shiyuan Liang, Sudhan Adithya.

## Interview Questions to Use Across Passes

1. Show the exact target-construction code and explain why the response belongs to month `t` rather than month `t+1`.
2. Explain why your split represents future deployment.
3. Explain how AUC can be acceptable while probabilities are unusable for cash-flow levels.
4. Tell me which feature captures a 100 bp rate drop and what direction the effect should have.
5. Identify your largest leakage risk.
6. Remove the strongest feature and predict what changes.
7. Explain one AI suggestion you rejected.
8. Rebuild or inspect the actual response dump live.
