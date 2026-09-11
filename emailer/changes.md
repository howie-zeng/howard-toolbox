Hi all,

Jumbo and non-FIGRE HELOC are now on the same foreclosure framework as CRT, NQM and MI. This is Phase 1: framework only, no new model. FIGRE is unchanged. It charges off at D180, so it has no real FCLS state. Phase 2 is the deep-delinquency model update, which we can do all at once or product by product once this lands.

- **Foreclosure is now visible.** Both tapes already carried FCLS loans, but the production engine was rewriting them to 270+ DPD at simulation start, so an FCLS cohort had nothing to track. In the new engine, a model that has an FCLS state keeps the loan there; a model that does not behaves as before.
- **If you pull HELOC from the deal manager, what you get has already changed.** `deal_type=HELOC` now returns the LP / CoreLogic (non-FIGRE) pools. FIGRE is `deal_type=FIGRE`. That swap took effect when the database was renamed, ahead of any code merge.
- **Tracking now includes the delinquent loans these models are about.** Jumbo and HELOC status cohorts (M30 / M60 / M90+ / M270+ / FCLS / REO) are no longer age-capped. The CPR attribute buckets still have the age filter.

**Framework**

Jumbo and HELOC used to have no FCLS state. A loan went from M270P straight to liquidation. Phase 1 adds FCLS and REO, so every product except FIGRE runs the same state machine. Once that is in, we can update the deep-delinquency models in Phase 2 either all at once or gradually.

![Jumbo and non-FIGRE HELOC on the STACR framework](assets/framework_states.png)

**HELOC vs FIGRE**

What we used to call `HELOC_PSEUDO` was really FIGRE. Non-FIGRE HELOC had no home. That is now split:

| | source | pool ids |
|---|---|---|
| `FIGRE_PSEUDO` | dv01 / FIGRE | `FIGRE*` |
| `HELOC_PSEUDO` | LP / CoreLogic | `HELOC*` |

Happy to walk through any of it.
