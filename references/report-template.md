# Report template

Save to `<cwd>/skill-freshness-report-<YYYY-MM-DD>.md` (or the user's path)
and show the summary table in the reply. Write prose in the user's language;
keep skill names, statuses and commands in English. The user reads the table
first and the details only for rows that are not `actual`.

```markdown
# Skill freshness report — <YYYY-MM-DD>

**Machine:** <OS> · Python <v> · Node <v>
**Agents:** <host> <version> (<surfaces the user uses>) · <host> ... · not installed but folders found: <...>
**Surfaces source:** saved profile | detected (<evidence>) | asked the user | assumed conservative
**Scope:** <N> skills in <M> folders (<K> vendor-managed skipped) · checks: scan --check [--smoke], web research for <R> skills
**Not verified:** <what the audit could not do and why: offline, no API key, agent not installed, GUI-only, sub-agent failed>

## Summary

| # | Skill | Loaded by | Status | Conf. | Why (with source) | Recommendation |
|---|---|---|---|---|---|---|
| 1 | `defuddle` | Claude Code, Codex | broken | high | `defuddle` CLI not on PATH; npm `defuddle` 0.19.6 ([npm](https://www.npmjs.com/package/defuddle)) | update: `npm i -g defuddle` |
| 2 | `playwright-skill` | Codex | actual | high | Codex IDE extension has no browser; the desktop-only in-app browser does not count for this user | keep |
| 3 | `loop-runner` | Claude Code | superseded | high | `/loop` exists on all Claude Code surfaces ([changelog](https://code.claude.com/docs/en/changelog)) | built-in: `/loop` (Claude Code, all surfaces); delete |
| ... |

Totals: actual N · outdated N · broken N · superseded N · orphan N

## Cross-cutting findings

- Duplicates across agents, folders no agent reads, nested copies, trigger collisions.

## Details (rows that are not `actual`)

### `<skill>` — <status>
- Loaded by: <hosts> (<surfaces>)
- Checked: <what was run / fetched>
- Found: <facts, each with a link or command output>
- Not verified: <what remains unknown>
- Recommendation: <...> — <one sentence>

## Proposed actions (for `--fix`)

1. [ ] <action> — <skill> — <why>

Nothing above has been applied. Run `/skill-freshness --fix` and confirm each item.
```

Rules the template encodes:
- Every non-`actual` row cites a source: a URL, a command and its output, or a path.
- "Not verified" is part of the audit. A skill that got only static checks says so (`conf. low`).
- The "Loaded by" column always reflects installed agents; a superseded verdict
  names the host and surfaces where the replacement exists.
- The report changes nothing. `--fix` applies items one by one after confirmation.
