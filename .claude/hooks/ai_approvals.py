#!/usr/bin/env python3
"""Per-session Law 38 tier 3 approvals for MCP tools (#138).

The Law 32 hook asks before the first call of a tier 3 MCP tool in a
session. Once a call has actually run (the user approved it in Claude
Code's own permission prompt), the hook's PostToolUse step calls
`record()`, and later calls of that tool in the same session pass
`approved()`. Nothing else should write this file: Claude writing to it
asks the user first, because it's a guardrail file (#117).

Each line stores the time, the session id and the full tool name, never
the call's arguments or output. Writes hold the block log's lock
(`hook_log.locked()`) and drop lines older than 7 days. If the lock
isn't free, the record is skipped and the next call simply asks again.

Dependency-free stdlib only.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import hook_log

APPROVALS_NAME = "ai-approvals.jsonl"
KEEP_DAYS = 7


def approvals_path() -> str:
    return os.path.join(hook_log.log_dir(), APPROVALS_NAME)


def _valid(record: object) -> bool:
    return (
        isinstance(record, dict)
        and isinstance(record.get("session"), str) and bool(record["session"])
        and isinstance(record.get("tool"), str) and bool(record["tool"])
        and isinstance(record.get("ts"), str)
    )


def _read() -> list[dict]:
    """Every well-formed line; a missing or unreadable file has none."""
    try:
        with open(approvals_path()) as f:
            lines = f.readlines()
    except OSError:
        return []
    records = []
    for line in lines:
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if _valid(record):
            records.append(record)
    return records


def approved(session_id: str, tool: str) -> bool:
    if not session_id or not tool:
        return False
    return any(r["session"] == session_id and r["tool"] == tool for r in _read())


def _fresh(record: dict, cutoff: datetime) -> bool:
    try:
        ts = datetime.strptime(record["ts"], hook_log.TS_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return ts >= cutoff


def record(session_id: str, tool: str) -> bool:
    """Record that `tool` ran in `session_id`. Returns False when there's
    nothing to record or the lock wasn't free."""
    if not session_id or not tool:
        return False
    os.makedirs(hook_log.log_dir(), exist_ok=True)
    path = approvals_path()
    with hook_log.locked() as ok:
        if not ok:
            return False
        cutoff = datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)
        kept = [r for r in _read() if _fresh(r, cutoff)]
        if any(r["session"] == session_id and r["tool"] == tool for r in kept):
            return True  # every later call runs PostToolUse too; keep one line
        kept.append({"ts": hook_log.utc_now(), "session": session_id, "tool": tool})
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in kept)
        os.replace(tmp, path)
    return True
