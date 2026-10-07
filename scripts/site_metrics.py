#!/usr/bin/env python3
"""The real numbers on the Design Forge page (#177).

Counts come from the repo and merged-PR numbers from `gh`. They go to
`site/data.js`, which the page loads with a <script> tag (a browser won't
fetch local JSON from a page opened from disk), and to the `data-metric`
fallbacks in `site/index.html`. Incremental, as #177 asks:
`site/metrics-state.json` keeps one record per merged PR, and each run asks
`gh` only for PRs merged since the newest one seen. A number keeps its date
until its value changes. Public data only.

    python3 scripts/site_metrics.py [--today YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from datetime import date

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import laws_cost  # noqa: E402  the rules' token estimate (#188)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join("site", "data.js")
STATE = os.path.join("site", "metrics-state.json")
PAGE = os.path.join("site", "index.html")
PR_LIMIT = "5000"
PERCENTS = ("prs_within_400",)

RELEASE_TAG_RE = re.compile(r"^v\d+\.\d+\.\d+$")
LAW_RE = re.compile(r"^\d+\. \*\*", re.MULTILINE)  # `5a.` and nested lists don't count
TEST_RE = re.compile(r"^\s*def test_", re.MULTILINE)
SPAN_RE = re.compile(r'(<span\b[^>]*\bdata-metric="(\w+)"[^>]*>)[^<]*(</span>)')
TIME_RE = re.compile(r"<time\b([^>]*)>[^<]*</time>")
DATE_NAME_RE = re.compile(r'\bdata-metric-date="(\w+)"')
DATETIME_RE = re.compile(r'\s*\bdatetime="[^"]*"')


def read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def repo_counts(root: str) -> dict[str, int]:
    tags = subprocess.run(["git", "-C", root, "tag", "-l", "v*"], capture_output=True,
                          text=True, check=True).stdout.split()
    tests = sum(len(TEST_RE.findall(read(p))) for p in glob.glob(os.path.join(root, "tests", "test_*.py")))
    tokens = sum(laws_cost.estimate(name, len(read(os.path.join(root, name)).encode("utf-8")))
                 for name in laws_cost.FILES)
    return {
        "releases": sum(1 for t in tags if RELEASE_TAG_RE.match(t)),
        "laws": len(LAW_RE.findall(read(os.path.join(root, "CLAUDE_LAWS.md")))),
        "skills": len(glob.glob(os.path.join(root, "skills", "*", "SKILL.md"))),
        "agents": len(glob.glob(os.path.join(root, "agents", "*.md"))),
        "guides": len([p for p in glob.glob(os.path.join(root, "knowledge", "*.md"))
                       if not p.endswith(".example.md")]),
        "tests": tests,
        "rules_tokens": tokens,
    }


def fetch_prs(root: str, gh: str, since: str | None) -> list[dict]:
    """Merged PRs from `gh`, all of them when `since` is None. Raises
    RuntimeError when `gh` fails, so nothing is written."""
    cmd = [gh, "pr", "list", "--state", "merged", "--limit", PR_LIMIT,
           "--json", "number,additions,deletions,mergedAt"]
    if since:
        cmd += ["--search", f"merged:>={since[:10]}"]
    try:
        done = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise RuntimeError(f"gh didn't run ({e.__class__.__name__})")
    if done.returncode != 0:
        raise RuntimeError(f"gh failed: {done.stderr.strip()[:200] or done.returncode}")
    return json.loads(done.stdout)


def median(values: list[int]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    if not n:
        return 0
    return ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2


def pr_numbers(prs: dict[str, dict]) -> dict[str, int]:
    lines = [p["lines"] for p in prs.values()]
    within = sum(1 for n in lines if n <= 400)
    return {
        "prs_merged": len(lines),
        "median_pr_lines": round(median(lines)),
        "prs_within_400": round(100 * within / len(lines)) if lines else 0,
    }


def format_value(name: str, value: int) -> str:
    return f"{value}%" if name in PERCENTS else f"{value:,}"


def format_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d:%b} {d.day}, {d.year}"


def fill_html(html: str, numbers: dict[str, dict]) -> str:
    """Each `data-metric` span gets its formatted value and each
    `data-metric-date` time its date. Unknown names are left alone."""
    def span(m: re.Match) -> str:
        n = numbers.get(m.group(2))
        return f"{m.group(1)}{format_value(m.group(2), n['value'])}{m.group(3)}" if n else m.group(0)

    def when(m: re.Match) -> str:
        name = DATE_NAME_RE.search(m.group(1))
        n = numbers.get(name.group(1)) if name else None
        if not n:
            return m.group(0)
        attrs = DATETIME_RE.sub("", m.group(1)) + f' datetime="{n["as_of"]}"'
        return f"<time{attrs}>{format_date(n['as_of'])}</time>"

    return TIME_RE.sub(when, SPAN_RE.sub(span, html))


def one_per_line(mapping: dict) -> str:
    """JSON with one entry per line, so a diff shows each new PR or
    changed number as one line."""
    rows = [f"  {json.dumps(k)}: {json.dumps(v, sort_keys=True)}" for k, v in mapping.items()]
    return "{\n" + ",\n".join(rows) + "\n}" if rows else "{}"


def render_data(numbers: dict[str, dict]) -> str:
    body = one_per_line(dict(sorted(numbers.items())))
    return ("// Generated by scripts/site_metrics.py; don't edit by hand (#177).\n"
            f'window.DF_METRICS = {{"numbers": {body}}};\n')


def render_state(newest: str | None, numbers: dict[str, dict], prs: dict[str, dict]) -> str:
    ordered = dict(sorted(prs.items(), key=lambda kv: int(kv[0])))
    return (f'{{"collected_through": {json.dumps(newest)},\n'
            f'"numbers": {one_per_line(dict(sorted(numbers.items())))},\n'
            f'"prs": {one_per_line(ordered)}}}\n')


def write_if_changed(path: str, text: str) -> bool:
    if os.path.exists(path) and read(path) == text:
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)
    return True


def update(root: str, gh: str, today: str) -> bool:
    """Collect, then write every file that changed. True if any did."""
    state_path = os.path.join(root, STATE)
    state = json.loads(read(state_path)) if os.path.exists(state_path) else {}
    prs = dict(state.get("prs", {}))
    for p in fetch_prs(root, gh, state.get("collected_through")):
        prs[str(p["number"])] = {"lines": p["additions"] + p["deletions"], "merged_at": p["mergedAt"]}

    old = state.get("numbers", {})
    numbers = {}
    for name, value in {**repo_counts(root), **pr_numbers(prs)}.items():
        kept = old.get(name, {})
        numbers[name] = {"value": value, "as_of": kept["as_of"] if kept.get("value") == value else today}

    newest = max((p["merged_at"] for p in prs.values()), default=None)
    changed = write_if_changed(state_path, render_state(newest, numbers, prs))
    changed |= write_if_changed(os.path.join(root, DATA), render_data(numbers))
    page = os.path.join(root, PAGE)
    if os.path.exists(page):
        changed |= write_if_changed(page, fill_html(read(page), numbers))
    return changed


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Refresh the real numbers on the Design Forge page.")
    parser.add_argument("--root", default=ROOT, help="the Design Forge repo (default: this checkout)")
    parser.add_argument("--gh", default="gh", help="the GitHub CLI to use")
    parser.add_argument("--today", default=date.today().isoformat(), help="the date a changed number gets")
    args = parser.parse_args(argv)
    try:
        changed = update(args.root, args.gh, args.today)
    except (RuntimeError, OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as e:
        print(f"site_metrics: {e}; nothing was written", file=sys.stderr)
        return 1
    print("site_metrics: updated site/" if changed else "site_metrics: nothing changed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
