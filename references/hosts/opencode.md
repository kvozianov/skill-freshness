# OpenCode: built-ins baseline for "superseded?" checks

Snapshot 2026-10-27, OpenCode v1.19.4 (2026-10-22) and v2.2.0 (2026-10-27); both lines
coexist (`opencode upgrade --major`). Repo: github.com/anomalyco/opencode (formerly sst/opencode).

Official sources:
- Docs: https://opencode.ai/docs/
- Skills: https://opencode.ai/docs/skills/
- Agents: https://opencode.ai/docs/agents/
- Commands: https://opencode.ai/docs/commands/
- Releases: https://github.com/anomalyco/opencode/releases

## 1. Where skills load from

- Project (walks up to the git root): `.opencode/skills/`, `.claude/skills/`, `.agents/skills/`
- Global: `~/.config/opencode/skills/`, `~/.claude/skills/`, `~/.agents/skills/`
- **Every Claude Code user skill is already visible to OpenCode.**
- Frontmatter: `name` (required, `^[a-z0-9]+(-[a-z0-9]+)*$`, 1-64 chars, must equal dir),
  `description` (1-1024), optional `license`, `compatibility`, `metadata`. Unknown fields ignored.
- A skill with an uppercase or mismatched `name` fails validation here even if Claude Code loads it:
  flag it as a portability problem.
- Permissions: `permission.skill` in `opencode.json` (allow / deny / ask).

## 2. Agents and commands

- Built-in agents: **build**, **plan** (no edits except plan files), **general** (parallel research
  subagent), **explore** (read-only search subagent).
- Custom agents: `.opencode/agents/*.md`, `~/.config/opencode/agents/*.md`.
- Custom commands: `.opencode/commands/*.md`, `~/.config/opencode/commands/*.md` (`$ARGUMENTS`, `$1`, `` !`cmd` ``, `@file`).
- Built-in TUI commands: `/init` (AGENTS.md), `/undo`, `/redo`, `/help`, `/connect`, `/update`.

## 3. Built-in features

- Rules: `AGENTS.md`. Plugins (event hooks), custom tools, MCP, LSP, formatters, SDK, server.
- Session sharing was **discontinued** in v1.19.1; the GitHub Action was removed in v2.2.0.
- No built-in scheduler and no browser automation.

## 4. Surfaces

| Feature | TUI / CLI | Desktop app | Web / server |
|---|---|---|---|
| Skills, agents, commands | yes | yes (unverified, high) | yes (unverified, medium) |
| Desktop plugins, Todo tool | no | yes (v2.2, experimental) | no |
| Scheduling, browser | none | none | none |

## 5. Supersession patterns

| Skill does... | OpenCode built-in |
|---|---|
| read-only planning before edits | `plan` agent |
| parallel codebase research | `explore`, `general` subagents |
| undo an agent change | `/undo`, `/redo` |
| generate AGENTS.md | `/init` |
| prompt shortcut with args | custom command |
| share a session link | **gone** (discontinued): not superseded |
| schedule / browser automation | nothing built-in: not superseded |
