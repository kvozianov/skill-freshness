# OpenAI Codex: built-ins baseline for "superseded?" checks

Snapshot 2026-10-27, Codex CLI 0.164.0 (stable, 2026-10-23). Codex ships fast:
during an audit run `codex --version` and re-fetch the sources below for
anything released after the snapshot.

Official sources (developers.openai.com/codex/* redirects to learn.chatgpt.com/docs/*):
- Skills: https://learn.chatgpt.com/docs/build-skills
- Commands (CLI + IDE): https://learn.chatgpt.com/docs/developer-commands?surface=cli
- Plugins: https://learn.chatgpt.com/docs/plugins
- Scheduled tasks (automations): https://learn.chatgpt.com/docs/automations
- Hooks: https://learn.chatgpt.com/docs/hooks
- Subagents: https://learn.chatgpt.com/docs/agent-configuration/subagents
- Computer use: https://learn.chatgpt.com/docs/computer-use
- Desktop app: https://learn.chatgpt.com/docs/app
- Releases: https://github.com/openai/codex/releases
- Local evidence: `~/.codex/skills/.system/*/SKILL.md` + `agents/openai.yaml`, `~/.codex/config.toml`

## 1. Where skills load from

| Scope | Path | Source |
|---|---|---|
| Repo | `.agents/skills` in each dir from CWD up to repo root | docs |
| User | `~/.agents/skills` | docs |
| Admin | `/etc/codex/skills` | docs |
| System | bundled; on disk at `~/.codex/skills/.system/` | local |
| Legacy user | `~/.codex/skills` (`$CODEX_HOME/skills`) | local: `skill-installer` still installs here; not in current docs (unverified, high) |
| Legacy repo | `.codex/skills` | not in current docs (unverified, medium) |

- Same-named skills are not merged: both show in the picker. Symlinked skill folders are followed.
- The `skills` CLI (v1.7.x) installs `-a codex -g` into `~/.agents/skills` (lockfile `~/.agents/.skill-lock.json`).
- Disable a skill with `[[skills.config]] path = ".../SKILL.md"`, `enabled = false` in `~/.codex/config.toml`.
- Context budget: the skill list uses at most 2% of the window (or 8,000 chars); `skills.max_context_tokens` raises it.

## 2. SKILL.md and agents/openai.yaml

- Frontmatter Codex reads: `name`, `description` (required); `metadata.short-description` (system skills).
  Claude-only fields (`allowed-tools`, `context: fork`, `disable-model-invocation`) are ignored.
- `agents/openai.yaml`: `interface.*` (display name, icons, default prompt),
  `policy.allow_implicit_invocation` (default `true`), `dependencies.tools[]` (MCP servers).
- Invocation: `$skill-name` or `/skills` in CLI and IDE, `@skill` in ChatGPT, or implicitly by description.

## 3. System skills

`~/.codex/skills/.system/`: `skill-creator`, `skill-installer` (curated list or any GitHub path),
`imagegen` (raster generate/edit), `openai-docs` (Codex and OpenAI self-knowledge),
`review-agent` (read-only defect-first review, explicit only).

## 4. CLI subcommands and slash commands (0.164.0)

Subcommands: `exec`, `review`, `resume`, `fork`, `archive`, `cloud` (experimental), `apply`,
`plugin` (+ `plugin marketplace`), `mcp`, `features`, `doctor`, `sandbox`, `execpolicy`, `queue`,
`agents`, `app`, `app-server`, `remote-control`, `login`/`logout`, `update`, `completion`.

TUI slash commands: `/review`, `/diff`, `/plan`, `/goal`, `/init` (AGENTS.md), `/memories`,
`/skills`, `/plugins`, `/apps`, `/hooks`, `/mcp`, `/agents`, `/subagents`, `/side` (`/btw`),
`/fork`, `/resume`, `/new`, `/clear`, `/rename`, `/compact`, `/recap`, `/export`, `/copy`,
`/worktree`, `/ps`, `/stop`, `/import` (Claude Code / Cursor setup and chats), `/app`, `/model`,
`/fast`, `/permissions`, `/status`, `/usage`, `/statusline`, `/theme`, `/pets`, `/cd`, `/ide`.

## 5. Built-in features

- **Scheduled tasks (automations):** recurring tasks (cadence or RRULE). Managed in the desktop app
  or on the web, **not in the CLI or IDE extension**. Local runs need the app open.
- **Cloud tasks:** `codex cloud`, `codex apply` from the terminal; full UI on the web.
- **Plugins:** bundle skills, MCP servers, browser extensions, hooks (`/plugins`, `codex plugin`).
- **Subagents:** built-ins `default`, `worker`, `explorer`; custom TOML in `~/.codex/agents/`.
- **Hooks:** SessionStart/End, UserPromptSubmit, PreToolUse, PermissionRequest, PostToolUse,
  Pre/PostCompact, SubagentStart/Stop, Stop, Interrupt (`~/.codex/hooks.json` or config.toml).
- **Memories:** `/memories`. **Web search:** cached by default, `--search` for live.
- **Image generation:** `imagegen` system skill. **Review:** `/review`, `codex review`, `review-agent`.
- **Browser / computer use:** in-app browser, Chrome extension, Computer Use (desktop app only).
- **Goals:** `/goal`. **Pets:** `/pets`.

## 6. Surfaces

| Feature | CLI | IDE extension | Desktop app | Cloud / web |
|---|---|---|---|---|
| Skills | yes | yes | yes | not stated |
| Plugins | yes | **no** | yes | plugin skills in ChatGPT |
| Scheduled tasks | **no** | **no** | yes (local) | yes |
| Computer use, in-app browser | no | no | **yes** | no |
| Hooks | yes | not stated | not stated | admin only |
| Subagents | yes | yes | yes | read-only |

Rule: a terminal or IDE user's cron, browser or computer-use skill is **not** superseded by app-only features.

## 7. Supersession patterns

| Skill does... | Codex built-in that likely replaces it |
|---|---|
| run a prompt on a schedule, watch inbox/PRs | Scheduled tasks (desktop app / web only) |
| generate or edit images | `imagegen` system skill |
| review a diff for bugs | `/review`, `codex review`, `review-agent` |
| create / scaffold a skill | `skill-creator` |
| install skills from GitHub | `skill-installer`, `/plugins`, `codex plugin` |
| drive a browser, click around the desktop | in-app browser, Computer Use (app only) |
| remember facts across sessions | `/memories`, AGENTS.md |
| answer "how does Codex do X" | `openai-docs` system skill |
| migrate setup from Claude Code / Cursor | `/import` |
| side question | `/side` (`/btw`) |
| keep working until done | `/goal` |
| orchestrate role agents | native subagents (partial overlap) |
