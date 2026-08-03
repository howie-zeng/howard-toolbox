# Technical Interview Question Bank

**Role:** Quantitative Software Developer / Credit Modeler  
**Purpose:** Test statistical fundamentals, mathematical reasoning, implementation knowledge, modeling judgment, and ownership.

## Question 1: Complete separation in logistic regression

### What this question tests

- Recognition of complete separation
- Understanding of maximum-likelihood logistic regression
- Ability to reason mathematically about log loss
- Knowledge of practical library behavior
- Credit-modeling judgment when a result looks unrealistically perfect

### Main question

Suppose you have a loan-level dataset with a binary default outcome and only one predictor: FICO score. In the observed data, every loan with a FICO score below 600 defaulted, while every loan with a FICO score above 600 did not default. Assume there are no observations with a FICO score exactly equal to 600.

What would you expect to happen if you fit an unregularized logistic regression using maximum likelihood?

### Expected answer

This is **complete separation**.

- FICO perfectly separates defaults from non-defaults.
- With default coded as 1 and raw FICO as the predictor, the FICO coefficient tends toward negative infinity.
- The intercept tends toward positive infinity at the corresponding scale so that the separating boundary remains between the highest-FICO default and the lowest-FICO non-default.
- Predicted default probabilities approach 1 below 600 and 0 above 600.
- No finite maximum-likelihood estimate exists.
- An optimizer may fail to converge, issue a separation warning, or return extremely large coefficients and standard errors.

If 600 is chosen as an illustrative separating boundary, a concise parameterization is:

```text
P(default | FICO) = sigmoid(a × (600 - FICO))
```

Equivalently, in the usual raw-FICO form:

```text
P(default | FICO) = sigmoid(β₀ + β₁ × FICO)
β₁ = -a
β₀ = 600a
```

The value 600 is not necessarily the unique boundary. If the observed classes are separated by a gap, any boundary inside that gap can separate the sample.

As `a → ∞`:

```text
P(default | FICO < 600) → 1
P(default | FICO > 600) → 0
```

This parameterization assumes there are no observations exactly at 600. An observation at exactly 600 would retain probability 0.5 under this particular parameterization, so the boundary would need to move. Whether complete or quasi-complete separation remains depends on the labels and surrounding support.

### Follow-up 1: Why does 100% accuracy not stop the optimizer?

Why does the optimizer continue increasing the coefficient magnitude after the model achieves 100% classification accuracy?

#### Expected answer

Logistic regression maximizes likelihood, or equivalently minimizes log loss. It does not minimize classification error.

Once all observations are on the correct side of the decision boundary, scaling the entire separating parameter vector still moves each predicted probability closer to its observed outcome:

- Defaults move closer to probability 1.
- Non-defaults move closer to probability 0.

Every increase improves the likelihood and reduces log loss. Classification accuracy remains 100%, but the likelihood has no finite maximizer.

### Follow-up 2: Show it mathematically

Can you explain the result using the logistic loss or likelihood?

#### Expected answer

For observation `i`, let:

```text
z_i = a × (600 - FICO_i)
p_i = sigmoid(z_i)
```

The binary log loss is:

```text
L_i = -y_i log(p_i) - (1 - y_i) log(1 - p_i)
```

For every default below 600:

```text
z_i → +∞
p_i → 1
L_i → 0
```

For every non-default above 600:

```text
z_i → -∞
p_i → 0
L_i → 0
```

The total loss approaches zero as `a → ∞`, but no finite `a` produces probabilities exactly equal to zero or one. Therefore, no finite MLE exists.

### Follow-up 3: Break the separation

Suppose one borrower with a FICO score of 650 defaults, while another borrower with a FICO score of 620 does not default. What changes?

#### Expected answer

The outcomes now overlap in FICO space, so no single threshold can perfectly separate defaults from non-defaults.

Increasing the negative FICO coefficient would improve predictions for most observations but assign an increasingly small default probability to the FICO 650 defaulter. The optimizer must trade off these observations, generally producing a finite MLE.

The combination of a non-default at 620 and a default at 650 guarantees that no one-dimensional FICO threshold can preserve the original ordering. More generally, the decisive condition is whether **any** linear boundary in the submitted feature space can still perfectly separate the outcomes.

### Follow-up 4: Practical implementation

Would you necessarily observe coefficient divergence if you used scikit-learn’s `LogisticRegression`?

#### Expected answer

Not necessarily. Scikit-learn applies L2 regularization by default.

The penalty makes very large coefficients costly, so the optimization problem has a finite solution. The estimated coefficient magnitude will depend partly on the regularization strength, controlled by `C`.

A smaller `C` means stronger regularization and a smaller coefficient magnitude. A large `C` approximates an unregularized fit and may expose numerical instability more clearly.

The candidate should distinguish:

- A finite penalized estimate
- A finite unregularized maximum-likelihood estimate

Regularization produces the former; it does not make the unregularized MLE exist.

### Follow-up 5: Modeling judgment

If you observed perfect separation in a real credit-risk dataset, what would you investigate before accepting the model?

#### Strong answers should mention

- Target or feature leakage
- Incorrect predictor and outcome timestamps
- Post-event or future information
- Small sample size
- Sparse categories or rare factor levels
- Underwriting and sample-selection effects
- Policy rules that mechanically determine the outcome
- Lack of support or overlap near the boundary
- Data-quality or coding errors
- Out-of-time performance
- Probability calibration
- Whether the relationship persists across vintages and economic regimes

The strongest candidates should be skeptical of an apparently perfect credit model before treating it as genuine signal.

### Follow-up 6: Possible solutions

If the separation is real and not caused by a data problem, how could you obtain finite, usable probability estimates?

#### Possible answers

- Ridge or another penalized logistic regression
- Firth bias-reduced logistic regression
- Bayesian logistic regression with proper priors
- More observations **if they introduce support and outcome overlap near the separating boundary**
- Substantively justified category merging when sparse categories create separation

The candidate should explain that regularization, Firth correction, or proper priors address the absence of a finite unregularized MLE. More data help only if they introduce overlap. Probability calibration does not make the separated MLE exist; it is a separate downstream step for assessing or correcting probabilities from the chosen finite estimator. Every solution still requires honest out-of-time validation.

## Suggested interview sequence

For a concise interview, ask:

1. What happens to the unregularized logistic regression?
2. Why does 100% classification accuracy not stop the optimizer?
3. Show the result using log loss or likelihood.
4. What changes when outcomes overlap in FICO space?
5. Why might scikit-learn still return a finite coefficient?
6. What would you investigate before trusting perfect separation?
7. How would you obtain finite probability estimates if the separation is genuine?

This sequence tests recognition, mathematical reasoning, counterfactual reasoning, implementation knowledge, and practical modeling judgment.

## Scoring guide

| Area | Points | Strong response |
|---|---:|---|
| Recognition | 2 | Immediately identifies complete separation and the absence of a finite MLE |
| Mathematical reasoning | 3 | Explains likelihood improvement after perfect classification and derives the limiting probabilities |
| Counterfactual reasoning | 1 | Understands that overlap, not merely one changed label, determines whether separation is broken |
| Implementation and remedies | 2 | Explains scikit-learn’s default regularization, the role of `C`, and valid finite-estimate approaches such as Firth or Bayesian logistic regression |
| Modeling judgment | 2 | Investigates leakage, timestamps, support, validation, and calibration before trusting the result |
| **Total** | **10** | |

### Interpretation

- **9–10:** Excellent statistical understanding and practical judgment
- **7–8:** Strong; minor gaps but fundamentally correct
- **5–6:** Recognizes the issue but lacks mathematical or implementation depth
- **3–4:** Partial understanding; confuses classification accuracy with likelihood or regularization
- **0–2:** Does not recognize separation or gives materially incorrect reasoning

## Red flags

- Says the model is valid simply because training accuracy is 100%
- Claims the optimizer should stop once every class is predicted correctly
- Does not distinguish classification error from log loss
- Says the finite scikit-learn result proves that separation is absent
- Treats a very large coefficient as reliable evidence without checking leakage or support
- Recommends using the fitted probabilities without out-of-time calibration assessment, or assumes recalibration is unnecessary without testing it

## Optional live extension

Ask the candidate to write a small simulation with:

- FICO values below and above 600
- Perfectly separated outcomes
- An unregularized logistic fit
- A regularized logistic fit
- One overlapping counterexample

Before running anything, ask the candidate to predict:

- Coefficient direction and magnitude
- Convergence behavior
- Predicted probabilities
- How the answer changes with regularization strength
