# Audit checklist: how to decide a skill's status

Work through the questions below for every skill in scope. Write down what
you checked and what you could not check; the report has a column for both.

## Status vocabulary (pick exactly one)

| Status | Meaning | Typical evidence |
|---|---|---|
| **actual** | Works, nothing replaces it for this user, instructions match the tool it drives | deps present, no newer built-in on the user's surfaces, upstream unchanged |
| **outdated** | Still useful, but part of it is wrong or stale | upstream moved on, removed flag, old model id, broken doc link, frontmatter typos, a diverged duplicate |
| **broken** | Cannot work as written on this machine | missing CLI, script syntax error, missing module, referenced file absent, nested SKILL.md, project-relative path |
| **superseded** | A built-in feature of **every host that loads it, on every surface the user uses**, or a maintained alternative, does the job | match in the host reference's Supersession table and Surfaces table |
| **orphan** | No installed agent loads its folder | scanner flag `no installed host loads this root` |

Confidence goes next to the status: `high` (verified by running, by a diff,
or by an official source), `medium` (one secondary source or a strong
heuristic), `low` (a guess; say what would settle it). Never raise
confidence to make the table look cleaner.

## (0) Who loads it, and how does the user run that agent?

From the scanner: `readers_installed` (hosts that load the root and are
installed) and `duplicates`. From step 0: the user's surfaces per host.

- `readers_installed` empty → **orphan**. Ask whether the user plans to use
  that agent; recommend deleting only if not. Never call an orphan broken.
- Several hosts load it → every verdict below must hold for each of them.
  A skill can be superseded in Claude Code and still needed in Codex.
- Same name in several roots: identical content (`same_content: true`) is a
  deliberate multi-host install unless two of those roots are read by the
  same host; diverged content is **outdated** for the older copy.

## (a) Does it work technically?

1. **CLIs**: `missing` for a token marked "could be parser noise" is a
   finding only if it is really a command. For a real missing CLI, check the
   package (`npm view <pkg> version`, `pip index versions <pkg>`,
   `brew info <pkg>`) and whether the skill also offers `npx`/`uvx`.
2. **Scripts**: syntax errors and missing third-party modules are hard
   failures. Modules shipped beside the script are fine; test files are skipped.
3. **Referenced files**: a path into another skill or a project-relative
   path (`.agents/skills/x/scripts/...`) that does not resolve from where the
   skill is installed means it breaks as written.
4. **URLs**: optional `curl -sI -o /dev/null -w '%{http_code}' <url>` for the
   skill's main doc link; a 404 there is **outdated**.
5. **Frontmatter**: missing `description` = never auto-triggers. Unknown
   fields are ignored by most hosts. A `name` that breaks the Agent Skills
   spec (uppercase, underscores, not equal to the folder) works in Claude
   Code but may fail in OpenCode/Cursor: note "portability".
6. **Nested**: a SKILL.md deeper than `<root>/<name>/` is never loaded.
7. **Smoke**: only `--help`, `--version`, dry-run flags. Never run anything
   that writes outside the skill folder, needs credentials or network keys.

Everything you could not run goes in "Not verified", not into the status.

## (b) Is it replaced by a built-in feature of the host?

1. Read `references/hosts/<id>.md` for each host in `readers_installed`:
   section "Surfaces" first, then "Supersession patterns". Compare the
   skill's *purpose*, not its name.
2. **Surface rule.** A built-in counts only if it exists on every surface
   the user uses for that host. Examples: the Claude desktop app's browser
   pane does not exist in the terminal CLI; Codex scheduled tasks exist only
   in the desktop app and on the web; Cursor's browser is IDE-only. If the
   replacement covers some of the user's surfaces, the status stays
   **actual** with a note ("on desktop, the built-in browser does this").
3. Check the host version against the reference's snapshot. For anything
   newer, search the host's changelog since the skill's `last_modified`.
   Blog posts are secondary evidence (confidence `medium` at most).
4. For skills that wrap an SDK or API: search `<product> changelog <year>`
   and compare versions, flags, import paths and model ids.
5. Partial overlap is **actual** with a note, never **superseded**.

## (c) Is there a newer or maintained alternative, or no need at all?

1. Upstream: `metadata` / homepage in the frontmatter, the lockfile
   `~/.agents/.skill-lock.json`, a git remote in the folder, or a byte
   comparison with the likely source repo. Newer upstream = **outdated**,
   with the upstream's own install command as the fix.
2. Other installed skills with the same purpose: keep the better one.
3. Registries: the host's skill/plugin directory, `npx skills find <topic>`,
   GitHub. Prefer sources with recent commits; note the date.
4. Does the model now do this unaided? A short "write good X" skill adds
   little; recommend **delete** with confidence `medium` (the user's call).

## Recommendations (pick one, add a sentence)

`keep` · `update: <command>` · `replace with <X>` · `delete` ·
`built-in: <feature> (<host>, <surfaces>)` · `merge into <skill>` ·
`move` (nested or wrong folder) · `install <agent> or delete` (orphan).

## What `--fix` may do

Only after the user confirms each item:
- move a skill folder to `<root>/.skill-freshness-trash/<date>/` (never `rm -rf`);
- back up a SKILL.md into the same trash folder, then edit it;
- run the upstream's own install / update command;
- install a missing dependency with the exact line from the skill;
- move a nested skill to a loadable place.

Never touch vendor-managed skills (Anthropic-synced, Codex `.system`,
Antigravity `builtin`) or plugin cache folders: use the host's plugin
update. GUI toggles, admin prompts and API keys go back to the user.
