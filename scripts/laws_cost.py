#!/usr/bin/env python3
"""What loading the rules costs every session (#188).

    python3 scripts/laws_cost.py [--budget N]
    python3 scripts/laws_cost.py --measure [--claude PATH] [--model NAME]

Run from the repo root. Every Claude Code session under Design Forge
loads CLAUDE.md and CLAUDE_LAWS.md (through `~/.claude/CLAUDE.md`)
before the first message, so their size is paid on every session.

The default prints each file's bytes, words and estimated tokens, and
the total. The estimate is bytes / BYTES_PER_TOKEN, a ratio per file
taken from the last --measure run. With --budget N it also prints a GitHub Actions
`::warning::` when the total passes N tokens and still exits 0: a
release over budget is the owner's decision, not a red build.

--measure counts the same files exactly. In an empty temp folder it
runs the `claude` CLI headless: once as is, once with a one-character
appended system prompt, and once with each file appended. A file's
count is its run's input tokens (fresh, cache write and cache read
added up) minus the one-character run's, which cancels the appended
prompt's own wrapper; repeat runs agree to about ten tokens. It uses
the owner's logged-in account and refuses to run when CI is set;
tests never call it.

Dependency-free stdlib only.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

# From --measure on claude-opus-5-5 at v2.35.0 (docs/features/issue-188/report.md).
# CLAUDE.md's tables and links make it denser than the laws' prose.
BYTES_PER_TOKEN = {"CLAUDE.md": 2.423, "CLAUDE_LAWS.md": 2.772}
FILES = tuple(BYTES_PER_TOKEN)
PROMPT = "Reply with exactly: ok"
MARKER = "."


def sizes(paths: tuple[str, ...] = FILES) -> list[tuple[str, int, int]]:
    """(path, bytes, words) for each file."""
    out = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        out.append((path, len(text.encode("utf-8")), len(text.split())))
    return out


def estimate(path: str, n_bytes: int) -> int:
    return round(n_bytes / BYTES_PER_TOKEN[path])


def table(rows: list[tuple[str, int, int, int]], last: str) -> str:
    lines = [f"{'file':<16}{'bytes':>9}{'words':>8}{last:>16}"]
    for name, b, w, t in rows:
        lines.append(f"{name:<16}{b:>9,}{w:>8,}{t:>16,}")
    return "\n".join(lines)


def run_estimate(budget: int | None) -> int:
    try:
        found = sizes()
    except OSError as e:
        print(f"{e.filename}: can't read it ({e.strerror}); run from the repo root", file=sys.stderr)
        return 1
    rows = [(p, b, w, estimate(p, b)) for p, b, w in found]
    total = sum(r[3] for r in rows)
    rows.append(("total", sum(r[1] for r in rows), sum(r[2] for r in rows), total))
    print(table(rows, "tokens (est.)"))
    print("\nEstimate: bytes / bytes per token, measured per file with --measure.")
    if budget is not None:
        if total > budget:
            print(f"::warning title=Rules token budget::CLAUDE.md + CLAUDE_LAWS.md are about "
                  f"{total:,} tokens, over the {budget:,} budget (#188). Every session pays this; "
                  f"cut something, or raise the budget on purpose.")
        else:
            print(f"Within the {budget:,}-token budget.")
    return 0


def input_tokens(result: dict) -> int:
    """All input tokens of one `claude -p --output-format json` result."""
    u = result.get("usage") or {}
    return sum(int(u.get(k) or 0) for k in
               ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))


def main_model(result: dict) -> str:
    """The model that read the most input tokens in the run."""
    usage = result.get("modelUsage") or {}
    if not usage:
        return "unknown"
    return max(usage, key=lambda m: sum(int(usage[m].get(k) or 0) for k in
               ("inputTokens", "cacheReadInputTokens", "cacheCreationInputTokens")))


def exact_counts(marker_run: dict, file_runs: dict[str, dict]) -> dict[str, int]:
    """Each file's exact token count: its run minus the one-character run."""
    base = input_tokens(marker_run)
    return {path: input_tokens(r) - base for path, r in file_runs.items()}


def call_claude(claude: str, cwd: str, append: str | None, model: str | None) -> dict:
    cmd = [claude, "-p", PROMPT, "--output-format", "json", "--no-session-persistence",
           "--tools", "", "--strict-mcp-config", "--max-turns", "1"]
    if model:
        cmd += ["--model", model]
    if append is not None:
        cmd += ["--append-system-prompt", append]
    done = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=600)
    try:
        result = json.loads(done.stdout)
    except ValueError:
        result = None
    if done.returncode != 0 or not isinstance(result, dict) or result.get("is_error"):
        tail = (done.stderr or done.stdout).strip().splitlines()[-1:] or ["no output"]
        raise RuntimeError(f"claude exited {done.returncode}: {tail[0]}")
    return result


def run_measure(claude: str | None, model: str | None) -> int:
    if os.environ.get("CI"):
        print("--measure uses the owner's logged-in account; it refuses to run in CI.", file=sys.stderr)
        return 2
    claude = claude or shutil.which("claude")
    if not claude:
        print("No `claude` CLI on PATH; pass --claude PATH.", file=sys.stderr)
        return 2
    try:
        found = sizes()
        texts = {}
        for path in FILES:
            with open(path, encoding="utf-8") as f:
                texts[path] = f.read()
    except OSError as e:
        print(f"{e.filename}: can't read it ({e.strerror}); run from the repo root", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as empty:
        try:
            bare = call_claude(claude, empty, None, model)
            marker = call_claude(claude, empty, MARKER, model)
            runs = {path: call_claude(claude, empty, texts[path], model) for path in FILES}
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as e:
            print(f"Measuring failed: {e}", file=sys.stderr)
            return 1

    counts = exact_counts(marker, runs)
    rows = [(p, b, w, counts[p]) for p, b, w in found]
    total_bytes = sum(r[1] for r in rows)
    total = sum(counts.values())
    rows.append(("total", total_bytes, sum(r[2] for r in rows), total))
    print(f"Model: {main_model(bare)}")
    print(f"Minimal session (no tools, no MCP): {input_tokens(bare):,} input tokens, "
          f"${float(bare.get('total_cost_usd') or 0):.4f} at list price")
    print(f"Appended-prompt wrapper: {input_tokens(marker) - input_tokens(bare):,} tokens, subtracted\n")
    print(table(rows, "tokens (exact)"))
    print("\nBytes per token, for BYTES_PER_TOKEN: " + ", ".join(
        f"{p} {b / counts[p]:.3f}" for p, b, _ in found))
    print("Raw input tokens per run: " + ", ".join(
        f"{name} {input_tokens(r):,}" for name, r in
        (("bare", bare), ("marker", marker), *runs.items())))
    return 0


def main(argv: list[str]) -> int:
    usage = "usage: laws_cost.py [--budget N] | --measure [--claude PATH] [--model NAME]"
    budget = claude = model = None
    measure = False
    args = list(argv)
    try:
        while args:
            flag = args.pop(0)
            if flag == "--measure":
                measure = True
            elif flag == "--budget":
                budget = int(args.pop(0))
            elif flag == "--claude":
                claude = args.pop(0)
            elif flag == "--model":
                model = args.pop(0)
            else:
                raise ValueError(flag)
    except (IndexError, ValueError):
        print(usage, file=sys.stderr)
        return 2
    if measure and budget is not None or not measure and (claude or model):
        print(usage, file=sys.stderr)
        return 2
    return run_measure(claude, model) if measure else run_estimate(budget)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
