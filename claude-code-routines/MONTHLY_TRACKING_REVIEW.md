# Monthly Tracking Review — Runbook

Everything needed to produce the Monthly Tracking Review email, and everything that has
already gone wrong doing it. Read this before changing the helper or the routine prompts.

Built 2026-08-04 by reverse-engineering Howard's own sends (2026-01, 2026-06, 2026-07) out of
Outlook, and confirmed against him.

## What this is

A monthly email to `LibreMax-Modeling` reporting how the RESI models are tracking across five
cohorts — **STACR, CAS, NQM, JUMBO, HELOC** — with the per-cohort tracking workbooks attached
and a screenshot of each cohort's `CtP` sheet inline.

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
tracking_STACR_V1_8_2_CRT_20260803.xlsx
tracking_CAS_V1_8_2_CRT_20260803.xlsx
tracking_V1_7_6_NONQM_20260701.xlsx
tracking_V1_8_1_JUMBO_20260803.xlsx
tracking_V2_0_7_HE_20260803.xlsx
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
(CAS 0.989→"0.99", NQM 1.338→"1.34", JUMBO 1.171→"1.17", HELOC 1.096→"1.10"). The AGE row does
not match and will mislead you. `facts` reports both so you can cross-check.

**`Ratio = sum(Proj) / sum(Actual)`** over the window — not Actual/Proj. Confirmed against the
sign of the `Abs` column. A ratio below 1.0 means the model is projecting slower than actual.

**Label the windows correctly.** `6M Error` is the six-month tracking error. The July 2026 email
called it a "12-month average"; Howard confirmed that was his mistake. Consequence: a cohort's
correctly-labelled figure will not line up with what July's email said for the same metric — if
that is visible, say so in a sentence rather than leaving the team to reconcile it.

**Dial status is verified or omitted.** `Dialed` vs `Undialed` numerically identical ⇒ no dial
applied; differing ⇒ dial applied. In July 2026 they were identical for STACR/CAS and divergent
for NQM (1.17 dialed vs 0.78 undialed), matching what Howard wrote. When no `Undialed` twin
exists for that date the answer is **unverified — say nothing about dials**, and never carry
forward the previous month's claim.

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

- **It never sends.** The email goes to the whole modeling team over Howard's name. Both
  routines stop at an Outlook draft; he reviews and sends.
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
