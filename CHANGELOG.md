# Changelog

## 1.0.0 — 2026-10-28

- Multi-agent scanner (`scripts/scan.py`) driven by a JSON registry of 11 agents plus a home-folder sweep; records which installed agent loads each skill folder.
- Surface detection (terminal CLI, desktop app, IDE extension, cloud) and a saved user profile, so desktop-only features never make a skill "superseded" for a terminal user.
- Dated built-in feature baselines for Claude Code, Codex, Gemini CLI, Antigravity, Cursor, Copilot CLI, OpenCode and the shared `.agents/skills` convention.
- Statuses `actual` / `outdated` / `broken` / `superseded` / `orphan` with confidence and sources.
- `--fix` with per-item confirmation, trash folder instead of deletion, backups before edits.
- One-command installer for every agent on the machine.
