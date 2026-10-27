#!/usr/bin/env bash
# Install or update skill-freshness for every agent found on this machine.
#
# 1. Clones (or pulls) the repo into ~/.agents/skills/skill-freshness, the shared
#    folder read by Codex, Cursor, Copilot, OpenCode and Gemini CLI.
# 2. Links it into the skills folder of each other agent that exists here.
#
# Nothing outside those folders is touched. Existing non-link folders with the
# same name are left alone and reported.
set -euo pipefail

REPO="${SKILL_FRESHNESS_REPO:-https://github.com/kvozianov/skill-freshness.git}"
NAME="skill-freshness"
CANON="$HOME/.agents/skills/$NAME"

say() { printf '%s\n' "$*"; }

command -v git >/dev/null 2>&1 || { say "git is required"; exit 1; }
command -v python3 >/dev/null 2>&1 || say "warning: python3 not found; the scanner needs Python 3.9+"

mkdir -p "$(dirname "$CANON")"
if [ -d "$CANON/.git" ]; then
  say "updating $CANON"
  git -C "$CANON" pull --ff-only --quiet
elif [ -e "$CANON" ]; then
  say "$CANON exists and is not a git checkout; leaving it as is"
else
  say "installing to $CANON"
  git clone --depth 1 --quiet "$REPO" "$CANON"
fi

# agent home folder -> skills folder that agent reads
link_into() {
  local agent_home="$1" skills_dir="$2" label="$3"
  [ -d "$agent_home" ] || return 0
  mkdir -p "$skills_dir"
  local target="$skills_dir/$NAME"
  if [ -L "$target" ]; then
    ln -sfn "$CANON" "$target"
    say "linked   $label  ($target)"
  elif [ -e "$target" ]; then
    say "skipped  $label  ($target exists; remove it to use the shared copy)"
  else
    ln -s "$CANON" "$target"
    say "linked   $label  ($target)"
  fi
}

link_into "$HOME/.claude"             "$HOME/.claude/skills"               "Claude Code"
link_into "$HOME/.gemini/config"      "$HOME/.gemini/config/skills"        "Antigravity (app / IDE)"
link_into "$HOME/.gemini/antigravity-cli" "$HOME/.gemini/antigravity-cli/skills" "Antigravity CLI"
link_into "$HOME/.qwen"               "$HOME/.qwen/skills"                 "Qwen Code"
link_into "$HOME/.kilocode"           "$HOME/.kilocode/skills"             "Kilo Code"
link_into "$HOME/.roo"                "$HOME/.roo/skills"                  "Roo Code"
link_into "$HOME/.codeium/windsurf"   "$HOME/.codeium/windsurf/skills"     "Windsurf"

say "shared   Codex, Cursor, Copilot, OpenCode, Gemini CLI  ($CANON)"
say ""
say "Done. In your agent, run /$NAME (or ask: \"check which of my skills are outdated\")."
say "Standalone scanner: python3 \"$CANON/scripts/scan.py\" --env"
