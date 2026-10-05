"""Tests for `scripts/ai_tools.py`, the Law 38 registry (#115).

The CLI runs as a subprocess with a temp HOME; the lookup helpers are
imported directly with HOME patched for the same reason.

Run: python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
SCRIPT = os.path.join(SCRIPTS, "ai_tools.py")
sys.path.insert(0, SCRIPTS)
sys.dont_write_bytecode = True
import ai_tools  # noqa: E402


class AiToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        self.project = os.path.join(self.tmp.name, "project")
        os.makedirs(self.home)
        os.makedirs(self.project)
        self.personal = os.path.join(self.home, ".design-forge", "ai-tools.json")
        self.shared = os.path.join(self.project, ".claude", "ai-tools.json")
        patcher = mock.patch.dict(os.environ, {"HOME": self.home})
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-B", SCRIPT, *args],
            capture_output=True, text=True, env={**os.environ, "HOME": self.home},
        )

    def read(self, path: str) -> dict:
        with open(path) as f:
            return json.load(f)

    def write(self, path: str, data) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(data if isinstance(data, str) else json.dumps(data))

    def test_set_writes_and_keeps_other_entries_and_hand_added_fields(self) -> None:
        r = self.cli("set", "mcp:gmail", "--tier", "2", "--owner", "alice", "--label", "Mail",
                     "--override", "send_message=3", "--personal")
        self.assertEqual(r.returncode, 0, r.stderr)
        data = self.read(self.personal)
        data["tools"]["mcp:gmail"]["note"] = "added by hand"
        data["custom"] = "kept"
        self.write(self.personal, data)
        self.assertEqual(self.cli("set", "plugin:design@inline", "--tier", "1",
                                  "--owner", "alice", "--personal").returncode, 0)
        data = self.read(self.personal)
        gmail = data["tools"]["mcp:gmail"]
        self.assertEqual((gmail["tier"], gmail["owner"], gmail["label"]), (2, "alice", "Mail"))
        self.assertEqual(gmail["overrides"], {"send_message": 3})
        self.assertEqual(gmail["note"], "added by hand")
        self.assertEqual(data["custom"], "kept")
        self.assertEqual(data["tools"]["plugin:design@inline"]["tier"], 1)

    def test_invalid_input_exits_nonzero_and_leaves_the_file(self) -> None:
        self.cli("set", "mcp:gmail", "--tier", "2", "--owner", "alice", "--personal")
        before = self.read(self.personal)
        for args in (
            ["mcp:gmail", "--tier", "0", "--owner", "alice"],
            ["mcp:gmail", "--tier", "5", "--owner", "alice"],
            ["skill:ux-writing", "--tier", "1", "--owner", "alice"],
            ["gmail", "--tier", "1", "--owner", "alice"],
            ["mcp:gmail", "--tier", "1", "--owner", " "],
            ["mcp:gmail", "--tier", "2", "--owner", "alice", "--override", "send_message=9"],
        ):
            r = self.cli("set", *args, "--personal")
            self.assertEqual(r.returncode, 2, args)
            self.assertIn("error:", r.stderr)
        self.assertEqual(self.read(self.personal), before)

    def test_project_entry_wins_over_personal(self) -> None:
        self.cli("set", "mcp:db", "--tier", "2", "--owner", "alice", "--personal")
        entry, path, _ = ai_tools.lookup("mcp", "db", self.project)
        self.assertEqual((entry["tier"], path), (2, self.personal))
        self.cli("set", "mcp:db", "--tier", "4", "--owner", "team-lead", "--project", self.project)
        entry, path, _ = ai_tools.lookup("mcp", "db", self.project)
        self.assertEqual((entry["tier"], entry["owner"], path), (4, "team-lead", self.shared))
        self.assertIn("tier 4, owner team-lead", self.cli("show", "mcp:db", "--project", self.project).stdout)

    def test_tier_for_override_server_and_unclassified(self) -> None:
        entry = {"tier": 2, "owner": "alice", "overrides": {"execute_sql": 4}}
        self.assertEqual(ai_tools.tier_for(entry, "execute_sql"), 4)
        self.assertEqual(ai_tools.tier_for(entry, "list_tables"), 2)
        self.assertEqual(ai_tools.tier_for(entry), 2)
        self.assertEqual(ai_tools.tier_for(None, "anything"), 3)
        self.assertIn("unclassified (tier 3)", self.cli("show", "mcp:unknown").stdout)

    def test_invalid_entries_count_as_unclassified(self) -> None:
        self.write(self.personal, {"version": 1, "tools": {
            "mcp:a": {"tier": "high", "owner": "alice"},
            "mcp:b": {"tier": 1},
            "mcp:c": {"tier": True, "owner": "alice"},
            "nokind": {"tier": 1, "owner": "alice"},
            "mcp:ok": {"tier": 1, "owner": "alice"},
        }})
        tools, problems = ai_tools.load(self.personal)
        self.assertEqual(list(tools), ["mcp:ok"])
        self.assertEqual(len(problems), 4)
        entry, _, _ = ai_tools.lookup("mcp", "a", None)
        self.assertEqual(ai_tools.tier_for(entry), 3)

    def test_broken_file_is_reported_and_never_overwritten(self) -> None:
        self.write(self.personal, "{not json")
        tools, problems = ai_tools.load(self.personal)
        self.assertEqual(tools, {})
        self.assertEqual(len(problems), 1)
        r = self.cli("set", "mcp:gmail", "--tier", "2", "--owner", "alice", "--personal")
        self.assertEqual(r.returncode, 2)
        self.assertIn("won't overwrite", r.stderr)
        with open(self.personal) as f:
            self.assertEqual(f.read(), "{not json")

    def test_write_is_atomic_and_leaves_no_temp_files(self) -> None:
        for i in range(5):
            self.cli("set", f"mcp:s{i}", "--tier", "2", "--owner", "alice", "--personal")
            self.read(self.personal)  # valid JSON after every write
        folder = os.path.dirname(self.personal)
        self.assertEqual(sorted(os.listdir(folder)), ["ai-tools.json"])
        self.assertEqual(len(self.read(self.personal)["tools"]), 5)


if __name__ == "__main__":
    unittest.main()
