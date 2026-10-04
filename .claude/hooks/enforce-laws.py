#!/usr/bin/env python3
"""PreToolUse hook — mechanically enforces Law 32 (CLAUDE_LAWS.md).

Reads the tool-call JSON Claude Code sends on stdin, inspects Bash
commands for a narrow set of patterns, and blocks (exit 2 + reason on
stderr) the ones that would break Law 7 (never merge / never push to
the default branch), Law 13 (Conventional Commits), Law 14 (secret
scan before commit), or Law 34 (ask before PR screenshots). Everything else passes through untouched.

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


CD_RE = re.compile(r"(?:^|&&|\|\||;|\n)\s*cd\s+(\"[^\"]+\"|'[^']+'|[^\s;&|]+)")


def resolve_cwd(command: str, base: str) -> str:
    """Best-effort: `base` is the shell's cwd *before* the proposed
    command runs, which may not match a `cd` the command itself does
    first (e.g. `cd ~/foo && git push ...` or `cd ~/foo` on its own
    line). Without this, every check below would silently evaluate the
    wrong repo's branch — a correctness bug, not just an edge case,
    since multi-line `cd`-then-`git` scripts are the norm for this
    hook's own laws (branch + pull, cleanup, etc).

    Walks every `cd` in order, each relative to the one before, and
    skips any target that isn't a directory (`cd -`, a `cd` quoted in
    a commit message). Pass heredoc-stripped text, so a `cd` inside a
    message or PR body is never followed.
    """
    cwd = base
    for raw in CD_RE.findall(command):
        target = os.path.expanduser(os.path.expandvars(raw.strip("'\"")))
        target = os.path.normpath(os.path.join(cwd, target))
        if os.path.isdir(target):
            cwd = target
    return cwd


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


HEREDOC_PLACEHOLDER_RE = re.compile(r"\x00HEREDOC(\d+)\x00")


def split_segments(command: str) -> list[str] | None:
    """Split a shell command into its top-level simple commands on
    `&&`, `||`, `;`, `|`, `&` and newlines, ignoring separators inside
    quotes, `$(...)`, `(...)` and backticks. Returns None when quoting
    doesn't balance, so callers can fail open.
    """
    segments: list[str] = []
    stack: list[str] = []
    start = i = 0
    n = len(command)
    while i < n:
        c = command[i]
        top = stack[-1] if stack else ""
        if top == "'":
            if c == "'":
                stack.pop()
        elif c == "\\":
            i += 1  # skip the escaped character
        elif top == '"':
            if c == '"':
                stack.pop()
            elif command.startswith("$(", i):
                stack.append("(")
                i += 1
            elif c == "`":
                stack.append("`")
        elif top == "`" and c == "`":
            stack.pop()
        elif c in "'\"":
            stack.append(c)
        elif command.startswith("$(", i):
            stack.append("(")
            i += 1
        elif c == "(":
            stack.append("(")
        elif c == ")" and top == "(":
            stack.pop()
        elif c == "`":
            stack.append("`")
        elif not stack and c in "&|;\n":
            segments.append(command[start:i])
            if command.startswith(("&&", "||"), i):
                i += 1
            start = i + 1
        i += 1
    if stack:
        return None
    segments.append(command[start:])
    return [s.strip() for s in segments if s.strip()]


def extract_commit_messages(command: str, cwd: str) -> list[str]:
    """The messages of every `git commit` in the command, and only
    those: a heredoc, `-m`/`--message`, or `-F <file>` must sit in the
    commit's own segment. A heredoc attached to another command (e.g. a
    `gh pr create --body "$(cat <<'EOF' ...)"` chained after the commit)
    is that command's data, not the commit message.
    """
    # Each heredoc (opener line break, body, closing delimiter) collapses
    # to a placeholder on the opener's line, so quotes or `&&` inside a
    # commit message or PR body can't confuse the segment splitter, and a
    # top-level `git commit -F - <<EOF` keeps its body in its own segment.
    bodies: list[str] = []

    def stash(m: re.Match) -> str:
        bodies.append(m.group(3))
        return f"{m.group(1).rstrip()} \x00HEREDOC{len(bodies) - 1}\x00"

    segments = split_segments(HEREDOC_BODY_RE.sub(stash, command))
    if segments is None:
        return []  # fail open — can't tell which message is the commit's

    messages = []
    for seg in segments:
        if not re.search(r"\bgit\s+commit\b", seg):
            continue
        # Heredoc first: `git commit -m "$(cat <<'EOF' ... EOF)"` is this
        # project's own mandated commit-message idiom (see CLAUDE.md), and
        # it must be checked before the plain -m "..." pattern below —
        # otherwise the naive quote-matcher grabs the raw `$(cat <<'EOF'`
        # / `EOF\n)` shell syntax as if it were the message itself.
        m = HEREDOC_PLACEHOLDER_RE.search(seg)
        if m:
            messages.append(bodies[int(m.group(1))])
            continue
        m = re.search(r"(?:\s-[A-Za-z]*m|--message)(?:\s+|=)(['\"])(.*?)\1", seg, re.DOTALL)
        if m:
            messages.append(m.group(2))
            continue
        m = re.search(r"(?:-F|--file)(?:\s+|=)(\"[^\"]+\"|'[^']+'|\S+)", seg)
        if m:
            path = os.path.expanduser(m.group(1).strip("'\""))
            try:
                with open(os.path.join(cwd, path)) as f:
                    messages.append(f.read())
            except Exception:
                pass  # can't read the file — fail open
    return messages


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
    dangerous-pattern matching runs; `extract_commit_messages` still
    reads the real (unstripped) command, so actual commit-message
    content is unaffected.
    """
    return HEREDOC_BODY_RE.sub(lambda m: m.group(1) + m.group(4).lstrip("\n"), command)


SCREENSHOTS_LINE_RE = re.compile(
    r"screenshots?:?\s+(yes|requested|skipped|not applicable)|no screens affected",
    re.IGNORECASE,
)
BODY_FILE_RE = re.compile(r"(?:--body-file|-F)\s+(\"[^\"]+\"|'[^']+'|\S+)")


def pr_body_has_screenshots_line(command: str) -> bool:
    """True if the `gh pr create` command (or its --body-file) states the
    screenshot decision. Fails open when the body can't be inspected."""
    if SCREENSHOTS_LINE_RE.search(command):
        return True
    m = BODY_FILE_RE.search(command)
    if m:
        path = os.path.expanduser(m.group(1).strip("'\""))
        try:
            with open(path) as f:
                return bool(SCREENSHOTS_LINE_RE.search(f.read()))
        except Exception:
            return True  # can't read the file — fail open
    return False


def check_bash(command: str, base: str) -> None:
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

    # Law 34 — ask before creating PR screenshots; the body records the answer.
    if re.search(r"\bgh\s+pr\s+create\b", scan) and not pr_body_has_screenshots_line(cmd):
        block(
            "Blocked (Law 34): ask the user \"Do you want e2e/screenshot images "
            "for this PR?\" first, then add one line to the PR body: "
            "`Screenshots: yes`, `Screenshots: skipped at the user's request` "
            "or `Screenshots: not applicable`."
        )

    is_commit = bool(re.search(r"\bgit\s+commit\b", scan))
    push_matches = list(PUSH_RE.finditer(scan))

    if is_commit or push_matches:
        cwd = resolve_cwd(scan, base)
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
        cwd = resolve_cwd(scan, base)
        for msg in extract_commit_messages(cmd, cwd):
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

    # The Bash tool's cwd. The hook process itself may sit in another
    # checkout (e.g. the main repo while the session runs in a worktree),
    # and Claude Code drops a leading `cd <cwd> &&` before calling hooks.
    base = payload.get("cwd")
    if not isinstance(base, str) or not os.path.isdir(base):
        base = os.getcwd()

    try:
        check_bash(command, base)
    except SystemExit:
        raise
    except Exception:
        return  # fail open — don't block on a bug in this script


if __name__ == "__main__":
    main()
