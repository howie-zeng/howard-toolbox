---
name: duplicate-scheduled-run-guard
description: "The daily RESI/CLO scheduled task can fire twice within minutes — check for an already-sent same-day email before sending, to avoid duplicating Howard's email"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 5f4390ab-2de3-4f60-82ce-44eced1b801b
---

The Daily RESI/CLO Email Summary scheduled task can fire a **second, concurrent invocation** within a couple of minutes of one that has already completed the whole job. On 2026-07-13 a prior run had already written `outputs/daily-resi-clo-summary-20260713.md` (file mtime 08:51) **and sent** the email (Sent Items subject `Daily RESI/CLO Summary - 2026-07-13`); a duplicate run started ~08:53 and would have emailed Howard a second identical copy if it had blindly followed the "then send" step.

**Why:** Sending is an outward-facing, hard-to-reverse action. A duplicate summary email is spam to Howard and erodes trust in the routine. Regenerating/overwriting the summary in a duplicate run also risks a conflicting or lower-quality file.

**How to apply — at the START of every run, before regenerating or sending:**
1. Check whether `claude-code-routines/outputs/daily-resi-clo-summary-<today>.md` already exists and is fresh (mtime within the last ~hour). Read it if so.
2. Check Outlook **Sent Items** (via COM, primary store by DisplayName) for a message whose subject is `Daily RESI/CLO Summary - <today>` with `SentOn.date() == today`.
3. If BOTH the file and a same-day sent email exist, do a quick Inbox freshness scan for any NEW in-scope RESI/CLO item since that send. If nothing new/in-scope arrived, **stand down: do NOT re-send and do NOT overwrite** — just report that the task was already completed by the prior run and what the freshness check found. Only re-send/append if a genuine new in-scope signal appeared after the prior send.

`send_outlook_summary.py` writes no persistent log, so Sent Items is the only reliable "already sent today?" signal. See [[mailbox-folder-map]] for COM store/sync gotchas and [[daily-resi-clo-summary-scope]] for what counts as in-scope.
