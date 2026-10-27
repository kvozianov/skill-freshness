# Google Gemini CLI: built-ins baseline for "superseded?" checks

Snapshot 2026-10-27, Gemini CLI v0.65.0 (stable, 2026-10-20). Run `gemini --version`.
Per geminicli.com, **Gemini CLI was replaced by Antigravity CLI (`agy`) on 2026-06-18
for unpaid-tier and Google One users**; such users probably run `agy` now (see antigravity.md).

Official sources:
- Docs: https://geminicli.com/docs/
- Skills: https://geminicli.com/docs/cli/skills/
- Commands: https://geminicli.com/docs/reference/commands/
- Custom commands: https://geminicli.com/docs/cli/custom-commands/
- Extensions: https://geminicli.com/docs/extensions/
- Hooks: https://geminicli.com/docs/hooks/
- Memory: https://geminicli.com/docs/cli/gemini-md/, /docs/cli/auto-memory/
- Releases: https://github.com/google-gemini/gemini-cli/releases

## 1. Where skills load from (lowest to highest precedence)

1. Built-in skills (`/skills list all`)
2. Extension skills
3. User: `~/.gemini/skills/` or alias `~/.agents/skills/`
4. Workspace: `.gemini/skills/` or alias `.agents/skills/`

- Higher tier wins on a name collision; within a tier `.agents/skills/` beats `.gemini/skills/`.
- Activation goes through the `activate_skill` tool with a user confirmation prompt.
- Frontmatter: Agent Skills spec (`name`, `description`) (unverified, high).

## 2. Skill management

- TUI: `/skills list [all]`, `/skills link <path>`, `/skills enable|disable <name>`, `/skills reload`.
- Shell: `gemini skills list --all`, `gemini skills install <git-url|path>`, `gemini skills uninstall <name>`.

## 3. Custom commands

TOML files in `~/.gemini/commands/` and `.gemini/commands/`; `/commands list|reload`.
A prompt-only skill may be simpler as a TOML command, and vice versa.

## 4. Built-in slash commands (v0.65)

`/about`, `/agents`, `/auth`, `/bug`, `/chat` (`/resume`), `/clear`, `/commands`, `/compress`,
`/copy`, `/directory`, `/docs`, `/editor`, `/extensions`, `/help`, `/hooks`, `/ide`, `/init`
(GEMINI.md), `/mcp`, `/memory`, `/model`, `/permissions`, `/plan`, `/policies`, `/privacy`,
`/quit`, `/restore`, `/rewind`, `/settings`, `/shells`, `/setup-github`, `/skills`, `/stats`,
`/terminal-setup`, `/theme`, `/tools`, `/upgrade`, `/vim`. `@path` injects files, `!cmd` runs shell.

## 5. Built-in features

- **Memory:** hierarchical `GEMINI.md`; Auto Memory (experimental).
- **Hooks:** lifecycle scripts (`/hooks`).
- **Extensions:** bundle MCP servers, commands, skills, context.
- **Subagents:** `/agents` (local + remote, experimental).
- **Checkpointing:** `/restore`, `/rewind`.
- **Web tools:** `google_web_search`, `web_fetch`. No browser automation.
- **GitHub:** `/setup-github` installs Actions for triage and PR review.
- **Scheduling:** **none built-in** (only headless `gemini -p` from cron/CI).

## 6. Surfaces

| Feature | Terminal CLI | IDE companion | Cloud |
|---|---|---|---|
| Skills, commands, hooks, MCP | yes | via CLI | GitHub Actions (headless) |
| Browser automation | no | no | no |
| Scheduling | no | no | user-built Actions cron |

Gemini CLI has no GUI-only features.

## 7. Supersession patterns

| Skill does... | Gemini CLI built-in |
|---|---|
| plan before editing | `/plan` |
| undo / restore files | `/rewind`, `/restore` |
| GitHub PR review / triage bots | `/setup-github` |
| remember facts | GEMINI.md, `/memory`, Auto Memory |
| run on a schedule | nothing built-in: **not superseded** |
| install skills from git | `gemini skills install` |
| browser automation | nothing built-in: **not superseded** |
| generate GEMINI.md | `/init` |
