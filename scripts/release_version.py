#!/usr/bin/env python3
"""Check that a release's version agrees everywhere (Law 27, #116).

    python3 scripts/release_version.py check

Run from the repo root. Reads the `**Version:**` line of CLAUDE_LAWS.md
and checks it against `.claude-plugin/plugin.json`, both versions in
`.claude-plugin/marketplace.json` and a `## vX.Y.Z` heading in
RELEASES.md. Prints the version and exits 0 when they agree; otherwise
names each file that disagrees and exits 1. The release-tag workflow
tags only a version this accepts.

Dependency-free stdlib only.
"""
from __future__ import annotations

import json
import re
import sys

LAWS = "CLAUDE_LAWS.md"
PLUGIN = ".claude-plugin/plugin.json"
MARKETPLACE = ".claude-plugin/marketplace.json"
RELEASES = "RELEASES.md"
VERSION_RE = re.compile(r"^\*\*Version:\*\* *(\d+\.\d+\.\d+)\s*$", re.MULTILINE)


def read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def check() -> tuple[str | None, list[str]]:
    """(version, problems). The version is None when CLAUDE_LAWS.md has none."""
    try:
        m = VERSION_RE.search(read(LAWS))
    except OSError as e:
        return None, [f"{LAWS}: can't read it ({e.strerror})"]
    if not m:
        return None, [f"{LAWS}: no `**Version:** X.Y.Z` line"]
    version, problems = m.group(1), []

    found: list[tuple[str, object]] = []
    for path, pick in (
        (PLUGIN, lambda d: [("version", d.get("version"))]),
        (MARKETPLACE, lambda d: [("metadata.version", (d.get("metadata") or {}).get("version"))]
         + [(f"plugins[{i}].version", p.get("version")) for i, p in enumerate(d.get("plugins") or [])]),
    ):
        try:
            data = json.loads(read(path))
            found += [(f"{path} {field}", value) for field, value in pick(data)]
        except (OSError, ValueError, AttributeError) as e:
            problems.append(f"{path}: can't read it ({e.__class__.__name__})")
    for where, value in found:
        if value != version:
            problems.append(f"{where} is {value!r}, expected {version!r}")

    try:
        if not re.search(rf"^## v{re.escape(version)}(\s|$)", read(RELEASES), re.MULTILINE):
            problems.append(f"{RELEASES}: no `## v{version}` heading")
    except OSError as e:
        problems.append(f"{RELEASES}: can't read it ({e.strerror})")
    return version, problems


def main(argv: list[str]) -> int:
    if argv != ["check"]:
        print("usage: release_version.py check", file=sys.stderr)
        return 2
    version, problems = check()
    if problems:
        for p in problems:
            print(p, file=sys.stderr)
        return 1
    print(version)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
