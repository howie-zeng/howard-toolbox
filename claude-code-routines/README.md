# Claude Code Routines

Local scheduled Claude Code routines for Howard Toolbox.

## Daily RESI/CLO Email Summary

Routine prompt:

- `daily-email-summary.md`

Routine-specific memory:

- `memory/`

Outputs:

- `outputs/daily-resi-clo-summary-YYYYMMDD.md`

The routine should review Outlook email first, especially `Inbox/auto`,
`Jenkins Automation`, `CLO`, `HECM`, `RESI`, and `Tracking`, then save a
summary and email it to Howard.

## Email Helper

Dry-run render:

```powershell
python claude-code-routines/send_outlook_summary.py `
  --body-file claude-code-routines/outputs/test-daily-resi-clo-summary.md `
  --to hzeng@libremax.com `
  --subject "Daily RESI/CLO Summary - Test" `
  --dry-run
```

Create an Outlook draft:

```powershell
python claude-code-routines/send_outlook_summary.py `
  --body-file claude-code-routines/outputs/test-daily-resi-clo-summary.md `
  --to hzeng@libremax.com `
  --subject "Daily RESI/CLO Summary - Test" `
  --draft
```

Send today's summary using the default output filename:

```powershell
python claude-code-routines/send_outlook_summary.py `
  --date 2026-06-01 `
  --to hzeng@libremax.com `
  --send `
  --fallback-draft
```
