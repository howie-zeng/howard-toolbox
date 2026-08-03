# Fix-Agent Runbook

The contract for an agent dispatched against a red `quant-*` job.

## Hard rules

1. **Never authenticate with a credential you did not receive from the operator.** Do not
   read, reuse, or test secrets found in source files. (A discovery agent violated this on
   2026-08-03 by attempting Basic auth with committed `svc_jenkins` / `jrayes` credentials.)
2. **Never push, open a PR, or merge.** Stop at a local commit and report.
3. **Never edit `C:\Git\LMQR` directly.** Work only in a worktree you created.
4. **Never build off `S:\QR\hzeng\Github\LMQR\LMQR`** — it is ~541 days stale.
5. **Never stage** `CLAUDE.md`, `AGENTS.md`, `.claude/`, `.cursor/`, `.omc/` — all gitignored.

## Setup

```bash
git -C C:/Git/LMQR fetch origin master --prune
git -C C:/Git/LMQR worktree add -b fix/<kebab-topic> C:/Git/LMQR-worktrees/<name> origin/master
cd C:/Git/LMQR-worktrees/<name>
git rev-list --left-right --count origin/master...HEAD   # must print "0 0"
uv sync
```

## Verify before claiming a fix works

```bash
uvx ruff@0.15.22 format .
uvx pre-commit run --all-files
uv run pytest tests/unit/<affected_pkg> -q -m "not local_only"
```

`pytest` does **not** run on LMQR pull requests — the PR gate is only
`ruff format --check` plus a CRLF guard. Running the tests locally is the *only*
automated signal that exists. A fix with no local test run is unverified.

## LMQR code conventions that constrain the fix

- **Fail loudly.** Do not add defensive guards for keys/columns that must always exist.
  Wrapping `model_result_json["ALL"]["Transition"]` in `.get()` would hide a real data gap
  and is the wrong fix.
- Error messages must be actionable — include the path, the value, and what was expected.
- DB access only via `lmdata/lmdb.py`.
- ruff `py311`, line-length 120, double quotes, LF endings.
- Conventional commit subject: `fix(<scope>): <what and why>`.

## Report back

State the root cause, the files changed, the exact test command run and its output, the
branch and worktree path, and anything you could not verify.
