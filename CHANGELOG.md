# Changelog

## 1.1.0 — 2026-10-28

- `scripts/show_report.py`: prints a report's summary in the terminal with coloured statuses (works with translated headers).
- Demo GIF re-recorded with it.

## 1.0.1 — 2026-10-28

- Test suite (31 tests) and the Agent Skills validator in CI; end-to-end eval cases with a fixture home.
- Installable as a Claude Code plugin (`/plugin install skill-freshness --marketplace kvozianov/skill-freshness`).
- New portability checks: non-spec frontmatter, names that break the spec or differ from the folder, invalid YAML.
- Surface detection no longer mistakes a CLI started from the desktop app for the app itself.
- Description reworked for triggering; validated against 20 trigger queries.
- Scanner Markdown: compiler errors fit on one line (no absolute paths), table cells are escaped, nested copies show as loaded by none.
- New portability check: frontmatter that opens with `---` but never closes.
- Test fixture: `investment-memo` frontmatter now closes properly (the agent caught the literal `\n`).
- Demo GIF and social preview in `assets/`.

## 1.0.0 — 2026-10-28

- Multi-agent scanner (`scripts/scan.py`) driven by a JSON registry of 11 agents plus a home-folder sweep; records which installed agent loads each skill folder.
- Surface detection (terminal CLI, desktop app, IDE extension, cloud) and a saved user profile, so desktop-only features never make a skill "superseded" for a terminal user.
- Dated built-in feature baselines for Claude Code, Codex, Gemini CLI, Antigravity, Cursor, Copilot CLI, OpenCode and the shared `.agents/skills` convention.
- Statuses `actual` / `outdated` / `broken` / `superseded` / `orphan` with confidence and sources.
- `--fix` with per-item confirmation, trash folder instead of deletion, backups before edits.
- One-command installer for every agent on the machine.
