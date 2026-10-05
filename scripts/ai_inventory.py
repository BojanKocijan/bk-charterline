#!/usr/bin/env python3
"""AI inventory (#114): every MCP server, extension, plugin, skill,
agent, hook and permission rule a Claude Code session can use.

Writes ~/.design-forge/ai-inventory.md (also printed) and keeps
first-seen dates in ~/.design-forge/ai-inventory.json, so a re-run marks
what is new or removed since the last one.

Only names are read, never secrets: MCP `args`, `env`, `headers` and URL
paths are never touched, and the desktop app's `config.json` (OAuth
token caches) is never opened. claude.ai account connectors are not in
any local file, so the session passes their names with --session.

Usage: ai_inventory.py [--project PATH] [--session NAME ...]
Dependency-free stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from datetime import date
from urllib.parse import urlparse

# Law 14 patterns: anything matching is shown as [masked].
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"\b(ghp|gho|github_pat|glpat|xoxb|xoxp)_[A-Za-z0-9_-]{10,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*\S{16,}"),
]

SECTIONS = [
    ("mcp", "MCP servers"),
    ("extension", "Desktop extensions"),
    ("plugin", "Plugins"),
    ("skill", "Skills"),
    ("agent", "Agents"),
    ("hook", "Hooks"),
    ("permission", "Permission rules"),
]


def home() -> str:
    return os.path.expanduser("~")


def tilde(path: str) -> str:
    for h in (home(), os.path.realpath(home())):
        if path == h or path.startswith(h + os.sep):
            return "~" + path[len(h):]
    return path


def mask(text: str) -> str:
    return "[masked]" if any(p.search(text) for p in SECRET_PATTERNS) else text


class Inventory:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}
        self.problems: list[str] = []

    def add(self, kind: str, scope: str, name: str, detail: str, source: str) -> None:
        name, detail = mask(str(name)), mask(str(detail))
        key = f"{kind}|{scope}|{name}"
        self.items.setdefault(key, {
            "kind": kind, "scope": scope, "name": name,
            "detail": detail, "source": tilde(source),
        })

    def load_json(self, path: str):
        if not os.path.isfile(path):
            return None
        try:
            with open(path) as f:
                return json.load(f)
        except (OSError, ValueError):
            self.problems.append(tilde(path))
            return None


def server_detail(cfg) -> str:
    """Transport plus the executable's basename or the URL host. Never
    args, env, headers or URL paths."""
    if not isinstance(cfg, dict):
        return "?"
    url = cfg.get("url")
    kind = cfg.get("type") or ("http" if url else "stdio")
    if url or kind in ("http", "sse"):
        host = urlparse(url).hostname if isinstance(url, str) else None
        return f"{kind} · {host or '?'}"
    cmd = cfg.get("command")
    return f"stdio · {os.path.basename(cmd) if isinstance(cmd, str) else '?'}"


def add_servers(inv: Inventory, servers, scope: str, source: str, note=lambda name: "") -> None:
    if isinstance(servers, dict):
        for name, cfg in servers.items():
            inv.add("mcp", scope, name, server_detail(cfg) + note(name), source)


def hook_script(command: str) -> str:
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    for t in tokens:
        if t.endswith((".py", ".sh", ".js", ".ts")) or "/" in t:
            return os.path.basename(t)
    return os.path.basename(tokens[0]) if tokens else "?"


def collect_settings(inv: Inventory, path: str, scope: str) -> None:
    data = inv.load_json(path)
    if not isinstance(data, dict):
        return
    plugins = data.get("enabledPlugins")
    if isinstance(plugins, dict):
        for name, on in plugins.items():
            inv.add("plugin", scope, name, "enabled" if on else "disabled", path)
    elif isinstance(plugins, list):
        for name in plugins:
            inv.add("plugin", scope, name, "enabled", path)
    hooks = data.get("hooks")
    if isinstance(hooks, dict):
        for event, groups in hooks.items():
            for group in groups if isinstance(groups, list) else []:
                if not isinstance(group, dict):
                    continue
                matcher = group.get("matcher") or "*"
                for h in group.get("hooks", []):
                    cmd = h.get("command", "") if isinstance(h, dict) else ""
                    inv.add("hook", scope, f"{event} · {matcher} · {hook_script(cmd)}",
                            h.get("type", "command") if isinstance(h, dict) else "?", path)
    perms = data.get("permissions")
    if isinstance(perms, dict):
        for verdict in ("allow", "ask", "deny"):
            for rule in perms.get(verdict, []) or []:
                inv.add("permission", scope, rule, verdict, path)


def collect_dir_entries(inv: Inventory, folder: str, kind: str, scope: str) -> None:
    if not os.path.isdir(folder):
        return
    for entry in sorted(os.listdir(folder)):
        if entry.startswith("."):
            continue
        path = os.path.join(folder, entry)
        if kind == "agent" and not entry.endswith(".md"):
            continue
        detail = f"→ {tilde(os.path.realpath(path))}" if os.path.islink(path) else "local"
        inv.add(kind, scope, entry[:-3] if kind == "agent" else entry, detail, folder)


def desktop_dir() -> str:
    mac = os.path.join(home(), "Library", "Application Support", "Claude")
    return mac if os.path.isdir(mac) else os.path.join(home(), ".config", "Claude")


def collect(project: str, session: list[str] | None) -> Inventory:
    inv = Inventory()
    h = home()
    project = os.path.realpath(project)

    claude_json = os.path.join(h, ".claude.json")
    data = inv.load_json(claude_json)
    if isinstance(data, dict):
        add_servers(inv, data.get("mcpServers"), "user", claude_json)
        projects = data.get("projects") if isinstance(data.get("projects"), dict) else {}
        for path, cfg in projects.items():
            if isinstance(cfg, dict):
                add_servers(inv, cfg.get("mcpServers"), "local", f"{claude_json} ({tilde(path)})")
        for plugin_id in (data.get("pluginUsage") or {}):
            inv.add("plugin", "desktop", plugin_id, "used", claude_json)
        this = projects.get(project) if isinstance(projects.get(project), dict) else {}
        enabled = set(this.get("enabledMcpjsonServers") or [])
        disabled = set(this.get("disabledMcpjsonServers") or [])
    else:
        enabled, disabled = set(), set()

    mcp_json = os.path.join(project, ".mcp.json")
    project_mcp = inv.load_json(mcp_json)
    if isinstance(project_mcp, dict):
        add_servers(inv, project_mcp.get("mcpServers"), "project", mcp_json,
                    lambda n: " · disabled" if n in disabled else (" · enabled" if n in enabled else ""))

    desk = desktop_dir()
    desk_cfg_path = os.path.join(desk, "claude_desktop_config.json")
    desk_cfg = inv.load_json(desk_cfg_path)
    if isinstance(desk_cfg, dict):
        add_servers(inv, desk_cfg.get("mcpServers"), "desktop", desk_cfg_path)
    ext_dir = os.path.join(desk, "Claude Extensions")
    if os.path.isdir(ext_dir):
        for ext in sorted(os.listdir(ext_dir)):
            manifest = inv.load_json(os.path.join(ext_dir, ext, "manifest.json"))
            if isinstance(manifest, dict):
                inv.add("extension", "desktop", manifest.get("name") or ext,
                        f"v{manifest.get('version', '?')}", os.path.join(ext_dir, ext))

    installed = inv.load_json(os.path.join(h, ".claude", "plugins", "installed_plugins.json"))
    if isinstance(installed, dict):
        names = installed.get("plugins") if isinstance(installed.get("plugins"), dict) else installed
        for name in names:
            if name != "version":
                inv.add("plugin", "user", name, "installed",
                        os.path.join(h, ".claude", "plugins", "installed_plugins.json"))

    for path, scope in (
        (os.path.join(h, ".claude", "settings.json"), "user"),
        (os.path.join(project, ".claude", "settings.json"), "project"),
        (os.path.join(project, ".claude", "settings.local.json"), "local"),
    ):
        collect_settings(inv, path, scope)

    for base, scope in ((os.path.join(h, ".claude"), "user"), (os.path.join(project, ".claude"), "project")):
        collect_dir_entries(inv, os.path.join(base, "skills"), "skill", scope)
        collect_dir_entries(inv, os.path.join(base, "agents"), "agent", scope)

    for name in session or []:
        inv.add("mcp", "session", name, "connected in this session", "Claude session tools")
    return inv


def cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render(inv: Inventory, state: dict, first_run: bool, project: str, session) -> tuple[str, dict]:
    today = date.today().isoformat()
    new_state = {k: {"first_seen": state.get(k, {}).get("first_seen", today)} for k in inv.items}
    if session is None:
        # Without --session, connectors are unknown, not gone: keep them.
        new_state.update({k: v for k, v in state.items() if k.startswith("mcp|session|")})
    new_keys = [] if first_run else [k for k in inv.items if k not in state]
    removed = sorted(k for k in state if k not in new_state)

    lines = [
        "# AI inventory",
        "",
        f"Generated {today} · Project `{tilde(os.path.realpath(project))}` · "
        + (f"Session servers: {len(session)}" if session is not None
           else "**Session servers not provided** — account connectors are missing; "
                "run via the `ai inventory` trigger"),
        "",
        f"{len(inv.items)} items"
        + (" (first run)" if first_run else f" · {len(new_keys)} new · {len(removed)} removed"),
    ]
    for kind, title in SECTIONS:
        rows = [k for k, v in inv.items.items() if v["kind"] == kind]
        lines += ["", f"## {title}", ""]
        if not rows:
            lines.append("_None found._")
            continue
        lines += ["| Name | Scope | Detail | Source | First seen | |", "|---|---|---|---|---|---|"]
        for k in sorted(rows, key=lambda k: (inv.items[k]["scope"], inv.items[k]["name"].lower())):
            v = inv.items[k]
            lines.append(
                f"| {cell(v['name'])} | {v['scope']} | {cell(v['detail'])} | {cell(v['source'])} "
                f"| {new_state[k]['first_seen']} | {'**new**' if k in new_keys else ''} |"
            )
    if removed:
        lines += ["", "## Removed since last run", ""]
        lines += [f"- {cell(k.replace('|', ' · '))}" for k in removed]
    if inv.problems:
        lines += ["", "## Couldn't parse", ""] + [f"- `{p}`" for p in inv.problems]
    return "\n".join(lines) + "\n", new_state


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="List every AI tool a Claude Code session can use.")
    parser.add_argument("--project", default=os.getcwd())
    parser.add_argument("--session", nargs="*", default=None,
                        help="MCP server names from the session's own tool list")
    args = parser.parse_args(argv)

    out_dir = os.path.join(home(), ".design-forge")
    state_path = os.path.join(out_dir, "ai-inventory.json")
    inv = collect(args.project, args.session)
    previous = inv.load_json(state_path)
    first_run = not isinstance(previous, dict)
    markdown, new_state = render(inv, previous if not first_run else {}, first_run,
                                 args.project, args.session)
    print(markdown, end="")
    try:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "ai-inventory.md"), "w") as f:
            f.write(markdown)
        with open(state_path, "w") as f:
            json.dump(new_state, f, indent=1, sort_keys=True)
    except OSError as e:
        print(f"Couldn't write the inventory to {tilde(out_dir)}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
