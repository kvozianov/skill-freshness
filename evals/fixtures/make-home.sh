#!/usr/bin/env bash
# Builds a small, known-bad skill landscape in $HOME for the eval cases.
# Every problem below is one the audit is expected to find.
set -eu
H="$HOME"
mk() { # mk <dir> <name> <frontmatter-extra> <body>
  mkdir -p "$1/$2"
  printf -- '---\nname: %s\ndescription: %s\n%s---\n\n%s\n' "$2" "$3" "$4" "$5" > "$1/$2/SKILL.md"
}
C="$H/.claude/skills"; X="$H/.codex/skills"; A="$H/.agents/skills"
mkdir -p "$C" "$X" "$A" "$H/.codex"
touch "$H/.codex/config.toml"

# broken: CLI not installed
mk "$C" defuddle "Extract clean Markdown from web pages with the Defuddle CLI." "" \
'Install: `npm install -g defuddle`

```bash
defuddle parse https://example.com --md
```'
# superseded by Claude Code /loop
mk "$C" loop-runner "Re-run a prompt or slash command every N minutes until stopped, e.g. to babysit a deploy." "" \
'When the user asks to repeat something on an interval, start a bash `while true; do ...; sleep 300; done` loop and re-send the prompt each time.'
# browser automation (not superseded for a terminal user)
mk "$C" playwright-browser "Open pages, click, fill forms and take screenshots with Playwright for QA." "" \
'```bash
npx playwright screenshot https://example.com shot.png
```'
# diverged duplicate: newer copy in Claude, older in Codex
mk "$C" obsidian-bases "Create and edit Obsidian Bases (.base files)." "" 'A filter object contains exactly one of `and`, `or`, `not`.'
mk "$X" obsidian-bases "Create and edit Obsidian Bases (.base files)." "" 'Filters may combine `and:`, `or:` and `not:` in one object.'
# identical duplicate in the shared store
mk "$C" grilling "Interview the user relentlessly about a plan." "" "Ask one round of questions at a time."
mk "$A" grilling "Interview the user relentlessly about a plan." "" "Ask one round of questions at a time."
# nested copy from a git clone: never loaded
mkdir -p "$X/taste-skill/skills"
mk "$X/taste-skill/skills" design-taste "Opinionated frontend design rules." "" "Use bold typography."
# stale model ids and a non-spec frontmatter field
mk "$X" investment-memo "Write investment memos." $'models: [claude-3-5-sonnet, gpt-4]\n' "Structure: thesis, risks, recommendation."
# script with a syntax error
mk "$C" csv-tools "Clean CSV files." "" 'Run `python3 scripts/clean.py input.csv`.'
mkdir -p "$C/csv-tools/scripts"; printf 'def clean(:\n    pass\n' > "$C/csv-tools/scripts/clean.py"
# healthy prompt-only skill
mk "$C" ux-copy "Write and review UX microcopy." "" "Prefer verbs on buttons."
echo "fixture home ready: $(find "$H" -name SKILL.md | wc -l | tr -d ' ') skills"
