# Cursor: built-ins baseline for "superseded?" checks

Snapshot 2026-10-27, Cursor (no version on the public changelog; latest entry
"Agent SDK", 2026-10-20). Skills need Cursor 2.4+. Built-in browser GA since 2.0.

Official sources:
- Skills: https://cursor.com/docs/context/skills
- Rules: https://cursor.com/docs/rules
- Hooks: https://cursor.com/docs/agent/hooks
- Browser: https://cursor.com/docs/agent/tools/browser
- Subagents: https://cursor.com/docs/subagents
- Cloud agents / automations: https://cursor.com/docs/cloud-agent, https://cursor.com/docs/cloud-agent/automations
- CLI: https://cursor.com/docs/cli/overview
- Changelog: https://cursor.com/changelog

## 1. Where skills load from

- Native: `.cursor/skills/`, `.agents/skills/` (project); `~/.cursor/skills/`, `~/.agents/skills/` (user).
- Compatibility: also `.claude/skills/`, `.codex/skills/`, `~/.claude/skills/`, `~/.codex/skills/`.
  **Claude Code and Codex skills are already visible in Cursor**; same name in two of those dirs is a real duplicate.
- Frontmatter: `name` (required, must match folder), `description` (required), `paths` (globs),
  `disable-model-invocation`, `icon`, `color`, `metadata`.
- Invocation: automatic, `/skill-name` in Agent chat, or as a Custom Mode.

## 2. Rules, commands, hooks

- **Rules:** `.cursor/rules/*.mdc` (`description`, `globs`, `alwaysApply`), `AGENTS.md`, user and team rules.
- **Commands:** `.cursor/commands/*.md` (legacy); `/migrate-to-skills` converts them.
- **Hooks:** `hooks.json` (enterprise, team, `.cursor/hooks.json`, `~/.cursor/hooks.json`). Events include
  sessionStart/End, pre/postToolUse, subagentStart/Stop, before/afterShellExecution,
  before/afterMCPExecution, beforeReadFile, afterFileEdit, beforeSubmitPrompt, preCompact, stop.

## 3. Built-in skills

`/create-skill`, `/create-rule`, `/create-hook`, `/create-subagent`, `/migrate-to-skills`,
`/loop`, `/shell`, `/automate`, `/statusline`, `/update-cli-config`.

## 4. Built-in features

- **Browser:** embedded browser the agent drives (navigate, click, type, screenshot, console, network).
- **Subagents:** custom plus a built-in Browser subagent.
- **Cloud Agents:** remote agents (web, mobile, Slack); hand off from the CLI with `&`.
- **Automations:** cloud agents on cron or GitHub/Slack/webhook/Linear/Sentry triggers, with per-automation memories.
- **Bugbot / Security Review:** PR review in the cloud.
- **Agent SDK:** agents as code with a `skills/` folder and cron triggers.

## 5. Surfaces

| Feature | IDE / Agents Window | `agent` CLI | Cloud agents / automations |
|---|---|---|---|
| Skills | yes | not stated (unverified, medium) | repo skills; personal only with "Sync Skills" |
| Rules / AGENTS.md | yes | yes | yes |
| Hooks | yes | partial | project and team only |
| Built-in browser | **IDE only** | no | own computer (unverified, medium) |
| Scheduling | via automations | via handoff | **yes** |

## 6. Supersession patterns

| Skill does... | Cursor built-in |
|---|---|
| run on a schedule / on PR or Slack events | Automations (cloud) |
| repeat a prompt in-session | `/loop` |
| browser QA of a local app | built-in browser (IDE only) |
| create skills, rules, hooks, subagents | `/create-skill`, `/create-rule`, `/create-hook`, `/create-subagent` |
| convert old commands or rules | `/migrate-to-skills` |
| PR bug / security review | Bugbot, Security Review |
| remember facts | rules / AGENTS.md (memories only inside automations) |
