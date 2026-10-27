"""Tests for scripts/scan.py. Standard library only: python3 -m unittest discover -s tests"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCAN = REPO / "scripts" / "scan.py"


def load_module():
    spec = importlib.util.spec_from_file_location("scan", SCAN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


scan = load_module()

# Environment variables the scanner reads to guess the current host/surface.
HOST_ENV = [k for k in os.environ if k.startswith(("CLAUDE", "CODEX_", "GEMINI", "OPENCODE"))] + [
    "__CFBundleIdentifier", "TERM_PROGRAM"]


def skill(root: Path, name: str, body: str = "", fm: str | None = None) -> Path:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    front = fm if fm is not None else f"name: {name}\ndescription: test skill {name}"
    (d / "SKILL.md").write_text(f"---\n{front}\n---\n\n{textwrap.dedent(body)}")
    return d


class FakeHome(unittest.TestCase):
    """Builds a throw-away $HOME and runs the scanner against it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sf-test-"))
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.project = self.tmp / "project"
        self.project.mkdir()
        self.bin = self.tmp / "bin"
        self.bin.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fake_binary(self, name: str, version: str = "1.0.0"):
        p = self.bin / name
        p.write_text(f"#!/bin/sh\necho '{version}'\n")
        p.chmod(0o755)

    def env(self, **extra) -> dict:
        e = {k: v for k, v in os.environ.items() if k not in HOST_ENV}
        e["HOME"] = str(self.home)
        e["XDG_CONFIG_HOME"] = str(self.home / ".config")
        # Keep python/node/git reachable but hide the developer's real agents.
        e["PATH"] = os.pathsep.join([str(self.bin), str(Path(sys.executable).parent), "/usr/bin", "/bin"])
        e.update(extra)
        return e

    def run_scan(self, *args, **env) -> dict:
        out = self.tmp / "out.json"
        cmd = [sys.executable, "-I", str(SCAN), "--project", str(self.project), "--out", str(out), *args]
        r = subprocess.run(cmd, capture_output=True, text=True, env=self.env(**env), timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(out.read_text())

    def by_name(self, data: dict, name: str) -> list[dict]:
        return [s for s in data["skills"] if s["name"] == name]


class TestDiscovery(FakeHome):
    def test_roots_and_readers(self):
        skill(self.home / ".claude" / "skills", "alpha")
        skill(self.home / ".agents" / "skills", "beta")
        skill(self.home / ".codex" / "skills", "gamma")
        (self.home / ".claude").mkdir(exist_ok=True)
        self.fake_binary("claude", "2.1.0 (Claude Code)")
        self.fake_binary("codex", "codex-cli 0.164.0")
        d = self.run_scan("--no-home-scan")
        alpha, = self.by_name(d, "alpha")
        beta, = self.by_name(d, "beta")
        gamma, = self.by_name(d, "gamma")
        self.assertIn("claude-code", alpha["readers_installed"])
        self.assertEqual(alpha["kind"], "shared")  # ~/.claude/skills is also read by Cursor/OpenCode
        self.assertIn("codex", beta["readers_installed"])
        self.assertNotIn("claude-code", beta["readers"])  # Claude Code does not read ~/.agents/skills
        self.assertIn("codex", gamma["readers_installed"])

    def test_version_of_installed_host(self):
        self.fake_binary("claude", "2.1.308 (Claude Code)")
        d = self.run_scan("--no-home-scan")
        cc = next(h for h in d["environment"]["hosts"] if h["id"] == "claude-code")
        self.assertTrue(cc["installed"])
        self.assertEqual(cc["version"], "2.1.308 (Claude Code)")
        self.assertIn("cli", cc["surfaces"])

    def test_config_folder_alone_is_not_an_install(self):
        (self.home / ".gemini").mkdir()
        skill(self.home / ".gemini" / "skills", "only-gemini")
        d = self.run_scan("--no-home-scan")
        g = next(h for h in d["environment"]["hosts"] if h["id"] == "gemini-cli")
        self.assertFalse(g["installed"])
        s, = self.by_name(d, "only-gemini")
        self.assertEqual(s["readers_installed"], [])
        self.assertIn("no installed host loads this root", s["flags"])

    def test_nested_skill_is_flagged(self):
        root = self.home / ".codex" / "skills"
        skill(root, "top")
        skill(root / "clone" / "skills", "deep")
        self.fake_binary("codex")
        d = self.run_scan("--no-home-scan")
        deep, = self.by_name(d, "deep")
        top, = self.by_name(d, "top")
        self.assertTrue(deep["nested"])
        self.assertFalse(top["nested"])
        self.assertIn("nested: hosts never load it", deep["flags"])

    def test_symlinked_copy_is_merged(self):
        canon = skill(self.home / ".agents" / "skills", "shared-one")
        (self.home / ".claude" / "skills").mkdir(parents=True)
        os.symlink(canon, self.home / ".claude" / "skills" / "shared-one")
        self.fake_binary("claude")
        self.fake_binary("codex")
        d = self.run_scan("--no-home-scan")
        copies = self.by_name(d, "shared-one")
        self.assertEqual(len(copies), 1, "symlinked copy should be reported once")
        self.assertTrue({"claude-code", "codex"} <= set(copies[0]["readers_installed"]))
        self.assertTrue(copies[0].get("also_at"))

    def test_duplicates_same_and_diverged(self):
        skill(self.home / ".claude" / "skills", "twin", body="same")
        skill(self.home / ".agents" / "skills", "twin", body="same")
        skill(self.home / ".claude" / "skills", "drift", body="new text")
        skill(self.home / ".agents" / "skills", "drift", body="old text")
        d = self.run_scan("--no-home-scan")
        for s in self.by_name(d, "twin"):
            self.assertTrue(all(x["same_content"] for x in s["duplicates"]))
        for s in self.by_name(d, "drift"):
            self.assertFalse(any(x["same_content"] for x in s["duplicates"]))

    def test_trash_and_managed_are_skipped(self):
        root = self.home / ".claude" / "skills"
        skill(root, "live")
        skill(root / ".skill-freshness-trash" / "2026-01-01", "dead")
        skill(root / "synced" / "bundle", "vendor")
        skill(self.home / ".codex" / "skills" / ".system", "sys")
        d = self.run_scan("--no-home-scan")
        names = {s["name"] for s in d["skills"]}
        self.assertIn("live", names)
        self.assertNotIn("dead", names)
        self.assertNotIn("vendor", names)
        self.assertNotIn("sys", names)
        d2 = self.run_scan("--no-home-scan", "--include-managed")
        self.assertTrue({"vendor", "sys"} <= {s["name"] for s in d2["skills"]})

    def test_project_level_skills(self):
        skill(self.project / ".claude" / "skills", "proj-claude")
        skill(self.project / ".agents" / "skills", "proj-agents")
        d = self.run_scan("--no-home-scan")
        pc, = self.by_name(d, "proj-claude")
        pa, = self.by_name(d, "proj-agents")
        self.assertEqual(pc["kind"], "project")
        self.assertIn("claude-code", pc["readers"])
        self.assertIn("codex", pa["readers"])
        self.assertNotIn("claude-code", pa["readers"])
        d2 = self.run_scan("--no-home-scan", "--no-project")
        self.assertFalse(self.by_name(d2, "proj-claude"))

    def test_home_sweep_finds_other_projects(self):
        other = self.home / "code" / "site"
        skill(other / ".claude" / "skills", "elsewhere")
        skill(self.home / "random" / "skills", "loose")
        (self.home / "Library" / "x" / "skills").mkdir(parents=True)
        skill(self.home / "Library" / "x" / "skills", "ignored")
        d = self.run_scan()
        e, = self.by_name(d, "elsewhere")
        lo, = self.by_name(d, "loose")
        self.assertEqual(e["kind"], "project")
        self.assertIn("claude-code", e["readers"])
        self.assertEqual(lo["kind"], "unknown")
        self.assertFalse(self.by_name(d, "ignored"))

    def test_host_filter_and_only(self):
        skill(self.home / ".claude" / "skills", "c1")
        skill(self.home / ".agents" / "skills", "a1")
        d = self.run_scan("--host", "codex")
        self.assertEqual({s["name"] for s in d["skills"]}, {"a1"})
        d = self.run_scan("--no-home-scan", "--only", "c1")
        self.assertEqual({s["name"] for s in d["skills"]}, {"c1"})

    def test_claude_plugins_from_manifest(self):
        cache = self.home / ".claude" / "plugins" / "cache" / "mkt" / "plug" / "1.0.0"
        skill(cache / "skills", "plugged")
        stale = self.home / ".claude" / "plugins" / "cache" / "mkt" / "old" / "0.1.0"
        skill(stale / "skills", "stale")
        (self.home / ".claude" / "plugins" / "installed_plugins.json").write_text(json.dumps(
            {"version": 2, "plugins": {"plug@mkt": [{"installPath": str(cache), "version": "1.0.0"}]}}))
        d = self.run_scan("--no-home-scan")
        p, = self.by_name(d, "plugged")
        self.assertEqual(p["kind"], "plugin")
        self.assertEqual(p["plugin"], "plug@mkt")
        self.assertFalse(self.by_name(d, "stale"), "cache dirs not in the manifest are not live plugins")


class TestChecks(FakeHome):
    def test_missing_cli_and_npx_fallback(self):
        skill(self.home / ".claude" / "skills", "needs-cli", body="""
            ```bash
            definitely-missing-tool run --x
            ```
            """)
        skill(self.home / ".claude" / "skills", "npx-ok", body="""
            ```bash
            npx knap render x
            knap render x
            ```
            """)
        d = self.run_scan("--no-home-scan", "--check")
        nc, = self.by_name(d, "needs-cli")
        nk, = self.by_name(d, "npx-ok")
        self.assertTrue(any("definitely-missing-tool" in p for p in nc["checks"]["problems"]))
        self.assertFalse(any("knap" in p for p in nk["checks"]["problems"]), nk["checks"])

    def test_script_syntax_and_imports(self):
        d0 = skill(self.home / ".claude" / "skills", "scripted")
        (d0 / "scripts").mkdir()
        (d0 / "scripts" / "good.py").write_text("import json\nfrom helper import x\n")
        (d0 / "scripts" / "helper.py").write_text("x = 1\n")
        (d0 / "scripts" / "bad.py").write_text("def broken(:\n")
        (d0 / "scripts" / "dep.py").write_text("import surely_not_installed_mod\n")
        (d0 / "scripts" / "tests").mkdir()
        (d0 / "scripts" / "tests" / "test_x.py").write_text("import pytest\n")
        (d0 / "scripts" / "run.sh").write_text("if then fi\n")
        (d0 / "scripts" / "doc.py").write_text('"""\nfrom the docs import nothing\n"""\n')
        d = self.run_scan("--no-home-scan", "--check")
        s, = self.by_name(d, "scripted")
        probs = " | ".join(s["checks"]["problems"])
        self.assertIn("bad.py: syntax-error", probs)
        self.assertIn("surely_not_installed_mod", probs)
        self.assertIn("run.sh: syntax-error", probs)
        self.assertNotIn("helper", probs)
        self.assertNotIn("pytest", probs)
        self.assertNotIn("the", s["checks"]["py_imports"])

    def test_placeholder_and_missing_paths(self):
        skill(self.home / ".claude" / "skills", "paths", body="""
            ```bash
            python3 <runtime>/agent.py
            python3 ~/.claude/skills/other-skill/scripts/run.py
            ```
            """)
        d = self.run_scan("--no-home-scan", "--check")
        s, = self.by_name(d, "paths")
        probs = " | ".join(s["checks"]["problems"])
        self.assertNotIn("<runtime>", probs)
        self.assertIn("other-skill/scripts/run.py", probs)

    def test_heredoc_and_python_c_are_not_commands(self):
        skill(self.home / ".claude" / "skills", "embedded", body="""
            ```bash
            python3 -c '
            import os
            results = compute()
            '
            cat <<EOF
            neverseen_token one two
            EOF
            ```
            """)
        d = self.run_scan("--no-home-scan", "--check")
        s, = self.by_name(d, "embedded")
        self.assertEqual(s["checks"]["problems"], [], s["checks"])

    def test_portability_against_spec(self):
        root = self.home / ".claude" / "skills"
        skill(root, "good")
        skill(root, "folder-a", fm="name: other-name\ndescription: x")
        skill(root, "upper", fm="name: Upper_Case\ndescription: x")
        skill(root, "hinted", fm="name: hinted\ndescription: x\nargument-hint: \"[x]\"")
        skill(root, "nodesc", fm="name: nodesc")
        skill(root, "badyaml", fm="name: badyaml\ndescription: Use it for: audits")
        skill(root, "okyaml", fm='name: okyaml\ndescription: "Use it for: audits"')
        d = self.run_scan("--no-home-scan")
        port = {s["name"]: " | ".join(s["portability"]) for s in d["skills"]}
        self.assertEqual(port["good"], "")
        self.assertIn("differs from folder", port["other-name"])
        self.assertIn("breaks the spec", port["Upper_Case"])
        self.assertIn("argument-hint", port["hinted"])
        self.assertIn("never auto-triggers", port["nodesc"])
        self.assertIn("not valid YAML", port["badyaml"])
        self.assertEqual(port["okyaml"], "")

    def test_smoke_runs_help(self):
        d0 = skill(self.home / ".claude" / "skills", "smoky")
        (d0 / "scripts").mkdir()
        (d0 / "scripts" / "cli.py").write_text("import argparse\nargparse.ArgumentParser().parse_args()\n")
        d = self.run_scan("--no-home-scan", "--check", "--smoke")
        s, = self.by_name(d, "smoky")
        self.assertIn("smoke --help ok", s["checks"]["scripts"]["scripts/cli.py"])


class TestEnvironment(FakeHome):
    def env_session(self, **env) -> dict:
        r = subprocess.run([sys.executable, "-I", str(SCAN), "--env"], capture_output=True, text=True,
                           env=self.env(**env), timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)["current_session"]

    def test_claude_desktop(self):
        s = self.env_session(CLAUDECODE="1", CLAUDE_CODE_ENTRYPOINT="claude-desktop")
        self.assertEqual((s["host"], s["surface"]), ("claude-code", "desktop"))

    def test_claude_cli_in_terminal(self):
        s = self.env_session(CLAUDECODE="1", CLAUDE_CODE_ENTRYPOINT="cli", TERM_PROGRAM="iTerm.app")
        self.assertEqual((s["host"], s["surface"]), ("claude-code", "cli"))

    def test_claude_cli_inside_vscode_terminal(self):
        s = self.env_session(CLAUDECODE="1", CLAUDE_CODE_ENTRYPOINT="cli", TERM_PROGRAM="vscode")
        self.assertEqual(s["surface"], "ide")

    def test_cli_child_of_desktop_app_is_cli(self):
        s = self.env_session(CLAUDECODE="1", CLAUDE_CODE_ENTRYPOINT="cli", CLAUDE_CODE_DESKTOP_APP_VERSION="3.0")
        self.assertEqual(s["surface"], "cli")

    def test_sdk_entrypoint(self):
        s = self.env_session(CLAUDECODE="1", CLAUDE_CODE_ENTRYPOINT="sdk-cli", CLAUDE_CODE_DESKTOP_APP_VERSION="3.0")
        self.assertEqual(s["surface"], "sdk")

    def test_claude_vscode_extension(self):
        s = self.env_session(CLAUDECODE="1", CLAUDE_CODE_ENTRYPOINT="claude-vscode")
        self.assertEqual(s["surface"], "ide")

    def test_gemini(self):
        s = self.env_session(GEMINI_CLI="1")
        self.assertEqual((s["host"], s["surface"]), ("gemini-cli", "cli"))

    def test_unknown_is_not_confident(self):
        s = self.env_session()
        self.assertIsNone(s["host"])
        self.assertFalse(s["confident"])

    def test_profile_roundtrip_and_validation(self):
        cmd = [sys.executable, "-I", str(SCAN), "--save-profile", "claude-code=cli;codex=ide,desktop"]
        r = subprocess.run(cmd, capture_output=True, text=True, env=self.env(), timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        prof = json.loads((self.home / ".config" / "skill-freshness" / "profile.json").read_text())
        self.assertEqual(prof["hosts"], {"claude-code": ["cli"], "codex": ["ide", "desktop"]})
        bad = subprocess.run([sys.executable, "-I", str(SCAN), "--save-profile", "nope=cli"],
                             capture_output=True, text=True, env=self.env(), timeout=60)
        self.assertNotEqual(bad.returncode, 0)
        bad = subprocess.run([sys.executable, "-I", str(SCAN), "--save-profile", "codex=phone"],
                             capture_output=True, text=True, env=self.env(), timeout=60)
        self.assertNotEqual(bad.returncode, 0)


class TestParsing(unittest.TestCase):
    def test_frontmatter_variants(self):
        fm, body = scan.parse_frontmatter('---\nname: x\ndescription: "quoted: yes"\n---\nbody')
        self.assertEqual(fm["description"], "quoted: yes")
        self.assertEqual(body, "body")
        fm, _ = scan.parse_frontmatter("---\nname: x\ndescription: >\n  folded line one\n  line two\n---\n")
        self.assertEqual(fm["description"], "folded line one line two")
        fm, _ = scan.parse_frontmatter("---\nname: x\ndescription: starts here\n  and continues\nmetadata:\n  author: a\n---\n")
        self.assertEqual(fm["description"], "starts here and continues")
        fm, body = scan.parse_frontmatter("no frontmatter")
        self.assertEqual(fm, {})

    def test_cli_extraction_ignores_prose_and_noise(self):
        trusted, untrusted = scan.shell_lines(textwrap.dedent("""
            ```bash
            export FOO=1
            cd "$(git rev-parse --show-toplevel)" && realtool --flag | grep x
            # comment line
            ```
            Some prose `the next step` here.
            """))
        clis = scan.extract_clis(trusted) | scan.extract_clis(untrusted, require_on_path=True)
        self.assertIn("realtool", clis)
        for noise in ("rev-parse", "the", "next", "export", "cd", "git"):
            self.assertNotIn(noise, clis)

    def test_registry_is_consistent(self):
        reg = json.loads((REPO / "scripts" / "hosts.json").read_text())
        ids = [h["id"] for h in reg["hosts"]]
        self.assertEqual(len(ids), len(set(ids)))
        for h in reg["hosts"]:
            for key in ("name", "binaries", "user_skill_dirs", "project_skill_dirs"):
                self.assertIn(key, h, h["id"])
            ref = h.get("reference")
            if ref:
                self.assertTrue((REPO / "references" / ref).is_file(), f"{h['id']}: missing {ref}")


class TestRepoHygiene(unittest.TestCase):
    """The skill must load in every agent: valid frontmatter per the Agent Skills spec."""

    def test_skill_md_follows_spec(self):
        fm, body = scan.parse_frontmatter((REPO / "SKILL.md").read_text())
        self.assertEqual(fm["name"], REPO.name if REPO.name == "skill-freshness" else "skill-freshness")
        self.assertRegex(fm["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
        self.assertLessEqual(len(fm["description"]), 1024)
        self.assertLess(body.count("\n"), 500)

    def test_referenced_files_exist(self):
        text = (REPO / "SKILL.md").read_text()
        import re
        for rel in set(re.findall(r"`((?:scripts|references|examples)/[\w./-]+\.(?:py|json|md))`", text)):
            self.assertTrue((REPO / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
