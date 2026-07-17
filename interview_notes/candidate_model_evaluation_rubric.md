# Candidate Model Evaluation Rubric

**Role:** Quantitative Software Developer / Credit Modeler
**Assignment:** Loan-level Non-QM prepayment model
**Candidate level:** New graduate
**AI use:** Permitted, but the candidate must explain and defend the submission
**Assessment confidence:** High

## Bottom Line

Do not primarily grade raw AUC, model complexity, or prior Non-QM knowledge.
The strongest signals are:

1. Correct target construction.
2. Leakage control.
3. Appropriate chronological validation.
4. Probability calibration and stability.
5. Economic reasoning.
6. Ability to explain and modify the submitted work.

A basic logistic model that is correctly constructed and honestly evaluated is
stronger than a polished machine-learning model fitted to a leaked or incorrect
response.

## Expected Interpretation of the Assignment

The response should generally be defined as:

```text
response(i, t) = 1 when status(i, t) = "C" and status(i, t + 1) = "PD"
```

The predictors must come from month `t`. The modeling population should
generally contain observations that are current (`C`) at month `t`.

The requested three-column response dump appears to mean:

```text
loan_id | r_dt | response
```

The assignment does not state whether `r_dt` should be the predictor month or
the subsequent event month. Accept either convention if it is clearly
documented, internally consistent, and free of future information. The
predictor-month convention is preferable.

## Hard Gates

Check these before assigning the detailed score:

- [ ] The response represents a genuine `C` to `PD` transition.
- [ ] Predictors are observed no later than the prediction date.
- [ ] The candidate performs genuine out-of-sample validation.
- [ ] The validation design respects calendar time.
- [ ] The response dump agrees with the modeling data.
- [ ] The candidate can explain the target, split, model, and principal results.

A materially wrong target, serious leakage, fabricated results, or inability to
explain the submitted work should override the numerical score.

## 100-Point Scorecard

### 1. Target and Panel Construction — 20 Points

**Score: ____ / 20**

Look for:

- [ ] Data are sorted by loan and date before creating the response.
- [ ] The response uses the next observed monthly status.
- [ ] Only eligible current loan-months enter the risk set.
- [ ] Rows without a valid subsequent observation are handled explicitly.
- [ ] Duplicate loan-date records and date gaps are investigated.
- [ ] Static loan attributes are checked for unexpected changes.
- [ ] Missing values and implausible values are handled sensibly.
- [ ] No future status, balance, HPI, or macro information is used.
- [ ] The three-column response dump is correct and reproducible.

The sophistication of the model cannot compensate for an incorrect response.

### 2. Out-of-Sample Validation and Leakage Control — 25 Points

**Score: ____ / 25**

Look for:

- [ ] The principal holdout is chronological rather than a random row split.
- [ ] The split represents how the model would be used prospectively.
- [ ] Imputation, scaling, encoding, and feature selection are fitted on the
      training sample only.
- [ ] Results are compared with a simple baseline.
- [ ] Training and holdout performance are compared directly.
- [ ] Performance is examined across calendar periods.
- [ ] The candidate discusses rate-regime changes and COVID-era instability.
- [ ] Calibration and ranking are both evaluated.
- [ ] Material performance deterioration is disclosed rather than hidden.

A random loan-month split is misleading because the same loans repeat across
months and historical regimes are mixed between training and testing.

The same surviving loan appearing before and after a chronological cutoff is
not automatically leakage. It can represent forward scoring of an existing
portfolio. The candidate should understand and explain the intended use case.

### 3. Modeling Methodology — 15 Points

**Score: ____ / 15**

Look for:

- [ ] A defensible logistic/GLM or other simple baseline.
- [ ] Model choice is explained rather than selected by fashion.
- [ ] Model complexity is proportionate to the six-to-eight-hour assignment.
- [ ] Predictions are treated as probabilities, not merely classifications.
- [ ] Event imbalance is handled thoughtfully.
- [ ] Class weighting or undersampling is accompanied by a calibration
      discussion or correction.
- [ ] Additional models, if used, are compared on the same holdout.
- [ ] Hyperparameter tuning does not contaminate the final test sample.

Do not reward boosted trees merely for being more sophisticated.

### 4. Features and Economic Interpretation — 15 Points

**Score: ____ / 15**

Economically sensible candidate features include:

- Refinance incentive: current note rate relative to market mortgage rates.
- Loan age or seasoning.
- Current and original balance.
- FICO, LTV/CLTV, DTI, occupancy, purpose, and property type.
- Prepayment-penalty status and remaining penalty term.
- HPA since origination or an approximate current-equity measure.
- Product type, documentation type, DSCR, IO, and foreign-national status.
- Rate-regime or calendar effects.

Look for:

- [ ] Features use only information available at the prediction date.
- [ ] Important effects have plausible directions.
- [ ] Magnitude and economic relevance are discussed.
- [ ] Interactions or nonlinearities have a defensible purpose.
- [ ] Feature importance is not described as causality.
- [ ] Unexpected effects are investigated rather than rationalized after the
      fact.

Non-QM-specific concepts such as burnout, turnover/refinance decomposition,
competing risks, LLPA-adjusted incentive, and CPR should be treated as bonuses,
not prerequisites for a new graduate.

### 5. Communication and Presentation — 10 Points

**Score: ____ / 10**

The deck should let an investment or risk reader answer:

- [ ] What exactly was modeled?
- [ ] Is the model usable out of sample?
- [ ] What drives predicted prepayment?
- [ ] Where and when does the model fail?
- [ ] What portfolio decision could be informed by the results?

Penalize unreadable charts, unexplained acronyms, methodology-heavy slides, and
conclusions that are not supported by validation.

### 6. Code Quality and Reproducibility — 10 Points

**Score: ____ / 10**

Look for:

- [ ] A clear execution order or entry point.
- [ ] Relative or configurable paths.
- [ ] Deterministic seeds where relevant.
- [ ] No hidden manual transformations.
- [ ] Target construction is easy to audit.
- [ ] Submitted predictions and charts can be regenerated from the code.
- [ ] Code is reasonably organized and documented.
- [ ] The solution avoids unnecessary framework code or abstraction.

### 7. Judgment and Ownership — 5 Points

**Score: ____ / 5**

Look for:

- [ ] Assumptions are explicit.
- [ ] Limitations are candid.
- [ ] Work is prioritized sensibly under the time limit.
- [ ] Unsuccessful experiments are reported honestly.
- [ ] The candidate distinguishes predictive association from causation.
- [ ] The candidate can explain and modify the submitted work.

## Recommended Model Metrics

Accuracy should not be a primary metric. Monthly prepayment is imbalanced, so a
model predicting no prepayment everywhere may have high accuracy and no
economic value.

Preferred evaluation:

1. **Log loss** and **Brier score** for probability quality.
2. **Calibration:** predicted versus observed prepayment rates.
3. **PR-AUC** and **ROC-AUC** as secondary ranking measures.
4. Observed versus predicted prepayment by calendar month.
5. Calibration by prediction decile and major loan segments.
6. Count-weighted and, ideally, current-balance-weighted results.
7. Monthly SMM and optionally CPR:

   ```text
   CPR = 1 - (1 - SMM)^12
   ```

8. Deterioration from training to validation and final holdout periods.

For an investment audience, stable aggregate calibration is generally more
useful than maximizing classification accuracy or F1.

## Major Red Flags

Heavily downgrade or reject submissions with:

- A contemporaneous or otherwise misaligned response.
- Future-status or future-period leakage.
- No genuine holdout.
- Only a random loan-month split.
- Accuracy as the principal evidence of model quality.
- Class weighting or undersampling with uncorrected probabilities.
- An elaborate machine-learning model with no baseline.
- Feature importance without direction or economic interpretation.
- A response dump inconsistent with the model data.
- Results that cannot be reproduced from the submitted code.
- Code or analysis the candidate cannot explain.

## Testing AI Ownership During the Interview

The polished deck and code are weak evidence of individual ability when AI use
is permitted. Ask the candidate to:

1. Show the exact target-construction code and explain every shift and filter.
2. Explain why the chosen split represents future deployment.
3. Explain how a model can have strong AUC but unusable probabilities.
4. Describe what should happen to prepayment if market rates fall by 100 basis
   points and identify the feature that captures it.
5. Identify the largest leakage risk in the submission.
6. Predict what would happen if the strongest feature were removed.
7. Make one small modification using the submitted code.
8. Identify one AI suggestion that was rejected and explain why.

The candidate does not need to have known Non-QM modeling before the exercise.
They do need to demonstrate statistical fundamentals, economic intuition,
learning ability, and ownership of the submitted work.

## Overall Assessment

**Total score: ____ / 100**

**Hard-gate result:** Pass / Fail

**Recommended decision:** Strong advance / Advance / Discuss / Reject

**Primary strengths:**

-
-
-

**Primary concerns:**

-
-
-

**Interview follow-ups:**

-
-
-

Do not allow presentation quality or a high headline metric to outweigh errors
in the target or validation design. A modest-performing, correctly validated
model is a strong new-graduate submission; a high-performing leaked model is
not.
