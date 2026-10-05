#!/usr/bin/env python3
"""AI tool registry for Law 38 (#115): a risk tier (1-4) and an owner
for every MCP server, desktop extension and plugin.

Two files with the same shape; the project file wins over the personal
one for the same key:
    ~/.design-forge/ai-tools.json        personal, gitignored
    <project>/.claude/ai-tools.json      shared, committed

    {"version": 1, "tools": {"mcp:gmail": {"tier": 2, "owner": "alice",
        "label": "Mail", "overrides": {"send_message": 3}}}}

An unclassified tool, an entry that fails validation or a duplicated
key counts as tier 3, and an invalid project entry never falls through
to a lower personal one: a mistake never silently lowers a tier.

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
import re
import stat
import sys
import tempfile
from datetime import date

KINDS = ("mcp", "extension", "plugin")
TIERS = (1, 2, 3, 4)
DEFAULT_TIER = 3
MASKED = "[masked]"
BROKEN = "*"  # in resolve(): the project file is broken, so every tool is unclassified
_DUPLICATES = "\0duplicates"

# Law 14 patterns. Shared with ai_inventory.py; anything matching is
# masked in output and refused in the registry.
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"\b(ghp|gho|github_pat|glpat|xoxb|xoxp)_[A-Za-z0-9_-]{10,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*\S{16,}"),
]


def looks_secret(text: str) -> bool:
    return any(p.search(text) for p in SECRET_PATTERNS)


def personal_path() -> str:
    return os.path.join(os.path.expanduser("~"), ".design-forge", "ai-tools.json")


def project_path(project: str) -> str:
    return os.path.join(project, ".claude", "ai-tools.json")


def parse_key(key: str) -> tuple[str, str]:
    kind, sep, name = key.partition(":")
    if not sep or kind not in KINDS or not name:
        raise ValueError(f"key must be <kind>:<name> with kind one of {', '.join(KINDS)}: {key!r}")
    if name == MASKED:
        raise ValueError(f"{MASKED} stands for a name hidden because it looked like a secret; it can't be classified")
    return kind, name


def valid_tier(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value in TIERS


def has_duplicates(obj) -> bool:
    """True if any object anywhere in a parsed file repeated a key."""
    if isinstance(obj, dict):
        return _DUPLICATES in obj or any(has_duplicates(v) for v in obj.values())
    if isinstance(obj, list):
        return any(has_duplicates(v) for v in obj)
    return False


def entry_problem(entry) -> str | None:
    if not isinstance(entry, dict):
        return "not an object"
    if has_duplicates(entry):
        return "a field is listed more than once"
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


def _pairs(pairs: list) -> dict:
    """json object hook that remembers duplicated keys instead of
    silently keeping the last one."""
    obj, dups = {}, set()
    for k, v in pairs:
        if k in obj:
            dups.add(k)
        obj[k] = v
    if dups:
        obj[_DUPLICATES] = sorted(dups)
    return obj


def load(path: str) -> tuple[dict, set, list[str]]:
    """(valid entries, invalid keys, problems) for one registry file.
    Invalid keys (a failed check or a duplicate) count as unclassified.
    A file that can't be read as a registry returns invalid = {BROKEN}.
    A missing file is simply empty."""
    if not os.path.isfile(path):
        return {}, set(), []
    try:
        with open(path) as f:
            data = json.load(f, object_pairs_hook=_pairs)
    except (OSError, ValueError) as e:
        return {}, {BROKEN}, [f"{path}: {e.__class__.__name__}"]
    if isinstance(data, dict) and _DUPLICATES in data:
        return {}, {BROKEN}, [f"{path}: a top-level key is listed more than once"]
    tools = data.get("tools") if isinstance(data, dict) else None
    if not isinstance(tools, dict):
        return {}, {BROKEN}, [f"{path}: no \"tools\" object"]
    duplicates = set(tools.pop(_DUPLICATES, []))
    valid, invalid, problems = {}, set(), []
    for key, entry in tools.items():
        problem = "listed more than once" if key in duplicates else entry_problem(entry)
        try:
            parse_key(key)
        except ValueError as e:
            problem = str(e)
        if problem:
            invalid.add(key)
            problems.append(f"{path}: {key}: {problem} (treated as unclassified)")
        else:
            valid[key] = entry
    return valid, invalid, problems


def resolve(project: str | None) -> tuple[dict, list[str]]:
    """Every key in either file, mapped to (entry, path). The project file
    wins, and an invalid entry maps to (None, path): it stays unclassified
    and never falls through to a lower personal entry."""
    resolved: dict = {}
    problems: list[str] = []
    personal = personal_path()
    for path in [personal] + ([project_path(project)] if project else []):
        valid, invalid, found = load(path)
        problems += found
        if BROKEN in invalid:
            if path == personal:
                continue  # a broken personal file just has no entries
            # A broken project file must not let personal entries stand
            # in for the team's: every tool is unclassified until fixed.
            problems.append(f"{path}: every tool counts as unclassified (tier 3) until this file is fixed")
            return {BROKEN: (None, path)}, problems
        resolved.update({k: (v, path) for k, v in valid.items()})
        resolved.update({k: (None, path) for k in invalid})
    return resolved, problems


def lookup(kind: str, name: str, project: str | None) -> tuple[dict | None, str | None, list[str]]:
    """The entry for a tool. Returns (entry, path, problems); entry is
    None when unclassified or invalid."""
    resolved, problems = resolve(project)
    entry, path = resolved.get(f"{kind}:{name}") or resolved.get(BROKEN) or (None, None)
    return entry, path, problems


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
    for text in [key, owner, label or "", note or ""] + list(overrides or {}):
        if looks_secret(text):
            raise ValueError("a value looks like a secret (Law 14); the registry stores names only")
    path = os.path.realpath(path)  # write through a symlink, not over it

    data = {"version": 1, "tools": {}}
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f, object_pairs_hook=_pairs)
        except (OSError, ValueError) as e:
            raise ValueError(f"won't overwrite {path}: it can't be parsed ({e.__class__.__name__}); fix it first")
        if has_duplicates(data):
            raise ValueError(f"won't overwrite {path}: a key is listed more than once; fix it first")
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
    problem = entry_problem(entry)
    if problem:
        raise ValueError(f"{key} would still be invalid after this change ({problem}); fix it in {path}")
    data["tools"][key] = entry

    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    if os.path.exists(path):
        mode = stat.S_IMODE(os.stat(path).st_mode)
    else:
        umask = os.umask(0)
        os.umask(umask)
        mode = 0o666 & ~umask
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".ai-tools.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)  # keeps the existing key order
            f.write("\n")
        os.chmod(tmp, mode)
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
    p_set.add_argument("--clear-overrides", action="store_true")
    where = p_set.add_mutually_exclusive_group(required=True)
    where.add_argument("--personal", action="store_true")
    where.add_argument("--project")

    p_show = sub.add_parser("show", help="print a tool's tier and owner")
    p_show.add_argument("key")
    p_show.add_argument("--project")

    args = parser.parse_args(argv)
    try:
        if args.command == "set":
            if args.project is not None and not os.path.isdir(args.project):
                raise ValueError(f"--project must be an existing folder (the repo root): {args.project}")
            path = personal_path() if args.personal else project_path(args.project)
            overrides = parse_overrides(args.override) if args.override is not None else None
            if args.clear_overrides:
                overrides = {}
            entry = set_entry(path, args.key, args.tier, args.owner, args.label, args.note, overrides)
            print(f"{args.key}: tier {entry['tier']}, owner {entry['owner']} → {path}")
            return 0
        kind, name = parse_key(args.key)
        entry, path, problems = lookup(kind, name, args.project)
        for problem in problems:
            print(f"warning: {problem}", file=sys.stderr)
        if entry is None:
            print(f"{args.key}: unclassified (tier {DEFAULT_TIER})" + (f" — invalid entry in {path}" if path else ""))
        else:
            extra = ", ".join(f"{t} → {v}" for t, v in sorted(entry.get("overrides", {}).items()))
            label = f" ({entry['label']})" if entry.get("label") else ""
            print(f"{args.key}{label}: tier {entry['tier']}, owner {entry['owner']}"
                  + (f", overrides {extra}" if extra else "") + f" ({path})")
        return 0
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
