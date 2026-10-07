#!/usr/bin/env python3
"""PreToolUse hook — mechanically enforces Law 32 (CLAUDE_LAWS.md).

Reads the tool-call JSON Claude Code sends on stdin (Bash commands and
the file-editing tools), checks a narrow set of patterns, and either
blocks (exit 2 + reason on stderr) the ones that would break Law 5/7
(never commit, push or force-push to the default branch, never merge),
Law 13 (Conventional Commits), Law 14 (secret scan), Law 32 (never
skip git hooks) or Law 34 (ask before PR screenshots), or returns
permissionDecision "ask" so the user approves in Claude Code's own
prompt: changing a guardrail file or the Law 38 tool registry or
approvals (`ai_tools.py set` included), or deleting a tracked file (Law 8).
Every block check runs before any ask. Everything else passes through.

MCP tool calls (`mcp__*`) get Law 38's tier from the registry
(`scripts/ai_tools.py`): tier 4 asks on every call, tier 3 asks until
the tool has run once in the session (#138). As a PostToolUse hook, the
same script records that run in `ai_approvals.py`; it never blocks there.

Fails open: if anything here can't be parsed confidently, the call is
allowed rather than blocked on an infrastructure fluke. This is a
backstop against mechanical slips, not a replacement for the judgment
the rest of CLAUDE_LAWS.md already asks for.

Dependency-free stdlib only, so it runs anywhere Python 3 does.
"""
from __future__ import annotations

import base64
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

# Secret shapes for the Law 14 commit check and Law 39's MCP inputs (#119).
# Every quantifier is bounded, so a large input can't backtrack for long.
# `body` is the part after the prefix: one repeated character there is a
# placeholder (`ghp_xxxx…`).
SECRET_KINDS = [(kind, re.compile(pattern, re.ASCII)) for kind, pattern in (
    ("an AWS access key", r"\b(?:AKIA|ASIA)(?P<body>[0-9A-Z]{16})\b"),
    ("a GitHub token", r"\bgh[pousr]_(?P<body>[A-Za-z0-9]{36,255})\b"),
    ("a GitHub token", r"\bgithub_pat_(?P<body>[A-Za-z0-9_]{60,255})\b"),
    ("a GitLab token", r"\bglpat-(?P<body>[A-Za-z0-9_-]{20,255})"),
    ("a Slack token", r"\bxox[abposr]-(?P<body>[A-Za-z0-9-]{10,255})"),
    ("a Slack token", r"\bxapp-(?P<body>[A-Za-z0-9-]{10,255})"),
    ("a Stripe live key", r"\b[rs]k_live_(?P<body>[A-Za-z0-9]{20,255})"),
    ("an Anthropic key", r"\bsk-ant-(?P<body>[A-Za-z0-9_-]{20,255})"),
    ("an OpenAI key", r"\bsk-(?:proj|svcacct|admin)-(?P<body>[A-Za-z0-9_-]{20,255})"),
    ("a Google API key", r"\bAIza(?P<body>[0-9A-Za-z_-]{35})(?![0-9A-Za-z_-])"),
    ("a Supabase key", r"\bsbp_(?P<body>[a-f0-9]{40})\b"),
    ("a Supabase key", r"\bsb_secret_(?P<body>[A-Za-z0-9_-]{20,255})"),
    ("a Netlify token", r"\bnfp_(?P<body>[A-Za-z0-9]{36,255})"),
    ("an npm token", r"\bnpm_(?P<body>[A-Za-z0-9]{36})\b"),
    ("a Figma token", r"\bfigd_(?P<body>[A-Za-z0-9_-]{30,255})"),
)]
PRIVATE_KEY_RE = re.compile(r"-----BEGIN ((RSA|EC|DSA|OPENSSH|ENCRYPTED|PGP) )?PRIVATE KEY( BLOCK)?-----")
# A key body: a line break (or a literal `\n` in a .env value), then 40+ base64 characters.
PRIVATE_KEY_BODY_RE = re.compile(r"(?:\r?\n|\\n)\s{0,8}[A-Za-z0-9+/=]{40,}")
JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{10,4096}\.(?P<payload>eyJ[A-Za-z0-9_-]{10,8192})\.[A-Za-z0-9_-]{10,4096}", re.ASCII)
# A name containing a credential word, then `=` or `:`, then a value. The match
# starts at the word itself, so `STRIPE_SECRET_KEY` and `client_secret` count.
ASSIGNMENT_RE = re.compile(
    r"(?i)(?:api[_-]?key|secret|token|passw(?:or)?d|private[_-]?key|access[_-]?key)[\w.-]{0,40}"
    r"[\"']?\s{0,4}[:=]\s{0,4}(?P<quote>[\"']?)(?P<value>[A-Za-z0-9+/=_.~-]{16,1024})(?P=quote)"
    r"(?![A-Za-z0-9+/=_.~-])",
    re.ASCII,
)
REFERENCE_PREFIXES = ("${{", "${", "$", "process.env", "os.environ", "import.meta.env")
PUBLIC_PREFIXES = ("sk_test_", "pk_", "sb_publishable_")
# A git SHA, a UUID or an integrity string: shaped like a key, but not one.
NOT_A_KEY_RE = re.compile(
    r"[0-9a-f]{40}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    r"|sha(?:1|256|384|512)-.*",
    re.ASCII,
)
PLACEHOLDER_RE = re.compile(r"(?:[A-Za-z]{1,12}[_-]){0,3}(.)\1{7,}", re.ASCII)


def _jwt_role(payload: str) -> object:
    try:
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except Exception:
        return None
    return data.get("role") if isinstance(data, dict) else None


def _assignment_is_secret(value: str) -> bool:
    if (value.startswith(REFERENCE_PREFIXES) or value.startswith(PUBLIC_PREFIXES)
            or "EXAMPLE" in value or PLACEHOLDER_RE.fullmatch(value)
            or NOT_A_KEY_RE.fullmatch(value) or JWT_RE.match(value)):
        return False  # a JWT is judged by its own rule
    mixed = re.search(r"[A-Za-z]", value) and re.search(r"[0-9]", value)
    return bool(mixed) or len(value) >= 32


def find_secret(text: str) -> tuple[str, int] | None:
    """The kind and offset of the first secret in `text`, or None.
    Placeholders, references, test and public keys, key headers with no
    key body and Supabase anon JWTs pass (#119)."""
    found: list[tuple[int, str]] = []
    for kind, pattern in SECRET_KINDS:
        for match in pattern.finditer(text):
            if "EXAMPLE" not in match.group(0) and len(set(match.group("body"))) > 1:
                found.append((match.start(), kind))
                break
    for match in PRIVATE_KEY_RE.finditer(text):
        if PRIVATE_KEY_BODY_RE.search(text, match.end(), match.end() + 300):
            found.append((match.start(), "a private key"))
            break
    for match in JWT_RE.finditer(text):
        if _jwt_role(match.group("payload")) != "anon":
            found.append((match.start(), "a JWT"))
            break
    for match in ASSIGNMENT_RE.finditer(text):
        if _assignment_is_secret(match.group("value")):
            found.append((match.start(), "a credential assignment"))
            break
    if not found:
        return None
    offset, kind = min(found)
    return kind, offset


def added_lines(diff: str) -> list[tuple[str, str]]:
    """(file, the lines it adds) for each file in a unified diff. Removed and
    context lines don't count, so deleting a leaked secret isn't blocked."""
    files: dict[str, list[str]] = {}
    path, previous = "?", ""
    for line in diff.splitlines():
        if line.startswith("+++ ") and previous.startswith("--- "):
            target = line[4:]
            path = target[2:] if target.startswith("b/") else target
        elif line.startswith("+"):
            files.setdefault(path, []).append(line[1:])
        previous = line
    return [(name, "\n".join(lines)) for name, lines in files.items()]


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
        elif not stack and c in "&|" and (
            (i > 0 and command[i - 1] == ">") or command.startswith(">", i + 1)
        ):
            pass  # part of a redirection (`>|`, `>&`, `2>&1`, `&>`), not a separator
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


class Asked(Blocked):
    """Raised to hand the call to the user: Claude Code shows its own
    permission prompt with the reason (#117). Only the user's click in
    the app approves it; nothing Claude or a tool output says can."""


def ask(reason: str, check: str) -> None:
    raise Asked(reason, check)


# Permission modes in which an "ask" would let the call through without
# a prompt; there the hook denies instead. Empty: a live probe
# (2026-10-05, Claude Code 2.1.289) found no such mode — default,
# acceptEdits, auto, dontAsk, plan and bypassPermissions all withheld
# the edit. Add a mode here if a later version changes that.
ASK_DENIED_MODES: set[str] = set()

FILE_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")

# Files under the installed clone that its own tools write (relative paths
# or name prefixes); everything else in ~/.design-forge is protected. The
# Law 38 registry and approvals are protected too: a tier is the user's call
# and an approval is the user's click (#138).
DF_DATA_PREFIXES = ("hook-log.", "ai-inventory.")
DF_DATA_FILES = ("projects.yaml", os.path.join("knowledge", "PATTERNS.md"))


def resolve_path(path: str, cwd: str) -> str:
    """Absolute, symlink-resolved path, with ~ and $VARS expanded."""
    return os.path.realpath(os.path.join(cwd, os.path.expandvars(os.path.expanduser(path))))


def _fold(path: str) -> str:
    # macOS file systems ignore case by default: ~/.Claude/Settings.json is
    # the same file as ~/.claude/settings.json, so compare case-folded there.
    return path.casefold() if sys.platform == "darwin" else path


def protected_target(path: str, cwd: str) -> str | None:
    """What a path protects, or None. Compared after expanding ~ and $VARS
    and resolving symlinks, so ~/.claude/skills/x (a link into
    ~/.design-forge) counts. Fails open (None) if it can't be resolved."""
    try:
        real = _fold(resolve_path(path, cwd))
        home = _fold(os.path.realpath(os.path.expanduser("~")))
    except Exception:
        return None
    claude = os.path.join(home, ".claude")
    if real in (os.path.join(claude, "settings.json"), os.path.join(claude, "settings.local.json")):
        return "your Claude Code settings"
    if real == os.path.join(claude, "claude.md" if sys.platform == "darwin" else "CLAUDE.md"):
        return "your global CLAUDE.md"
    if os.path.basename(real) in ("settings.json", "settings.local.json") \
            and os.path.basename(os.path.dirname(real)) == ".claude":
        return "a project's Claude Code settings"
    if os.path.basename(real) == _fold("ai-tools.json") and os.path.basename(os.path.dirname(real)) == ".claude":
        return "a project's Law 38 tool registry"
    if os.path.basename(real) == ".claude":
        # Moving or linking a folder onto .claude swaps its settings and
        # registry in one step, past the per-file checks above.
        return "a .claude folder"
    forge = _fold(os.path.realpath(os.path.join(os.path.expanduser("~"), ".design-forge")))
    if real == forge or real.startswith(forge + os.sep):
        rel = os.path.relpath(real, forge)
        if rel == _fold("ai-tools.json"):
            return "your Law 38 tool registry"
        if rel.startswith(_fold("ai-approvals")):
            return "your Law 38 approvals"
        if rel.startswith(tuple(_fold(p) for p in DF_DATA_PREFIXES)) or rel in {_fold(f) for f in DF_DATA_FILES}:
            return None
        return "the installed Design Forge"
    return None


def check_file_edit(tool: str, tool_input: dict, base: str) -> None:
    path = tool_input.get("notebook_path" if tool == "NotebookEdit" else "file_path")
    if not isinstance(path, str) or not path:
        return
    what = protected_target(path, base)
    if what:
        ask(
            f"Law 32 (guardrail): {tool} would change {what} ({path}). "
            "Approve only if you asked for this change.",
            "guardrail-edit",
        )


WRITE_VERBS = {"tee", "rm", "unlink", "truncate", "chmod", "chown"}
COPY_VERBS = {"cp", "mv", "ln", "install"}  # write to a destination


def deleted_paths(segment: str) -> list[str]:
    """Paths deleted by `rm`, `unlink` or `git rm` (not `--cached`, which
    keeps the file) in one segment; `git -C DIR rm x` yields DIR/x.
    Untokenisable input yields nothing (fail open)."""
    found = git_invocation(segment, "rm")
    if found is not None:
        global_opts, args = found
        if "--cached" in args:
            return []
        git_dir = None
        for i, opt in enumerate(global_opts):
            if opt == "-C" and i + 1 < len(global_opts):
                git_dir = global_opts[i + 1]
        paths = [a for a in args if not a.startswith("-")]
        return [os.path.join(git_dir, a) if git_dir else a for a in paths]
    try:
        tokens = strip_command_prefix(shlex.split(segment))
    except ValueError:
        return []
    if tokens and os.path.basename(tokens[0]) in ("rm", "unlink"):
        return [t for t in tokens[1:] if not t.startswith("-")]
    return []


PYTHON_RE = re.compile(r"python(\d+(\.\d+)?)?")


def writes_registry(segment: str) -> bool:
    """`ai_tools.py set …`, run directly, through python (`-m ai_tools`
    too), `uv run` or a nested `bash|sh|zsh -c`. `show` only reads.
    Untokenisable input is False (fail open)."""
    try:
        tokens = strip_command_prefix(shlex.split(segment))
    except ValueError:
        return False
    if tokens and os.path.basename(tokens[0]) in ("bash", "sh", "zsh") and "-c" in tokens[1:-1]:
        inner = tokens[tokens.index("-c", 1) + 1]
        return any(writes_registry(s) for s in split_segments(inner) or [])
    if tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if tokens and PYTHON_RE.fullmatch(os.path.basename(tokens[0])):
        i = 1
        while i < len(tokens) and tokens[i].startswith("-"):
            if tokens[i] == "-m" and i + 1 < len(tokens):
                tokens[i + 1] = tokens[i + 1].rsplit(".", 1)[-1] + ".py"
                i += 1
                break
            i += 2 if tokens[i] in ("-W", "-X") else 1  # these take a value
        tokens = tokens[i:]
    if not tokens or os.path.basename(tokens[0]) != "ai_tools.py":
        return False
    args = [t for t in tokens[1:] if not t.startswith("-")]
    return bool(args) and args[0] == "set"


# git subcommands that change the installed clone's files: dforge-update's
# reviewed-diff gate is skipped when Claude runs them by hand (#170).
CLONE_GIT_MOVES = {
    "checkout", "switch", "pull", "reset", "merge", "rebase", "restore",
    "cherry-pick", "am", "apply", "clean", "revert", "stash",
}
# Exceptions that stay free, each with its reason. Add a command that asks
# wrongly here, with a test, instead of loosening the check.
CLONE_GIT_ALLOWED = {
    ("stash", "list"): "only lists stashes",
    ("stash", "show"): "only shows a stash",
}
SHELLS = ("bash", "sh", "zsh", "$SHELL", "${SHELL}")


def in_installed_clone(path: str) -> bool:
    try:
        real = _fold(os.path.realpath(path))
        forge = _fold(os.path.realpath(os.path.join(os.path.expanduser("~"), ".design-forge")))
    except Exception:
        return False
    return real == forge or real.startswith(forge + os.sep)


def moves_installed_clone(segment: str, cwd: str) -> str | None:
    """The git subcommand when `segment` would change the files of the
    installed ~/.design-forge, else None. Follows `-C` (chained),
    `--git-dir`, `--work-tree`, `GIT_DIR=`/`GIT_WORK_TREE=` and a nested
    `bash|sh|zsh -c`. Untokenisable input is None (fail open)."""
    try:
        tokens = shlex.split(segment)
    except ValueError:
        return None
    if tokens and os.path.basename(tokens[0]) in SHELLS:
        flag = next((i for i, t in enumerate(tokens[1:-1], 1) if re.fullmatch(r"-[a-z]*c[a-z]*", t)), None)
        if flag is not None:
            parts = split_segments(tokens[flag + 1]) or []
            for index, part in enumerate(parts):
                found = moves_installed_clone(part, resolve_cwd("\n".join(parts[:index]), cwd))
                if found:
                    return found
            return None

    def expand(path: str, base: str) -> str:
        return os.path.normpath(os.path.join(base, os.path.expandvars(os.path.expanduser(path))))

    git_dir = work_tree = None
    for token in tokens:
        m = re.fullmatch(r"(GIT_DIR|GIT_WORK_TREE)=(.*)", token)
        if m:
            if m.group(1) == "GIT_DIR":
                git_dir = expand(m.group(2), cwd)
            else:
                work_tree = expand(m.group(2), cwd)
    tokens = strip_command_prefix(tokens)
    if not tokens or os.path.basename(tokens[0]) != "git":
        return None
    repo = cwd
    i = 1
    while i < len(tokens) and tokens[i].startswith("-"):
        opt = tokens[i]
        if opt == "-C" and i + 1 < len(tokens):
            repo = expand(tokens[i + 1], repo)
            i += 2
        elif opt in ("--git-dir", "--work-tree") and i + 1 < len(tokens):
            value = expand(tokens[i + 1], repo)
            git_dir, work_tree = (value, work_tree) if opt == "--git-dir" else (git_dir, value)
            i += 2
        elif opt.startswith(("--git-dir=", "--work-tree=")):
            name, value = opt.split("=", 1)
            value = expand(value, repo)
            git_dir, work_tree = (value, work_tree) if name == "--git-dir" else (git_dir, value)
            i += 1
        else:
            i += 2 if opt == "-c" else 1  # -c takes a value
    if i >= len(tokens) or tokens[i] not in CLONE_GIT_MOVES:
        return None
    sub = tokens[i]
    args = tokens[i + 1:]
    if args and (sub, args[0]) in CLONE_GIT_ALLOWED:
        return None
    target = work_tree or git_dir or repo  # a git dir inside the clone counts
    return sub if in_installed_clone(target) else None


# Hosting CLIs act with the user's logged-in account (#173). Only commands
# verified as reads or local-only are free; anything else asks, unknown
# commands included. Sources: each CLI's --help (netlify-cli 27.11.2), the
# bundled Netlify OpenAPI spec, and vercel.com/docs/cli (2026-10-06).
HOSTING_CLIS = {"netlify": "netlify", "ntl": "netlify", "netlify-cli": "netlify",
                "vercel": "vercel", "vc": "vercel"}
HELP_FLAGS = {"--help", "-h", "--version", "-v"}
NETLIFY_FREE = {"help", "logs", "log", "status", "status:hooks", "watch", "dev", "serve", "build",
                "link", "unlink", "open", "open:site", "open:admin", "completion", "recipes",
                "recipes:list"}
NETLIFY_FREE_GROUPS = {"logs", "log", "functions", "function"}  # every subcommand
NETLIFY_READ_SUBS = {"list", "get", "show", "search"}
NETLIFY_API_READ = re.compile(r"(get|list|show|search)[A-Z]")  # all GETs in the spec
NETLIFY_VALUE_OPTS = {"--auth", "--filter"}
VERCEL_FREE = {"help", "whoami", "ls", "list", "inspect", "logs", "activity", "alerts", "metrics",
               "usage", "contract", "security", "bisect", "dev", "build", "open", "init"}
VERCEL_READ_SUBS = {"ls", "list", "inspect", "get", "status"}
# Global options, and deploy's, that take a value: `vercel --scope ls deploy`
# deploys, `vercel --name ls` too.
VERCEL_VALUE_OPTS = {"--cwd", "--scope", "-S", "--team", "-T", "--token", "-t", "--project",
                     "--local-config", "-A", "--global-config", "-Q", "--env", "-e",
                     "--build-env", "-b", "--meta", "-m", "--name", "-n", "--regions",
                     "--target", "--archive"}
SUBSTITUTION_RE = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")


def _positionals(args: list[str], value_opts: set[str]) -> list[str]:
    found, i = [], 0
    while i < len(args):
        if args[i] in value_opts:
            i += 2
            continue
        if not args[i].startswith("-"):
            found.append(args[i])
        i += 1
    return found


def _unwrap_runner(tokens: list[str]) -> list[str]:
    """`npx`, `bunx`, `bun x`, `pnpm dlx|exec`, `pnpm <bin>`, `yarn dlx|exec`,
    `yarn <bin>` and `npm exec|x`, down to `<package or bin> args…`."""
    head, rest = os.path.basename(tokens[0]), tokens[1:]
    if head in ("pnpm", "yarn"):
        rest = rest[1:] if rest and rest[0] in ("dlx", "exec") else rest
    elif head in ("bun", "npm"):
        if not rest or rest[0] not in (("x",) if head == "bun" else ("exec", "x")):
            return tokens
        rest = rest[1:]
    elif head not in ("npx", "bunx"):
        return tokens
    i = 0
    while i < len(rest) and rest[i].startswith("-"):
        if rest[i] == "--":
            i += 1
            break
        i += 2 if rest[i] in ("-p", "--package") else 1
    return rest[i:]


def hosting_cli_write(segment: str) -> str | None:
    """The Netlify or Vercel command, as shown in the prompt, when `segment`
    runs one that isn't a verified read or local-only command; else None.
    Looks through runners, `VAR=` prefixes, nested shells and `$(…)`.
    Untokenisable input is None (fail open)."""
    # $(…) and backticks run, except escaped or inside single quotes.
    live = re.sub(r"'[^']*'", "''", re.sub(r"\\.", "", segment))
    for m in SUBSTITUTION_RE.finditer(live):
        for part in split_segments(m.group(1) or m.group(2) or "") or []:
            found = hosting_cli_write(part)
            if found:
                return found
    try:
        tokens = strip_command_prefix(shlex.split(segment))
    except ValueError:
        return None
    if not tokens:
        return None
    if os.path.basename(tokens[0]) in SHELLS:
        flag = next((i for i, t in enumerate(tokens[1:-1], 1) if re.fullmatch(r"-[a-z]*c[a-z]*", t)), None)
        if flag is not None:
            for part in split_segments(tokens[flag + 1]) or []:
                found = hosting_cli_write(part)
                if found:
                    return found
        return None
    tokens = _unwrap_runner(tokens)
    if not tokens:
        return None
    cli = HOSTING_CLIS.get(os.path.basename(tokens[0]).split("@")[0])
    args = tokens[1:]
    if args[:1] == ["--"]:
        args = args[1:]
    if cli is None or any(a in HELP_FLAGS for a in args):
        return None
    if cli == "netlify":
        words = _positionals(args, NETLIFY_VALUE_OPTS)
        if not words or words[0] in NETLIFY_FREE:
            return None  # bare `netlify` prints its help
        group, _, sub = words[0].partition(":")
        sub = sub or (words[1] if len(words) > 1 else "")
        if (group in NETLIFY_FREE_GROUPS
                or (group == "api" and (not sub or NETLIFY_API_READ.match(sub)))
                or (group in ("database", "db") and sub == "status")
                or (group != "env" and sub in NETLIFY_READ_SUBS)):
            return None
    else:
        words = _positionals(args, VERCEL_VALUE_OPTS)
        # Bare `vercel` and `vercel <path>` deploy.
        if words and (words[0] in VERCEL_FREE
                      or (words[0] != "env" and len(words) > 1 and words[1] in VERCEL_READ_SUBS)):
            return None
    return " ".join([cli, *words[:2]])


# `dforge-update … --approve`, also inside `"$SHELL" -ic '…'` or `bash -c`.
APPROVE_RE = re.compile(r"\bdforge-update\b[^\n;&|]*?\s--approve\b")


def tracked_by_git(path: str, cwd: str) -> bool:
    """True if `path` (a file, folder or glob, relative or absolute, with ~
    and $VARS expanded) matches files git tracks. git runs in the folder the
    path is in, so absolute paths into another repo count too. Any error —
    not a repo, a missing folder — is False (fail open)."""
    try:
        expanded = os.path.join(cwd, os.path.expandvars(os.path.expanduser(path)))
        if os.path.isdir(expanded):
            run_dir, spec = os.path.realpath(expanded), "."
        else:
            run_dir, spec = os.path.realpath(os.path.dirname(expanded)), os.path.basename(expanded)
        if not os.path.isdir(run_dir) or not spec:
            return False
        if any(ch in spec for ch in "*?["):
            spec = f":(glob){spec}"  # shell-like: `*` stays within one folder
        out = subprocess.run(
            ["git", "ls-files", "--", spec],
            capture_output=True, text=True, timeout=5, cwd=run_dir,
        )
        return out.returncode == 0 and bool(out.stdout.strip())
    except Exception:
        return False


def redirect_targets(segment: str) -> list[str]:
    """Files a segment redirects output into (`>`, `>>`, `&>`, `>|`, `2>`).
    Quote-aware: a `>` inside a quoted message is not a redirection."""
    try:
        lex = shlex.shlex(segment, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        return []
    targets = []
    for op, target in zip(tokens, tokens[1:]):
        if set(op) <= set(">&|") and ">" in op and not target.isdigit() and not target.startswith("&") \
                and not (op.endswith("&") and target.isdigit()):
            if not set(target) <= set("<>&|;"):
                targets.append(target)
    return targets


def bash_write_targets(segment: str, cwd: str) -> list[str]:
    """Paths one command segment writes to: redirection targets, the
    arguments of a write verb, the destination of cp/mv/ln/install (a file
    inside it when it's a folder, or `-t DIR`) plus mv's sources, and the
    files of `sed`/`perl` run in place. Best-effort; an untokenisable
    segment yields only its redirections (fail open)."""
    targets = redirect_targets(segment)
    try:
        lex = shlex.shlex(segment, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        raw = list(lex)
    except ValueError:
        return targets
    # Drop redirections (`2>/dev/null`, `> out 2>&1`) and their targets, so
    # a trailing redirect can't pose as cp's destination.
    tokens, skip = [], False
    for i, t in enumerate(raw):
        if skip:
            skip = False
            continue
        if set(t) <= set("<>&|") and ">" in t:
            skip = True
            continue
        if t.isdigit() and i + 1 < len(raw) and set(raw[i + 1]) <= set("<>&|") and ">" in raw[i + 1]:
            continue  # the fd number in `2>`
        tokens.append(t)
    tokens = strip_command_prefix(tokens)
    if not tokens:
        return targets
    verb = os.path.basename(tokens[0])
    rest = tokens[1:]
    target_dir = None
    for i, t in enumerate(rest):
        if t in ("-t", "--target-directory") and i + 1 < len(rest):
            target_dir = rest[i + 1]
        elif t.startswith("--target-directory="):
            target_dir = t.split("=", 1)[1]
    args = [t for t in rest if not t.startswith("-") and set(t) - set("<>&|") and t != target_dir]
    if verb in COPY_VERBS and args:
        if target_dir is not None:
            dest_dir, sources = target_dir, args
        else:
            dest, sources = args[-1], args[:-1]
            dest_dir = dest if dest.endswith("/") or os.path.isdir(resolve_path(dest, cwd)) else None
            if dest_dir is None:
                targets.append(dest)
        if dest_dir is not None:
            targets.append(dest_dir)
            targets += [os.path.join(dest_dir, os.path.basename(src.rstrip("/"))) for src in sources]
        if verb == "mv":
            targets += sources  # moving a guardrail file away changes it too
    elif verb in WRITE_VERBS:
        targets += args
    elif verb in ("sed", "perl") and any(
        t == "--in-place" or t.startswith("--in-place=")
        or (re.match(r"-[A-Za-z]*i", t) and not t.startswith("--"))
        for t in rest
    ):
        targets += args
    return targets


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
        if any((o[2:] if o.startswith("-c") else o).lower().startswith("core.hookspath") for o in global_opts) \
                or re.search(r"\bGIT_CONFIG_KEY_\d+=core\.hooksPath\b", segment, re.IGNORECASE):
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

    # Law 32 — writing to a guardrail file asks the user in the app (#117).
    # Held until the end: every block check below must still run, so an
    # approved prompt can never let a blocked command through.
    pending_ask = None
    segments = split_segments(scan) or []
    for index, segment in enumerate(segments):
        # Each segment's paths resolve against the cwd at that point, so a
        # later `cd` can't move an earlier relative path somewhere harmless.
        write_cwd = resolve_cwd("\n".join(segments[:index]), base)
        for target in bash_write_targets(segment, write_cwd):
            what = protected_target(target, write_cwd)
            if what and pending_ask is None:
                pending_ask = (
                    f"Law 32 (guardrail): this command writes to {what} ({target}). "
                    "Approve only if you asked for this change.",
                    "guardrail-write",
                )
        # Law 8 — deleting a file git tracks needs the user's approval.
        for target in deleted_paths(segment):
            if pending_ask is None and tracked_by_git(target, write_cwd):
                pending_ask = (
                    f"Law 8 (no deletion without approval): this deletes {target}, "
                    "which git tracks. Approve only if you want it removed.",
                    "tracked-delete",
                )
        # Law 32 — git that changes the installed clone skips dforge-update's
        # reviewed-diff gate (Law 28), so the user approves it here (#170).
        moved = moves_installed_clone(segment, write_cwd) if pending_ask is None else None
        if moved:
            pending_ask = (
                f"Law 32 (guardrail): `git {moved}` would change the installed Design Forge "
                "(~/.design-forge) without dforge-update's reviewed diff. Approve only if you "
                "asked for it; to update, use dforge-update.",
                "guardrail-git",
            )
        # Law 38 — a hosting CLI acts with the user's account: anything but a
        # verified read or local command asks, on every call (#173).
        hosted = hosting_cli_write(segment) if pending_ask is None else None
        if hosted:
            pending_ask = (
                f"Law 38: `{hosted}` isn't on the hosting CLI read list, so it may change a "
                "live site, its settings or data, or copy its secrets, using your logged-in "
                "account. Approve only if you asked for exactly this.",
                "hosting-write",
            )
        # Law 38 — a tier is only written after the user approves it (#138).
        if pending_ask is None and writes_registry(segment):
            pending_ask = (
                "Law 38: this command writes a tool's tier to the registry "
                "(ai_tools.py set). Approve only if you approved this classification.",
                "registry-write",
            )

    # Law 28 — `dforge-update --approve` applies a hook change without the
    # terminal y; the user's click in this prompt is that approval (#170).
    if pending_ask is None and APPROVE_RE.search(scan):
        pending_ask = (
            "Law 28: this applies a Design Forge update that changes the Law 32 hook "
            "(dforge-update --approve). Approve only if you reviewed its diff and want "
            "exactly that commit installed.",
            "update-approve",
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
            for path, text in added_lines(diff):
                found = find_secret(text)
                if found:
                    block(
                        f"Blocked (Law 14): the staged diff adds what looks like {found[0]} "
                        f"in {path}. Remove it before committing.",
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

    if pending_ask:
        ask(*pending_ask)


HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(HOOKS_DIR)), "scripts")


def import_from(folder: str, name: str):
    """A sibling module of this script or of the clone's scripts/."""
    if folder not in sys.path:
        sys.path.insert(0, folder)
    sys.dont_write_bytecode = True  # keep the ~/.design-forge clone clean
    return __import__(name)


def split_mcp(tool_name: str) -> tuple[str, str] | None:
    """`mcp__<server>__<tool>` → (server, tool), split at the first `__`
    after the prefix. None if the name doesn't have both parts."""
    if not tool_name.startswith("mcp__"):
        return None
    server, sep, tool = tool_name[len("mcp__"):].partition("__")
    return (server, tool) if server and sep and tool else None


def git_toplevel(cwd: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def mcp_tier(tool_name: str, base: str) -> tuple[int, dict | None]:
    """Law 38 tier and registry entry for an MCP tool. Anything that goes
    wrong counts as tier 3: a mistake must never lower a tier."""
    try:
        parts = split_mcp(tool_name)
        if parts is None:
            return 3, None
        ai_tools = import_from(SCRIPTS_DIR, "ai_tools")
        entry, _, _ = ai_tools.lookup("mcp", parts[0], git_toplevel(base))
        tier = ai_tools.tier_for(entry, parts[1])
        return (tier, entry) if tier in (1, 2, 3, 4) else (3, None)
    except Exception:
        return 3, None


def session_approved(session_id: object, tool_name: str) -> bool:
    if not isinstance(session_id, str) or not session_id:
        return False
    try:
        return import_from(HOOKS_DIR, "ai_approvals").approved(session_id, tool_name)
    except Exception:
        return False


def check_mcp(tool_name: str, session_id: object, base: str) -> None:
    tier, entry = mcp_tier(tool_name, base)
    if tier <= 2:
        return
    parts = split_mcp(tool_name)
    label = (entry or {}).get("label") or (parts[0] if parts else tool_name)
    owner = (entry or {}).get("owner") or "none"
    if tier == 4:
        ask(
            f"Law 38: {tool_name} is tier 4 ({label}, owner {owner}). Approve only "
            "this call. Check the arguments below. Nothing carries over to the next call.",
            "tier4-unapproved",
        )
    if session_approved(session_id, tool_name):
        return
    if entry is None:
        ask(
            f"Law 38: {tool_name} is unclassified, so it counts as tier 3. Approving "
            "lets it run for the rest of the session. Run `ai classify` to give it a tier.",
            "tier3-first-use",
        )
    ask(
        f"Law 38: first use of {tool_name} this session (tier 3, owner {owner}). "
        "Approving lets this tool run for the rest of the session.",
        "tier3-first-use",
    )


def record_mcp(tool_name: str, session_id: object, base: str) -> None:
    """PostToolUse: the call ran, so the user approved it. Remember tier 3
    tools for the session. Tier 1, 2 and 4 calls are never recorded."""
    if not isinstance(session_id, str) or not session_id:
        return
    if mcp_tier(tool_name, base)[0] == 3:
        import_from(HOOKS_DIR, "ai_approvals").record(session_id, tool_name)


def log_block(blocked: Blocked, command: str, base: str, record_type: str = "block") -> None:
    """Record the block in the local block log (`hook_log.py`, #113).
    Never raises: a missing module, an unwritable log or a held lock
    must not change the decision."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        sys.dont_write_bytecode = True  # keep the ~/.design-forge clone clean
        import hook_log

        m = re.search(r"Law (\d+)", blocked.reason)
        cwd = resolve_cwd(strip_heredoc_bodies(command.strip()), base)
        hook_log.append_block(
            int(m.group(1)) if m else None, blocked.check, cwd,
            current_branch(cwd), command, record_type,
        )
    except Exception:
        pass


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return  # fail open — can't parse input
    if not isinstance(payload, dict):
        return  # fail open — not a tool-call object

    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    is_mcp = isinstance(tool, str) and tool.startswith("mcp__")
    if payload.get("hook_event_name") == "PostToolUse":
        # Runs after the call; it can't block anything and must not try.
        if is_mcp:
            try:
                cwd = payload.get("cwd")
                record_mcp(tool, payload.get("session_id"),
                           cwd if isinstance(cwd, str) and os.path.isdir(cwd) else os.getcwd())
            except Exception:
                pass
        return
    if is_mcp:
        command = tool  # what the log hashes for an MCP call
    elif tool == "Bash":
        command = tool_input.get("command")
        if not isinstance(command, str) or not command.strip():
            return
    elif tool in FILE_TOOLS:
        # What the log hashes for a file edit: the tool and its target.
        command = f"{tool} {tool_input.get('file_path') or tool_input.get('notebook_path') or ''}"
    else:
        return

    # The Bash tool's cwd. The hook process itself may sit in another
    # checkout (e.g. the main repo while the session runs in a worktree),
    # and Claude Code drops a leading `cd <cwd> &&` before calling hooks.
    base = payload.get("cwd")
    if not isinstance(base, str) or not os.path.isdir(base):
        base = os.getcwd()

    try:
        if is_mcp:
            check_mcp(tool, payload.get("session_id"), base)
        elif tool == "Bash":
            check_bash(command, base)
        else:
            check_file_edit(tool, tool_input, base)
    except Asked as asked:
        mode = payload.get("permission_mode")
        decision = "deny" if mode in ASK_DENIED_MODES else "ask"
        log_block(asked, command, base, "ask" if decision == "ask" else "block")
        reason = asked.reason if decision == "ask" else (
            asked.reason + f" In `{mode}` mode this can't be confirmed in a prompt, so it's "
            "blocked: do it yourself or switch permission mode."
        )
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }}))
        sys.exit(0)
    except Blocked as blocked:
        log_block(blocked, command, base)
        print(blocked.reason, file=sys.stderr)
        sys.exit(2)
    except Exception:
        return  # fail open — don't block on a bug in this script


if __name__ == "__main__":
    main()
