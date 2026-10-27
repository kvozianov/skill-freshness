# Claude Code built-ins (baseline for "superseded?" checks)

Snapshot taken 2026-10-27 against Claude Code 2.1.308. The host moves fast:
treat this file as the floor, not the ceiling. During an audit, run
`claude --version`, then WebSearch / WebFetch the official sources below for
anything released after the snapshot date and append it to this file if the
user confirms (that is a change to the skill, so it goes through `--fix`).

Official sources (fetch these, prefer them over blog posts):
- Commands reference: https://code.claude.com/docs/en/commands
- Changelog: https://code.claude.com/docs/en/changelog (also https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- Weekly "what's new": https://code.claude.com/docs/en/whats-new/<year>-w<week>
- Skills: https://code.claude.com/docs/en/skills
- Hooks: https://code.claude.com/docs/en/hooks
- Memory: https://code.claude.com/docs/en/memory
- Codex: https://developers.openai.com/codex (and the `openai-docs` system skill in Codex)

## 0. Surfaces (read this before calling anything "superseded")

Claude Code runs on several surfaces. Detect the user's with `scan.py --env`
(`CLAUDE_CODE_ENTRYPOINT`: `cli`, `claude-desktop`, `claude-vscode`, `sdk-*`,
remote/cloud) and the saved profile. A feature replaces a skill only on the
surfaces where it exists.

| Feature | Terminal CLI | Desktop app (Code tab) | IDE extension | Cloud session |
|---|---|---|---|---|
| Slash commands, skills, hooks, subagents, Workflow, WebSearch/WebFetch, auto memory | yes | yes | yes | yes |
| `/loop`, CronCreate, Monitor, ScheduleWakeup | yes | yes | yes | yes (wakeups can be lost on container restart) |
| `/schedule` (cloud routines) | yes, needs claude.ai login + GitHub | same | same | yes |
| `/code-review`, `/security-review`, `/simplify`, `/verify`, `/run` | yes | yes | yes | yes |
| Claude in Chrome (`/chrome`, `mcp__claude-in-chrome__*`) | yes, needs the Chrome extension | yes | yes | no |
| Built-in browser pane (`mcp__Claude_Browser__*`, preview servers) | **no** | yes | no | no |
| iOS Simulator panel (`mcp__Claude_Code_iOS_Simulator__*`) | **no** | yes (macOS) | no | no |
| Computer use (`mcp__computer-use__*`, desktop control) | **no** (unverified for CLI on macOS) | yes | no | via linked computer only |
| Terminal tabs, side panes, task list, session cards (`ccd_*` tools) | **no** | yes | partial | no |
| Artifacts (`/artifacts`, Artifact tool), `/slides`, `/design`, Dashboard type | where the account has artifacts | yes | where available | where available |
| Voice (`/voice`), `/mobile`, Remote Control | partial | yes | partial | n/a |

Rule of thumb: anything named `mcp__Claude_Browser__*`, `mcp__ccd_*`,
`mcp__Claude_Code_iOS_Simulator__*` or `mcp__computer-use__*` is a
desktop-app feature. A terminal user still needs a Playwright / browser
skill, a simulator skill, a screenshot skill.

## 1. Claude Code slash commands (2.1.308)

"Skill" = a bundled skill (a prompt, like user skills). Everything else is
host code. A user skill whose whole purpose matches one of these is a
candidate for **superseded**.

### Session / context
`/clear`, `/compact [instructions]`, `/autocompact`, `/context`, `/cost` `/usage` `/stats`,
`/rewind` (`/checkpoint`, `/undo`), `/branch [name]` (fork the conversation),
`/fork [prompt]` (copy into a background session), `/subtask <task>` (forked
background subagent), `/background [prompt]`, `/resume`, `/rename`, `/recap`,
`/export`, `/copy`, `/btw` (side question outside the conversation), `/focus`,
`/tasks` (`/bashes`), `/goal [condition]` (keep working until condition met),
`/effort`, `/fast`, `/model`, `/advisor`, `/output-style`.

### Recurring / scheduled work  <- replaces most "looper", "cron", "watchdog" skills
- `/loop [interval] [prompt]` (Skill, since 2.1.71, March 2026): run a prompt or
  slash command repeatedly while the session is open. No interval = Claude
  self-paces (ScheduleWakeup tool). Session-scoped, min 1 min.
- `/schedule [description]` (`/routines`): cloud scheduled tasks on a cron,
  survive the session. Needs claude.ai login + GitHub connected (`/web-setup`).
- `/autofix-pr [prompt]`: cloud session that watches the branch's PR and
  pushes fixes on CI failure / review comments.
- Tools: `CronCreate`/`CronList`/`CronDelete` (in-session cron), `Monitor`
  (watch a command's output for an event instead of polling),
  `ScheduleWakeup`, `RemoteTrigger`, `PushNotification`.

### Code quality  <- replaces "review", "refactor", "security scan" skills
- `/code-review [level] [--fix] [--comment] [pr#|branch|path]` (`/review`), levels low..max, `ultra` = multi-agent cloud review (`/ultrareview`).
- `/simplify [target]` (Skill): four parallel agents for reuse / simplification / efficiency.
- `/security-review`: vulnerabilities in the branch diff.
- `/diff`: review working-tree changes.
- `/verify` and `/run` (Skills): build, launch and drive the app to confirm a change;
  `/run-skill-generator` writes a per-project launch skill.
- `/batch <instruction>` (Skill): decompose a large change into 5-30 parallel units.
- `/deep-research <question>` (Workflow): fan-out web research with citations.

### Setup / config / maintenance  <- replaces "settings helper", "permissions", "doctor" skills
- `/init` (CLAUDE.md), `/memory`, `/doctor [prompt-audit]`, `/config [key=value]`,
  `/permissions`, `/fewer-permission-prompts` (Skill), `/update-config [request]` (Skill),
  `/hooks`, `/keybindings`, `/statusline`, `/theme`, `/terminal-setup`, `/tui`,
  `/sandbox`, `/mcp`, `/add-dir`, `/cd`, `/ide`, `/chrome`, `/import [codex|gemini|cursor]`
  (migrate config, commands, MCP servers and skills from other agents), `/insights`
  (HTML report of your sessions), `/team-onboarding`, `/powerup`, `/release-notes`.
- Skills management: `/skills` (list, hide, sort by tokens), `/skill-doctor`
  (context cost + usage frequency per skill, since 2.1.252), `/reload-skills`,
  `/plugin [list|install|enable|disable]`, `/reload-plugins`, `/plugin-authoring` (mods),
  `claude plugin eval` (eval suites for skills).
- Planning: `/plan [description]` (plan mode). `/ultraplan` removed.
- Removed: `/pr-comments` (2.1.91), `/vim` (2.1.92), `/ultraplan`.

### Artifacts / design / docs  <- replaces "make slides", "dashboard", "diagram" skills *when* artifacts are available
`/artifacts`, `/artifact-capabilities`, `/artifact-diagramming`, `/dataviz`,
`/design [brief]` (Claude Design), `/design-sync`, `/slides [brief]` (Claude Slides),
Docs connector (first-party docs). `/claude-api [...]` (API migration helpers).

### Cloud / collaboration
`/schedule`, `/teleport` (`/tp`), `/remote-control` (`/rc`), `/remote-env`,
`/web-setup`, `/desktop` (`/app`), `/install-github-app`, `/install-slack-app`,
`/list-agents` (`/peers`), `/workflows`, `/workflow-authoring`, `/voice`, `/mobile`.

## 2. Built-in tools (what a skill no longer needs to script)

Agent / Task (subagents, incl. `fork`), Workflow (deterministic multi-agent
scripts), WebSearch (standard/extended), WebFetch, Artifact (publish HTML pages),
ArtifactData / ArtifactComments, Monitor, CronCreate, ScheduleWakeup, SendMessage
(cross-session), ListAgents, AskUserQuestion, EnterPlanMode / ExitPlanMode,
EnterWorktree / ExitWorktree, NotebookEdit, SearchSkills / ListSkills,
SearchPlugins / ListPlugins, SendUserFile, ToolSearch (deferred tools), Skill.
Built-in browser (`mcp__Claude_Browser__*`), Claude in Chrome, computer-use,
iOS Simulator control, terminal tabs, scheduled-tasks MCP.

## 3. Hook events (2.1.308)

SessionStart, Setup, UserPromptSubmit, UserPromptExpansion, PreToolUse,
PermissionRequest, PermissionDenied, PostToolUse, PostToolUseFailure,
PostToolBatch, Notification, MessageDisplay, SubagentStart, SubagentStop,
TaskCreated, TaskCompleted, Stop, StopFailure, TeammateIdle, InstructionsLoaded,
ConfigChange, CwdChanged, DirectoryAdded, FileChanged, WorktreeCreate,
WorktreeRemove, PreCompact, PostCompact, PreModelSwitch, PostModelSwitch,
Elicitation, ElicitationResult, SessionEnd.
Handler types: `command`, `http`, `prompt`, `agent`, `mcp_tool`.
A skill that says "run X after every tool call / before compaction / on session
start" is usually better as a hook (`/update-config` writes it).

## 4. Memory and instructions

CLAUDE.md hierarchy (enterprise > user `~/.claude/CLAUDE.md` > project >
nested), `AGENTS.md` accepted in place of CLAUDE.md, `.claude/rules/*.md`
(path-scoped rules), **auto memory** (Claude's own notes per repository,
`~/.claude/projects/<project>/memory/`, first 200 lines / 25 KB loaded every
session). A skill whose job is "remember facts between sessions" overlaps
with auto memory; a skill that *organizes* those notes (an Obsidian vault)
does not.

## 5. Skills system facts

- Discovery: `~/.claude/skills/<name>/SKILL.md`, `.claude/skills/<name>/SKILL.md`
  (project, and nested in subdirs), `--add-dir`, plugins
  (`<plugin>/skills/<name>/SKILL.md`, invoked as `/plugin:skill`), enterprise,
  claude.ai account skills. Only `<root>/<name>/SKILL.md` is loaded; deeper
  SKILL.md files are invisible.
- Frontmatter: `name`, `description`, `when_to_use`, `argument-hint`, `arguments`,
  `disable-model-invocation`, `user-invocable`, `allowed-tools`, `disallowed-tools`,
  `model`, `effort`, `context: fork`, `agent`, `background`, `hooks`, `paths`,
  `shell`; `metadata`/`license`/`compatibility` informational. Unknown fields
  are silently ignored (so `user-invokable`, `args`, `tools` are typos that do nothing).
- Arguments: `$ARGUMENTS`, `$ARGUMENTS[N]` / `$N`, named `$name` via `arguments:`;
  with no placeholder the host appends `ARGUMENTS: ...`.
- Up to six skills can be stacked in one message.
- `.claude/commands/*.md` still work but skills are the current form.

## 6. Other hosts

See `codex.md`, `gemini-cli.md`, `antigravity.md`, `cursor.md`, `copilot-cli.md`,
`opencode.md` and `agents-shared.md` in this folder.

## 7. Common supersession patterns (quick map)

| Skill does... | Built-in that likely replaces it |
|---|---|
| repeat a prompt every N minutes, poll a deploy, "babysit" | `/loop`, Monitor, CronCreate (all surfaces) |
| run something on a schedule when no session is open | `/schedule` (cloud) |
| watch a PR and fix CI | `/autofix-pr`, ccd_pr Auto-fix |
| review diff for bugs / security | `/code-review`, `/security-review`, `/simplify` |
| "remember this across sessions" | auto memory, CLAUDE.md, `.claude/rules/` |
| allow-list commands, edit settings, add hooks | `/update-config`, `/fewer-permission-prompts`, `/permissions` |
| find / install skills from a registry | `SearchSkills`, `SearchPlugins`, `/plugin`, `find-skills` style skills partially overlap |
| create a skill | skill-creator (Anthropic-synced), Codex `skill-creator` |
| migrate config from Codex/Cursor/Gemini | `/import` |
| which skills cost context / are unused | `/skill-doctor`, `/skills` |
| make slides / dashboards / diagrams | `/slides`, Dashboard artifact type, `/dataviz`, `/artifact-diagramming` (only where artifacts are enabled) |
| browse a site, screenshot, fill forms (Playwright-style) | built-in browser pane (**desktop app only**); Claude in Chrome (CLI + desktop, needs the extension) |
| run an iOS app in the simulator | iOS Simulator panel (**desktop app on macOS only**) |
| control desktop apps | computer use (**desktop app only**) |
| deep multi-source web research | `/deep-research`, WebSearch extended |
| launch the app and check a change | `/run`, `/verify` |
| onboarding doc from usage | `/team-onboarding`, `/insights` |
