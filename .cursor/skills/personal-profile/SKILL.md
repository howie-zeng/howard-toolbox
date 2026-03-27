---
name: personal-profile
description: >-
  Global user preferences and generic agent behavior rules for Howard Zeng.
  Applies across all projects and workspaces. Use whenever working with this
  user, regardless of which repository is open.
---

# Personal Profile

## Preferences

- Prefer simple designs first; only add complexity when it clearly pays off.
- When offering solutions, present option A (quick fix) and option B (robust refactor).
- Use bullet points and clear sections in responses.
- Start responses with a 1-3 line plan before diving into details.
- Give full runnable code unless explicitly asked for a snippet.
- When working from an attached plan file, treat the plan as the execution spec: show the plan first if asked, do not edit the plan file unless explicitly requested, and do not recreate plan todos that already exist.

## Mistakes to Avoid

- Do not use `sed` or `awk` for file edits on Windows/PowerShell. Use proper file editing tools.
- In PowerShell, `&&` is not a valid statement separator. Use `;` or separate commands.
- Do not guess APIs, library behavior, or file formats. State assumptions and offer a safer approach.
- Do not add comments that narrate what code does. Only explain non-obvious intent.
- Never output secrets, tokens, or credentials. Use env vars and placeholders.

## Update Instructions

The agent may proactively propose updates to this file. All writes require a
diff preview and user approval before saving. Write to the S drive first
(`S:\QR\hzeng\howard-toolbox\.cursor\skills\personal-profile\SKILL.md`), then
copy to `~/.cursor/skills/personal-profile/SKILL.md`.

Consolidate if this file exceeds ~50 entries: merge duplicates, compress related items.
