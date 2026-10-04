#!/usr/bin/env python3
"""Block log for the Law 32 hook (#113).

`enforce-laws.py` calls `append_block()` once per blocked tool call, so
false positives can be counted instead of guessed. Each line stores the
law, a fixed check id, the repo the hook judged and a hash of the
command, never the command, the commit message or the block reason.

The log rotates to `hook-log.1.jsonl` at 1 MB, and every write or
rotation holds an exclusive lock on `hook-log.lock`, so concurrent
sessions never interleave lines. If the lock isn't free within 200 ms
the line is skipped: logging must never slow down or change a decision.

CLI (the `hook log` trigger):
    python3 hook_log.py --summary
    python3 hook_log.py --false-positive "why the latest block was wrong"

Dependency-free stdlib only.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Iterator

try:
    import fcntl
except ImportError:  # Windows: append without a lock
    fcntl = None

LOG_DIR = "~/.design-forge"
LOG_NAME = "hook-log.jsonl"
OLD_NAME = "hook-log.1.jsonl"
LOCK_NAME = "hook-log.lock"
MAX_BYTES = 1_000_000
LOCK_TIMEOUT = 0.2
SUMMARY_DAYS = 30
TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def log_dir() -> str:
    return os.path.expanduser(LOG_DIR)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime(TS_FORMAT)


@contextlib.contextmanager
def locked() -> Iterator[bool]:
    """Yields True while holding the lock, False if it wasn't free in
    time. Without fcntl there's nothing to lock, so it yields True."""
    if fcntl is None:
        yield True
        return
    with open(os.path.join(log_dir(), LOCK_NAME), "a") as lock:
        deadline = time.monotonic() + LOCK_TIMEOUT
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    yield False
                    return
                time.sleep(0.01)
        try:
            yield True
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def append_record(record: dict) -> bool:
    """Append one JSON line, rotating first if the log has reached
    MAX_BYTES. Returns False when the lock wasn't free."""
    os.makedirs(log_dir(), exist_ok=True)
    path = os.path.join(log_dir(), LOG_NAME)
    with locked() as ok:
        if not ok:
            return False
        if os.path.exists(path) and os.path.getsize(path) >= MAX_BYTES:
            os.replace(path, os.path.join(log_dir(), OLD_NAME))
        with open(path, "a") as f:
            f.write(json.dumps(record) + "\n")
    return True


def append_block(law: int | None, check: str, cwd: str, branch: str | None, command: str) -> bool:
    return append_record({
        "ts": utc_now(),
        "type": "block",
        "law": law,
        "check": check,
        "cwd": cwd,
        "branch": branch,
        "command_sha256": hashlib.sha256(command.encode()).hexdigest(),
    })


def read_records() -> list[dict]:
    """Every record, oldest first: the rotated file, then the current one."""
    records = []
    for name in (OLD_NAME, LOG_NAME):
        try:
            with open(os.path.join(log_dir(), name)) as f:
                for line in f:
                    try:
                        records.append(json.loads(line))
                    except ValueError:
                        continue  # skip a damaged line, keep the rest
        except OSError:
            continue
    return records


def mark_false_positive(note: str) -> int:
    blocks = [r for r in read_records() if r.get("type") == "block"]
    if not blocks:
        print(f"No blocks in {os.path.join(log_dir(), LOG_NAME)} to mark.")
        return 1
    last = blocks[-1]
    if not append_record({
        "ts": utc_now(),
        "type": "false_positive",
        "ref_ts": last.get("ts"),
        "check": last.get("check"),
        "command_sha256": last.get("command_sha256"),
        "note": note,
    }):
        print("The hook log is locked by another session. Try again.")
        return 1
    print(
        f"Marked the block at {last.get('ts')} (Law {last.get('law')}, "
        f"{last.get('check')}, {last.get('cwd')}) as a false positive."
    )
    return 0


def summary() -> int:
    records = read_records()
    where = os.path.join(log_dir(), LOG_NAME)
    if not records:
        print(f"No hook log yet ({where}).")
        return 0
    cutoff = (datetime.now(timezone.utc) - timedelta(days=SUMMARY_DAYS)).strftime(TS_FORMAT)
    recent = [r for r in records if str(r.get("ts", "")) >= cutoff]
    blocks = [r for r in recent if r.get("type") == "block"]
    false_positives = [r for r in recent if r.get("type") == "false_positive"]
    counts: dict[tuple, int] = {}
    for r in blocks:
        key = (r.get("law"), r.get("check"))
        counts[key] = counts.get(key, 0) + 1
    print(f"Law 32 hook blocks, last {SUMMARY_DAYS} days ({where}):")
    for (law, check), n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  Law {law} · {check}: {n}")
    print(f"Total: {len(blocks)} blocks, {len(false_positives)} marked false positive.")
    for r in false_positives:
        print(f"  - {r.get('ref_ts')} {r.get('check')}: {r.get('note')}")
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["--summary"]:
        return summary()
    if argv[:1] == ["--false-positive"] and len(argv) > 1:
        return mark_false_positive(" ".join(argv[1:]))
    print("Usage: hook_log.py --summary | --false-positive NOTE", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
