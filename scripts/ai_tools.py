#!/usr/bin/env python3
"""AI tool registry for Law 38 (#115): a risk tier (1-4) and an owner
for every MCP server, desktop extension and plugin.

Two files with the same shape; the project file wins over the personal
one for the same key:
    ~/.design-forge/ai-tools.json        personal, gitignored
    <project>/.claude/ai-tools.json      shared, committed

    {"version": 1, "tools": {"mcp:gmail": {"tier": 2, "owner": "alice",
        "label": "Mail", "overrides": {"send_message": 3}}}}

An unclassified tool, or an entry that fails validation, counts as
tier 3 — a mistake never silently lowers a tool to tier 1.

CLI (used by the `ai classify` trigger after the user approves):
    ai_tools.py set mcp:gmail --tier 2 --owner alice [--label Mail]
        [--note TEXT] [--override send_message=3 ...] (--personal | --project PATH)
    ai_tools.py show mcp:gmail [--project PATH]

Dependency-free stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import date

KINDS = ("mcp", "extension", "plugin")
TIERS = (1, 2, 3, 4)
DEFAULT_TIER = 3


def personal_path() -> str:
    return os.path.join(os.path.expanduser("~"), ".design-forge", "ai-tools.json")


def project_path(project: str) -> str:
    return os.path.join(project, ".claude", "ai-tools.json")


def parse_key(key: str) -> tuple[str, str]:
    kind, sep, name = key.partition(":")
    if not sep or kind not in KINDS or not name:
        raise ValueError(f"key must be <kind>:<name> with kind one of {', '.join(KINDS)}: {key!r}")
    return kind, name


def valid_tier(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value in TIERS


def entry_problem(entry) -> str | None:
    if not isinstance(entry, dict):
        return "not an object"
    if not valid_tier(entry.get("tier")):
        return f"tier must be 1-4, got {entry.get('tier')!r}"
    if not isinstance(entry.get("owner"), str) or not entry["owner"].strip():
        return "owner is missing"
    overrides = entry.get("overrides", {})
    if not isinstance(overrides, dict) or not all(
        isinstance(k, str) and valid_tier(v) for k, v in overrides.items()
    ):
        return "overrides must map tool names to tiers 1-4"
    return None


def load(path: str) -> tuple[dict, list[str]]:
    """Valid entries keyed `<kind>:<name>`, plus a problem per broken file
    or invalid entry. A missing file is simply empty."""
    if not os.path.isfile(path):
        return {}, []
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        return {}, [f"{path}: {e.__class__.__name__}"]
    tools = data.get("tools") if isinstance(data, dict) else None
    if not isinstance(tools, dict):
        return {}, [f"{path}: no \"tools\" object"]
    valid, problems = {}, []
    for key, entry in tools.items():
        problem = entry_problem(entry)
        try:
            parse_key(key)
        except ValueError as e:
            problem = str(e)
        if problem:
            problems.append(f"{path}: {key}: {problem} (treated as unclassified)")
        else:
            valid[key] = entry
    return valid, problems


def lookup(kind: str, name: str, project: str | None) -> tuple[dict | None, str | None, list[str]]:
    """The entry for a tool, project file first. Returns (entry, path, problems)."""
    key = f"{kind}:{name}"
    problems: list[str] = []
    for path in ([project_path(project)] if project else []) + [personal_path()]:
        tools, found = load(path)
        problems += found
        if key in tools:
            return tools[key], path, problems
    return None, None, problems


def tier_for(entry: dict | None, tool: str | None = None) -> int:
    if entry is None:
        return DEFAULT_TIER
    if tool is not None and tool in entry.get("overrides", {}):
        return entry["overrides"][tool]
    return entry["tier"]


def set_entry(path: str, key: str, tier: int, owner: str, label: str | None = None,
              note: str | None = None, overrides: dict | None = None) -> dict:
    """Add or update one entry, keeping every other entry and any field
    the user added by hand. Refuses to touch a file it can't parse."""
    parse_key(key)
    if not valid_tier(tier):
        raise ValueError(f"tier must be 1-4, got {tier!r}")
    if not owner or not owner.strip():
        raise ValueError("owner is required")
    if overrides is not None and not all(valid_tier(v) for v in overrides.values()):
        raise ValueError("override tiers must be 1-4")

    data = {"version": 1, "tools": {}}
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            raise ValueError(f"won't overwrite {path}: it can't be parsed ({e.__class__.__name__}); fix it first")
        if not isinstance(data, dict) or not isinstance(data.setdefault("tools", {}), dict):
            raise ValueError(f"won't overwrite {path}: no \"tools\" object; fix it first")

    entry = data["tools"].get(key) if isinstance(data["tools"].get(key), dict) else {}
    entry.update({"tier": tier, "owner": owner.strip(), "classified": date.today().isoformat()})
    if label is not None:
        entry["label"] = label
    if note is not None:
        entry["note"] = note
    if overrides is not None:
        entry["overrides"] = overrides
    data["tools"][key] = entry

    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".ai-tools.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return entry


def parse_overrides(pairs: list[str]) -> dict:
    overrides = {}
    for pair in pairs:
        tool, sep, value = pair.partition("=")
        if not sep or not tool or not value.isdigit():
            raise ValueError(f"override must be tool=tier, got {pair!r}")
        overrides[tool] = int(value)
    return overrides


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Law 38 AI tool registry")
    sub = parser.add_subparsers(dest="command", required=True)

    p_set = sub.add_parser("set", help="record an approved classification")
    p_set.add_argument("key")
    p_set.add_argument("--tier", type=int, required=True)
    p_set.add_argument("--owner", required=True)
    p_set.add_argument("--label")
    p_set.add_argument("--note")
    p_set.add_argument("--override", action="append", default=None, metavar="TOOL=TIER")
    where = p_set.add_mutually_exclusive_group(required=True)
    where.add_argument("--personal", action="store_true")
    where.add_argument("--project")

    p_show = sub.add_parser("show", help="print a tool's tier and owner")
    p_show.add_argument("key")
    p_show.add_argument("--project")

    args = parser.parse_args(argv)
    try:
        if args.command == "set":
            path = personal_path() if args.personal else project_path(args.project)
            overrides = parse_overrides(args.override) if args.override is not None else None
            entry = set_entry(path, args.key, args.tier, args.owner, args.label, args.note, overrides)
            print(f"{args.key}: tier {entry['tier']}, owner {entry['owner']} → {path}")
            return 0
        kind, name = parse_key(args.key)
        entry, path, problems = lookup(kind, name, args.project)
        for problem in problems:
            print(f"warning: {problem}", file=sys.stderr)
        if entry is None:
            print(f"{args.key}: unclassified (tier {DEFAULT_TIER})")
        else:
            extra = ", ".join(f"{t} → {v}" for t, v in sorted(entry.get("overrides", {}).items()))
            print(f"{args.key}: tier {entry['tier']}, owner {entry['owner']}"
                  + (f", overrides {extra}" if extra else "") + f" ({path})")
        return 0
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
