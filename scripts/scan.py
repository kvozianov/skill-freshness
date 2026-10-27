#!/usr/bin/env python3
"""skill-freshness scanner: find every agent skill on this machine.

Reads the host registry in hosts.json (Claude Code, Codex, Gemini CLI,
Antigravity, Cursor, Copilot, OpenCode, Qwen Code, Kilo Code, Roo Code,
Windsurf, ...), detects which hosts are installed and on which surfaces
(terminal CLI, desktop app, IDE extension), scans every skill root once,
records which hosts load each root, then sweeps the home directory for any
other SKILL.md the registry does not know about.

For each skill it parses SKILL.md and extracts what an audit needs: CLIs,
packages, URLs, slash commands, MCP tools, model ids, env vars, last change.
With --check it verifies dependencies exist on this machine.

The script never modifies or executes skills. The only things it runs are
`<host> --version`, `python -m py_compile`, `bash -n`, `node --check`, and
with --smoke `<script> --help` under a 15 s timeout.

Usage:
  scan.py --env                    # only the environment: hosts, surfaces, current session
  scan.py                          # all hosts, all roots, home sweep; JSON to stdout
  scan.py --check --md             # + dependency checks, Markdown table
  scan.py --host codex --host claude-code
  scan.py --only defuddle          # one skill by name or path substring
  scan.py --project /path          # project whose skill dirs to include (default: cwd)
  scan.py --no-home-scan           # registry roots only (faster)
  scan.py --out inventory.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import glob
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
HERE = Path(__file__).resolve().parent
PROFILE_PATH = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "skill-freshness" / "profile.json"

SKIP_DIRS = {"synced", ".system", "node_modules", ".git", "__pycache__", ".skill-freshness-trash"}


def expand(p: str) -> Path:
    return Path(os.path.expanduser(p))


def load_registry() -> dict:
    return json.loads((HERE / "hosts.json").read_text())


# ---------------------------------------------------------------------------
# Environment: which hosts exist, on which surfaces, and where are we now
# ---------------------------------------------------------------------------

def _ide_extensions(reg: dict) -> list[str]:
    names: list[str] = []
    for d in reg.get("ide_extension_dirs", []):
        d = expand(d)
        if d.is_dir():
            names += [x.name.lower() for x in d.iterdir()]
    return names


def _apps(reg: dict) -> set[str]:
    found: set[str] = set()
    for d in reg.get("app_dirs", []):
        d = expand(d)
        if d.is_dir():
            found |= {x.name for x in d.iterdir() if x.suffix == ".app"}
    return found


def current_session() -> dict:
    """Best-effort guess of the host and surface running this script.

    The surface matters: a terminal user has no desktop-only features (browser
    pane, simulator panel, artifacts preview), so a skill must not be called
    superseded by one of them.
    """
    e = os.environ
    host, surface, evidence = None, None, []
    if e.get("CLAUDECODE") == "1" or e.get("CLAUDE_CODE_ENTRYPOINT"):
        host = "claude-code"
        ep = e.get("CLAUDE_CODE_ENTRYPOINT", "")
        evidence.append(f"CLAUDE_CODE_ENTRYPOINT={ep or '?'}")
        if ep in {"claude-desktop", "desktop"} or e.get("CLAUDE_CODE_DESKTOP_APP_VERSION"):
            surface = "desktop"
        elif "vscode" in ep or "jetbrains" in ep or "ide" in ep:
            surface = "ide"
        elif ep.startswith("sdk") or ep in {"remote", "cloud"} or e.get("CLAUDE_CODE_REMOTE"):
            surface = "cloud" if ep in {"remote", "cloud"} or e.get("CLAUDE_CODE_REMOTE") else "sdk"
        elif ep == "cli":
            surface = "ide" if e.get("TERM_PROGRAM") == "vscode" else "cli"
    elif any(k.startswith("CODEX_") for k in e):
        host = "codex"
        origin = e.get("CODEX_INTERNAL_ORIGINATOR_OVERRIDE", "")
        evidence.append("CODEX_* env" + (f", originator={origin}" if origin else ""))
        surface = "ide" if "vscode" in origin else ("desktop" if "desktop" in origin or "app" in origin else ("cli" if e.get("TERM") else None))
    elif e.get("GEMINI_CLI") == "1":
        host, surface = "gemini-cli", "cli"
        evidence.append("GEMINI_CLI=1")
    elif e.get("OPENCODE") or e.get("OPENCODE_BIN_PATH"):
        host, surface = "opencode", "cli"
        evidence.append("OPENCODE env")
    if e.get("__CFBundleIdentifier"):
        evidence.append(f"bundle={e['__CFBundleIdentifier']}")
    if e.get("TERM_PROGRAM"):
        evidence.append(f"TERM_PROGRAM={e['TERM_PROGRAM']}")
    return {"host": host, "surface": surface, "evidence": evidence,
            "confident": host is not None and surface is not None}


def detect_hosts(reg: dict, want_versions: bool = True) -> list[dict]:
    exts = _ide_extensions(reg)
    apps = _apps(reg)
    out = []
    for h in reg["hosts"]:
        surfaces = {}
        bins = [b for b in h.get("binaries", []) if shutil.which(b)]
        if bins:
            surfaces["cli"] = shutil.which(bins[0])
        app = [a for a in h.get("apps", []) if a in apps]
        if app:
            surfaces["desktop"] = ", ".join(app)
        ext = sorted({x for x in exts for pref in h.get("ide_extensions", []) if x.startswith(pref.lower())})
        if ext:
            surfaces["ide"] = ext[-1]
        cfg = [str(expand(c)) for c in h.get("config_dirs", []) if expand(c).exists()]
        version = None
        if want_versions and bins and h.get("version_cmd"):
            code, outp = run(h["version_cmd"], timeout=8)
            version = outp.splitlines()[0] if code == 0 and outp else None
        out.append({
            "id": h["id"], "name": h["name"],
            "installed": bool(surfaces),
            "surfaces": surfaces,
            "config_present": cfg,
            "version": version,
            "reference": h.get("reference"),
        })
    return out


def load_profile() -> dict | None:
    try:
        return json.loads(PROFILE_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def find_skill_files(root: Path, max_depth: int = 3) -> list[Path]:
    """Return SKILL.md files under root, up to max_depth levels deep."""
    out: list[Path] = []
    if not root.is_dir():
        return out
    root_depth = len(root.parts)
    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        p = Path(dirpath)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".skill-freshness")]
        if len(p.parts) - root_depth >= max_depth:
            dirnames[:] = []
        if "SKILL.md" in filenames:
            out.append(p / "SKILL.md")
    return sorted(out)


def _globs(pattern: str) -> list[Path]:
    return [Path(p) for p in sorted(glob.glob(os.path.expanduser(pattern)))]


def build_roots(reg: dict, hosts: list[dict], project: Path | None, only_hosts: set[str] | None) -> dict[str, dict]:
    """Map every skill root path -> {kind, readers[], managed, plugin?}."""
    # A config folder alone is not an install (e.g. ~/.gemini is created by Antigravity).
    installed = {h["id"] for h in hosts if h["installed"]}
    roots: dict[str, dict] = {}

    def add(path: Path, host: str, kind: str, **extra):
        if only_hosts and host not in only_hosts:
            return
        if not path.is_dir():
            return
        key = str(path.resolve())
        r = roots.setdefault(key, {"path": str(path), "kind": kind, "readers": [], **extra})
        if host not in r["readers"]:
            r["readers"].append(host)

    for h in reg["hosts"]:
        hid = h["id"]
        for d in h.get("user_skill_dirs", []):
            add(expand(d), hid, "user")
        for d in h.get("managed_skill_dirs", []):
            for p in _globs(d):
                add(p, hid, "managed", managed=True)
        for d in h.get("plugin_skill_dirs", []):
            for p in _globs(d):
                add(p, hid, "plugin", plugin=p.parent.name)
        if project:
            for d in h.get("project_skill_dirs", []):
                add(project / d, hid, "project")

    # Claude Code plugins: trust installed_plugins.json, not stale cache dirs.
    pj = HOME / ".claude" / "plugins" / "installed_plugins.json"
    if pj.is_file() and (not only_hosts or "claude-code" in only_hosts):
        enabled: dict = {}
        try:
            enabled = json.loads((HOME / ".claude" / "settings.json").read_text()).get("enabledPlugins", {})
        except (OSError, json.JSONDecodeError):
            pass
        try:
            data = json.loads(pj.read_text())
        except json.JSONDecodeError:
            data = {}
        for pid, installs in data.get("plugins", {}).items():
            for inst in installs:
                path = Path(inst.get("installPath", ""))
                meta = {"plugin": pid, "plugin_version": inst.get("version"),
                        "plugin_updated_at": inst.get("lastUpdated"),
                        "plugin_enabled": enabled.get(pid, True)}
                add(path / "skills", "claude-code", "plugin", **meta)
                add(path / "commands", "claude-code", "plugin-commands", **meta)

    for r in roots.values():
        r["readers_installed"] = [x for x in r["readers"] if x in installed]
        if r["kind"] == "user" and len(r["readers"]) > 1:
            r["kind"] = "shared"
    return roots


def home_sweep(reg: dict, known_roots: dict[str, dict], hosts: list[dict]) -> dict[str, dict]:
    """Find skill dirs anywhere under $HOME that the registry does not cover.

    Classifies each by its path suffix (e.g. <proj>/.claude/skills ->
    claude-code project skills) so project-level copies are attributed.
    """
    cfg = reg.get("home_scan", {})
    max_depth = cfg.get("max_depth", 5)
    skip = set(cfg.get("skip", []))
    suffix_map: list[tuple[str, str]] = []
    for h in reg["hosts"]:
        for d in h.get("project_skill_dirs", []):
            suffix_map.append((d.rstrip("/"), h["id"]))
    known = {Path(k) for k in known_roots}
    found: dict[str, dict] = {}
    base_depth = len(HOME.parts)
    for dirpath, dirnames, filenames in os.walk(HOME):
        p = Path(dirpath)
        depth = len(p.parts) - base_depth
        dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith(".skill-freshness")]
        if depth >= max_depth:
            dirnames[:] = []
        if p.name != "skills":
            continue
        rp = p.resolve()
        if rp in known or any(k in rp.parents for k in known):
            dirnames[:] = []
            continue
        if not any((c / "SKILL.md").is_file() for c in p.iterdir() if c.is_dir()):
            continue
        readers = [hid for suf, hid in suffix_map if str(p).endswith("/" + suf)]
        installed = {h["id"] for h in hosts if h["installed"]}
        found[str(rp)] = {"path": str(p), "kind": "project" if readers else "unknown",
                          "readers": readers, "readers_installed": [r for r in readers if r in installed]}
        known.add(rp)
        dirnames[:] = []  # skills inside are handled by find_skill_files
    return found


def discover(roots: dict[str, dict]) -> list[dict]:
    found: list[dict] = []
    for key, r in roots.items():
        root = Path(r["path"])
        meta = {k: v for k, v in r.items() if k not in {"path"}}
        if r["kind"] == "plugin-commands":
            for c in sorted(root.glob("*.md")):
                found.append({"root": r["path"], "skill_file": str(c), "nested": False, **meta})
            continue
        for f in find_skill_files(root):
            found.append({"root": r["path"], "skill_file": str(f),
                          # Hosts load only <root>/<name>/SKILL.md; deeper files are invisible.
                          "nested": f.parent.resolve() != root.resolve() and f.parent.parent.resolve() != root.resolve(),
                          **meta})
    return found


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.S)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Minimal YAML-ish frontmatter parser (enough for SKILL.md)."""
    m = FM_RE.match(text)
    if not m:
        return {}, text
    fm: dict = {}
    current_key = None
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")) and current_key:
            # nested mapping or continuation; keep raw lines
            fm.setdefault(current_key + "_raw", []).append(line.strip())
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            k = k.strip()
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            fm[k] = v
            current_key = k
    # Folded / literal block scalars: `description: >` followed by indented lines
    for k in list(fm):
        if k.endswith("_raw") or k not in fm:
            continue
        raw = fm.get(k + "_raw")
        if not isinstance(raw, list):
            continue
        if fm[k] in {">", "|", ">-", "|-", ""}:
            fm[k] = " ".join(raw)
            fm.pop(k + "_raw")
        elif not any(re.match(r"^[\w-]+:", ln) or ln.startswith("- ") for ln in raw):
            # multi-line plain scalar: continuation lines of the same value
            fm[k] = fm[k] + " " + " ".join(raw)
            fm.pop(k + "_raw")
    return fm, text[m.end():]


URL_RE = re.compile(r"https?://[^\s)>\]\"'`]+")
FENCE_RE = re.compile(r"```([\w+-]*)\s*\n(.*?)```", re.S)
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
SLASH_RE = re.compile(r"(?<![\w/])/([a-z][\w-]{1,40})\b")
MCP_RE = re.compile(r"\bmcp__[\w-]+__[\w-]+")
MODEL_RE = re.compile(
    r"\b(claude-(?:[a-z0-9]+-)+(?:\d{8}|\d+(?:-\d+)?)|claude-\d-\d-[a-z]+|"
    r"gpt-[\w.-]+|o[134](?:-mini)?\b|gemini-[\w.-]+)\b"
)
PKG_RE = re.compile(
    r"\b(?:npm (?:install|i|add)(?: -g| --global)?|pnpm add|yarn add|bun add|"
    r"pip3? install(?: --user)?|uv (?:pip install|add)|brew install|cargo install|"
    r"gem install|go install) +((?:[@\w][@\w./-]*)(?: (?:[@\w][@\w./-]*)){0,3})"
)
ENV_RE = re.compile(r"\$\{?([A-Z][A-Z0-9_]{3,})\}?")

SHELL_NOISE = {
    "cd", "echo", "cat", "ls", "mkdir", "rm", "cp", "mv", "export", "set", "if",
    "then", "fi", "for", "do", "done", "while", "else", "elif", "case", "esac",
    "function", "return", "exit", "true", "false", "sudo", "source", "test",
    "touch", "grep", "sed", "awk", "head", "tail", "find", "xargs", "sort",
    "uniq", "wc", "tr", "cut", "tee", "pwd", "printf", "read", "local", "env",
    "which", "chmod", "sleep", "date", "open", "man", "less", "more", "bash",
    "sh", "zsh", "python", "python3", "node", "git", "curl", "wget", "jq", "yq",
    "rg", "fd", "fzf", "diff", "basename", "dirname", "realpath", "ln", "stat",
    "kill", "ps", "trap", "eval", "shift", "break", "continue", "in", "select",
    "import", "from", "def", "class", "raise", "with", "except", "try", "print",
    "const", "let", "var", "await", "async", "pass", "not", "and", "or", "is",
    "pip", "pip3", "npm", "pnpm", "yarn", "bun", "brew", "apt", "apt-get", "cargo",
    "go", "gem", "make", "cmake", "docker", "ssh", "scp", "rsync", "tar", "zip",
    "unzip", "gzip", "rmdir", "cp", "yes", "no", "command", "type", "hash",
    "neither", "next", "then", "also", "your", "the", "this", "that", "what", "path",
    "items", "run", "use", "see", "note", "example", "output", "result", "step", "add",
    "rev-parse", "lorem", "ipsum", "foo", "bar", "baz", "etc",
    "||", "&&", "{", "}", "(", ")", "[[", "]]", "[", "]", "#", "//", "%", "$",
    "&&", "|", ">", ">>", "<", "..", "...", "...", "-", "--",
}
PATH_TOKEN = re.compile(r"^[\w.@+-]+$")


HEREDOC_RE = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?")


def strip_heredocs(code: str) -> list[str]:
    """Drop heredoc bodies and multi-line quoted strings (python -c '...')
    embedded in bash, and return the remaining lines."""
    out: list[str] = []
    end: str | None = None
    in_quote: str | None = None
    for ln in code.splitlines():
        if end is not None:
            if ln.strip() == end:
                end = None
            continue
        if in_quote:
            if ln.count(in_quote) % 2 == 1:
                in_quote = None
            continue
        m = HEREDOC_RE.search(ln)
        if m:
            end = m.group(1)
        else:
            # a line that opens a quote it does not close starts a multi-line string
            for q in ("'", '"'):
                if ln.count(q) % 2 == 1:
                    in_quote = q
                    break
        out.append(ln)
    return out


def shell_lines(body: str) -> tuple[list[str], list[str]]:
    """Return (trusted, untrusted) command-looking lines.

    trusted: fenced blocks labelled as shell, and `$ cmd` prompts - a first
    token there that is not on PATH is a real finding.
    untrusted: unlabelled fences and inline code - prose and other languages
    leak in, so a token from here only counts if it exists on PATH.
    """
    trusted: list[str] = []
    untrusted: list[str] = []
    for lang, code in FENCE_RE.findall(body):
        lang = lang.lower()
        if lang in {"bash", "sh", "shell", "zsh", "console", "terminal"}:
            dest = trusted
        elif lang == "":
            dest = untrusted
        else:
            continue
        for ln in strip_heredocs(code):
            ln = ln.strip()
            if ln.startswith("$ "):
                ln = ln[2:]
                dest = trusted
            if ln and not ln.startswith("#"):
                dest.append(ln)
    for code in INLINE_CODE_RE.findall(body):
        code = code.strip()
        if code.startswith("$ "):
            trusted.append(code[2:])
        elif len(code) < 120 and re.match(r"^[a-z][\w.-]*(?: [-\w./@=]+)+$", code):
            untrusted.append(code)
    return trusted, untrusted


def extract_clis(lines: list[str], require_on_path: bool = False) -> set[str]:
    clis: set[str] = set()
    for ln in lines:
        # split pipelines / chains into simple commands
        ln = ln.replace("$(", "; ").replace("`", "; ")
        for seg in re.split(r"\s*(?:\|\||&&|\||;)\s*", ln):
            toks = seg.strip().split()
            # skip env assignments and sudo
            while toks and (re.match(r"^[A-Z_][A-Z0-9_]*=", toks[0]) or toks[0] in {"sudo", "time", "nohup"}):
                toks = toks[1:]
            if not toks:
                continue
            cmd = toks[0]
            if cmd in {"npx", "uvx", "bunx", "pnpx"} and len(toks) > 1:
                clis.add(f"{cmd} {toks[1]}")
                continue
            if cmd in {"python", "python3", "node", "bash", "sh", "uv"}:
                # script invocation: capture the script path instead
                for t in toks[1:]:
                    if t.endswith((".py", ".js", ".mjs", ".ts", ".sh")):
                        clis.add(t)
                        break
                continue
            if cmd in SHELL_NOISE or not PATH_TOKEN.match(cmd):
                continue
            if cmd.startswith((".", "/", "~", "-")) and not cmd.endswith((".py", ".js", ".sh")):
                continue
            if not re.match(r"^[a-z][a-z0-9._+-]*$", cmd) or cmd.endswith(".") or len(cmd) < 2:
                continue
            if cmd.endswith((".py", ".js", ".mjs", ".sh")):
                clis.add(cmd)
                continue
            if require_on_path and not shutil.which(cmd):
                continue
            clis.add(cmd)
    return clis


def analyse_skill(entry: dict) -> dict:
    f = Path(entry["skill_file"])
    text = f.read_text(errors="replace")
    fm, body = parse_frontmatter(text)
    skill_dir = f.parent

    # Files bundled with the skill (node_modules, .git etc. pruned during walk)
    bundled: list[str] = []
    scripts: list[str] = []
    mtimes: list[float] = []
    has_node_modules = False
    for dirpath, dirnames, filenames in os.walk(skill_dir):
        if "node_modules" in dirnames:
            has_node_modules = True
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and d not in {".venv", "venv"}]
        for fn in filenames:
            p = Path(dirpath) / fn
            rel = str(p.relative_to(skill_dir))
            bundled.append(rel)
            try:
                mtimes.append(p.stat().st_mtime)
            except OSError:
                pass
            top_level = Path(dirpath) == skill_dir
            if p.suffix in {".py", ".sh", ".js", ".mjs", ".ts"} and ("scripts" in p.parts or top_level):
                scripts.append(rel)

    # Last modification: newest file in the skill folder
    last_modified = dt.datetime.fromtimestamp(max(mtimes)).date().isoformat() if mtimes else None

    trusted, untrusted = shell_lines(body)
    trusted_clis = extract_clis(trusted)
    clis = extract_clis(untrusted, require_on_path=True) | {
        c for c in trusted_clis if shutil.which(c.split()[0]) or "." in c or c.startswith(("npx ", "uvx ", "bunx ", "pnpx "))
    }
    # Tokens from shell-labelled blocks that are not on PATH: either a missing
    # dependency or parser noise - the audit decides which.
    clis_unresolved = trusted_clis - clis
    pkgs = {m.strip() for m in PKG_RE.findall(body)}
    urls = sorted(set(URL_RE.findall(body)))
    slash = sorted({s for s in SLASH_RE.findall(body)
                    if s not in {"dev", "tmp", "usr", "etc", "bin", "var", "opt", "home", "api", "v1", "v2", "docs", "path", "to", "your", "root", "dist", "src", "lib"}})
    mcp = sorted(set(MCP_RE.findall(text)))
    models = sorted(set(MODEL_RE.findall(text)))
    envs = sorted({e for e in ENV_RE.findall(body) if e not in {"HOME", "PATH", "PWD", "USER", "SHELL", "ARGUMENTS"}})
    # Mentions of Claude Code tools (capitalised tool names in the body)
    tools = sorted(set(re.findall(
        r"\b(WebSearch|WebFetch|Bash|Read|Write|Edit|Grep|Glob|Agent|Task|AskUserQuestion|"
        r"TodoWrite|NotebookEdit|Skill|Artifact|Monitor|CronCreate|ScheduleWakeup)\b", body)))

    name = fm.get("name") or skill_dir.name
    return {
        **entry,
        "name": name,
        "dir": str(skill_dir),
        "description": fm.get("description", "").strip(),
        "frontmatter": {k: v for k, v in fm.items() if k not in {"name", "description"}},
        "last_modified": last_modified,
        "skill_md_lines": text.count("\n") + 1,
        "bundled_files": len(bundled),
        "has_node_modules": has_node_modules,
        "scripts": sorted(scripts),
        "clis": sorted(clis),
        "clis_unresolved": sorted(clis_unresolved),
        "packages": sorted(pkgs),
        "urls": urls,
        "slash_commands": slash,
        "mcp_tools": mcp,
        "model_ids": models,
        "env_vars": envs,
        "host_tools": tools,
        "invokes_subagents": bool(re.search(r"\bsub-?agents?\b|\bAgent tool\b|\bTask tool\b", body, re.I)),
    }


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def run(cmd: list[str], timeout: int = 10, cwd: str | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd,
                           env={**os.environ, "NO_COLOR": "1"})
        return p.returncode, (p.stdout + p.stderr).strip()[-400:]
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except FileNotFoundError as e:
        return 127, str(e)


def check_skill(sk: dict, smoke: bool) -> dict:
    checks: dict = {"clis": {}, "scripts": {}, "py_imports": {}, "problems": []}
    skill_dir = sk["dir"]

    via_runner = {c.split()[1] for c in sk["clis"] if c.split()[0] in {"npx", "uvx", "bunx", "pnpx"} and len(c.split()) > 1}
    for cli in sk["clis"] + sk["clis_unresolved"]:
        head = cli.split()[0]
        if head in via_runner and not shutil.which(head):
            checks["clis"][cli] = "not installed, but the skill also runs it via npx/uvx"
            continue
        if cli.endswith((".py", ".js", ".mjs", ".ts", ".sh")) and re.search(r"[<>{}$]|/tmp/|your", cli):
            checks["clis"][cli] = "placeholder path, skipped"
            continue
        if cli.endswith((".py", ".js", ".mjs", ".ts", ".sh")):
            # a referenced script path: does it exist relative to the skill?
            cand = [Path(skill_dir) / cli, Path(cli).expanduser()]
            cand += [Path(skill_dir) / "scripts" / Path(cli).name]
            cand += [a / cli for a in list(Path(skill_dir).parents)[:3]]
            cand += [a / "scripts" / Path(cli).name for a in list(Path(skill_dir).parents)[:3]]
            ok = any(c.is_file() for c in cand)
            checks["clis"][cli] = "found" if ok else "missing"
            if not ok:
                checks["problems"].append(f"script referenced but not found: {cli}")
            continue
        if head in {"npx", "uvx", "bunx", "pnpx"}:
            # runner exists? package itself is fetched on demand
            checks["clis"][cli] = "runner-ok" if shutil.which(head) else f"{head} missing"
            continue
        path = shutil.which(head)
        checks["clis"][cli] = "found" if path else "missing"
        if not path:
            hint = " (from a shell block; could be parser noise - verify)" if cli in sk["clis_unresolved"] else ""
            checks["problems"].append(f"CLI not on PATH: {head}{hint}")

    for rel in sk["scripts"]:
        p = Path(skill_dir) / rel
        if re.search(r"(^|/)(tests?|__tests__|spec)/|(^|/)test_[^/]*$|_test\.py$", rel):
            checks["scripts"][rel] = "test file, skipped"
            continue
        if p.suffix == ".py":
            code, out = run([sys.executable, "-I", "-m", "py_compile", str(p)])
            status = "syntax-ok" if code == 0 else f"syntax-error: {out}"
            # top-level imports
            src_py = p.read_text(errors="replace")
            mods = set(re.findall(r"^\s*from +([A-Za-z_]\w*)(?:\.[\w.]+)? +import\b", src_py, re.M))
            mods |= set(re.findall(r"^\s*import +([A-Za-z_]\w*)(?:\.[\w.]+)?\s*(?:as \w+)?\s*$", src_py, re.M))
            stdlib = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else set()
            # Modules shipped with the skill (or its plugin/repo): look in the
            # script's folder and up to three levels above the skill folder.
            local_names: set[str] = set()
            anc = p.parent
            stop = Path(skill_dir).parents[min(2, len(Path(skill_dir).parents) - 1)]
            while True:
                try:
                    local_names |= {q.stem for q in anc.iterdir()} | {q.name for q in anc.iterdir() if q.is_dir()}
                except OSError:
                    pass
                if anc == stop or anc == anc.parent:
                    break
                anc = anc.parent
            for m in sorted(mods - stdlib - {"__future__"}):
                if m in checks["py_imports"] or m in local_names:
                    continue  # sibling module shipped with the skill
                c, _ = run([sys.executable, "-I", "-c", f"import {m}"])
                checks["py_imports"][m] = "importable" if c == 0 else "missing"
                if c != 0:
                    checks["problems"].append(f"python module not importable: {m} (used by {rel})")
        elif p.suffix == ".sh":
            code, out = run(["bash", "-n", str(p)])
            status = "syntax-ok" if code == 0 else f"syntax-error: {out}"
        elif p.suffix in {".js", ".mjs"}:
            code, out = run(["node", "--check", str(p)])
            status = "syntax-ok" if code == 0 else f"syntax-error: {out}"
        else:
            status = "not-checked"
        if status.startswith("syntax-error"):
            checks["problems"].append(f"{rel}: {status}")
        if smoke and status == "syntax-ok" and p.suffix in {".py", ".sh", ".js", ".mjs"}:
            src = p.read_text(errors="replace")
            if "--help" in src or "argparse" in src or "getopts" in src:
                runner = {"py": [sys.executable, "-I"], "sh": ["bash"], "js": ["node"], "mjs": ["node"]}[p.suffix[1:]]
                code, out = run(runner + [str(p), "--help"], timeout=15, cwd=skill_dir)
                status += f"; smoke --help {'ok' if code == 0 else 'failed: ' + out[:200]}"
                if code != 0:
                    checks["problems"].append(f"{rel}: --help exited {code}")
        checks["scripts"][rel] = status

    return checks


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def to_markdown(result: dict) -> str:
    lines = []
    env = result["environment"]
    cs = env["current_session"]
    lines.append(f"Machine: {env['os']} · generated {result['generated_at']}")
    lines.append(f"Current session: host={cs['host'] or 'unknown'} surface={cs['surface'] or 'unknown'} ({', '.join(cs['evidence']) or 'no signals'})")
    prof = env.get("profile")
    lines.append(f"Profile: {PROFILE_PATH if prof else 'none (ask the user which surfaces they use)'}")
    lines.append("")
    lines.append("| Host | Installed surfaces | Version |")
    lines.append("|---|---|---|")
    for h in env["hosts"]:
        if h["installed"] or h["config_present"]:
            surf = ", ".join(f"{k}" for k in h["surfaces"]) or "config folder only (not installed)"
            lines.append(f"| {h['name']} | {surf} | {h['version'] or '—'} |")
    lines.append("")
    lines.append("| # | Skill | Root kind | Loaded by | Modified | CLIs / packages | Problems |")
    lines.append("|---|---|---|---|---|---|---|")
    for i, s in enumerate(result["skills"], 1):
        deps = ", ".join(s.get("clis", []) + [f"{x}?" for x in s.get("clis_unresolved", [])] + [f"pkg:{x}" for x in s.get("packages", [])]) or "—"
        probs = "; ".join(s.get("checks", {}).get("problems", [])) or ("—" if "checks" in s else "not checked")
        kind = s["kind"] + (f" ({s['plugin']})" if s.get("plugin") else "") + (" NESTED" if s.get("nested") else "")
        readers = ", ".join(s.get("readers_installed") or []) or "**none installed**"
        lines.append(f"| {i} | `{s['name']}` | {kind} | {readers} | {s.get('last_modified')} | {deps} | {probs} |")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env", action="store_true", help="print only the environment (hosts, surfaces, current session)")
    ap.add_argument("--save-profile", metavar="SPEC",
                    help="save which hosts/surfaces the user really uses, e.g. 'claude-code=desktop,cli;codex=ide' "
                         f"(written to {PROFILE_PATH})")
    ap.add_argument("--host", action="append", help="limit to these host ids (repeatable); see hosts.json")
    ap.add_argument("--project", type=Path, default=Path.cwd(), help="project root for project-level skill dirs (default: cwd)")
    ap.add_argument("--no-project", action="store_true", help="skip project-level skill dirs")
    ap.add_argument("--no-home-scan", action="store_true", help="do not sweep $HOME for unregistered skill dirs")
    ap.add_argument("--extra-root", type=Path, action="append", default=[], help="another skills dir to include (repeatable)")
    ap.add_argument("--include-managed", action="store_true", help="include vendor-managed skills (Anthropic-synced, Codex .system, Antigravity builtin)")
    ap.add_argument("--only", help="name or path substring of a single skill")
    ap.add_argument("--check", action="store_true", help="check CLIs, script syntax, python imports")
    ap.add_argument("--smoke", action="store_true", help="with --check: run scripts with --help (15 s timeout)")
    ap.add_argument("--md", action="store_true", help="print Markdown instead of JSON")
    ap.add_argument("--out", type=Path, help="also write JSON to this file")
    args = ap.parse_args()

    reg = load_registry()
    if args.save_profile:
        known = {h["id"] for h in reg["hosts"]}
        surfaces_ok = {"cli", "desktop", "ide", "cloud", "sdk"}
        prof: dict = {"hosts": {}, "updated": dt.date.today().isoformat()}
        for part in filter(None, (x.strip() for x in args.save_profile.split(";"))):
            hid, _, surf = part.partition("=")
            hid = hid.strip()
            vals = [v.strip() for v in surf.split(",") if v.strip()]
            if hid not in known or not set(vals) <= surfaces_ok:
                ap.error(f"bad profile entry {part!r}: host must be one of {sorted(known)}, surfaces of {sorted(surfaces_ok)}")
            prof["hosts"][hid] = vals
        PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROFILE_PATH.write_text(json.dumps(prof, indent=2) + "\n")
        print(f"saved {PROFILE_PATH}: {prof['hosts']}")
        return 0
    hosts = detect_hosts(reg)
    env = {
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python": sys.version.split()[0],
        "node": run(["node", "--version"])[1] if shutil.which("node") else None,
        "current_session": current_session(),
        "profile": load_profile(),
        "profile_path": str(PROFILE_PATH),
        "hosts": hosts,
    }
    if args.env:
        print(json.dumps(env, indent=2, ensure_ascii=False))
        return 0

    only_hosts = set(args.host) if args.host else None
    roots = build_roots(reg, hosts, None if args.no_project else args.project, only_hosts)
    for extra in args.extra_root:
        extra = extra.expanduser()
        roots.setdefault(str(extra.resolve()), {"path": str(extra), "kind": "extra", "readers": [], "readers_installed": []})
    if not args.no_home_scan and not only_hosts:
        roots.update(home_sweep(reg, roots, hosts))

    entries = discover(roots)
    if not args.include_managed:
        entries = [e for e in entries if not e.get("managed")]
    if args.only:
        q = args.only.lower()
        entries = [e for e in entries if q in Path(e["skill_file"]).parent.name.lower() or q in e["skill_file"].lower()]

    # Same file reached through two roots (symlinks): keep one entry, merge readers.
    seen: dict[str, dict] = {}
    unique: list[dict] = []
    for e in entries:
        real = str(Path(e["skill_file"]).resolve())
        if real in seen:
            first = seen[real]
            first["readers"] = sorted(set(first["readers"]) | set(e["readers"]))
            first["readers_installed"] = sorted(set(first["readers_installed"]) | set(e["readers_installed"]))
            first.setdefault("also_at", []).append(e["skill_file"])
            continue
        seen[real] = e
        unique.append(e)

    skills = []
    for e in unique:
        try:
            s = analyse_skill(e)
        except Exception as ex:  # keep going; report the failure
            s = {**e, "name": Path(e["skill_file"]).parent.name, "error": f"{type(ex).__name__}: {ex}"}
        if args.check and "error" not in s:
            s["checks"] = check_skill(s, args.smoke)
        try:
            s["sha1"] = hashlib.sha1(Path(e["skill_file"]).read_bytes()).hexdigest()[:12]
        except OSError:
            s["sha1"] = None
        if not s.get("readers_installed") and not s.get("nested"):
            s.setdefault("flags", []).append("no installed host loads this root")
        if s.get("nested"):
            s.setdefault("flags", []).append("nested: hosts never load it")
        skills.append(s)

    # Same name in several places: identical copies vs diverged copies.
    by_name: dict[str, list[dict]] = {}
    for s in skills:
        by_name.setdefault(s["name"], []).append(s)
    for name, group in by_name.items():
        if len(group) < 2:
            continue
        for s in group:
            s["duplicates"] = [{"path": o["skill_file"], "kind": o["kind"], "same_content": o["sha1"] == s["sha1"],
                                "last_modified": o.get("last_modified")} for o in group if o is not s]

    result = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "environment": env,
        "roots": sorted(roots.values(), key=lambda r: r["path"]),
        "count": len(skills),
        "skills": skills,
    }
    if args.out:
        args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    if args.md:
        print(to_markdown(result))
    elif not args.out:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"wrote {args.out} ({len(skills)} skills from {len(roots)} roots)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
