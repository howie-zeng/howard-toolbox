---
name: daily-resi-clo-summary-scope
description: "Scope exclusions for the Daily RESI/CLO email summary task — what is NOT Howard's responsibility"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 88006759-18e6-40fc-9f37-7d457d251d7b
---

For the Daily RESI/CLO Email Summary, Howard considers automated **risk runs** (the "LIBREMAX Risk Run" / "SWIB Risk Run ... scenario set" job notifications), **Resi SSS file generation** ("Daily Resi SSS File Generation"), and the **Compliance Engine** (Compliance@/Compliance_EOD@ started/stopped/failed) to be **out of scope** — ignore their failures/successes in the summary.

**Why:** These are run/owned by other people on the team, not Howard. Flagging their failures (e.g., a 2,156-bond SSS failure, CRT/CLO risk-run bond failures, a Compliance Engine crash) is noise for him.

**How to apply:** In the daily summary, exclude those three categories entirely. Focus instead on Howard's RESI/CLO model + report work: CRT model, Figure/DV01, LMSim vectors, CRTStats, factor_month/reporting_month (RESI); EUR/USD model training, V2/V2R/V3, spread models, walk-forward backtests, color/BWIC ingestion, model-fit, production comparison (CLO); plus surveillance/pricing/Intex-loader and Trimaran reports. The task file daily-email-summary.md was updated with an "Out of scope" note.
