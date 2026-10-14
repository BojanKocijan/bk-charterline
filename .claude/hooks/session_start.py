#!/usr/bin/env python3
"""SessionStart hook (#270): run the session-start checks so Claude doesn't.

On `startup` and `clear` it reads the rules version, the project, the
language and port in projects.yaml and PROJECT_KNOWLEDGE.md, and gives Claude
one block of context: the confirmation to print, and the steps to take when
code work starts. The network checks (newest release, GitHub login, open PRs)
come next (#270, part 1b); until then the GitHub line says `unknown`.

It only reads. Its one write is a marker in the system temp folder, so a hook
registered more than once (install.sh, the plugin, this repo) runs once per
session. Any error means no output: a SessionStart hook never blocks, and
CLAUDE.md has a fallback. Dependency-free stdlib only.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_COPY = os.path.dirname(os.path.dirname(HERE))  # the rules repo this script ships in
MAX_CHARS = 1900  # Claude Code cuts additionalContext past 10,000; stay far below
FIRST_PORT = 5173
VERSION = re.compile(r"^\*\*Version:\*\*\s*(\d+\.\d+\.\d+)", re.M)


def run(args: list[str], cwd: str | None = None) -> str | None:
    """stdout of a local command, or None when it fails."""
    try:
        done = subprocess.run(args, cwd=cwd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    except OSError:
        return None
    return done.stdout if done.returncode == 0 else None


def read(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def first_marker(session_id: object) -> bool:
    """True the first time this session runs the hook. A missing session id
    runs every time: better a doubled block than none."""
    safe = re.sub(r"[^A-Za-z0-9_-]", "", str(session_id or ""))[:100]
    if not safe:
        return True
    path = os.path.join(tempfile.gettempdir(), f"bk-charterline-session-start-{safe}")
    try:
        os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
        return True
    except FileExistsError:
        return False
    except OSError:
        return True


def rules_dirs() -> list[str]:
    """Where the rules may be: the installed clone, the plugin, this repo."""
    sys.path.insert(0, HERE)
    from rules_home import rules_home
    dirs = [rules_home()]
    if os.environ.get("CLAUDE_PLUGIN_ROOT"):
        dirs.append(os.environ["CLAUDE_PLUGIN_ROOT"])
    return dirs + [REPO_COPY]


def rules_version(dirs: list[str]) -> str | None:
    for folder in dirs:
        match = VERSION.search(read(os.path.join(folder, "CLAUDE_LAWS.md")) or "")
        if match:
            return match.group(1)
    return None


def project(cwd: str) -> tuple[str | None, str]:
    """(project root, name). The name is the main folder's, also in a worktree (Law 18)."""
    top = run(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    if top is None:
        return None, "not a git repo"
    common = (run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=cwd) or "").strip()
    main = os.path.dirname(common) if os.path.basename(common) == ".git" else top.strip()
    return top.strip(), os.path.basename(main)


def projects_yaml(home: str) -> dict | None:
    """language and projects from projects.yaml without a YAML library.
    None when the file is missing; {"broken": True} when it can't be read."""
    path = os.path.join(home, "projects.yaml")
    if not os.path.exists(path):
        return None
    text = read(path)
    if text is None:
        return {"broken": True}
    language, projects, section, keys, current = None, [], None, set(), None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line[0].isspace() and not line.startswith("-"):
            section = line.split(":", 1)[0].strip()
            keys.add(section)
            continue
        item = line.strip()
        if section == "settings" and item.startswith("language:"):
            language = item.split(":", 1)[1].strip().strip("'\"")
        elif section == "projects" and item.startswith("- name:"):
            current = {"name": item.split(":", 1)[1].strip().strip("'\""), "port": None}
            projects.append(current)
        elif section == "projects" and current is not None and item.startswith("port:"):
            try:
                current["port"] = int(item.split(":", 1)[1].strip())
            except ValueError:
                pass
    if not keys & {"settings", "projects"}:
        return {"broken": True}
    return {"language": language if language in ("english-only", "any") else None, "projects": projects}


def section(text: str, prefix: str) -> list[str]:
    """The lines under the first heading that starts with prefix, to the next heading."""
    lines, inside = [], False
    for line in text.splitlines():
        if line.startswith("#"):
            if inside:
                break
            inside = line.startswith(prefix)
        elif inside:
            lines.append(line)
    return lines


def knowledge(root: str) -> tuple[str | None, str | None] | None:
    """(the §1 line, the active feature) from PROJECT_KNOWLEDGE.md, or None when it is missing."""
    text = read(os.path.join(root, "PROJECT_KNOWLEDGE.md"))
    if text is None:
        return None
    purpose = next((l.strip() for l in section(text, "## 1.") if l.strip() and not l.strip().startswith("<!--")), None)
    feature = None
    rows = [l for l in section(text, "## 11.") if l.strip().startswith("|")]
    for row in rows[2:3]:  # header, separator, then the active row
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0] and cells[2] != "handed-off":
            feature = f"{cells[0]} · {cells[1]} · {cells[2]}"
    return purpose, feature


def short(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def build(cwd: str) -> str:
    dirs = rules_dirs()
    home = dirs[0]
    root, name = project(cwd)
    where = root or cwd
    version, registry, known = rules_version(dirs), projects_yaml(home), knowledge(where)
    user = "unknown"  # the login check comes with the network checks (#270, part 1b)
    confirm = [f"Rules loaded: BK CHARTERLINE v{version or 'unknown'}", f"Project: {name}", "Persona: Frontend",
               f"GitHub: {user}"]
    if known and known[0]:
        confirm.append(f"Knowledge: PROJECT_KNOWLEDGE.md — {short(known[0], 120)}")
    if known and known[1]:
        confirm.append(f"Feature: {short(known[1], 120)}")
    if os.path.exists(os.path.join(home, "dashboard", "index.html")):
        confirm.append("Dashboard: ~/.bk-charterline/dashboard/index.html")
    confirm.append("Ready.")

    before, settings, later = [], [], []
    broken = bool(registry and registry.get("broken"))
    if broken:
        before.append("~/.bk-charterline/projects.yaml can't be read: tell the user, don't overwrite it, and don't "
                      "start the preview until it's fixed (Law 20).")
    elif not (registry and registry["language"]):
        before.append("Language not set: ask the Law 1 question as your whole first reply instead, "
                      "and print the confirmation in the next one.")
    else:
        settings.append(f"Reply language: {registry['language']} (Law 1).")

    if root and not broken:
        entries = (registry or {}).get("projects", [])
        mine = next((p for p in entries if p["name"] == name), None)
        if mine and mine["port"]:
            settings.append(f"Preview port: {mine['port']} (Law 18).")
        else:
            port = max([p["port"] for p in entries if p["port"]] + [FIRST_PORT - 1]) + 1
            later.append(f"Register {name} in projects.yaml on port {port} (Law 20).")
    if root:
        missing = [what for f, what in (("PROJECT_KNOWLEDGE.md", "PROJECT_KNOWLEDGE.md from its template"),
                                        ("CLAUDE.md", "a one-line local CLAUDE.md (@./PROJECT_KNOWLEDGE.md)"))
                   if not os.path.exists(os.path.join(root, f))]
        if missing:
            later.append(f"Create {' and '.join(missing)} (Law 11).")
    if root:
        later.append("Pull the default branch and sweep merged branches (Laws 5, 9, 25).")
    if os.path.exists(os.path.join(where, "SESSION_NOTE.md")):
        later.insert(0, "SESSION_NOTE.md exists: summarize it in one line and ask whether to resume (Law 33).")

    def assemble() -> str:
        parts = ["BK Charterline session start (from the SessionStart hook; these checks are done, "
                 "make no tool calls for them).", "Print this confirmation as your first reply:", "", *confirm]
        if before:
            parts += ["", "Before it:", *(f"- {b}" for b in before)]
        if settings:
            parts += ["", "Apply this session:", *(f"- {s}" for s in settings)]
        if later:
            parts += ["", "When code work starts (not before):", *(f"- {s}" for s in later)]
        return "\n".join(parts)

    return assemble()[:MAX_CHARS]


def main() -> None:
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict) or event.get("source", "startup") not in ("startup", "clear"):
            return
        if not first_marker(event.get("session_id")):
            return
        cwd = event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        context = build(cwd if os.path.isdir(cwd) else os.getcwd())
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}))
    except Exception:  # noqa: BLE001  a session start must never fail because of this hook
        pass


if __name__ == "__main__":
    main()
    sys.exit(0)
