#!/usr/bin/env python3
"""Tests for scripts/my_metrics_sessions.py (#256, #198): counts from Claude
Code's session logs, kept incrementally, with no prompt text stored."""
from __future__ import annotations

import datetime
import json
import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import my_metrics_sessions as sessions  # noqa: E402

NOW = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
SINCE = NOW - datetime.timedelta(days=30)
MARKER = "SECRET-PROMPT-MARKER /Users/alice/private/plan.txt"


def ts(days: float) -> str:
    return (NOW - datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def user(text, days: float) -> dict:
    return {"type": "user", "timestamp": ts(days), "message": {"role": "user", "content": text}}


def reply(msg_id: str, days: float, tokens: int, tools: list | None = None) -> list[dict]:
    """One reply, logged once per content block with the same usage, as Claude Code does."""
    usage = {"input_tokens": tokens // 2, "cache_read_input_tokens": tokens // 2, "output_tokens": 0, "service_tier": "standard"}
    blocks = [{"type": "text", "text": "ok"}] + [{"type": "tool_use", "name": n, "input": i} for n, i in tools or []]
    return [{"type": "assistant", "timestamp": ts(days), "message": {"id": msg_id, "usage": usage, "content": [b]}} for b in blocks]


class SessionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        self.root = os.path.join(self.tmp.name, "projects")
        os.makedirs(self.home)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def log(self, rel: str, rows: list[dict]) -> str:
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows) + "{damaged\n")
        return path

    def busy_user(self) -> None:
        self.log("-proj-a/s1.jsonl", [user(MARKER, 3), *reply("m1", 3, 1000, [("Skill", {"skill": "code-review"})]),
                                      user([{"type": "text", "text": "  Fullstack   Mode "}], 3),
                                      *reply("m2", 3, 500, [("Skill", {"skill": "code-review"}), ("Bash", {"command": MARKER})])])
        self.log("-proj-a/s1/subagents/agent-x.jsonl", reply("m3", 3, 300, [("Skill", {"skill": "ux-writing"})]))
        self.log("-proj-b/s2.jsonl", [user(MARKER, 10), user([{"type": "tool_result", "content": "tester mode"}], 10),
                                      *reply("m4", 10, 200, [("Agent", {"subagent_type": "tester", "prompt": MARKER})])])
        self.log("-proj-b/s3.jsonl", [user("hello", 1), *reply("m5", 1, 4000)])

    def run_it(self) -> dict:
        return sessions.sessions(self.home, NOW, SINCE, self.root)

    def test_counts_tokens_skills_and_personas(self) -> None:
        self.busy_user()
        r = self.run_it()
        self.assertEqual(r["sessions"], 3)
        self.assertEqual(r["median_tokens"], 1800)  # s1: 1000 + 500 + its subagent's 300, each reply once
        self.assertEqual(r["skills"], [{"skill": "code-review", "runs": 2}, {"skill": "ux-writing", "runs": 1}])
        self.assertEqual(r["personas"], [{"persona": "Frontend", "sessions": 1}, {"persona": "Lead", "sessions": 1},
                                         {"persona": "Tester", "sessions": 1}])  # a tool result is never a mode command
        self.assertEqual(r["skipped"], 0)

    def test_a_session_outside_the_window_drops_out(self) -> None:
        self.log("-proj-a/old.jsonl", [user("x", 40), *reply("m9", 40, 100)])
        os.utime(os.path.join(self.root, "-proj-a/old.jsonl"), (0, 0))
        self.assertEqual(self.run_it()["sessions"], 0)

    def test_the_cache_is_reused_and_pruned(self) -> None:
        self.busy_user()
        self.run_it()
        state_path = os.path.join(self.home, "dashboard", "sessions-state.json")
        with open(state_path) as f:
            state = json.load(f)
        path = os.path.join(self.root, "-proj-b/s3.jsonl")
        state[path]["summary"]["tokens"] = 7  # an unchanged file is never read again
        with open(state_path, "w") as f:
            json.dump(state, f)
        self.assertEqual(self.run_it()["median_tokens"], 200)  # 1800, 200 and 7, not 4000
        os.remove(path)
        self.run_it()
        with open(state_path) as f:
            self.assertNotIn(path, json.load(f))

    def test_no_prompt_text_is_kept(self) -> None:
        self.busy_user()
        r = self.run_it()
        with open(os.path.join(self.home, "dashboard", "sessions-state.json")) as f:
            self.assertNotIn("SECRET-PROMPT-MARKER", f.read())
        self.assertNotIn("SECRET-PROMPT-MARKER", json.dumps(r))

    def test_no_logs_folder_says_so(self) -> None:
        with self.assertRaises(FileNotFoundError):
            self.run_it()


if __name__ == "__main__":
    unittest.main()
