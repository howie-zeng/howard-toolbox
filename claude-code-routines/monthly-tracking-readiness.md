# Monthly Tracking Readiness

## Name

Monthly Tracking Readiness

## Description

On-demand pre-flight check. Report whether the month's RESI tracking data is complete enough
to write the Monthly Tracking Review from — which cohorts have landed, and whether the ones
that landed are actually usable.

## When to run

Run when asked, and as the first step of the Monthly Tracking Review. It is not scheduled.

Useful early in the month, before sitting down to write the review: a cohort whose tracking
pipeline failed is worth chasing on the 3rd, not discovered on the 7th. On the 2026-08 run
NQM had never been produced and HELOC had lost a projection — both would have been visible
days earlier.

This routine only reports. It does not draft, email, or fix anything.

## Instructions

Read `claude-code-routines/memory/monthly-tracking-review-scope.md` first — it holds the
methodology and the known failure modes.

```powershell
python monthly_tracking_review.py readiness --month YYYY-MM
```

Exit `0` means every cohort is present and clean. Exit `4` means something is missing or
gapped. The five cohorts are **STACR, CAS, NQM, JUMBO, HELOC**, read from
`R:\QR\Resi_shared\tracking\Dialed`.

Two distinct problems get reported, and they need different follow-up:

**A cohort is MISSING.** Its workbook was never produced for that month. This normally means
its tracking pipeline failed. Check the Jenkins monitor for the `quant-Monthly-ResiTracking-*`
jobs:

```powershell
python -m jenkins_monitor.cli facts --outputs outputs
```

Note that a failure there may have emailed nobody — `PAGER_DUTY` is unset for pipelines using
`notifyBuildResult`, so absence of a failure email is not evidence of health. Name the failing
build and the root cause from its console if you can.

**A cohort has a DATA GAP.** Its workbook exists, but a month's projection is zero or blank.
That is an absent projection, not a slow model, and it drags down every tracking-error window
containing it — so the cohort's ratios must not be quoted until it is fixed.

Worth checking whether the projection was present in a **prior** month's workbook for the same
cohort. If it was, the value was lost rather than never computed, which is a regression in that
month's tracking generation and a stronger thing to report. On 2026-08, HELOC's June projection
was `2.0519` in the July workbook and `0` in the August one, with an identical actual.

### Reporting

Give Howard, briefly:

- The readiness verdict and the per-cohort table.
- For anything missing: the likely pipeline cause, named as specifically as the evidence allows.
- For any gap: which windows are affected, and the recomputed figure so he can see the size of
  the distortion.
- Whether the review can proceed. It usually can — with the gaps stated explicitly rather than
  waited on.

## Rules

- Report only. No drafting, no emailing, no writing to `R:\QR\Resi_shared\tracking`.
- Never present a missing cohort as healthy, and never quote a gapped ratio at face value.
- If the Jenkins monitor cannot run, say job status is unknown rather than implying all clear.
