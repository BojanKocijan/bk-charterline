#!/usr/bin/env python3
"""PreToolUse hook — mechanically enforces Law 32 (CLAUDE_LAWS.md).

Reads the tool-call JSON Claude Code sends on stdin, inspects Bash
commands for a narrow set of patterns, and blocks (exit 2 + reason on
stderr) the ones that would break Law 7 (never merge / never push to
the default branch), Law 13 (Conventional Commits), or Law 14 (secret
scan before commit). Everything else passes through untouched.

Fails open: if anything here can't be parsed confidently, the call is
allowed rather than blocked on an infrastructure fluke. This is a
backstop against mechanical slips, not a replacement for the judgment
the rest of CLAUDE_LAWS.md already asks for.

Dependency-free stdlib only, so it runs anywhere Python 3 does.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys


def default_branch() -> str:
    try:
        out = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip().rsplit("/", 1)[-1]
    except Exception:
        pass
    return "main"


def current_branch() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return None


def staged_diff() -> str | None:
    try:
        out = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            return out.stdout
    except Exception:
        pass
    return None


CONVENTIONAL_COMMIT_RE = re.compile(
    r"^(feat|fix|chore|docs|refactor|test|style|perf)(\([^)]+\))?!?: .+"
)

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"\b(ghp|gho|github_pat|glpat|xoxb|xoxp)_[A-Za-z0-9_-]{10,}"),
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9+/_-]{16,}['\"]"),
]


def extract_commit_message(command: str) -> str | None:
    m = re.search(r"-m\s+(['\"])(.*?)\1", command, re.DOTALL)
    if m:
        return m.group(2)
    m = re.search(r"<<['\"]?EOF['\"]?\n(.*?)\nEOF", command, re.DOTALL)
    if m:
        return m.group(1)
    return None


def block(reason: str) -> None:
    print(reason, file=sys.stderr)
    sys.exit(2)


def check_bash(command: str) -> None:
    cmd = command.strip()

    # Law 7 — Claude never merges, under any circumstance.
    if re.search(r"\bgh\s+pr\s+merge\b", cmd):
        block(
            "Blocked (Law 7): `gh pr merge` is never run by Claude, with or "
            "without flags. Merging the default branch is exclusively the "
            "human's action in the GitHub UI."
        )
    if "mergePullRequest" in cmd:
        block(
            "Blocked (Law 7): GraphQL `mergePullRequest` is a merge — "
            "Claude never merges. Stop and let the human merge in the UI."
        )

    is_commit = bool(re.search(r"\bgit\s+commit\b", cmd))
    is_push = bool(re.search(r"\bgit\s+push\b", cmd))

    if is_commit or is_push:
        branch = current_branch()
        default = default_branch()
        if branch is not None and branch == default:
            law = "Law 5" if is_commit else "Law 7"
            action = "commit" if is_commit else "push"
            block(
                f"Blocked ({law}): refusing to {action} directly on "
                f"`{default}`. Create a feature branch first."
            )

    if is_commit:
        msg = extract_commit_message(cmd)
        if msg is not None:
            first_line = msg.strip().splitlines()[0] if msg.strip() else ""
            if first_line and not CONVENTIONAL_COMMIT_RE.match(first_line):
                block(
                    "Blocked (Law 13): commit message doesn't follow "
                    "Conventional Commits (`type(scope): description`). "
                    f"Got: {first_line!r}"
                )

        diff = staged_diff()
        if diff:
            for pattern in SECRET_PATTERNS:
                if pattern.search(diff):
                    block(
                        "Blocked (Law 14): staged diff matches a credential "
                        "pattern. Remove the secret before committing."
                    )
        if re.search(r"(^|\s)\.env(\.\w+)?(\s|$)", cmd) and ".env.example" not in cmd:
            # Best-effort: also check what's actually staged, not just the
            # command line, since `git commit -a` won't name files at all.
            try:
                staged_names = subprocess.run(
                    ["git", "diff", "--cached", "--name-only"],
                    capture_output=True, text=True, timeout=5,
                ).stdout.splitlines()
            except Exception:
                staged_names = []
            for name in staged_names:
                base = name.rsplit("/", 1)[-1]
                if base.startswith(".env") and base != ".env.example":
                    block(
                        f"Blocked (Law 14): `{name}` is staged for commit. "
                        "Env files other than `.env.example` must never be "
                        "committed."
                    )


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return  # fail open — can't parse input

    if payload.get("tool_name") != "Bash":
        return

    command = payload.get("tool_input", {}).get("command")
    if not isinstance(command, str) or not command.strip():
        return

    try:
        check_bash(command)
    except SystemExit:
        raise
    except Exception:
        return  # fail open — don't block on a bug in this script


if __name__ == "__main__":
    main()
