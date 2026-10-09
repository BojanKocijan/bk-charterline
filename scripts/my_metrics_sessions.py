#!/usr/bin/env python3
"""Sessions, skills and personas for a user's private dashboard (#256, #198).

Reads Claude Code's own session logs on this machine
(`~/.claude/projects/*/*.jsonl`, and each session's `subagents/` files) and
keeps counts only: tokens, skill runs, subagent runs and the personas a
session switched to. A prompt's text, a file name or a path is never stored.

Incremental: `dashboard/sessions-state.json` keeps one summary per log file,
keyed by path with its size and mtime, so a file is read again only when it
changes. Only lines that can hold a count are parsed as JSON.

Dependency-free stdlib only.
"""
from __future__ import annotations

import datetime
import glob
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".claude", "hooks"))
from persona_log import LOG_NAME, persona_of  # noqa: E402  the mode commands, shared with the hook

# The persona subagents in agents/.
SUBAGENTS = {"frontend": "Frontend", "fullstack": "Lead", "lead": "Lead", "backend": "Backend", "tester": "Tester",
             "design": "Design", "research": "Research", "analyst": "Analyst", "incident": "Incident"}
DEFAULT_PERSONA = "Frontend"
WANTED = ('"usage"', '"tool_use"', '"type":"user"')


def logs_dir() -> str:
    return os.path.join(os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"), "projects")


def prompt_text(content) -> str | None:
    """The text a person typed, or None for tool results and attachments."""
    if isinstance(content, str):
        return content
    if isinstance(content, list) and all(isinstance(c, dict) and c.get("type") == "text" for c in content):
        return "".join(c.get("text", "") for c in content)
    return None


def summarize(path: str) -> dict:
    """Counts for one log file. Each reply's usage is logged once per content
    block, so it is counted once, by message id."""
    usage, skills, subagents, personas, first, last = {}, {}, {}, set(), None, None
    with open(path, errors="replace") as f:
        for line in f:
            if not any(k in line for k in WANTED):
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if not isinstance(d, dict):
                continue
            ts = d.get("timestamp")
            if isinstance(ts, str):
                first, last = first or ts, ts
            m = d.get("message")
            if not isinstance(m, dict):
                continue
            if d.get("type") == "assistant":
                u = m.get("usage")
                if isinstance(u, dict):
                    usage[m.get("id") or len(usage)] = sum(v for k, v in u.items() if k.endswith("_tokens") and isinstance(v, int))
                for c in m.get("content") if isinstance(m.get("content"), list) else []:
                    if not isinstance(c, dict) or c.get("type") != "tool_use" or not isinstance(c.get("input"), dict):
                        continue
                    if c.get("name") == "Skill" and isinstance(c["input"].get("skill"), str):
                        skills[c["input"]["skill"]] = skills.get(c["input"]["skill"], 0) + 1
                    elif c.get("name") in ("Agent", "Task") and isinstance(c["input"].get("subagent_type"), str):
                        subagents[c["input"]["subagent_type"]] = subagents.get(c["input"]["subagent_type"], 0) + 1
            elif d.get("type") == "user":
                persona = persona_of(prompt_text(m.get("content")))
                if persona:
                    personas.add(persona)
    return {"first": first, "last": last, "tokens": sum(usage.values()), "skills": skills,
            "subagents": subagents, "personas": sorted(personas)}


def session_of(path: str, root: str) -> str:
    """A main log is <project>/<session>.jsonl; a subagent's is <project>/<session>/subagents/<agent>.jsonl."""
    parts = os.path.relpath(path, root).split(os.sep)
    return parts[1] if len(parts) > 2 else parts[-1][:-len(".jsonl")]


def parse(ts: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def sessions(home: str, now: datetime.datetime, since: datetime.datetime, root: str | None = None) -> dict:
    root = root or logs_dir()
    if not os.path.isdir(root):
        raise FileNotFoundError(root)
    state_path = os.path.join(home, "dashboard", "sessions-state.json")
    try:
        with open(state_path) as f:
            state = json.load(f)
    except (OSError, ValueError):
        state = {}
    files, skipped = {}, 0
    for path in glob.glob(os.path.join(root, "*", "*.jsonl")) + glob.glob(os.path.join(root, "*", "*", "subagents", "*.jsonl")):
        try:
            st = os.stat(path)
        except OSError:
            continue
        if st.st_mtime < since.timestamp():
            continue
        known = state.get(path)
        if known and known.get("size") == st.st_size and known.get("mtime") == int(st.st_mtime):
            files[path] = known
            continue
        try:
            files[path] = {"size": st.st_size, "mtime": int(st.st_mtime), "summary": summarize(path)}
        except (OSError, UnicodeError):
            skipped += 1
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    tmp = f"{state_path}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(files, f, sort_keys=True)  # files gone from disk or the window drop out
    os.replace(tmp, state_path)

    merged = {}
    for path, entry in files.items():
        s, m = entry["summary"], merged.setdefault(session_of(path, root), {"tokens": 0, "skills": {}, "subagents": {}, "personas": set(), "first": None, "last": None})
        m["tokens"] += s["tokens"]
        for key in ("skills", "subagents"):
            for name, n in s[key].items():
                m[key][name] = m[key].get(name, 0) + n
        m["personas"].update(s["personas"])
        if s["first"] and (m["first"] is None or s["first"] < m["first"]):
            m["first"] = s["first"]
        if s["last"] and (m["last"] is None or s["last"] > m["last"]):
            m["last"] = s["last"]
    logged = persona_log(home, since)
    for sid, personas in logged.items():  # a session whose log Claude Code already removed still counts
        merged.setdefault(sid, {"tokens": None, "skills": {}, "subagents": {}, "personas": set(), "first": None, "last": None})["personas"].update(personas)
    out = []
    for sid, m in merged.items():
        if m["tokens"] is None:
            out.append(m)
            continue
        try:
            if m["first"] is None or parse(m["last"]) < since:
                continue
        except ValueError:
            continue
        m["personas"].update(SUBAGENTS[a] for a in m["subagents"] if a in SUBAGENTS)
        out.append(m)
    return summary(out, skipped)


def persona_log(home: str, since: datetime.datetime) -> dict[str, set]:
    """session id -> personas, from the hook's log (#256)."""
    out = {}
    try:
        with open(os.path.join(home, LOG_NAME)) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    if parse(r["ts"]) >= since and r.get("session_id") and r.get("persona"):
                        out.setdefault(r["session_id"], set()).add(r["persona"])
                except (ValueError, KeyError, TypeError, AttributeError):
                    continue
    except OSError:
        pass
    return out


def summary(found: list[dict], skipped: int) -> dict:
    personas, skills, weeks = {}, {}, {}
    for m in found:
        for p in m["personas"] or {DEFAULT_PERSONA}:
            personas[p] = personas.get(p, 0) + 1
        if m["tokens"] is None:  # known from the persona log only
            continue
        for name, n in m["skills"].items():
            skills[name] = skills.get(name, 0) + n
        start = parse(m["first"]).date()
        week = (start - datetime.timedelta(days=start.weekday())).isoformat()
        weeks.setdefault(week, []).append(m["tokens"])
    tokens = [m["tokens"] for m in found if m["tokens"] is not None]
    return {
        "sessions": len(tokens),
        "median_tokens": round(statistics.median(tokens)) if tokens else None,
        "weekly": [{"week": w, "median": round(statistics.median(t))} for w, t in sorted(weeks.items())],
        "personas": [{"persona": p, "sessions": n} for p, n in sorted(personas.items(), key=lambda kv: (-kv[1], kv[0]))],
        "skills": [{"skill": s, "runs": n} for s, n in sorted(skills.items(), key=lambda kv: (-kv[1], kv[0]))],
        "skipped": skipped,
    }
