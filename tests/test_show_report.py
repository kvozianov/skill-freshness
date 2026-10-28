"""Tests for scripts/show_report.py. Standard library only."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SHOW = REPO / "scripts" / "show_report.py"

REPORT = """# Skill freshness report

**Not verified:** nothing.

## Summary

| # | Skill | Loaded by | Status | Conf. | Why (with source) | Recommendation |
|---|---|---|---|---|---|---|
| 1 | `defuddle` | Claude Code | **broken** | high | `which defuddle` → not found | update: `npm install -g defuddle` |
| 2 | loop-runner | Claude Code | superseded | high | [docs](https://example.com) | built-in: `/loop`; delete |
| 3 | ux-copy | Claude Code | actual | low | static only | keep |

Totals: actual 1 · broken 1 · superseded 1

## Proposed actions (for `--fix`)
"""


class TestShowReport(unittest.TestCase):
    def show(self, text: str, **env) -> subprocess.CompletedProcess:
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(text)
        e = {k: v for k, v in os.environ.items() if k not in {"NO_COLOR", "FORCE_COLOR"}}
        e.update(env)
        try:
            return subprocess.run([sys.executable, "-I", str(SHOW), f.name, "--width", "100"],
                                  capture_output=True, text=True, env=e, timeout=30)
        finally:
            os.unlink(f.name)

    def test_plain_output(self):
        r = self.show(REPORT)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("\x1b[", r.stdout)
        lines = r.stdout.splitlines()
        self.assertIn("defuddle", lines[2])
        self.assertIn("broken", lines[2])
        self.assertIn("npm install -g defuddle", lines[2])
        self.assertNotIn("`", r.stdout)
        self.assertIn("Totals: actual 1", r.stdout)

    def test_colours(self):
        r = self.show(REPORT, FORCE_COLOR="1")
        self.assertIn("\x1b[1;31mbroken", r.stdout)
        self.assertIn("\x1b[1;35msuperseded", r.stdout)
        self.assertIn("\x1b[32mactual", r.stdout)
        self.assertNotIn("\x1b[", self.show(REPORT, FORCE_COLOR="1", NO_COLOR="1").stdout)

    def test_translated_headers(self):
        ru = REPORT.replace("| Skill | Loaded by | Status |", "| Скилл | Кто загружает | Статус |")
        r = self.show(ru)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("loop-runner", r.stdout)

    def test_no_table(self):
        r = self.show("# empty\n")
        self.assertEqual(r.returncode, 1)

    def test_real_examples(self):
        r = subprocess.run([sys.executable, "-I", str(SHOW), str(REPO / "examples" / "report-2026-10-27.md")],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("playwright-skill", r.stdout)


if __name__ == "__main__":
    unittest.main()
