# Google Antigravity: built-ins baseline for "superseded?" checks

Snapshot 2026-10-27, Antigravity (IDE, "Antigravity 2.0" desktop app, `agy` CLI).
Version not published in the docs; local built-in skills dated 2026-09-26. The public
docs are thin; part of this file comes from the bundled skills `agy-customizations`
and `antigravity_guide` (local evidence).

Sources:
- Docs: https://antigravity.google/docs
- Skills: https://antigravity.google/docs/skills
- Rules & workflows: https://antigravity.google/docs/rules-workflows
- Hooks / plugins / MCP: https://antigravity.google/docs/{hooks,plugins,mcp}
- Browser: https://antigravity.google/docs/ide/browser
- CLI: https://antigravity.google/docs/cli/reference
- Changelog: https://antigravity.google/changelog
- Local: `~/.gemini/antigravity/builtin/skills/*`

## 1. Where skills load from

| Surface | Scope | Path |
|---|---|---|
| App, CLI, IDE | workspace | `<root>/.agents/skills/<name>/` (`.agent/skills` still accepted) |
| App, IDE | global | `~/.gemini/config/skills/<name>/` |
| CLI | global | `~/.gemini/antigravity-cli/skills/<name>/` |
| CLI | plugin | `~/.gemini/antigravity-cli/plugins/<name>/skills/` |
| IDE | global (legacy) | `~/.gemini/antigravity/skills/` |
| all | built-in | `~/.gemini/antigravity/builtin/skills/` (local) |

- **Antigravity does not read `~/.agents/skills`** (global skills live under `~/.gemini/...`).
- Plugins installed for the app live in `~/.gemini/config/plugins/<name>/skills/` (local evidence).
- The `skills` CLI id `antigravity` targets the legacy IDE dir; an app-only user may need `~/.gemini/config/skills`.
- Frontmatter: `description` required, `name` optional (defaults to folder name).
- Invocation: autonomous by description; app and CLI expose `/<skill-name>`.

## 2. Workflows, rules, plugins, hooks

- **Workflows** (`.agents/workflows/`, `~/.gemini/config/workflows/`) are legacy; the built-in
  `migrate-workflows` skill converts them to skills. A workflow file is "migrate", not "dead".
- **Rules:** `GEMINI.md`, `AGENTS.md`, `.agents/rules/*.md`, global `~/.gemini/config/`.
- **Plugins:** `plugin.json` bundles skills, rules, MCP; `agy plugin list|install`.
- **Hooks:** `hooks.json`; events PreToolUse, PostToolUse, PreInvocation, PostInvocation (unverified, medium).

## 3. Built-in skills (local)

`agy-customizations`, `antigravity_guide`, `generative_ui` (inline interactive widgets),
`migrate-workflows`, `permissioned-github`.

## 4. Built-in features

- **Browser Subagent:** controls a local Chrome (isolated profile), saves screenshots and videos.
- **Agent Manager / 2.0 app:** parallel agents, Background Tasks, Artifacts, **Scheduled Tasks**.
- **Knowledge:** `~/.gemini/antigravity/knowledge` (presumed memory; unverified, medium).
- **Generative UI:** inline widgets.

## 5. Surfaces

| Feature | IDE | 2.0 app | `agy` CLI |
|---|---|---|---|
| Skills / rules / MCP | yes | yes | yes (separate global dir) |
| Browser Subagent | **yes** | likely (unverified, low) | not documented |
| Scheduled Tasks | not stated | **yes** | not documented |
| Generative UI | yes | yes | no (unverified, medium) |

Do not mark a CLI user's browser or scheduler skill as superseded.

## 6. Supersession patterns

| Skill does... | Antigravity built-in |
|---|---|
| browser QA / screenshots of a dev site | Browser Subagent (IDE / app) |
| recurring background job | Scheduled Tasks (2.0 app) |
| render charts / widgets in chat | `generative_ui` |
| explain how to write skills, hooks, rules | `agy-customizations` |
| convert workflows to skills | `migrate-workflows` |
| GitHub ops with permission prompts | `permissioned-github` |
