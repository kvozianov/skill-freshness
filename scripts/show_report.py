#!/usr/bin/env python3
"""Print the summary table of a skill-freshness report in the terminal.

Reads the Markdown report the skill wrote and shows one line per skill:
number, skill, status (coloured) and recommendation, wrapped to the
terminal width, followed by the totals line. Colours are off when stdout is
not a terminal or NO_COLOR is set; FORCE_COLOR=1 turns them on.

Usage:
  show_report.py skill-freshness-report-2026-10-28.md
  show_report.py report.md --width 100
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import textwrap
from pathlib import Path

STATUSES = ["superseded", "outdated", "broken", "orphan", "actual"]
COLORS = {"broken": "1;31", "outdated": "1;33", "superseded": "1;35", "orphan": "1;36", "actual": "32"}
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def plain(cell: str) -> str:
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cell).replace("**", "").replace("`", "").strip()


def split_row(line: str) -> list[str]:
    return [plain(c) for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def status_of(cell: str) -> str | None:
    low = cell.lower()
    hits = [(low.find(s), s) for s in STATUSES if s in low]
    return min(hits)[1] if hits else None


def parse(text: str) -> tuple[list[dict], str | None]:
    """The first table that has a status column, plus the totals line."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not (line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip())):
            continue
        header = split_row(line)
        body = []
        for row in lines[i + 2:]:
            if not row.startswith("|"):
                break
            body.append(split_row(row))
        body = [r for r in body if len(r) == len(header)]
        if not body:
            continue
        # The status column is the one whose cells name a status most often.
        scores = [sum(1 for r in body if status_of(r[c]) and len(r[c]) < 40) for c in range(len(header))]
        st = max(range(len(header)), key=lambda c: scores[c])
        if scores[st] < max(1, len(body) // 2):
            continue
        num = 0 if header[0].strip() in {"#", "№", "N"} else None
        skill = 1 if num == 0 else 0
        rows = [{"num": r[num] if num is not None else str(k), "skill": r[skill], "status": r[st], "rec": r[-1]}
                for k, r in enumerate(body, 1)]
        totals = next((plain(t) for t in lines[i + 2 + len(body):] if re.search(r"\bactual\b.*\d", t, re.I)), None)
        return rows, totals
    return [], None


def paint(text: str, status: str | None, on: bool) -> str:
    return f"\x1b[{COLORS[status]}m{text}\x1b[0m" if on and status else text


def render(rows: list[dict], totals: str | None, width: int, color: bool) -> str:
    wn = max(len(r["num"]) for r in rows)
    ws = min(max(len(r["skill"]) for r in rows), 36)
    wt = min(max(len(r["status"]) for r in rows), 22)
    wr = max(width - wn - ws - wt - 6, 24)
    dim = (lambda s: f"\x1b[2m{s}\x1b[0m") if color else (lambda s: s)
    out = [dim(f"{'#':>{wn}}  {'Skill':<{ws}}  {'Status':<{wt}}  Recommendation"), dim("─" * min(width, wn + ws + wt + 6 + wr))]
    for r in rows:
        st = status_of(r["status"])
        skill = textwrap.wrap(r["skill"], ws) or [""]
        status = textwrap.wrap(r["status"], wt) or [""]
        rec = textwrap.wrap(r["rec"], wr) or [""]
        for k in range(max(len(skill), len(status), len(rec))):
            n = r["num"] if k == 0 else ""
            s = skill[k] if k < len(skill) else ""
            t = status[k] if k < len(status) else ""
            c = rec[k] if k < len(rec) else ""
            out.append(f"{n:>{wn}}  {s:<{ws}}  {paint(f'{t:<{wt}}', st, color)}  {c}".rstrip())
    if totals:
        for s in STATUSES:
            totals = re.sub(rf"\b{s}\b", lambda m: paint(m.group(0), s, color), totals)
        out += ["", totals]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report", type=Path, help="skill-freshness-report-<date>.md")
    ap.add_argument("--width", type=int, help="output width (default: terminal width)")
    args = ap.parse_args()
    rows, totals = parse(args.report.read_text(encoding="utf-8"))
    if not rows:
        print(f"no summary table with a status column in {args.report}", file=sys.stderr)
        return 1
    color = (sys.stdout.isatty() or os.environ.get("FORCE_COLOR")) and not os.environ.get("NO_COLOR")
    width = args.width or shutil.get_terminal_size((120, 40)).columns
    print(render(rows, totals, width, bool(color)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
