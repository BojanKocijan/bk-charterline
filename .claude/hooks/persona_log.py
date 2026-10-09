#!/usr/bin/env python3
"""UserPromptSubmit hook (#256): log which persona a session switched to.

When the whole prompt is one of CLAUDE.md's mode commands (case and spacing
ignored), it appends {"ts", "session_id", "persona"} to
~/.bk-charterline/persona-log.jsonl (rotated to persona-log.1.jsonl at 1 MB), so the private dashboard can count
sessions per persona after Claude Code removes old session logs. The prompt's
text is never written. Any other prompt writes nothing.

It never blocks, never prints, and ignores every error: exit 0 always.
Dependency-free stdlib only.
"""
from __future__ import annotations

import datetime
import json
import os
import sys

sys.dont_write_bytecode = True

# The trigger phrases in CLAUDE.md, typed as the whole prompt. scripts/my_metrics_sessions.py reads them too.
TRIGGERS = {"frontend mode": "Frontend", "fullstack mode": "Lead", "team": "Lead", "build feature": "Lead",
            "backend mode": "Backend", "tester mode": "Tester", "research mode": "Research",
            "research mode full": "Research", "analyst mode": "Analyst", "incident mode": "Incident"}
LOG_NAME = "persona-log.jsonl"
ROTATED_NAME = "persona-log.1.jsonl"  # like hook-log.jsonl: one rotated file, so the log never grows past ~2 MB
MAX_BYTES = 1_000_000


def persona_of(prompt: object) -> str | None:
    return TRIGGERS.get(" ".join(prompt.split()).casefold()) if isinstance(prompt, str) else None


def main() -> None:
    try:
        event = json.load(sys.stdin)
        persona = persona_of(event.get("prompt"))
        if not persona:
            return
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from rules_home import rules_home
        record = {"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "session_id": str(event.get("session_id") or "")[:100], "persona": persona}
        path = os.path.join(rules_home(), LOG_NAME)
        if os.path.exists(path) and os.path.getsize(path) > MAX_BYTES:
            os.replace(path, os.path.join(rules_home(), ROTATED_NAME))
        with open(path, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:  # noqa: BLE001  a log must never get in the way of a prompt
        pass


if __name__ == "__main__":
    main()
    sys.exit(0)
