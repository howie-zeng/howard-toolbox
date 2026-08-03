---
name: howard-job-ownership
description: "The 23 quant-* tracking/flat-file Jenkins jobs Howard owns and will fix, vs the 3 deploy jobs that are notify-only for the dev team"
metadata:
  node_type: memory
  type: project
---

Howard is in charge of **all the RESI tracking and flat-file generation processes** (stated
2026-08-03). Concretely, 23 `quant-*` Jenkins jobs are his to diagnose and fix:

`quant-DailySimDataUpdate`, `-DV01`, `-Intex`, `-LP`; `quant-DailySimHistVector`,
`quant-DailySimHistVectorUndialed`; `quant-DailyCRTVectors`; `quant-generate-vectors`;
`quant-WeekendCRTVectors`, `quant-WeekendCRTTrackingVectors`;
`quant-Monthly-ResiTracking-pipeline`, `-Tracking`, `-Unload`;
`quant-Monthly-Tracking-Report`, `-Undialed`; `quant-tracking-report-recache-workflow`;
`quant-PseudoDeal-Stats`, `-Tracking`, `-Unload`, `-Update`; `quant-RMBSLoader`;
`quant-HECMCollateralReport`; `quant-dv01-figure-sync`.

**Deploy jobs are NOT his:** `quant-deploy-lmqr`, `quant-deploy-lmsimdata`,
`quant-deploy-Rcode`. **Report** an error so he can tell the dev team; never hand him a fix.

**Why:** This is the ownership boundary that decides escalate-to-Howard vs merely-report. It
is the positive complement to [[daily-resi-clo-summary-scope]], which lists what belongs to
other people entirely (risk runs, Resi SSS, Compliance Engine).

**How to apply:**

- **Job names do not imply cadence — never infer it.** The authoritative trigger is
  `C:\Git\JenkinsJobs\<job>.jenkinsfile`. Several names actively mislead:
  `…DailySimDataUpdateIntex` is `cron 00 16 * * 5` (**Friday only**);
  `…Monthly-ResiTracking-Unload` is `H 2 * * *` (**daily**); `…-Tracking` is weekdays 11pm;
  `…Monthly-ResiTracking-pipeline` has its trigger **commented out** (manual).
  Do not flag a Friday-only job as stale on a Monday.
- **`…UpdateLP` UNSTABLE = real partial failure**, not a warning: the job runs
  `wh_lp_update.py` once per deal type, each in `catchError(buildResult: 'UNSTABLE')`.
  Identify which dropped by the missing `Done <X>` console echo. `--fail_on_deal_error`
  (Howard's own LMQR PR #13207) is what makes deal errors non-silent.
- **`wh_crt_update.py --log` does not mirror errors to stdout** — the Jenkins console shows
  little beyond a nonzero exit. Real error is on the NAS at
  `\\libremax-nas\QR_Sanbox\QR\logs\crt_update\`.
- **Wrapper jobs mask child failures** (`…ResiTracking-pipeline`,
  `…recache-workflow`) — drill into the child build, don't trust wrapper SUCCESS.
- His LMQR clone is **`C:\Git\LMQR`** (master). The `S:\QR\hzeng\Github\LMQR\LMQR` copy is
  ~541 days / 5,237 commits stale on branch `hecm` — never build a fix off it.

Full registry, per-job failure semantics, and the monitor/auto-fix design:
`howard-toolbox/docs/superpowers/specs/2026-08-03-jenkins-job-monitor-autofix-design.md`.
