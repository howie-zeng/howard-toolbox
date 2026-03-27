## Learned User Preferences

- Prefers iterative email revision workflow: review draft -> revise prose -> highlight takeaways -> test render
- Wants bare image filenames flagged as functional bugs; emailer only recognizes `![](...)` or `<img>` syntax
- Prefers bold section headers and bullet points in email content for scannability
- Wants summary and key takeaways surfaced at the top of email notes, with supporting detail below
- Prefers "Next steps" over "Todos" in professional email copy
- Prefers concise, polished email prose; draft notes should be rewritten to be send-ready
- When reviewing code or text: flag functional issues first, then clarity, then style
- Wants conclusions stated first, supporting charts and data after
- When revising email content, always read `emailer/ai_instructions.md` first for formatting rules
- "Revise for management" means: conclusions first, less technical jargon, cleaner section headers

## Learned Workspace Facts

- DFS share at `S:\QR\hzeng\howard-toolbox` locks `.cursor/` directory; use git plumbing (`hash-object` + `update-index`) to bypass
- PowerShell redirect (`>`) writes UTF-16 by default; use Python `open(encoding='utf-8')` for UTF-8 file writes
- `git update-index --assume-unchanged` is needed for `.cursor/` tracked files on the DFS share
- Skills in both workspace `.cursor/skills/` and global `~/.cursor/skills/` create duplicates in Cursor UI
- S: drive is source of truth for project files; `~/.cursor/skills/` is for cross-workspace loading only
- Personal-profile is a global skill at `~/.cursor/skills/`; project-specific skills stay in the repo
- The emailer markdown pipeline only recognizes `![](...)` or HTML `<img>` tags, not bare filenames
- Standard markdown renderer collapses consecutive lines without blank separators into one paragraph; use bullets or blank lines
- Unicode characters (e.g. checkmark) crash on cp1252 Windows console; use ASCII alternatives in console output
- `emailer/ai_instructions.md` defines image syntax, math formatting, and Outlook spacing rules for `MD_CONTENT`
