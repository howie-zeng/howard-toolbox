# LMSim build & development guide

Agents: this file is mandatory. Do not invent cmake or vcpkg flows. Use
`.\dev.ps1` (`windows-dev` / `build_dev`; Linux: `linux-dev`). Do not run
raw `cmake -S . -B ...` without the preset — the vcpkg cache env lives on
the preset. If any other doc disagrees, this file wins.

**This is the definitive guide.** One preset (`windows-dev` / `linux-dev`),
one build dir (`build_dev`), one script (`dev.ps1`); the logic lives in CMake
(presets + `dev-venv`/`dev-ext` targets + ctest), the script only bootstraps
the environment. Python is the only production entrypoint
(`lmsim.sim.Sim2Runner` / `run_sim_hecm`); the standalone exe, `run_sim`,
and the legacy flat-file loaders were removed in v2.3.0. Build instructions
found anywhere else are retired — if a doc disagrees with this one, this one
wins.

## Requirements

- Windows: **VS 2022** with the C++ toolset (auto-discovered via vswhere;
  BuildTools SKU works), **git**, **uv**. Linux: gcc/clang + ninja + uv.
- Network access on first configure (vcpkg registries + a FetchContent pull).

## Quickstart (Windows)

```powershell
git clone <repo> ; cd LMSim
.\dev.ps1 setup     # submodule + bootstrap vcpkg + configure (build_dev)
.\dev.ps1 build     # everything: lmsim2_lib, tests, both Python exts
.\dev.ps1 test      # ctest   (or: .\dev.ps1 test -Filter 'CompiledModelTest.*')
.\dev.ps1 pytest    # pure-Python tests (tape_clean etc.) — no native build
```

`setup` is idempotent. With warm binary caches the configure restores all
~125 vcpkg packages in about a minute; nothing cold-builds. Requirements:
VS 2022 with the C++ toolset (auto-discovered via vswhere), `uv`, git.

The dev preset builds **RelWithDebInfo** (`/O2 /Zi`, PDBs) against release
vcpkg deps on the shared `x64-windows` triplet — the same triplet CI uses for
the wheel, so caches are shared. There is deliberately no `-Od` Debug preset:
it would need debug-CRT vcpkg builds (cold, and a known CRT-mismatch trap).
For un-optimized stepping of one file, wrap it in
`#pragma optimize("", off)` / `#pragma optimize("", on)` locally.

## Everyday commands

| Task | Command |
|---|---|
| Incremental build | `.\dev.ps1 build` (or `.\dev.ps1 build lmsim2_tests`) |
| C++ tests | `.\dev.ps1 test` / `.\dev.ps1 test -Filter 'Gam*'` |
| Python-surface tests | `.\dev.ps1 pytest` |
| Debuggable install (RelWithDebInfo wheel → `python\.venv_dev`) | `.\dev.ps1 ext` |
| Redistributable wheel | `.\dev.ps1 wheel` (delvewheel-repaired, import-order-immune) |
| Nuke build | `.\dev.ps1 clean` |

Concurrency defaults to `-Parallel 4` — keep it there on shared/dev boxes.

## Running the sim locally

```powershell
.\dev.ps1 ext    # CMake dev-ext target: repaired RelWithDebInfo wheel -> python\.venv_dev
python python\scripts\debug_run.py my_config.json            # HECM configs run directly
python python\scripts\debug_run.py my_config.json --tape N:\FlatFilesMonthly\...\EZE_20260701.txt
```

`debug_run.py` bridges to `.venv_dev` automatically (`LMSIM_DEBUG_SITE`
override available), so it works from any interpreter — including the base
CPython the debugger needs.

- Config template: `python/scripts/debug_config.example.json`. Resolution
  order: `LMSIM2_DEBUG_CONFIG` env → argv → the example. `rate_as_of_date`
  must be set or the sim fails deep in.
- No database env is required: the engine takes rates and HPA as an Arrow
  bundle from the caller. `debug_run.py` still loads `<repo>/.env` and chdirs to
  the repo root, since `init_env` reads a CWD-relative `./.env`.
- **`REDIS_HOST` silently switches the HPA source to Redis.** Unset it when
  you need Postgres-sourced HPA (tie-outs).
- **Why a repaired wheel, not a loose/editable `_ext.pyd`:** pyarrow ships its
  own `arrow.dll`, and Windows binds dependent DLLs by base name to whatever
  loaded first — a loose ext referencing bare vcpkg DLL names crashes whenever
  pyarrow is in the process (either order). delvewheel renames the vendored
  DLLs, making the install collision-immune. `dev.ps1 ext` does this for you.

Small test deals: Jumbo `EZE`/`GXQ`; CRT `1436` (small), `21HQA2` (large),
`1435,1436` (2-pool); MI `BMIR20213`/`HMIR20231`; HELOC `ACHM2023HE1`.
`NumOfCPU=1` in the config gives deterministic path partitioning/scenout
scaling for comparisons.

## Step-into C++ debugging (VS Code)

1. `.\dev.ps1 ext` (= CMake target `dev-ext`) — RelWithDebInfo wheel from a
   nested tree (`build_dev/wheel_stage`), delvewheel-repaired, installed into `python/.venv_dev`. PDBs stay in
   `build_dev/wheel_stage/python/lmsim/<sub>/` and match the installed `.pyd` (delvewheel
   patches the import table, not the debug directory).
2. Open the repo folder; `.vscode/launch.json` ships the configs:
   - **`Py+C++: step into lmsim ext`** — one click (needs the
     "Python C++ Debugger" extension, `benjamin-simmonds.pythoncpp-debug`).
   - Manual: run `Python: debug_run` with `--wait`, then
     `Native: attach to python (lmsim ext)` on the printed PID.
3. Set breakpoints in `src/**.cpp`; symbols resolve via the launch config's
   `symbolSearchPath` (`build_dev/wheel_stage/python/lmsim/...`).

Why the launch configs run the **base** uv-managed CPython, not a venv:
every Windows venv `python.exe` is a trampoline that re-execs the real
interpreter as a child process — `cppvsdbg` won't follow it and breakpoints
never bind. `LMSIM_DEBUG_SITE` + `site.addsitedir` (or `PYTHONPATH`) bridge
to your packages without the trampoline.

## Profiling

- **Python side**: `debug_run.py --profile` (cProfile, top-30 cumulative).
- **C++ on Windows**: run with `--wait`, attach the VS **Performance
  Profiler** (Debug > Performance Profiler > attach to the PID) — the
  RelWithDebInfo PDBs from `dev.ps1 ext` give full native stacks.
- **C++ on Linux**: `cmake --preset linux-profile` (frame pointers +
  `-march=native`) then perf/Callgrind on a driver run.

## Caches & toolchain (why builds are fast, when they aren't)

The `windows-dev` preset's `environment` block sets `VCPKG_BINARY_SOURCES` to
the shared writable cache (`S:\QR\local_vcpkg_cache`) + the read-only CI cache
(`N:\vcpkg-cache\windows`). It starts with `clear`, so vcpkg's default
`%LOCALAPPDATA%\vcpkg\archives` cannot grow with duplicate artifacts. First-ever build on a
machine may compile deps once; every rebuild after restores from cache. To
point at a different cache, add a `CMakeUserPresets.json` that inherits
`windows-dev` and overrides the env — no script edits.

Known wart: CI runners use MSVC **14.44**, typical dev boxes **14.43** — the
compiler hash is part of vcpkg's ABI, so N:-cache artifacts usually miss for
local builds (see `docs/toolchain-parity.md`; toolset pinning is a deferred
follow-up). The local caches carry you regardless.

## Wheels / CI parity

CI (`.github/workflows/release-python.yaml`) builds the wheel with
`CMAKE_ARGS=--preset=windows-release-shared` (Linux:
`linux-release-shared`) + `python -m build`, then repairs with delvewheel
(`--add-path build_wheel/vcpkg_installed/x64-windows/bin`) / auditwheel
(`--strip --plat manylinux_2_39_x86_64`). `dev.ps1 wheel`
(`python/scripts/wheel_delve.ps1`) reproduces the Windows flow locally.
`python/scripts/dev_install.ps1` remains for installing a repaired wheel
into a local venv (`python/.venv_wheel`) for LMQR-style consumption.

CI does **not** build or run the C++ test suite; `dev.ps1 test` (or the
`windows-ci`/`linux-ci` workflow presets) is the coverage.

## Linux

```bash
git submodule update --init vcpkg && ./vcpkg/bootstrap-vcpkg.sh -disableMetrics
cmake --preset linux-dev && cmake --build build_dev -j 4
ctest --test-dir build_dev --output-on-failure
cmake --build build_dev --target dev-ext   # debuggable install (auditwheel)
```

## Troubleshooting

- **`cl.exe not found` / Ninja can't find a compiler** — Ninja needs the MSVC
  environment before configure; run through `dev.ps1` (it enters VsDevCmd), or
  work in a "Developer PowerShell for VS 2022".
- **Configure fails with `Could NOT find Python` or weird `SKBUILD` cache
  entries** — the build dir's CMakeCache was poisoned by a scikit-build run
  pointed at it. Never set `SKBUILD_BUILD_DIR` to an existing dev build dir
  (`dev-ext` uses the isolated `build_dev/wheel_stage` for exactly this
  reason). Fix: `.\dev.ps1 clean` then `setup`.
- **vcpkg cold-builds dependencies** — the cache env comes from the
  `windows-dev` preset; a raw `cmake -S . -B ...` without the preset gets no
  cache config. First-ever build on a machine compiles deps once; after that
  the `%LOCALAPPDATA%` cache carries you.
- **Ext import crashes / `procedure could not be found` next to pyarrow** —
  you're loading a loose/editable `_ext.pyd`. Use `dev.ps1 ext` and import
  from `python\.venv_dev`; never `pip install -e`.
- **Breakpoints never bind in C++** — you launched a venv `python.exe`
  (a re-exec trampoline). Launch the base uv-managed interpreter;
  `debug_run.py` bridges to `.venv_dev` itself.
