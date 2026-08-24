# Reading

Personal reading shelf. One folder per book. Notes live in git; purchased PDFs do not.

## How we use this

1. You read (or paste a page/section). Ask in Chinese or English.
2. I explain the idea, the market intuition, and how it connects to work here (dials, tracking, MBS/NQM, swaps, etc.).
3. If you say **记住**, **note**, or **记一下**, I append it to that book's `NOTES.md` in the same turn.
4. Terms go in `GLOSSARY.md`. Open questions stay at the top of `NOTES.md` until answered.
5. I do **not** dump chapters into the repo. Short quotes for explanation only.

## Shelf

| Folder | Book | Status |
|---|---|---|
| [`tuckman-serrat-2022/`](tuckman-serrat-2022/BOOK.md) | Tuckman & Serrat, *Fixed Income Securities* (Wiley, 4th ed., 2022) | Not started — Ch. 0 |

## Add a book later

Create `reading/<slug>/` with `BOOK.md` (source path + TOC), `NOTES.md`, `GLOSSARY.md`. Record the local PDF path; do not copy the PDF into this repo.

## PDF rule

Keep files like the Tuckman PDF in Downloads (or another local folder). `.gitignore` blocks `reading/**/*.pdf`.
