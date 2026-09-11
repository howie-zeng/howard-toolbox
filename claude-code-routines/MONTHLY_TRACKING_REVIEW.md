# Monthly Tracking Review — Runbook

Everything needed to produce the Monthly Tracking Review email, and everything that has
already gone wrong doing it. Read this before changing the helper or the routine prompts.

Built 2026-08-04 by reverse-engineering Howard's own sends (2026-01, 2026-06, 2026-07) out of
Outlook, and confirmed against him.

## What this is

A monthly email to `LibreMax-Modeling` reporting how the RESI models are tracking across six
cohorts — **STACR, CAS, NQM, JUMBO, FIGRE, HELOC** — with the per-cohort tracking workbooks
attached and a screenshot of each cohort's `CtP` sheet inline.

### The FIGRE / HELOC split — read this before anything else

Through 2026-08 the routine had five cohorts and the one it called **HELOC** was really the
**Figure** book, `tracking_V2_0_7_HE_<date>.xlsx`. Two things changed for the 2026-09 cycle:

- The Figure report is now named `tracking_V2_0_7_FIGRE_<date>.xlsx` — LMQR commit `79037f1a0`
  (`tracking_report_stem` in `lmanalytics/tracking/transition_report.py`) — and the historical
  files under `Dialed` and `Undialed` were renamed to match.
- A genuinely new cohort landed: the **non-Figure HELOC** book,
  `tracking_V1_0_V5_HE_<date>.xlsx` (`MODEL_VERSION_HELOC = "V1_0_V5_HE"`,
  `DealType.HELOC_PSEUDO`), first present in `Dialed` for 2026-09.

So `_HE_` no longer means what it used to. The old discovery pattern
`^tracking_.*_HE_(\d{8})\.xlsx$` never stopped matching — it silently began resolving to a
**different cohort**, and FIGRE dropped out of the review with no warning whatsoever. Run
against the 2026-09 data before the fix, `readiness` printed **"5 of 5 cohorts present —
READY"** while reviewing the wrong HELOC book and omitting Figure entirely.

`COHORTS` now carries both, FIGRE ahead of HELOC (`_scan` stops at the first matching
pattern), and the email order is **STACR, CAS, NQM, JUMBO, FIGRE, HELOC**.

**A cohort count is evidence of nothing.** Readiness counts what the patterns matched, not what
should exist. A renamed product passes every check it has.

Two routines, both **on-demand**:

| Routine | Prompt | Command | Purpose |
| --- | --- | --- | --- |
| Readiness | `monthly-tracking-readiness.md` | `/tracking-readiness` | Is the month's data reviewable yet? Reports only. |
| Review | `monthly-tracking-review.md` | `/monthly-tracking` | Writes the narrative, renders charts, leaves a draft. |

Shared helper: `monthly_tracking_review.py`. Shared memory:
`memory/monthly-tracking-review-scope.md`.

### Why neither is scheduled

- **The workbooks do not land on a fixed day.** July 2026 was dated `20260701`, August
  `20260803`. A cron would fire on days the files are not there.
- **Every month needs judgment.** On the first real run, NQM was missing entirely and HELOC had
  lost a projection in a way that made a healthy cohort look broken. An unattended run would
  have mailed a false claim to the whole modeling team or stalled.
- A monthly review a day late costs nothing. A wrong one costs a lot.

The daily RESI/CLO summary is scheduled because a missed day is a real loss. This is the
opposite trade.

## How to run

The normal path is to ask Claude — "run the monthly tracking review" — because the narrative is
judgment, not templating. The commands below are what that does underneath.

```powershell
python monthly_tracking_review.py readiness --month 2026-09
```

Exit `0` = every cohort present and clean. Exit `4` = something missing or gapped. Not a
blocker; it tells you what the narrative must address.

```powershell
python monthly_tracking_review.py facts --month 2026-09
```

JSON: per-cohort as-of date, dial status, 3M/6M/12M ratios for `CtP` and `CPR`, per-month
Actual/Proj pairs, and gap flags. `[DATA GAP]` and missing-cohort notes go to stderr.

```powershell
python monthly_tracking_review.py draft --month 2026-09 `
  --narrative outputs/monthly-tracking-review-202609.html `
  --draft
```

Renders the screenshots, attaches the workbooks, inlines the images, saves to Outlook Drafts.
`--dry-run` writes `preview.html` instead. `--send` exists and the routines never use it.

Narratives are kept at `outputs/monthly-tracking-review-YYYYMM.html` so a run is reproducible
without recomputing.

## The data

`R:\QR\Resi_shared\tracking\Dialed` — one workbook per cohort per month:

```
tracking_STACR_V1_8_2_CRT_20260901.xlsx
tracking_CAS_V1_8_2_CRT_20260901.xlsx
tracking_V1_8_0_NONQM_20260901.xlsx
tracking_V1_8_4_JUMBO_20260901.xlsx
tracking_V2_0_7_FIGRE_20260901.xlsx     <- Figure; was tracking_V2_0_7_HE_* through 2026-08
tracking_V1_0_V5_HE_20260901.xlsx       <- non-Figure HELOC, new in 2026-09
```

The model-version segment changes between months, so discovery is by regex on cohort +
date-stamp, not by fixed filename.

`Undialed` holds identically-named files and is the **dial-verification twin, not a second data
source**. `Dev`, `FullTracking`, and `test` are not used by this routine.

Each workbook has one sheet per transition: `CPR`, `CDR`, `CtP`, `CtM30`, `M30tC`, `M30`, `M60`,
`M90P`, `M270P`, and sometimes `FCLS`/`REO`. Layout of the sheets that matter:

- Row 2 — month headers (six months, newest first), then `3M Error`, `6M Error`, `12M Error`.
- Row 3 — cohort descriptors in cols B–M, then `Actual`/`Proj` pairs per month, then `Abs`/`Ratio`
  pairs per window. `Ratio` columns are 27, 29, 31.
- Row 4+ — data grouped into dimension blocks (AGE, WAC, FICO, MIS, UPDLTV, …), each block
  ending in an `ALL AVG` row.

Never open either folder for write. The helper copies to a scratch directory before Excel
touches anything.

## Methodology

**Quoted ratios come from the WAC `ALL AVG` row** — the *second* `ALL AVG` row in column C.
This was established empirically: it reproduces all five figures from the July 2026 email
(CAS 0.989→"0.99", NQM 1.338→"1.34", JUMBO 1.171→"1.17", HELOC 1.096→"1.10" — that "HELOC" is
the **Figure** book, which the review now calls FIGRE). The AGE row does not match and will
mislead you. `facts` reports both so you can cross-check.

**`Ratio = sum(Proj) / sum(Actual)`** over the window — not Actual/Proj. Confirmed against the
sign of the `Abs` column. A ratio below 1.0 means the model is projecting slower than actual.

**The published email stays high-level.** CPR/CtoP 3M/6M/12M plus one takeaway per cohort.
**FCLS is STACR-only.** CAS does not report FCLS; FCLS/REO rows in the CAS tracking workbook
are derived and must not be quoted or dialed.
**Prefer no dial; still dial if the model is off.** A newly released model is left undialed
and should converge to 1 (NQM V1_8_0 is the exhibit). If the published miss is the dial
itself, propose taking it off. If the undialed model is actually off (consistent miss, not
a window/restatement/gap), we still dial. Quote undialed CtoP and CPR separately — HELOC
2026-09 undialed CPR 12M was 1.00 while undialed CtoP was ~1.18. Screenshot the undialed
`CtP` sheet for that comparison; copy it to a distinct local filename first (Dialed/Undialed
share basenames). Delivery is `emailer/run.py --md-file` paste, not the helper Outlook draft.

**Label the windows correctly.** `6M Error` is the six-month tracking error. The July 2026 email
called it a "12-month average"; Howard confirmed that was his mistake. Consequence: a cohort's
correctly-labelled figure will not line up with what July's email said for the same metric — if
that is visible, say so in a sentence rather than leaving the team to reconcile it.

**Dial status is verified or omitted, and it is read off the projections, not the ratios.**
`dial_status` compares the per-month `Proj` values at the quoted WAC `ALL AVG` row of `CtP` and
`CPR` and reports the median dialed/undialed factor per sheet; months where either side's
projection is missing or zero are skipped and counted. When no `Undialed` twin exists the
answer is **unverified — say nothing about dials**, and never carry forward the previous
month's claim.

The check used to compare only the window `Ratio` cells, and that was **wrong in four of six
cohorts on 2026-09**: STACR and CAS reported "dial applied" off a +0.20 gap on the 3M `CtP`
ratio that was one absent 2026-08 projection (the surviving CAS buckets are bit-identical to
16 significant figures), JUMBO's "dial" was 7e-09 of float noise, and FIGRE's was an `Undialed`
book of zeros. Only HELOC had a real dial — ×1.1999 on `CtP` and ×1.15 on `CPR`, uniform across
all 35 rows and all six months. **That uniformity is what a dial looks like**; a one-month,
one-column difference is a defective run.

Two related facts worth holding. The `Undialed` books are a **separate, later re-run** — ~24 h
after their `Dialed` twins on 2026-09, except NQM at 9 minutes — not a no-dial branch of the
same process, so an incomplete newest column there says nothing about dialing. And a dial can
be sheet-specific: NQM's `CtP` is bit-identical dialed vs undialed while its `CPR` carries a
uniform +0.8%, so "NQM is undialed" is true only of `CtP`.

## Failure modes

Each of these has been hit. Do not re-derive them.

**A zero or blank `Proj` is an absent projection, not a slow model.** Because the window ratio
is summed-Proj over summed-Actual, one zero month drags down every window containing it. HELOC
2026-06 showed a 3-month CtoP of **0.72** against a true **~1.08**. A draft was written claiming
HELOC "has turned materially slow" and was caught only because the rendered screenshot showed
the `0.0`. `draft` now refuses to run when a gap is present unless `--ack-gaps` is passed — do
not pass it until the narrative explains the gap and gives the recomputed figure.

**A zero `Proj` may be a *lost* value.** HELOC's 2026-06 projection was `2.0519` in the July
workbook and `0` in the August one, with an identical actual (`1.7278`). That is a regression in
the August tracking generation, and a stronger thing to report than "the month is blank." When a
Proj is zero, open the previous month's workbook for the same cohort and compare before
describing the gap.

**Distinguish a data artifact from a genuine turn.** On the same run, JUMBO had no missing months
and had genuinely reversed from over-projecting early in the year to under-projecting recently,
so its 3-month 0.87 was real. The tell is in the Actual/Proj pairs, not the ratio.

**The newest month column is provisional, and a 3M move is usually the window, not the model.**
Both of 2026-09's apparent improvements were artifacts. NQM's 3M `CtP` went 0.894 → 0.988 almost
entirely because July's *realized* CtoP was restated down 22.9% (1.7295 → 1.3342) between the two
books, with the projection barely moving. JUMBO's went 0.873 → 0.957 purely because 2026-05
(monthly ratio 0.70) rolled out of the window — its newest month, 2026-08, is the worst of the
last three at 0.847. HELOC restated its own 2026-07 as well. **Before crediting a 3M move, check
what left the window and whether the overlapping months still hold their old values.**

**A model-version bump can silently change the universe, not just the model.** JUMBO went
V1_8_1 → V1_8_4 between the two books, and with it the delinquency universe expanded roughly
six-fold (M30: 311 loans / $211mm → 1,877 / $757mm) and `FCLS`/`REO` sheets appeared for the
first time. August's transition sheets were built on the WAC-block subset, September's on the
AGE-block pool. Transition ratios across that boundary are not comparable — say so rather than
reporting a move.

**A cohort can be present, complete-looking, and still unusable.** FIGRE's 2026-09 book had two
independent defects at once: 41 of 56 `CtP` rows carried a literal zero `Proj` in all five older
months (37 of them had a full series the month before), *and* its status sheets were stamped a
month behind — `CtP`/`CtM30`/`M30tC` labelled 2026-02..2026-07 while `CPR`/`CDR` in the same file
ran 2026-03..2026-08, with each September actual equal to the August book's value for the month
after. The `Undialed` twin carried the same shifted actuals and *more* zeros, which places the
fault upstream of the dial. Leading cause: the cohort's pseudo pools were renamed `HELOC*` →
`FIGRE*` at the 2026-08 factor date while the historical projections stayed in
`ResiTransitionTracking` under the old names — the rows are still there, keyed `V2_0_7_HE`,
purposes `PROD` and `PROD_UNDIALED`. Held back from the email with `--skip FIGRE`, named in the
narrative, not silently dropped.

**A missing cohort usually means its pipeline failed, and nobody was emailed.** Per
`memory/mailbox-folder-map.md`, `PAGER_DUTY` is unset for pipelines using `notifyBuildResult`,
so a FAILURE emails no one. **Absence of a failure email is never evidence of health.** Check
`python -m jenkins_monitor.cli facts --outputs outputs` for the `quant-Monthly-ResiTracking-*`
jobs.

**Never quote last month's figures for a missing cohort.** Say there is no tracking for it and
that an update will follow.

## How the charts are made

Each `<COHORT> CtoP` image is a **screenshot of the Excel `CtP` sheet**, not a plot. Range is
`A1:AE<2nd ALL AVG row>` — the AGE and WAC blocks only, not the FICO/MIS/UPDLTV blocks below —
carrying the sheet's own conditional formatting.

Reproduced pixel-identically with:

```
Range.CopyPicture(Appearance=xlScreen, Format=xlBitmap)
  -> Windows clipboard
  -> PIL ImageGrab.grabclipboard()
```

Two things that matter:

- **Excel must be `Visible = True`.** `CopyPicture` is unreliable without a real window.
- **Do not use the `ChartObject.Paste()` / `Chart.Export()` route.** It silently exports a
  **blank** image at the correct dimensions — it looks like it worked. The helper checks every
  render for near-uniformity and raises rather than shipping a blank.

Images are attached and referenced by content-id. A `cid` attached but not referenced in the
body renders as a broken image for every recipient, so the routine verifies the linkage after
building the draft.

## What this deliberately does not do

- **It never sends.** The email goes to the whole modeling team over Howard's name. As of
  2026-09 he pastes HTML from `emailer/run.py --md-file`; do not leave extra Outlook drafts.
- **It does not attach Howard's full Outlook signature.** The helper emits plain
  `Best, / Howard Zeng / QR`; the HTML signature with the logo is not reproduced.
- **It does not write to `R:\QR\Resi_shared\tracking`.**
- **It does not fix anything** — readiness reports, review drafts.

## Open items

- **HELOC bullet in the 2026-08 draft understates the correction.** It says "excluding that
  month, 3-month CtoP is 1.04." Substituting the known June projection gives **1.08**, and the
  stronger claim is that the August run dropped a value it previously had. Not revised because
  it reports a pipeline regression to the whole team — Howard's call.
- **Dial status was omitted for 2026-08** because no August `Undialed` files exist.
- **JUMBO `CDR` looks extreme** — 12-month ratio 12.8, 3-month 7.2. The Jan 2026 email flagged
  suspected CDR calculation bugs for JUMBO and HELOC, so this was left out of the draft rather
  than asserting a cause. Worth resolving.
- **Slash commands only register in the `claude-code-routines` folder.** They live in
  `claude-code-routines/.claude/commands/`, and there is no `.claude` at the `howard-toolbox`
  root. Moving them to `~/.claude/commands/` would make them work from anywhere.
- **NQM has two July workbooks** — `tracking_V1_7_6_NONQM_20260701.xlsx` and
  `tracking_V1_8_0_NONQM_20260701.xlsx`. July's email attached `V1_7_6`; `V1_8_0` is newer and
  is probably the model update mentioned in that email's Next Steps. Discovery currently takes
  the later-modified file for the month, which may not be the intended one.
