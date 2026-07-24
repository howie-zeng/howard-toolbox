# Runbook: Release the LMSim model (C++ → `lmsim` wheel)

The **only** release artifact is the `lmsim` Python wheel — the standalone native
`.exe`/`.dll` release workflow was removed. The C++ engine ships *inside* the wheel,
built via scikit-build-core + vcpkg + CMake presets. Authoritative source:
`LMSim/.github/workflows/release-python.yaml`.

## Steps (normal release)

1. **Merge your C++ change to LMSim `main`** (PR). Confirm `main` is at the commit you want to ship.
2. **Tag it and push the tag** — this is what triggers the build+publish:
   ```bash
   git tag v2.4.2 <commit-on-main>
   git push origin v2.4.2
   ```
   The version comes from the tag via **setuptools-scm** (CI checks out with `fetch-depth: 0` for full tag history).
   - ⚠️ **Version pitfall (bit us July 2026):** setuptools-scm derives the version from the *most recent* tag. A stray/leftover local tag (an abandoned `v2.5.0`, a `.dev` tag) makes the wheel build the wrong version. **Delete stray tags before releasing**, and don't create a local tag you don't intend to publish. Final canonical NQM release = `v2.4.2` at `main` commit `47525c1ea`.
3. **CI runs automatically** (`Build Python Wheel`):
   - `build-python-windows` → `python -m build --wheel python` with `CMAKE_ARGS=--preset=windows-release-shared`, `CMAKE_GENERATOR=Ninja` → **delvewheel** vendors vcpkg DLLs → smoke-tests `import lmsim.rate; RateManager()` on a clean venv → uploads the wheel artifact.
   - `build-python-linux` → same via `linux-release-shared` → **auditwheel repair --strip --plat manylinux_2_39_x86_64` → smoke-test → upload.
   - `publish` job → `twine upload` both wheels to `https://pypy.libremax.com/` (pypiserver, `--overwrite`, anonymous creds). Separate job so a flaky pypy is replayable without a rebuild.
4. **Cut a GitHub Release** from the tag (release notes).
5. **Pin it in LMQR** (`C:\Git\LMQR_hecm`):
   ```bash
   # pyproject.toml → lmsim==2.4.2
   uv lock --upgrade-package lmsim   # sync uv.lock
   ```
   Commit. (LMQR's `[tool.uv.sources]` points `lmsim` at the `local-pypi` index = pypy.libremax.com.)

## Re-publish without rebuilding
- pypy flaked mid-publish → GitHub Actions **"Re-run failed jobs"** reruns only `publish` (reuses this run's wheel artifacts).
- Re-publish an *older* run's wheels → **workflow_dispatch** with `publish_from_run_id=<run id>` (skips build entirely).

## Local dev wheel (optional, not a release)
From the LMSim repo root, in a VS x64 dev shell, with vcpkg submodules bootstrapped:
```bat
call "C:\BuildTools\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 -no_logo
set CMAKE_GENERATOR=Ninja
set CMAKE_ARGS=--preset=windows-release-shared
python -m build --wheel --outdir python\dist python
python -m delvewheel repair -w python\wheelhouse python\dist\lmsim-*.whl --add-path python\build_wheel\vcpkg_installed\x64-windows\bin
```

## Gotchas
- **pypy.libremax.com flaps.** `batch-ray` Ray workers `pip install lmsim` from pypy at job startup, so a down pypy fails the whole vector run. Never work around with `file://` wheels on a shared drive. For isolation/tie-out runs, prefer `-mode batch-local` (in-process, no Ray/pypy) — see [run-risk-and-vectors](run-risk-and-vectors.md).
- The engine change and the **model/data** files are separate: C++ ships in the wheel; model JSONs + flat-file config live in the **LMSimData** repo and deploy to the N: share separately — see [onboard-resi-deal](onboard-resi-deal.md).
- A tests-only bump (e.g. moving tests to Python) produces a model-identical wheel — tie-out done on the prior version still holds; no re-validation needed.
