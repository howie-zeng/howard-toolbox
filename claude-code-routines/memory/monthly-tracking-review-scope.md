---
name: monthly-tracking-review-scope
description: "Methodology and traps for the Monthly Tracking Review email — which row/columns the quoted ratios come from, and the data gaps that silently corrupt them"
metadata:
  node_type: memory
  type: reference
---

How Howard's **Monthly Tracking Review** email is built, reverse-engineered from the
2026-01/06/07 sends and confirmed by him on 2026-08-04. Routine prompt:
`claude-code-routines/monthly-tracking-review.md`. See [[mailbox-folder-map]] for the mailbox
side.

**Data source:** `R:\QR\Resi_shared\tracking\Dialed`, one workbook per cohort per month, e.g.
`tracking_STACR_V1_8_2_CRT_20260803.xlsx`, `tracking_V1_7_6_NONQM_20260701.xlsx`. Cohort
order in the email: **STACR, CAS, NQM, JUMBO, HELOC**. `Undialed` holds identically-named
files and is the dial-verification twin, not a second data source. Files do **not** land on a
fixed day (`20260701`, then `20260803`) — this is why the routine is on-demand, not scheduled.

**Where the quoted numbers come from:** the **WAC `ALL AVG` row** (the *second* `ALL AVG` row
in column C) of the `CtP` sheet, and `CPR` for the cohorts where CPR is discussed. Columns are
`3M Error`/`6M Error`/`12M Error`, each an `Abs`+`Ratio` pair; the email quotes the **Ratio**
(cols 27/29/31). Verified: this row reproduces all five of the July 2026 figures — CAS 0.989→"0.99",
NQM 1.338→"1.34", JUMBO 1.171→"1.17", HELOC 1.096→"1.10". The AGE row does **not** match.

**`Ratio = sum(Proj) / sum(Actual)`** over the window — not Actual/Proj. Confirmed against the
Abs column's sign.

**Howard mislabeled the window in the July 2026 email** — he wrote "12-month average" for what
is the `6M Error` column, and confirmed on 2026-08-04 it was his mistake ("6error is the 6m
tracking error"). **How to apply:** label windows correctly going forward, and expect a
cohort's stated figure not to line up with July's email for the same metric. Say so in a
sentence rather than letting readers reconcile it.

**A zero/blank `Proj` month is an absent projection, not a slow model — and it drags every
window containing it (learned 2026-08-04):** HELOC's 2026-06 Proj was `0.000` in both `CtP`
and `CPR`. Reported 3-month CtoP was **0.72** against a true **1.04** excluding that month
(CPR 0.67 vs 0.98), and the 6M/12M figures were understated too. A draft was written claiming
HELOC "has turned materially slow" — caught only because the rendered screenshot showed the
`0.0`. **How to apply:** check every month's Proj for zeros before quoting any ratio.
`monthly_tracking_review.py` now prints `[DATA GAP]` and refuses to draft without
`--ack-gaps`. Never pass that flag until the narrative explains the gap and gives the
recomputed figure. Contrast a genuine turn: JUMBO on the same run had no missing months and
had genuinely reversed from over- to under-projecting, so its 3-month 0.87 was real.

**A zero Proj can be a LOST value, not a never-computed one — check the prior month's workbook
(learned 2026-08-04):** HELOC's 2026-06 projection at the WAC `ALL AVG` row was **2.0519** in
`tracking_V2_0_7_HE_20260701.xlsx` and **0** in `tracking_V2_0_7_HE_20260803.xlsx`, with an
identical actual (1.7278) in both. So the August tracking generation dropped a projection it
had produced the month before — a regression worth reporting, and a stronger statement than
"the month is blank." Substituting the known value gives a 3-month CtoP of ~1.08 against the
0.72 the August workbook shows. **How to apply:** whenever a Proj is zero, open the previous
month's workbook for the same cohort and compare that month's cell before describing the gap.

**A zero ACTUAL corrupts a ratio too, and the helper does NOT detect it (learned
2026-08-05):** `_proj_gaps` only inspects the Proj cell, so a missing *Actual* passes silently
— and because `Ratio = sum(Proj)/sum(Actual)`, a zero actual *inflates* the ratio instead of
dragging it. `tracking_V1_7_6_NONQM_20260701.xlsx` had 2026-06 Actual `0` against Proj
`2.383`, producing 3M `1.917` / 6M `1.34`. The July 2026 email quoted that `1.34` for NQM.
**How to apply:** eyeball the Actual side of the monthly pairs as well as the Proj side before
quoting; don't trust the absence of a `[DATA GAP]` line on its own. The 2026-08 books were
checked and are clean on both sides.

**CPR is the headline metric, not CtoP, and STACR needs the whole status chain (Howard,
2026-08-05):** lead each cohort's bullet with **CPR**. For **STACR**, walk the full delinquency
chain — **`M30`, `M60`, `M90P`, `M270P`, `FCLS`, `REO`** — not just the prepay summary, and call
out where a **dial** is needed; `FCLS` was the case that prompted this. **Ignore `CDR`
entirely** — Howard's explicit call, so do not resurface it even though the STACR/CAS `CDR`
`ALL AVG` row reads 2–3x over-projected. **How to apply:** a dial follows a miss that is
consistent across 3M/6M/12M on a row carrying real balance; the corrective factor is ~1/Ratio,
and a ratio above 1.00 means dial the projection DOWN.

**Deep delinquency transitions live in separate sheets with a different shape (learned
2026-08-05):** beyond `CtP`/`CPR` the workbooks carry `CDR`, `CtM30`, `M30tC`, `M30`, `M60`,
`M90P`, `M270P`, and — new in NQM V1_8_0 — `FCLS` and `REO`. The `M*`/`FCLS`/`REO` sheets have
**no `ALL AVG` row**: they are one row per transition (`M90PtC`, `M90PtFCLS`, `M270PtP`, …),
with the Ratio columns still at `AA`/`AC`/`AE` = 3M/6M/12M. Quote individual transition rows,
not a summary row. The thin `tD`/`tP` terminal rows run far from 1.0 on very little balance —
noise, not signal. Note the screenshot step captures **`CtP` only**, so any transition figures
in the narrative are unillustrated. **Never hardcode column numbers** — the transition sheets
are identical across cohorts (`N`=Actual, `O`=Proj, Ratio at `AA`/`AC`/`AE`), but STACR/CAS
*summary* sheets are wider because they carry rate-scenario forecast columns, so months start
at `Y` and Ratio sits at `AL`/`AN`/`AP`. Use the helper's `_ratio_columns` / `_monthly_pairs`.

**NQM model versions:** V1_7_6 ran through the 2026-07-01 generation; **V1_8_0** was added as
a parallel 2026-07-01 run (written 7/9) and is the sole run from 2026-08-03. So a July-vs-August
comparison for NQM crosses a model change — use the V1_8_0 July book, not V1_7_6, for a
like-for-like read.

**Readiness pre-flight:** `python monthly_tracking_review.py readiness --month YYYY-MM` reports
which cohorts have landed and which are missing or gapped (exit 0 ready, 4 not). Routine prompt
`claude-code-routines/monthly-tracking-readiness.md`, slash command `/tracking-readiness`. A
missing cohort usually means its tracking pipeline failed — and per [[mailbox-folder-map]],
`PAGER_DUTY` is unset for `notifyBuildResult` pipelines, so no failure email is sent at all.
Absence of a failure email is never evidence of health.

**Dial status must be verified, never carried forward:** `Dialed` vs `Undialed` numerically
identical ⇒ no dial applied; differing ⇒ dial applied (2026-07: identical for STACR/CAS,
divergent for NQM at 1.17 vs 0.78). When no `Undialed` twin exists for that date the answer is
**unverified — say nothing about dials**. On 2026-08 there were no August `Undialed` files, so
July's "no dial currently applied" could not be confirmed.

**The "charts" are Excel screenshots, not plots:** each `<COHORT> CtoP` image is a screenshot
of that cohort's `CtP` sheet, range **`A1:AE<2nd ALL AVG row>`** (the AGE and WAC blocks only,
not the FICO/MIS/UPDLTV blocks below), with its conditional formatting. Reproduced
pixel-identically via Excel COM `Range.CopyPicture(xlScreen, xlBitmap)` → Windows clipboard →
PIL `ImageGrab.grabclipboard()`. The `ChartObject.Paste()`/`Chart.Export()` route exports a
**blank** image at correct dimensions — do not use it. Excel must be `Visible = True` for
`CopyPicture` to work reliably.

**Recipient and subject:** subject `Monthly Tracking Review - <Month>`. July 2026 went To
`LibreMax-Modeling`; June and Jan went To Kiet Sam, CC `LibreMax-Modeling`. Sign-off is
`Best, / Howard Zeng / QR` — the helper emits that as plain text and does **not** attach
Howard's full Outlook signature with the logo.

**Never send — draft only.** The email goes to the whole modeling team and Howard signs it.
`--send` exists in the helper but the routine stops at `--draft`.
