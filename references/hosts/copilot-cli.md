# GitHub Copilot CLI / cloud agent: built-ins baseline for "superseded?" checks

Snapshot 2026-10-27, Copilot CLI v1.0.104. Run `copilot version`.

Official sources:
- Agent skills: https://docs.github.com/en/copilot/concepts/agents/about-agent-skills
- CLI skills: https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills
- CLI command reference: https://docs.github.com/en/copilot/reference/cli-command-reference
- Customization cheat sheet: https://docs.github.com/en/copilot/reference/customization-cheat-sheet
- Releases: https://github.com/github/copilot-cli/releases

## 1. Where skills load from

- Project: `.github/skills/`, `.claude/skills/`, `.agents/skills/`
- Personal: `~/.copilot/skills/`, `~/.agents/skills/`
- `/add-dir PATH` also loads that dir's `.github/skills`. Plugins can ship skills.
- Frontmatter: `name`, `description` (required), `license`, `allowed-tools`.
- Personal skills are **not** guaranteed in the cloud agent; only repo skills are.
- Manage: `/skills` in the TUI; `copilot skill list|add|enable|disable|remove`; `gh skill` finds and installs.

## 2. Instructions, agents, hooks, MCP, plugins

| Feature | Paths | CLI | Cloud agent |
|---|---|---|---|
| Custom instructions | `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md`, `AGENTS.md` | yes | yes |
| Custom agents | `.github/agents/<name>.md` | yes (`/agent`) | yes |
| Hooks | `.github/hooks/*.json` | yes | yes |
| MCP | `copilot mcp`, `mcp.json` | yes | yes |
| Prompt files | `.github/prompts/*.prompt.md` | **no** | no (IDE only) |

Plugins: `copilot plugin install|list|update|enable|disable|uninstall` with marketplaces.

## 3. Built-in slash commands (partial)

`/add-dir`, `/after` (one-time scheduled prompt, experimental), `/agent`, `/app`, `/ask` (`/btw`),
`/allow-all`, `/autopilot` (`/goal`), `/changelog`, `/chronicle` (history insights incl. skill
proposals), `/clear`, `/compact`, `/skills`, `/mcp`, `/permissions`. Shell: `copilot workflow run`.

## 4. Built-in features

- **Autopilot / goal mode**, **fleet / subagents**, **workflows** (`copilot workflow run`).
- **Copilot code review** on GitHub.com (loads repo skills).
- **Scheduling:** only `/after` (one-time, experimental). No recurring scheduler.
- **Browser / computer use:** none documented for the CLI.

## 5. Surfaces

| Feature | CLI | Copilot app | VS Code agent mode | Cloud agent |
|---|---|---|---|---|
| Skills | yes | yes | yes | repo skills only |
| Prompt files | no | not stated | yes | no |
| `/after` scheduling | experimental | n/a | no | no |
| Browser tools | no | not stated | own tools (unverified, low) | no |

## 6. Supersession patterns

| Skill does... | Copilot built-in |
|---|---|
| keep going until a goal is met | `/autopilot` (`/goal`) |
| run something later, once | `/after` (experimental) |
| recurring schedule | none: **not superseded** |
| PR review | Copilot code review (cloud) |
| propose new skills from history | `/chronicle` |
| install skills | `copilot skill add`, `gh skill`, plugins |
| side question | `/ask` (`/btw`) |
