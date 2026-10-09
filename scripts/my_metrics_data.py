#!/usr/bin/env python3
"""The data behind a user's private dashboard (#120).

`collect()` reads only local sources (the hook log, the Law 38 approvals,
registry and inventory, projects.yaml) and, with network=True, the user's
own merged pull requests through `gh`. Each section reads its source on its
own: a missing or broken source becomes {"error": "<what to do>"} for that
section and never stops the others. Nothing is written but the dashboard's
own state.json (pull request records and a cursor per repo).

Dependency-free stdlib only.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import statistics
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), ".claude", "hooks"))
from rules_home import rules_home  # noqa: E402  ~/.bk-charterline, or the old name (#199)

WINDOW_DAYS = 30
GH_TIMEOUT = 20  # seconds per gh call
GH_BUDGET = 60  # seconds for every project together
TIERED = ("mcp", "extension", "plugin")
CRITICAL_CHECK, HIGH_CHECK = "tier4-unapproved", "tier3-first-use"


def parse_ts(ts: str) -> datetime.datetime:
    return datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


def read_jsonl(path: str) -> list[dict]:
    rows = []
    with open(path) as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue  # one damaged line never hides the rest
    return rows


def section(fn, *args, missing: str):
    """Run one section; a missing file or bad data becomes an error message."""
    try:
        return fn(*args)
    except FileNotFoundError:
        return {"error": missing}
    except Exception as e:  # noqa: BLE001  a dashboard must never stop an update or a session
        return {"error": f"Couldn't read this ({e.__class__.__name__})."}


def hook_activity(home: str, since: datetime.datetime) -> dict:
    blocks, asks, days, calls, false_positives = {}, {}, {}, [], 0
    for r in read_jsonl(os.path.join(home, "hook-log.jsonl")):
        try:
            ts = parse_ts(r["ts"])
        except (KeyError, ValueError, TypeError):
            continue
        if r.get("type") == "false_positive":  # marks a block; it isn't one
            try:  # counted with the block it marks, so the share stays within 100%
                false_positives += parse_ts(r["ref_ts"]) >= since
            except (KeyError, ValueError, TypeError):
                pass
            continue
        if ts < since:
            continue
        if r.get("type") not in ("block", "ask"):
            continue
        days[ts.strftime("%Y-%m-%d")] = days.get(ts.strftime("%Y-%m-%d"), 0) + 1
        if r.get("type") == "ask":
            asks[r.get("check")] = asks.get(r.get("check"), 0) + 1
            if r.get("tool") and r.get("check") in (CRITICAL_CHECK, HIGH_CHECK):
                calls.append({"ts": r["ts"], "tool": r["tool"], "critical": r["check"] == CRITICAL_CHECK})
        else:
            key = f"{r.get('law')}|{r.get('check')}"
            blocks[key] = blocks.get(key, 0) + 1
    # Approvals from before the hook named its tools (#120) fill the gaps.
    try:
        logged = [(parse_ts(c["ts"]), c["tool"]) for c in calls]
        for a in read_jsonl(os.path.join(home, "ai-approvals.jsonl")):
            ts = parse_ts(a["ts"])
            if ts >= since and not any(t == a["tool"] and abs((ts - lt).total_seconds()) < 300 for lt, t in logged):
                calls.append({"ts": a["ts"], "tool": a["tool"], "critical": False})
    except FileNotFoundError:
        pass
    return {
        "blocks": [{"law": int(k.split("|")[0]) if k.split("|")[0].isdigit() else None, "check": k.split("|")[1], "count": n}
                   for k, n in sorted(blocks.items(), key=lambda kv: -kv[1])],
        "asks": [{"check": k, "count": n} for k, n in sorted(asks.items(), key=lambda kv: -kv[1])],
        "days": [{"day": d, "count": n} for d, n in sorted(days.items())],
        "calls": sorted(calls, key=lambda c: c["ts"], reverse=True),
        "false_positives": false_positives,
    }


def tools(home: str) -> dict:
    with open(os.path.join(home, "ai-tools.json")) as f:
        registry = json.load(f).get("tools", {})
    listed = [{"key": k, "label": v.get("label") or k.split(":", 1)[-1], "tier": v.get("tier", 3),
               "overrides": v.get("overrides") or {}} for k, v in sorted(registry.items())]
    unrated = []
    try:
        with open(os.path.join(home, "ai-inventory.json")) as f:
            for key in json.load(f):
                kind, _, name = key.split("|", 2)
                if kind in TIERED and f"{kind}:{name}" not in registry:
                    unrated.append(name)
    except FileNotFoundError:
        pass
    unrated = sorted(set(unrated))
    return {"tools": listed, "unrated": unrated, "classified": len(listed), "known": len(listed) + len(unrated)}


def registered_projects(home: str) -> list[dict]:
    """name and repo of each project in projects.yaml, without a YAML library."""
    projects, current = [], None
    with open(os.path.join(home, "projects.yaml")) as f:
        for line in f:
            text = line.split("#", 1)[0].rstrip()
            if text.lstrip().startswith("- name:"):
                current = {"name": text.split(":", 1)[1].strip(), "repo": None}
                projects.append(current)
            elif current is not None and text.strip().startswith("repo:"):
                current["repo"] = text.split(":", 1)[1].strip() or None
    return [p for p in projects if p["repo"]]


def gh_merged(gh: str, repo: str, since: str) -> list[dict]:
    done = subprocess.run([gh, "pr", "list", "--repo", repo, "--state", "merged", "--limit", "500",
                           "--search", f"merged:>={since[:10]}",
                           "--json", "number,additions,deletions,createdAt,mergedAt,title,body"],
                          capture_output=True, text=True, timeout=GH_TIMEOUT)
    if done.returncode != 0:
        raise RuntimeError(done.stderr.strip()[:120] or "gh failed")
    return json.loads(done.stdout)


def pull_requests(home: str, gh: str, now: datetime.datetime, network: bool) -> dict:
    state_path = os.path.join(home, "dashboard", "state.json")
    try:
        with open(state_path) as f:
            state = json.load(f)
    except (OSError, ValueError):
        state = {}
    repos = state.setdefault("repos", {})
    since = now - datetime.timedelta(days=WINDOW_DAYS)
    started, out = time.monotonic(), []
    for project in registered_projects(home):
        repo = project["repo"]
        known = repos.setdefault(repo, {"cursor": None, "prs": {}})
        error = None
        if network:
            if time.monotonic() - started > GH_BUDGET:
                error = "Couldn't reach GitHub this time."
            else:
                try:
                    cursor = known["cursor"] or since.strftime("%Y-%m-%dT%H:%M:%SZ")
                    for p in gh_merged(gh, repo, cursor):
                        known["prs"][str(p["number"])] = {
                            "lines": p["additions"] + p["deletions"], "created": p["createdAt"], "merged": p["mergedAt"],
                            "revert": p["title"].startswith('Revert "'), "claude": "Claude Code" in (p.get("body") or ""),
                        }
                    newest = max((p["merged"] for p in known["prs"].values()), default=None)
                    known["cursor"] = newest or known["cursor"]
                except FileNotFoundError:
                    error = "Install the GitHub CLI and sign in with gh auth login to see pull request numbers."
                except (RuntimeError, subprocess.TimeoutExpired, ValueError):
                    error = "Sign in with gh auth login to see pull request numbers."
        recent = [p for p in known["prs"].values() if parse_ts(p["merged"]) >= since]
        lines = [p["lines"] for p in recent]
        hours = [(parse_ts(p["merged"]) - parse_ts(p["created"])).total_seconds() / 3600 for p in recent]
        out.append({
            "name": project["name"], "repo": repo, "error": error, "merged": len(recent),
            "median_lines": round(statistics.median(lines)) if lines else None,
            "within_400": round(100 * sum(1 for n in lines if n <= 400) / len(lines)) if lines else None,
            "median_hours": round(statistics.median(hours), 2) if hours else None,
            "reverts": sum(1 for p in recent if p["revert"]),
            "claude_share": round(100 * sum(1 for p in recent if p["claude"]) / len(recent)) if recent else None,
            "sizes": lines,
        })
    if network:
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        tmp = state_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state, f, indent=1, sort_keys=True)
        os.replace(tmp, state_path)
    return {"projects": out}


def rules_tokens(repo_root: str) -> dict:
    sys.path.insert(0, os.path.join(repo_root, "scripts"))
    import laws_cost
    total = 0
    for name in laws_cost.FILES:
        with open(os.path.join(repo_root, name), encoding="utf-8") as f:
            total += laws_cost.estimate(name, len(f.read().encode("utf-8")))
    return {"tokens": total}


TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
IMPORT_RE = re.compile(r"^@\./(\S+)$", re.MULTILINE)


def rules_cost(home: str, repo_root: str) -> dict:
    """Tokens each release loads into every session (#256): its CLAUDE.md and the
    files that imports, read at the release's own tag. Tags never move, so each is
    measured once and kept in dashboard/rules-cost.json."""
    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", home, *args], capture_output=True, text=True, timeout=GH_TIMEOUT)

    listed = git("tag", "-l", "v*")
    if listed.returncode != 0:
        raise FileNotFoundError(home)
    tags = sorted((t for t in listed.stdout.split() if TAG_RE.match(t)), key=lambda t: tuple(map(int, TAG_RE.match(t).groups())))
    cache_path = os.path.join(home, "dashboard", "rules-cost.json")
    try:
        with open(cache_path) as f:
            cache = json.load(f)
    except (OSError, ValueError):
        cache = {}
    sys.path.insert(0, os.path.join(repo_root, "scripts"))
    import laws_cost
    for tag in tags:
        if isinstance(cache.get(tag), int):
            continue
        main = git("show", f"{tag}:CLAUDE.md")
        if main.returncode != 0:
            continue
        total = laws_cost.estimate("CLAUDE.md", len(main.stdout.encode("utf-8")))
        for name in IMPORT_RE.findall(main.stdout):
            part = git("show", f"{tag}:{name}")
            if part.returncode == 0:
                size = len(part.stdout.encode("utf-8"))
                total += laws_cost.estimate(name, size) if name in laws_cost.FILES else round(size / 2.7)
        cache[tag] = total
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    tmp = f"{cache_path}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(cache, f, indent=1, sort_keys=True)
    os.replace(tmp, cache_path)
    return {"releases": [{"tag": t, "tokens": cache[t]} for t in tags if t in cache]}


def collect(home: str | None = None, *, network: bool = True, gh: str = "gh",
            now: datetime.datetime | None = None) -> dict:
    home = home or rules_home()
    now = now or datetime.datetime.now(datetime.timezone.utc)
    since = now - datetime.timedelta(days=WINDOW_DAYS)
    return {
        "generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": WINDOW_DAYS,
        "activity": section(hook_activity, home, since, missing="Your first blocked or approved call shows up here."),
        "tools": section(tools, home, missing="Run ai inventory, then ai classify, to see your tools here."),
        "pull_requests": section(pull_requests, home, gh, now, network,
                                 missing="Register a project in projects.yaml to see its pull requests here."),
        "rules": section(rules_tokens, os.path.dirname(HERE), missing="The rules' size couldn't be measured."),
        "rules_cost": section(rules_cost, home, os.path.dirname(HERE), missing="The rules' release history couldn't be read."),
    }


if __name__ == "__main__":
    print(json.dumps(collect(network="--local-only" not in sys.argv), indent=1))
