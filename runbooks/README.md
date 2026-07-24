# Runbooks

Operational how-to guides for the resi/NQM sim pipeline — the step-by-step
procedures that sit on top of the code. Deep C++/engine *facts* live in the
auto-synced `cursor-memory/lmsim/AGENTS.md`; these are the *procedures*.

| Runbook | When you need it |
|---|---|
| [release-lmsim-model.md](release-lmsim-model.md) | Cut a new `lmsim` release — tag → CI builds the wheel (C++ via scikit-build/vcpkg/CMake) → publish to pypy → pin in LMQR. |
| [run-risk-and-vectors.md](run-risk-and-vectors.md) | Generate vectors and run risk (`lm_sim_pub_main` + `riskrun_main`), the `--vector_purpose` trap, batch-ray vs batch-local, pypy-down fallback. |
| [onboard-resi-deal.md](onboard-resi-deal.md) | A deal fails the run (`deal no mapping` / `no collat` / `no pool file`) — the 4 layers, per-product flat-file generation, and the LMSimData → N: deploy conflict failure. |
| [dial-model.md](dial-model.md) | Calibrate a SIM2 submodel to tracking — pointer to the canonical `dial/DIAL_RUNBOOK.md` + the silent-failure trap checklist. |

> These were distilled from the NQM release work (shipped 2026-07-23, `lmsim` v2.4.2).
> Commands/purposes are point-in-time — verify against current code before relying on them.
