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
import shlex
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


PUSH_VALUE_FLAGS = ("-o", "--push-option", "--repo", "--receive-pack", "--exec")


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
    # A leading `+` on a refspec forces that one ref (`+main`, `+HEAD:main`);
    # strip it so the branch name underneath is still recognised. Values of
    # options that take a separate argument (`-o a:b`) are not refspecs.
    raw = [t for t in args.split() if t]
    tokens: list[str] = []
    skip = False
    for t in raw:
        if skip:
            skip = False
            continue
        if t in PUSH_VALUE_FLAGS:
            skip = True
            continue
        tokens.append(t[1:] if t.startswith("+") and len(t) > 1 else t)

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

    refspec_tokens = [t for t in tokens if ":" in t and not t.startswith("-")]
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
    if explicit_branch == "HEAD":
        explicit_branch = current  # `git push origin HEAD` pushes the current branch
    if explicit_branch is not None:
        return explicit_branch == default
    return current is not None and current == default


class Blocked(Exception):
    """Raised by a check to block the tool call. `check` is a fixed id
    for the block log, so the log never has to store the reason text
    (the Law 13 reason quotes the commit message)."""

    def __init__(self, reason: str, check: str) -> None:
        super().__init__(reason)
        self.reason = reason
        self.check = check


def block(reason: str, check: str) -> None:
    raise Blocked(reason, check)


FORCE_FLAGS = ("--force", "-f", "--force-with-lease", "--force-if-includes")


def push_is_forced(push_args: str) -> bool:
    for t in push_args.split():
        if t.startswith("+") and len(t) > 1:
            return True
        if t in FORCE_FLAGS or t.startswith("--force-with-lease="):
            return True
        if re.fullmatch(r"-[A-Za-z]*f[A-Za-z]*", t):  # short cluster such as -uf
            return True
    return False


PREFIX_WORDS = ("sudo", "command", "exec", "env", "nohup", "time")


def strip_command_prefix(tokens: list[str]) -> list[str]:
    """Drop leading `VAR=value` assignments and wrappers such as `sudo`,
    `env` or `command`, so `HUSKY=0 git commit …` is still `git commit`."""
    i = 0
    while i < len(tokens) and (
        tokens[i] in PREFIX_WORDS or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[i])
    ):
        i += 1
    return tokens[i:]


def git_invocation(segment: str, sub: str) -> tuple[list[str], list[str]] | None:
    """(global options, arguments) of `git [global options] <sub> …` in one
    command segment, or None if it isn't that git command or can't be
    tokenised (callers then fail open)."""
    try:
        tokens = strip_command_prefix(shlex.split(segment))
    except ValueError:
        return None
    if not tokens or os.path.basename(tokens[0]) != "git":
        return None
    i = 1
    while i < len(tokens) and tokens[i].startswith("-"):
        i += 2 if tokens[i] in ("-C", "-c") else 1  # these take a value
    if i < len(tokens) and tokens[i] == sub:
        return tokens[1:i], tokens[i + 1:]
    return None


def git_subcommand_args(segment: str, sub: str) -> list[str] | None:
    found = git_invocation(segment, sub)
    return found[1] if found else None


# git commit options whose value follows as the next token.
COMMIT_VALUE_FLAGS = ("-m", "--message", "-F", "--file", "-C", "--reuse-message",
                      "-c", "--reedit-message", "-t", "--template", "--author", "--date",
                      "--fixup", "--squash", "--cleanup", "--trailer")


def commit_skips_hooks(args: list[str]) -> bool:
    skip = False
    for t in args:
        if skip:
            skip = False
            continue
        if t == "--":
            return False  # pathspecs follow
        if t == "--no-verify":
            return True
        if t in COMMIT_VALUE_FLAGS:
            skip = True  # its value is the next token, not a flag
            continue
        if re.fullmatch(r"-[A-Za-z]+", t):
            for ch in t[1:]:
                if ch == "n":
                    return True
                if ch in "mFCct":
                    if ch == t[-1]:
                        skip = True  # value is the next token
                    break  # otherwise the rest of the cluster is the value
                if ch in "uS":
                    break  # optional value attached, e.g. -uno
    return False


def skips_git_hooks(segment: str) -> bool:
    """`git commit --no-verify` / `-n` (anywhere among the flags, alone or in
    a short cluster such as `-an`), `git push --no-verify`, or pointing git at
    another hooks folder with `-c core.hooksPath=…`. `git push -n` is a dry run."""
    for sub in ("commit", "push"):
        found = git_invocation(segment, sub)
        if found is None:
            continue
        global_opts, args = found
        if any(o.lower().startswith("core.hookspath") for o in global_opts):
            return True
        if sub == "commit":
            return commit_skips_hooks(args)
        return "--no-verify" in args
    return False


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
            "human's action in the GitHub UI.",
            "merge",
        )
    if "mergePullRequest" in scan:
        block(
            "Blocked (Law 7): GraphQL `mergePullRequest` is a merge — "
            "Claude never merges. Stop and let the human merge in the UI.",
            "graphql-merge",
        )

    # Law 34 — ask before creating PR screenshots; the body records the answer.
    if re.search(r"\bgh\s+pr\s+create\b", scan) and not pr_body_has_screenshots_line(cmd):
        block(
            "Blocked (Law 34): ask the user \"Do you want e2e/screenshot images "
            "for this PR?\" first, then add one line to the PR body: "
            "`Screenshots: yes`, `Screenshots: skipped at the user's request` "
            "or `Screenshots: not applicable`.",
            "screenshots",
        )

    # Law 32 — never skip git hooks (Claude's behaviour on a block forbids any bypass).
    for segment in split_segments(scan) or []:
        if skips_git_hooks(segment):
            block(
                "Blocked (Law 32): `--no-verify` / `git commit -n` skips git "
                "hooks. Fix whatever the hook objects to instead of bypassing it.",
                "no-verify",
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
                f"`{default}`. Create a feature branch first.",
                "commit-on-default",
            )

        for match in push_matches:
            if push_targets_default(match.group(1), branch, default) and push_is_forced(match.group(1)):
                block(
                    f"Blocked (Law 7): refusing to force-push to `{default}`. "
                    "Rewriting the shared history of the default branch is "
                    "never Claude's call; force-push only a feature branch.",
                    "force-push-default",
                )
            if push_targets_default(match.group(1), branch, default):
                block(
                    f"Blocked (Law 7): refusing to push to `{default}`. "
                    "Only a feature branch + PR gets pushed; the human "
                    "merges in the GitHub UI.",
                    "push-default",
                )

    if is_commit:
        cwd = resolve_cwd(scan, base)
        for msg in extract_commit_messages(cmd, cwd):
            first_line = msg.strip().splitlines()[0] if msg.strip() else ""
            if first_line and not CONVENTIONAL_COMMIT_RE.match(first_line):
                block(
                    "Blocked (Law 13): commit message doesn't follow "
                    "Conventional Commits (`type(scope): description`). "
                    f"Got: {first_line!r}",
                    "commit-message",
                )

        diff = staged_diff(cwd)
        if diff:
            for pattern in SECRET_PATTERNS:
                if pattern.search(diff):
                    block(
                        "Blocked (Law 14): staged diff matches a credential "
                        "pattern. Remove the secret before committing.",
                        "secret",
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
                        "committed.",
                        "env-file",
                    )


def log_block(blocked: Blocked, command: str, base: str) -> None:
    """Record the block in the local block log (`hook_log.py`, #113).
    Never raises: a missing module, an unwritable log or a held lock
    must not change the decision."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        sys.dont_write_bytecode = True  # keep the ~/.design-forge clone clean
        import hook_log

        m = re.match(r"Blocked \(Law (\d+)\)", blocked.reason)
        cwd = resolve_cwd(strip_heredoc_bodies(command.strip()), base)
        hook_log.append_block(
            int(m.group(1)) if m else None, blocked.check, cwd,
            current_branch(cwd), command,
        )
    except Exception:
        pass


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
    except Blocked as blocked:
        log_block(blocked, command, base)
        print(blocked.reason, file=sys.stderr)
        sys.exit(2)
    except Exception:
        return  # fail open — don't block on a bug in this script


if __name__ == "__main__":
    main()
