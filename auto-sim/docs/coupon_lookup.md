# FICO_BKT_COUPON vintage lookup — why the sim rebuilds it

## Symptom
The sim under-predicted `ctd1` (C→D1M) and mis-stated prepays vs realized,
even though the in-sample fit for the deal was good. The dump/engine were
proven faithful (sim ctd1 == original bam to 5e-4 on identical inputs), so the
gap was a **feature-value** mismatch, not a coef bug.

## Root cause
`rel_rate = note_rate / coupon_at_vintage` is a strong risk feature in `ctd1`
(and `rate_incentive_ALL` drives `ctp`/prepay). Both come from the
`FICO_BKT_COUPON` vintage-coupon lookup. For CRVNA 2022-P2 the sim was reading
coupons ~20–70% too high (e.g. 740+ 2022-04: **7.1%** vs the correct **4.1%**),
which deflated `rel_rate` from the trained ~1.34 to ~0.96 → the model saw the
loans as low-risk and under-called ctd1 at every age (worse at higher ages,
where ctd1 is larger).

The lookup the sim read (`LOOKUPS_DIR/<shelf>/FICO_BKT_COUPON.csv`) is **not**
the one the from0 models (ctd1/ctp) were trained on. In
`prep_transition.build_training_sets`, the lookup is computed over each
**from-state's at-risk `frame`** and the CSV is **overwritten every run**:

```python
frame   = p[(p.state == source_state) & ...]          # state-specific!
lookups = {"bkt_coupon": P.fico_bkt_coupon(frame, C)} # mean note_rate over frame
... to_csv(LOOKUPS_DIR/<shelf>/FICO_BKT_COUPON.csv)    # overwrites per from-state
```

`fico_bkt_coupon` de-dups to one row per loan, so the persisted CSV ends up
being the coupon over "unique loans ever in the *last* from-state that ran"
(e.g. S120 — higher-rate, delinquency-selected borrowers → inflated coupons).
The from0 (Current) population — what ctd1/ctp were trained on — gives the
correct, lower coupons (these are baked into `ctd1_train.parquet`).

## Fix (the auto-canonical way)
`processing.fico_bkt_coupon`'s own docstring says it is the mean note_rate over
the **de-duplicated origination snapshot (one row per loan), pooled across all
Prime issuers** — a market-wide reference. `tools/lookups/build_coupon_lookup.py`
rebuilds exactly that (all `*_panel.parquet`, de-duped by deal×asset → 9.78M
loans → `fico_bkt_coupon`) and writes `input/macro/FICO_BKT_COUPON.csv`. This
reproduces the training coupons (740+ 2022-04 → 0.042 ≈ training 0.041) and
feeds **both** `auto_tape`'s `rel_rate` and the sim's `rate_incentive_ALL`
macro.

`auto_tape._build_lookups` now reads `input/macro/FICO_BKT_COUPON.csv` (the
canonical rebuild), not `C.LOOKUPS_DIR`'s overwritten copy.

Result (CRVNA 2022-P2): ctd1 0.77%→0.88% (realized 0.95%), ctp into range
(1.61% vs 1.36%), CGL@48 3.82%→3.99%, lifetime CGL 3.82%→4.45%.

## Upstream fix (auto framework, not done here)
`prep_transition.build_training_sets` should persist `FICO_BKT_COUPON.csv` from
a **single canonical population** (the origination snapshot / from0), not
overwrite it per from-state. Until then, downstream tools that read the
persisted CSV (this sim, severity prep, dashboards) get whichever from-state
ran last. Rerun `tools/lookups/build_coupon_lookup.py` after any retrain.

## Secondary prep nits (small, not yet fixed)
- `month`: sim uses the current reporting month; training uses next month
  (`season_shift=1`). ~+0.005pp on ctd1.
- `days_to_month_end`: `None` at period 0 (term dropped) and `pmt_day` defaults
  to 15 for loans with no first-payment date in the early snapshot. ~+0.04pp.
