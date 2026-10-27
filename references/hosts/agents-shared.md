# Cross-agent conventions: Agent Skills spec, `.agents/skills`, `skills` CLI

Snapshot 2026-10-27, `skills` CLI (vercel-labs/skills) v1.7.x, Agent Skills spec (agentskills.io).

Sources:
- Spec: https://agentskills.io/specification (validator `skills-ref`, repo github.com/agentskills/agentskills)
- `skills` CLI: https://github.com/vercel-labs/skills (docs/agents.md, docs/commands.md)
- Directory: https://skills.sh
- Anthropic: https://docs.claude.com/en/docs/agents-and-tools/agent-skills

## 1. The Agent Skills spec

- A skill is a folder with `SKILL.md` plus optional `scripts/`, `references/`, `assets/`.
- Frontmatter: `name` (required; 1-64 chars, `a-z0-9-`, no leading/trailing/double hyphen,
  **must equal the folder name**), `description` (required, 1-1024), `license`,
  `compatibility` (<=500), `metadata` (string map), `allowed-tools` (experimental).
- Progressive disclosure: ~100 tokens of metadata at startup, body (<5000 tokens, <500 lines)
  on activation, resources on demand.
- `skills-ref validate ./my-skill` is a portable lint the audit can suggest.

## 2. Which hosts read which folders

| Host | `.agents/skills` (project) | `~/.agents/skills` | Also reads |
|---|---|---|---|
| Claude Code | no | no | `.claude/skills`, `~/.claude/skills`, plugins |
| Codex | yes | yes | `~/.codex/skills` (legacy), `/etc/codex/skills` |
| Cursor | yes | yes | `.cursor/`, `.claude/`, `.codex/` skills (project + user) |
| Copilot CLI | yes | yes | `.github/skills`, `.claude/skills`, `~/.copilot/skills` |
| OpenCode | yes | yes | `.opencode/`, `.claude/` (project + global) |
| Gemini CLI | yes | yes | `.gemini/skills`, `~/.gemini/skills` |
| Antigravity | yes | **no** | `.agent/skills`, `~/.gemini/config/skills`, `~/.gemini/antigravity*/skills` |

Consequences:
- One copy in `~/.agents/skills` reaches Codex, Cursor, Copilot, OpenCode and Gemini CLI.
  Claude Code and Antigravity need their own copies.
- Cursor, Copilot and OpenCode also see `~/.claude/skills`: a skill there plus a copy in
  `~/.agents/skills` is a **duplicate for those hosts**.
- Before calling a skill "dead because wrong folder", check `readers_installed` from the scanner.

## 3. `skills` CLI behaviour

- Commands: `add <source>`, `find [query]`, `list`, `use`, `check`, `update [-g|-p|-y]`, `remove`, `init`.
- `add` flags: `-g`, `-a <agent...>`, `-s <skill>` (repeat the flag for several), `-y`, `--copy`.
- Global installs go to the canonical store `~/.agents/skills` with lockfile
  `~/.agents/.skill-lock.json` (`source`, `sourceUrl`, `skillPath`, `skillFolderHash`, `updatedAt`).
  `-a claude-code -g` copies into `~/.claude/skills`, so that copy can drift: compare hashes and
  use `npx skills check` / `update` as the update oracle.
- The lockfile is the best upstream pointer for any skill installed this way.
- Needs Node >= 22.20.

## 4. Audit implications

| Situation | Verdict guidance |
|---|---|
| Same skill in `~/.agents/skills` and `~/.claude/skills`, equal content | intended dual install, not a problem |
| Same skill, content differs | drift: `npx skills update` / re-add |
| Installer / finder skills (`find-skills`) | overlap with `skills find`, Codex `skill-installer`, `gemini skills install`, `copilot skill add`, `gh skill`, Claude Code SearchSkills |
| `name` violates the spec | works in Claude Code, may fail in OpenCode/Cursor: flag "portability" |
| Host-specific fields (`context: fork`, `agents/openai.yaml`) | ignored by other hosts, harmless |
