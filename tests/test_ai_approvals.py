"""Tests for the per-session Law 38 approvals store (#138).

The store lives under $HOME, so each test points HOME at a temp folder
and never touches the real ~/.bk-charterline.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

HOOKS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".claude", "hooks"
)
sys.path.insert(0, HOOKS_DIR)
sys.dont_write_bytecode = True

import ai_approvals  # noqa: E402
import hook_log  # noqa: E402

try:
    import fcntl
except ImportError:  # Windows: no lock to hold
    fcntl = None

TOOL = "mcp__db__execute_sql"


class ApprovalsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.dict(os.environ, {"HOME": self.tmp.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.dir = os.path.join(self.tmp.name, ".bk-charterline")
        self.path = os.path.join(self.dir, "ai-approvals.jsonl")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def lines(self) -> list[dict]:
        with open(self.path) as f:
            return [json.loads(line) for line in f]

    def write_lines(self, lines: list[str]) -> None:
        os.makedirs(self.dir, exist_ok=True)
        with open(self.path, "w") as f:
            f.writelines(line + "\n" for line in lines)

    def test_missing_file_is_not_approved(self) -> None:
        self.assertFalse(ai_approvals.approved("s1", TOOL))

    def test_record_then_approved_for_that_session_and_tool_only(self) -> None:
        self.assertTrue(ai_approvals.record("s1", TOOL))
        self.assertTrue(ai_approvals.approved("s1", TOOL))
        self.assertFalse(ai_approvals.approved("s2", TOOL))
        self.assertFalse(ai_approvals.approved("s1", "mcp__db__list_tables"))

    def test_record_stores_only_time_session_and_tool(self) -> None:
        ai_approvals.record("s1", TOOL)
        [line] = self.lines()
        self.assertEqual(set(line), {"ts", "session", "tool"})

    def test_repeat_record_keeps_one_line(self) -> None:
        for _ in range(3):
            self.assertTrue(ai_approvals.record("s1", TOOL))
        self.assertEqual(len(self.lines()), 1)

    def test_empty_session_or_tool_is_never_recorded_or_approved(self) -> None:
        self.assertFalse(ai_approvals.record("", TOOL))
        self.assertFalse(ai_approvals.record("s1", ""))
        self.assertFalse(os.path.exists(self.path))
        self.assertFalse(ai_approvals.approved("", TOOL))

    def test_record_prunes_old_and_bad_lines(self) -> None:
        old = (datetime.now(timezone.utc) - timedelta(days=8)).strftime(hook_log.TS_FORMAT)
        recent = (datetime.now(timezone.utc) - timedelta(days=6)).strftime(hook_log.TS_FORMAT)
        self.write_lines([
            json.dumps({"ts": old, "session": "old", "tool": TOOL}),
            json.dumps({"ts": recent, "session": "recent", "tool": TOOL}),
            json.dumps({"ts": "not a time", "session": "bad-ts", "tool": TOOL}),
            "not json",
        ])
        ai_approvals.record("s1", TOOL)
        self.assertEqual([r["session"] for r in self.lines()], ["recent", "s1"])

    def test_corrupt_lines_are_skipped_when_reading(self) -> None:
        self.write_lines([
            "not json",
            json.dumps(["a", "list"]),
            json.dumps({"session": "s1", "tool": TOOL}),  # no ts
            json.dumps({"ts": hook_log.utc_now(), "session": "s1", "tool": 5}),
        ])
        self.assertFalse(ai_approvals.approved("s1", TOOL))

    def test_unreadable_file_is_not_approved(self) -> None:
        os.makedirs(self.path)  # a folder where the file should be
        self.assertFalse(ai_approvals.approved("s1", TOOL))

    @unittest.skipIf(fcntl is None, "no file locks on this platform")
    def test_busy_lock_skips_the_record(self) -> None:
        os.makedirs(self.dir, exist_ok=True)
        with open(os.path.join(self.dir, hook_log.LOCK_NAME), "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                self.assertFalse(ai_approvals.record("s1", TOOL))
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
        self.assertFalse(ai_approvals.approved("s1", TOOL))


if __name__ == "__main__":
    unittest.main()
