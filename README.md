# nota

Review Markdown files like a PR. Renders your markdown in the browser, lets you highlight text and leave notes, just like reviewing a pull request.

Also useful for reviewing CLAUDE.md, SKILLS.md, or any agent configuration files for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

Annotations are saved to a `.nota.json` file next to your markdown, so AI coding assistants like [Claude Code](https://docs.anthropic.com/en/docs/claude-code) can read and act on them.

## Install

```bash
pip install nota
```

## Usage

```bash
nota README.md
nota docs/Report.md --port 8080
```

Select any text to highlight it and add a note. Annotations are saved to `<file>.nota.json` (e.g. `Report.md.nota.json`).

## Reviewing agent changes

The **Changes** button turns nota into a pull request for your markdown. When nota starts it
snapshots the file to `<file>.nota.base` — that snapshot is the "before" version. Everything
written to the file afterwards (by Claude Code, by your editor, by anything) shows up as
reviewable chunks, rendered rather than raw: the old version of each chunk in red, the new one
in green, with the untouched parts of the document in between for context.

Each chunk has its own buttons:

- **Accept** keeps the new version and moves the baseline forward. Your file is not touched.
- **Reject** puts the old version back into the file.
- **Comment** leaves a note on that chunk for the times when the change is close but not
  quite right. The chunk stays pending, and the note goes into `<file>.nota.json` together
  with the before and after text, so Claude knows exactly which change you mean.
- **Accept & comment** (in the comment box) keeps the change and still records the note —
  for "fine for now, but follow up on this".
- **Accept all** / **Reject all** resolve everything at once.

Comments stick to their chunk by content, not by position, so they stay put while you
accept or reject the chunks around them.

The view polls the file, so changes an agent makes while the page is open appear on their own.
`--reset-base` re-snapshots the baseline and drops all pending changes.

## Workflow with [Claude Code](https://docs.anthropic.com/en/docs/claude-code)

1. `nota Report.md` - review and annotate
2. Tell Claude: "review the nota" or "read Report.md.nota.json and process all notes"
3. Claude reads your annotations and makes the changes
4. Hit **Changes** to see exactly what Claude rewrote, and accept, reject, or comment on each chunk
5. Tell Claude "review the nota" again - it picks up the comments on the chunks and revises them
