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
order in the email: **STACR, CAS, NQM, JUMBO, FIGRE, HELOC**. `Undialed` holds identically-named
files and is the dial-verification twin, not a second data source. Files do **not** land on a
fixed day (`20260701`, then `20260803`) — this is why the routine is on-demand, not scheduled.

**FIGRE and HELOC are two different cohorts as of 2026-09, and the old name moved (learned
2026-09-11):** every review through 2026-08 had five cohorts, and the one it called **HELOC**
was really the **Figure** book `tracking_V2_0_7_HE_<date>.xlsx`. LMQR commit `79037f1a0`
renamed that report to `tracking_V2_0_7_FIGRE_<date>.xlsx` (and the historical files under
`Dialed`/`Undialed` were renamed to match), while a genuinely new cohort — the non-Figure
HELOC book `tracking_V1_0_V5_HE_<date>.xlsx` (`MODEL_VERSION_HELOC`, `DealType.HELOC_PSEUDO`)
— started landing in `Dialed`. The discovery pattern `_HE_` never stopped matching; it just
began resolving to a **different cohort**, so FIGRE fell out of the review and `readiness`
still printed "5 of 5 cohorts present — READY". **How to apply:** the cohort list is now
**STACR, CAS, NQM, JUMBO, FIGRE, HELOC**, FIGRE ahead of HELOC in `COHORTS` because `_scan`
stops at the first matching pattern. A cohort count proves nothing — it counts what the
patterns matched. When reconciling against an older email, its "HELOC" line is today's FIGRE
line; say so instead of letting a relabelling read as a model move.

**Where the quoted numbers come from:** the **WAC `ALL AVG` row** (the *second* `ALL AVG` row
in column C) of the `CtP` sheet, and `CPR` for the cohorts where CPR is discussed. Columns are
`3M Error`/`6M Error`/`12M Error`, each an `Abs`+`Ratio` pair; the email quotes the **Ratio**
(cols 27/29/31). Verified: this row reproduces all five of the July 2026 figures — CAS 0.989→"0.99",
NQM 1.338→"1.34", JUMBO 1.171→"1.17", HELOC 1.096→"1.10" (that "HELOC" is the **Figure** book, now FIGRE). The
AGE row does **not** match.

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
(learned 2026-08-04, and again at larger scale 2026-09-11):** the Figure cohort's 2026-06
projection at the WAC `ALL AVG` row was **2.0519** in the 2026-07-01 book and **0** in the
2026-08-03 book, with an identical actual (1.7278) in both. (Both files were named
`tracking_V2_0_7_HE_<date>.xlsx` at the time and are now `tracking_V2_0_7_FIGRE_<date>.xlsx`.) So the August tracking generation dropped a projection it
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
out where a miss sits; `FCLS` was the case that prompted this. The published email stays
**high-level** (CPR/CtoP 3M/6M/12M plus one takeaway); only surface a STACR FCLS number when
it needs a call. **Ignore `CDR` entirely** — Howard's explicit call, so do not resurface it
even though the STACR/CAS `CDR` `ALL AVG` row reads 2–3x over-projected. **How to apply:**
1/Ratio is the size of the miss. Default is wait for a good/new model to converge to 1.
If the undialed model is actually off — consistent across 3M/6M/12M on real balance, not a
window, restatement, or gap — we still dial.

**CAS FCLS/REO in the tracking workbook is derived, not a reported CAS state (Howard,
2026-09-11):** CAS does not report FCLS. The `FCLS`/`REO` sheets in the CAS file are constructed,
so ratios there (e.g. FCLS→C 0.58) are not a tracking item and must not be quoted, dialed, or
compared to STACR. **Only STACR FCLS is in scope.** **Trigger:** any CAS `FCLS`/`REO` sheet, or
a draft that treats CAS FCLS like STACR FCLS.

**Prefer no dial; still dial if the model is off (Howard, 2026-09-11):** a good newly
released model should be left undialed and allowed to converge to 1 — highlight that path
(NQM V1_8_0: CtoP 0.99 / 0.94 / 0.91). If the published miss *is* the dial (HELOC 2026-09:
×1.20 CtoP / ×1.15 CPR), propose taking it off and put the undialed `CtP` screenshot next
to the dialed one. This is a preference, not a ban: if the *undialed* model is actually
off (consistent 3M/6M/12M miss on real balance, not a window/restatement/gap), we still
dial. **Trigger:** a new-model cohort still walking in, a published miss that is the dial,
or an undialed model that is genuinely off.

**Undialed CtoP is not undialed CPR (Howard, 2026-09-11):** HELOC undialed WAC ALL AVG CtoP
was 1.19 / 1.18 / 1.15; CPR was 1.06 / 1.01 / 1.00. Do not write "undialed CtoP is 1" because
12-month CPR is 1.00. Quote both sheets. Copy the Undialed workbook to a **distinct local
filename** before screenshotting — Dialed and Undialed share basenames, and
`render_ctp_images` will otherwise open the Dialed scratch copy already in the workdir.

**Delivery is paste, not the helper Outlook draft (Howard, 2026-09-11):** write
`outputs/mtr-YYYYMM/email.md` and run `python emailer/run.py --md-file ...` so Howard
Ctrl+V's HTML. Do not leave extra Outlook drafts. Never write `$amount` in that markdown
(emailer treats `$...$` as LaTeX / CodeCogs). No sign-off.

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

**Dial status must be verified, never carried forward, and never read off the window Ratio
cells (corrected 2026-09-11):** the old rule — `Dialed` vs `Undialed` Ratio cells identical ⇒
no dial, differing ⇒ dial — was **wrong in four of six cohorts on 2026-09**. A ratio gap is
produced just as easily by a projection the `Undialed` run never wrote. STACR and CAS reported
"dial applied" off a +0.20 gap on the 3M `CtP` ratio that was one absent 2026-08 projection
(the surviving CAS buckets are bit-identical to 16 significant figures); JUMBO's "dial" was
7e-09 of float noise; FIGRE's was an `Undialed` book whose projections are all zero. Only HELOC
had a real one. **How to apply:** `dial_status` now compares the per-month `Proj` values at the
quoted WAC `ALL AVG` row of `CtP` and `CPR`, skips months where either side is missing or zero,
and reports the median dialed/undialed factor per sheet (`DIAL_TOLERANCE` 0.002). A real dial is
a **uniform factor across every bucket and every month** — HELOC 2026-09 is ×1.1999 on `CtP` and
×1.15 on `CPR` across all 35 rows. A median of 1.0 with one month far from it is a defective
column and the helper now says so. A dial can also be sheet-specific: NQM's `CtP` is
bit-identical dialed vs undialed while its `CPR` carries a uniform +0.8%, so "NQM is undialed"
is true only of `CtP`. When no `Undialed` twin exists the answer is **unverified — say nothing
about dials**; on 2026-08 there were no August `Undialed` files at all.

**`Undialed` is a separate, later re-run, not a no-dial branch (learned 2026-09-11):** on
2026-09 five of the six `Undialed` books were written ~24 h after their `Dialed` twins (NQM was
9 minutes). That is why an `Undialed` newest column can be incomplete while the `Dialed` one is
fine. Check the file write times before drawing any conclusion from a newest-column difference.

**A 3M move is usually the window, not the model (learned 2026-09-11):** both of 2026-09's
apparent improvements were artifacts. NQM's 3M `CtP` went 0.894 → 0.988 almost entirely because
July's *realized* CtoP was restated down 22.9% (1.7295 → 1.3342) between the two books; JUMBO's
went 0.873 → 0.957 purely because 2026-05 (monthly ratio 0.70) rolled out, while its newest
month is the worst of the last three at 0.847. HELOC restated its own 2026-07 too. **How to
apply:** before crediting a 3M move, check what left the window and whether the overlapping
months still hold their old values. Treat the newest column as provisional in every cohort.

**A model-version bump can change the universe, not just the model (learned 2026-09-11):**
JUMBO V1_8_1 → V1_8_4 expanded the delinquency universe roughly six-fold (M30 311 loans /
$211mm → 1,877 / $757mm) and added `FCLS`/`REO` sheets; August's transition sheets were built on
the WAC-block subset and September's on the AGE-block pool. Transition ratios do not compare
across that boundary — say so rather than reporting a move.

**`--skip COHORT` holds a known-bad workbook out of the mail, but never out of the narrative
(added 2026-09-11):** used for FIGRE on 2026-09, whose book had lost most of its projection
history *and* had its status sheets stamped a month behind. The bullet still has to name the
cohort and say why. A cohort that simply stops appearing is the failure this routine exists to
catch.

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

**Never send.** The email goes to the whole modeling team and Howard signs it. As of 2026-09
the delivery he wants is emailer HTML paste (`email.md` → Ctrl+V), not the helper's Outlook
`--draft`. `--send` exists in the helper but the routine never uses it.
