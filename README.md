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

## Workflow with [Claude Code](https://docs.anthropic.com/en/docs/claude-code)

1. `nota Report.md` - review and annotate
2. Tell Claude: "review the nota" or "read Report.md.nota.json and process all notes"
3. Claude reads your annotations and makes the changes
