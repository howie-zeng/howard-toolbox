
## 🧠 For AI Agents / Developers

If you are an AI assistant helping with this codebase, here is the architecture:

- **Entry Point**: `emailer/run.py` is the main script. User edits `MD_CONTENT` string here.
- **Rendering Logic**: `emailer/render.py` handles:
  - Markdown -> HTML (using `markdown` lib)
  - Post-processing with `BeautifulSoup` (tables, styling, unwrap images)
  - LaTeX Math -> CodeCogs images (`$$...$$` -> `<img src="...">`)
  - Local Images -> Base64 encoded strings (for email portability)
- **Clipboard**: The script uses `win32clipboard` to put the final HTML into the Windows clipboard.
- **Special Tags**:
  - `{{CLIPBOARD}}`: Replaced at runtime with the image currently in the OS clipboard.
