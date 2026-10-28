---
name: skill-freshness
description: "Use this skill first whenever the user asks about the health of their installed agent skills: auditing, checking, cleaning up, updating or de-duplicating skills in ~/.claude/skills, ~/.codex/skills, ~/.agents/skills or plugin folders, or finding skills that are broken (missing CLI or script), outdated versus upstream, duplicated across agents, or made redundant by built-in features like /loop or /schedule. Do not inspect skill folders by hand: this skill ships a scanner that covers every agent (Claude Code, Codex, Cursor, Gemini CLI, Copilot, OpenCode, Antigravity), maps which agent loads each folder, and knows which built-ins exist in the terminal vs the desktop app vs the IDE. Also for Russian requests like 'проверь мои скиллы', 'какие скиллы устарели'. Writes a report with sources and changes nothing without per-item confirmation."
license: MIT
compatibility: Needs a shell and Python 3.9+. Works in Claude Code, Codex, Cursor, Gemini CLI, Copilot CLI, OpenCode, Antigravity and other Agent Skills hosts.
metadata:
  author: Kirill Vozianov
  version: "1.1.0"
  homepage: https://github.com/kvozianov/skill-freshness
---

# skill-freshness

Skills rot in four ways: the tool they drive changes (a CLI is gone, a flag
renamed, a model id retired); the host grows the feature in (Claude Code
shipped `/loop` and every "looper" skill became dead weight); someone
publishes a better-maintained version; or the skill sits in a folder no
installed agent reads. This skill finds every skill on the machine, checks
each on those axes, and hands the user a report. It is an auditor, not a
janitor: nothing is deleted or edited until the user confirms each item.

The skill works in any agent that can run a shell. Where a step names a
tool (sub-agents, a question dialog, web search), use your host's
equivalent; if it has none, do the step inline and say so in the report.

## Arguments

`$ARGUMENTS` may contain, in any order:

| Token | Effect |
|---|---|
| *(none)* | audit every skill from every host, plus a sweep of the home folder |
| `<name>` | audit one skill (name or path substring; all copies of it) |
| `--fix` | after the report, apply recommendations one by one, each after the user's yes |
| `--host <id>` | only skills loaded by this host (repeatable; ids in `scripts/hosts.json`) |
| `--quick` | local checks only, no web research (rows get confidence `low` unless verified locally) |
| `--smoke` | also run bundled scripts with `--help` (15 s timeout) |
| `--project <path>` | project whose skill dirs to include (default: current directory) |

Prose maps onto flags: "only my Codex skills" = `--host codex`; "just
defuddle" = `defuddle`; "and clean up" = `--fix` (still confirm each item).

## Workflow

`<skill-dir>` below is the folder containing this SKILL.md.

### 0. Environment: which agents, which surfaces

```bash
python3 -I <skill-dir>/scripts/scan.py --env
```

This lists every known host with the surfaces found on this machine (`cli`
binary on PATH, `desktop` app, `ide` extension), its version, the current
session's host and surface (from env vars such as `CLAUDE_CODE_ENTRYPOINT`),
and a saved profile if one exists.

Why it matters: features differ by surface. The Claude desktop app has a
built-in browser pane and an iOS simulator panel; the terminal CLI has
neither. A Playwright skill is redundant for someone who only uses the
desktop app and essential for someone in a terminal. Each host's reference
(`references/hosts/<id>.md`, section "Surfaces") says which features live
where.

- **The user already said how they work** ("I only use the terminal",
  "Codex in VS Code") → save that right away with `--save-profile` (below)
  and use it; do not ask again.
- **Profile exists** → use it; mention it in the report header.
- **No profile, and detection is unambiguous** (each installed host has one
  surface, current session is confident) → use the detected surfaces and say
  so in the report.
- **Otherwise ask once**, in one question: which agents they actually use
  and how (terminal / desktop app / IDE / cloud). Offer the detected
  combination as the default answer. Save it so later runs do not ask:

  ```bash
  python3 -I <skill-dir>/scripts/scan.py --save-profile 'claude-code=desktop,cli;codex=ide'
  ```

  In a non-interactive run (no way to ask), skip the question, use the
  conservative assumption below and say so in the report header.
  If the user does not answer, assume **the union of all installed
  surfaces minus desktop-only features**, i.e. be conservative: never call
  a skill superseded by something the user might not have.

### 1. Inventory (deterministic, ~20 s)

```bash
python3 -I <skill-dir>/scripts/scan.py --check [--smoke] [--host <id>] [--only <name>] [--project <path>] --out <scratch>/inventory.json
```

The scanner reads the host registry (`scripts/hosts.json`), scans each skill
root once, records which hosts load it (`readers`, `readers_installed`),
sweeps `$HOME` for skill folders the registry does not know (project-level
copies, repo checkouts), merges symlinked copies, and for every skill
records description, frontmatter, last change, scripts, referenced CLIs /
packages / URLs / slash commands / MCP tools / model ids / env vars,
duplicates (with `same_content`), and with `--check` whether its
dependencies exist. Read the JSON; `--md` is a quick human view.

Facts that drive triage:
- `checks.problems` → candidate **broken** (tokens marked "could be parser
  noise" need a look before you believe them);
- `flags: nested` → never loaded by any host → **broken** (move or delete);
- `flags: no installed host loads this root` → **orphan**: the skill only
  matters if the user plans to install that agent; ask, do not assume;
- `duplicates` → keep one copy per host; prefer the shared store
  (`~/.agents/skills`) when several hosts should see it;
- `kind: managed` (vendor-synced) → skipped unless `--include-managed`;
  never fix those.

### 2. Triage and scope the research

Do not web-search 200 skills. Split them:
- **Needs research**: skills that drive an external tool or API (CLI, SDK,
  model ids, URLs), skills whose purpose matches a row in section
  "Supersession patterns" of the reference for any host that loads them,
  skills with problems, skills older than 6 months, skills with an upstream
  (`metadata`, homepage, lockfile `~/.agents/.skill-lock.json`, git remote).
- **Static only**: pure-prompt skills with no dependencies. Judge by reading;
  say "static only" in the row.

Read `references/audit-checklist.md` now: statuses, confidence, evidence,
and the surface rule. Read `references/hosts/<id>.md` for every host that
appears in `readers_installed`.

### 3. Research (parallel where the host allows)

Group the "needs research" skills into batches of 5-8 by theme and hand
each batch to a sub-agent if your host has them (Claude Code Agent tool,
Codex sub-agents); otherwise work through the batches yourself. Each batch
gets: the skill entries from the inventory JSON, the paths to the checklist
and the relevant host references, the user's surfaces, today's date, and
this contract:

```
For each skill return: name | hosts that load it | status
(actual/outdated/broken/superseded/orphan) | confidence (high/medium/low) |
why, with at least one URL or command output per non-actual row |
recommendation (keep / update: how / replace with X / delete / built-in: <feature> on <host>/<surface> / merge into Y / move) |
not verified: what remains unknown.
Official sources first (the host's docs and changelog, the tool's own docs,
npm, PyPI, GitHub releases). Blog posts are secondary evidence. Do not
install, run or modify anything; `npm view`, `pip index versions`,
`curl -sI`, `git ls-remote` are fine.
```

Where to look, per axis:
- (a) technical: inventory `checks`; registries for current versions;
  `curl -sI` for a skill's main doc link.
- (b) built-in: `references/hosts/<id>.md` (Surfaces + Supersession
  patterns), then the host's changelog for everything after the skill's
  `last_modified` and after the reference's snapshot date.
- (c) alternatives: `duplicates`, the upstream named in the skill or the
  lockfile, the host's plugin/skill directory, `npx skills find <topic>`.

### 4. Report

Write in the user's language (skill names, statuses and commands stay in
English). Fill `references/report-template.md`; save to
`<cwd>/skill-freshness-report-<YYYY-MM-DD>.md` unless the user named a path;
show the summary table and the proposed actions in the reply. In a
terminal session, also print the summary with coloured statuses:
`python3 -I <skill-dir>/scripts/show_report.py <report.md>`.
Every non-`actual` row cites a source. The "Not verified" line is
mandatory: name what the audit could not do (offline, no API key, GUI-only,
agent not installed, sub-agent failed) instead of silently rating those
skills `actual`. See `examples/report-2026-10-27.md` for a real run.

### 5. `--fix` (only on request, only item by item)

For each proposed action show the exact change (command, or diff for a
SKILL.md edit) and get a yes. Apply only what was confirmed:
- delete = move to `<root>/.skill-freshness-trash/<date>/`, never `rm -rf`;
- before editing a SKILL.md, copy it into the same trash folder;
- update = the upstream's own installer (`npx skills add …`, the host's
  plugin command, the tool's `install`), not hand-copying files;
- never touch vendor-managed skills or a plugin's cache folder (use the
  host's plugin update instead);
- anything that needs the user's hands (a GUI toggle, an admin prompt, an
  API key) goes back to the user as a one-line instruction.

Append an "Applied" section to the report listing what changed.

## Keeping the baselines current

Each `references/hosts/<id>.md` is a dated snapshot. At the start of an
audit compare its date and version with the installed host's version; if
the host moved, read its changelog since the snapshot, use the new features
in this audit, and propose (as a `--fix` item) updating the reference.

## Files

- `scripts/scan.py` - run it; read it only when its output looks wrong.
- `scripts/hosts.json` - host registry; add a host here, no code change.
- `scripts/show_report.py` - step 4, prints the report's summary in a terminal.
- `references/audit-checklist.md` - step 2, every audit.
- `references/hosts/*.md` - step 2, for each host in `readers_installed`.
- `references/report-template.md` - step 4.
- `examples/report-2026-10-27.md` - a real report for orientation.
