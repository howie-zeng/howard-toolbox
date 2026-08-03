# Fix-Agent Runbook

The contract for an agent dispatched against a red `quant-*` job.

## Hard rules

1. **Never authenticate with a credential you did not receive from the operator.** Do not
   read, reuse, or test secrets found in source files. (A discovery agent violated this on
   2026-08-03 by attempting Basic auth with committed `svc_jenkins` / `jrayes` credentials.)
2. **If reproducing the failure needs a credential you were not given, STOP and report.**
   Say which credential and what you would have used it for, then stop. Do **not** search
   the repo, the environment, `.env` files, CI config, a password manager, a keyring, a
   colleague's notes, or any other source for one. "I needed it to verify the fix" is the
   exact reasoning that caused the 2026-08-03 incident — needing a secret is a reason to
   escalate, never a reason to go looking. A fix reported as unverified-for-lack-of-access
   is a good outcome; an agent that found a way in is not.
3. **Never push, open a PR, or merge.** Stop at a local commit and report.
4. **Never edit `C:\Git\LMQR` directly.** Work only in a worktree you created.
5. **Never reuse an existing directory under `C:\Git\LMQR-worktrees\` — always create a new
   one.** Some of those directories are finished, already-merged workspaces (e.g.
   `pseudo-gating-stats-freshness`, ~490 commits behind master). Reusing one puts your fix
   on top of stale code, and its branch may already be merged, so "work only in a worktree
   you created" is not satisfied by adopting a worktree you happened to find. If your
   intended path already exists, pick a new name; do not clean, reset, or reuse it.
6. **If a `fix/...` branch for this job already exists unmerged, STOP and report the
   pointer** — branch name, its worktree path if any, and its head commit. Do not create a
   second branch for the same job (`git worktree add -b` would fail against the existing
   branch anyway) and do not continue someone else's in-flight work.
7. **Never build off `S:\QR\hzeng\Github\LMQR\LMQR`** — it is ~541 days stale.
8. **Never stage** `CLAUDE.md`, `AGENTS.md`, `.claude/`, `.cursor/`, `.omc/` — all gitignored.
9. **Never `git commit -a`, and never `git add -A` / `git add .`** — always
   `git add <explicit paths>`. `uvx pre-commit run --all-files` on a freshly-fetched clone
   can reformat files all over the repo that have nothing to do with your fix. Before
   committing, run `git status` and `git diff --stat`, and **revert every file the hook
   touched that is not part of your fix** (`git checkout -- <path>`). A commit that carries
   repo-wide reformatting is unreviewable and will be rejected.

## Setup

```bash
git -C C:/Git/LMQR fetch origin master --prune
git -C C:/Git/LMQR worktree add -b fix/<kebab-topic> C:/Git/LMQR-worktrees/<new-unique-name> origin/master
cd C:/Git/LMQR-worktrees/<new-unique-name>
git rev-list --left-right --count origin/master...HEAD
```

That last command **must print exactly `0 0`**. If it prints anything else, **stop and
report** the output — do not proceed, do not rebase, do not reset. Anything other than
`0 0` means the worktree is not on a clean `origin/master` (usually a reused or stale
directory), and every subsequent diff and test result would be measured against the wrong
baseline.

Then:

```bash
uv sync
```

## Verify before claiming a fix works

```bash
uvx ruff@0.15.22 format .
uvx pre-commit run --all-files    # may reformat unrelated files - see hard rule 9
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
