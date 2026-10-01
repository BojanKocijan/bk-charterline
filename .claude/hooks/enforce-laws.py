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
import os
import re
import subprocess
import sys


CD_RE = re.compile(r"(?:^|&&|;|\n)\s*cd\s+(\"[^\"]+\"|'[^']+'|\S+)")


def resolve_cwd(command: str) -> str:
    """Best-effort: the hook is invoked with whatever cwd the harness
    reports *before* the proposed command runs, which may not match a
    `cd` the command itself does first (e.g. `cd ~/foo && git push ...`
    or `cd ~/foo` on its own line). Without this, every check below
    would silently evaluate the wrong repo's branch — a correctness
    bug, not just an edge case, since multi-line `cd`-then-`git`
    scripts are the norm for this hook's own laws (branch + pull,
    cleanup, etc). Falls back to the hook's actual cwd if no `cd` is
    found or it can't be resolved.
    """
    here = os.getcwd()
    matches = CD_RE.findall(command)
    if not matches:
        return here
    target = matches[-1].strip("'\"")
    target = os.path.expanduser(os.path.expandvars(target))
    if not os.path.isabs(target):
        target = os.path.join(here, target)
    target = os.path.normpath(target)
    return target if os.path.isdir(target) else here


def default_branch(cwd: str) -> str:
    try:
        out = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip().rsplit("/", 1)[-1]
    except Exception:
        pass
    return "main"


def current_branch(cwd: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return None


def staged_diff(cwd: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
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
    # Heredoc first: `git commit -m "$(cat <<'EOF' ... EOF)"` is this
    # project's own mandated commit-message idiom (see CLAUDE.md), and
    # it must be checked before the plain -m "..." pattern below —
    # otherwise the naive quote-matcher grabs the raw `$(cat <<'EOF'`
    # / `EOF\n)` shell syntax as if it were the message itself.
    m = re.search(r"<<-?\s*['\"]?(\w+)['\"]?\n(.*?)\n\1\b", command, re.DOTALL)
    if m:
        return m.group(2)
    m = re.search(r"-m\s+(['\"])(.*?)\1", command, re.DOTALL)
    if m:
        return m.group(2)
    return None


PUSH_RE = re.compile(r"\bgit\s+push\b([^\n;&|]*)")


def push_targets_default(push_args: str, current: str | None, default: str) -> bool:
    """Decide whether one `git push ...` invocation would advance the
    default branch on origin. Deliberately conservative: an explicit
    push to or deletion of some *other* branch must never be blocked,
    even while HEAD happens to be sitting on the default branch (e.g.
    cleaning up a just-merged feature branch right after `git checkout
    main`) — that was a real false positive this function exists to
    fix.
    """
    args = push_args.strip()
    tokens = [t for t in args.split() if t]

    delete_idx = None
    for flag in ("--delete", "-d"):
        if flag in tokens:
            delete_idx = tokens.index(flag)
            break
    if delete_idx is not None and delete_idx + 1 < len(tokens):
        ref = tokens[delete_idx + 1]
        for prefix in ("origin/", "refs/heads/"):
            if ref.startswith(prefix):
                ref = ref[len(prefix):]
        return ref == default

    refspec_tokens = [t for t in tokens if ":" in t]
    if refspec_tokens:
        dst = refspec_tokens[0].split(":", 1)[1]
        for prefix in ("refs/heads/",):
            if dst.startswith(prefix):
                dst = dst[len(prefix):]
        if dst == "":
            # `src:` with nothing after the colon deletes the remote ref
            # named `src` — not a push *to* anything, so it can't advance
            # the default branch. Treat as non-default.
            return False
        return dst == default

    # No explicit refspec. Last non-flag token (if any) after the
    # remote name is the branch being pushed; otherwise it's an
    # implicit push of the current branch.
    non_flags = [t for t in tokens if not t.startswith("-")]
    explicit_branch = non_flags[1] if len(non_flags) >= 2 else None
    if explicit_branch is not None:
        return explicit_branch == default
    return current is not None and current == default


def block(reason: str) -> None:
    print(reason, file=sys.stderr)
    sys.exit(2)


HEREDOC_BODY_RE = re.compile(r"(<<-?\s*['\"]?(\w+)['\"]?\n)(.*?)(\n\2\b)", re.DOTALL)


def strip_heredoc_bodies(command: str) -> str:
    """Heredoc payloads (commit messages, PR/issue bodies) are *data*,
    not commands — a PR description that mentions `gh pr merge` or
    `git push` in prose must not trip the checks below just because
    the text appears in the command string. Blanks out everything
    between a heredoc's opening and closing delimiter before any
    dangerous-pattern matching runs; `extract_commit_message` still
    reads the real (unstripped) command, so actual commit-message
    content is unaffected.
    """
    return HEREDOC_BODY_RE.sub(lambda m: m.group(1) + m.group(4).lstrip("\n"), command)


def check_bash(command: str) -> None:
    cmd = command.strip()
    scan = strip_heredoc_bodies(cmd)

    # Law 7 — Claude never merges, under any circumstance.
    if re.search(r"\bgh\s+pr\s+merge\b", scan):
        block(
            "Blocked (Law 7): `gh pr merge` is never run by Claude, with or "
            "without flags. Merging the default branch is exclusively the "
            "human's action in the GitHub UI."
        )
    if "mergePullRequest" in scan:
        block(
            "Blocked (Law 7): GraphQL `mergePullRequest` is a merge — "
            "Claude never merges. Stop and let the human merge in the UI."
        )

    is_commit = bool(re.search(r"\bgit\s+commit\b", scan))
    push_matches = list(PUSH_RE.finditer(scan))

    if is_commit or push_matches:
        cwd = resolve_cwd(cmd)
        branch = current_branch(cwd)
        default = default_branch(cwd)

        if is_commit and branch is not None and branch == default:
            block(
                f"Blocked (Law 5): refusing to commit directly on "
                f"`{default}`. Create a feature branch first."
            )

        for match in push_matches:
            if push_targets_default(match.group(1), branch, default):
                block(
                    f"Blocked (Law 7): refusing to push to `{default}`. "
                    "Only a feature branch + PR gets pushed; the human "
                    "merges in the GitHub UI."
                )

    if is_commit:
        cwd = resolve_cwd(cmd)
        msg = extract_commit_message(cmd)
        if msg is not None:
            first_line = msg.strip().splitlines()[0] if msg.strip() else ""
            if first_line and not CONVENTIONAL_COMMIT_RE.match(first_line):
                block(
                    "Blocked (Law 13): commit message doesn't follow "
                    "Conventional Commits (`type(scope): description`). "
                    f"Got: {first_line!r}"
                )

        diff = staged_diff(cwd)
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
                    capture_output=True, text=True, timeout=5, cwd=cwd,
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
