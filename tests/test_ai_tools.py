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

# Fake secrets are assembled at run time, so no whole token sits in this
# file: the hook's commit check would block the commit that adds them (#119).
MIX = "a1B2c3D4e5F6g7H8i9J0"  # 20 mixed letters and digits
FAKE = {
    "github": "gh" + "p_" + (MIX * 2)[:36],
    "gitlab": "gl" + "pat-" + MIX,
    "slack": "xo" + "xb-" + "1234567890-" + MIX,
    "openai": "sk" + "-" + MIX + "T3Blbk" + "FJ" + MIX,  # a legacy key
}


class AiToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        self.project = os.path.join(self.tmp.name, "project")
        os.makedirs(self.home)
        os.makedirs(self.project)
        self.personal = os.path.join(self.home, ".bk-charterline", "ai-tools.json")
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
        tools, invalid, problems = ai_tools.load(self.personal)
        self.assertEqual(list(tools), ["mcp:ok"])
        self.assertEqual(invalid, {"mcp:a", "mcp:b", "mcp:c", "nokind"})
        self.assertEqual(len(problems), 4)
        entry, _, _ = ai_tools.lookup("mcp", "a", None)
        self.assertEqual(ai_tools.tier_for(entry), 3)

    def test_broken_file_is_reported_and_never_overwritten(self) -> None:
        self.write(self.personal, "{not json")
        tools, invalid, problems = ai_tools.load(self.personal)
        self.assertEqual((tools, invalid), ({}, {ai_tools.BROKEN}))
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


    def test_invalid_project_entry_never_falls_through_to_personal(self) -> None:
        self.write(self.personal, {"version": 1, "tools": {"mcp:db": {"tier": 1, "owner": "alice"}}})
        self.write(self.shared, {"version": 1, "tools": {
            "mcp:db": {"tier": 2, "owner": "lead", "overrides": {"execute_sql": "4"}}}})
        entry, path, problems = ai_tools.lookup("mcp", "db", self.project)
        self.assertIsNone(entry)
        self.assertEqual(path, self.shared)
        self.assertEqual(ai_tools.tier_for(entry, "execute_sql"), 3)
        self.assertTrue(any("treated as unclassified" in p for p in problems))
        out = self.cli("show", "mcp:db", "--project", self.project).stdout
        self.assertIn("unclassified (tier 3) — invalid entry", out)

    def test_duplicate_keys_count_as_unclassified(self) -> None:
        self.write(self.personal,
                   '{"version": 1, "tools": {"mcp:x": {"tier": 4, "owner": "a"}, "mcp:x": {"tier": 1, "owner": "a"}}}')
        entry, _, problems = ai_tools.lookup("mcp", "x", None)
        self.assertIsNone(entry)
        self.assertTrue(any("listed more than once" in p for p in problems))

    def test_secrets_are_refused(self) -> None:
        for args in (
            ["mcp:" + FAKE["github"], "--tier", "1", "--owner", "alice"],
            ["mcp:db", "--tier", "1", "--owner", "alice", "--note", "token=r9" + MIX],
            ["mcp:db", "--tier", "1", "--owner", "alice", "--label", "AKIAABCDEFGHIJKLMNOP"],
        ):
            r = self.cli("set", *args, "--personal")
            self.assertEqual(r.returncode, 2, args)
            self.assertIn("looks like a secret", r.stderr)
        self.assertFalse(os.path.exists(self.personal))

    def test_every_kind_the_hook_knows_is_refused(self) -> None:
        for value in (FAKE["gitlab"], FAKE["slack"], FAKE["openai"]):  # missed before #186
            with self.subTest(value=value[:6]):
                r = self.cli("set", "mcp:db", "--tier", "1", "--owner", "alice", "--label", value, "--personal")
                self.assertEqual(r.returncode, 2)
                self.assertIn("looks like a secret", r.stderr)
        self.assertFalse(os.path.exists(self.personal))

    def test_placeholders_and_references_pass(self) -> None:
        for value in ("gh" + "p_" + "x" * 36, "${{ secrets.API_KEY }}", "token=your-token-goes-here"):
            with self.subTest(value=value):
                self.assertFalse(ai_tools.looks_secret(value))

    def test_masked_name_cannot_be_classified(self) -> None:
        r = self.cli("set", "mcp:[masked]", "--tier", "1", "--owner", "alice", "--personal")
        self.assertEqual(r.returncode, 2)
        self.assertFalse(os.path.exists(self.personal))

    def test_project_folder_must_exist(self) -> None:
        missing = os.path.join(self.tmp.name, "typo")
        r = self.cli("set", "mcp:db", "--tier", "2", "--owner", "alice", "--project", missing)
        self.assertEqual(r.returncode, 2)
        self.assertFalse(os.path.exists(missing))

    def test_set_refuses_to_leave_an_invalid_entry(self) -> None:
        self.write(self.personal, {"version": 1, "tools": {
            "mcp:z": {"tier": 2, "owner": "alice", "overrides": {"q": "4"}}}})
        r = self.cli("set", "mcp:z", "--tier", "2", "--owner", "alice", "--personal")
        self.assertEqual(r.returncode, 2)
        self.assertIn("would still be invalid", r.stderr)
        r = self.cli("set", "mcp:z", "--tier", "2", "--owner", "alice", "--clear-overrides", "--personal")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.read(self.personal)["tools"]["mcp:z"]["overrides"], {})

    def test_write_keeps_mode_key_order_and_symlink(self) -> None:
        real = os.path.join(self.tmp.name, "shared-registry.json")
        self.write(real, {"version": 1, "tools": {"mcp:b": {"tier": 2, "owner": "a"},
                                                   "mcp:a": {"tier": 2, "owner": "a"}}})
        os.chmod(real, 0o644)
        os.makedirs(os.path.dirname(self.personal))
        os.symlink(real, self.personal)
        self.assertEqual(self.cli("set", "mcp:c", "--tier", "1", "--owner", "a", "--personal").returncode, 0)
        self.assertTrue(os.path.islink(self.personal))
        self.assertEqual(oct(os.stat(real).st_mode & 0o777), "0o644")
        self.assertEqual(list(self.read(real)["tools"]), ["mcp:b", "mcp:a", "mcp:c"])


    def test_duplicates_at_any_level_are_never_resolved_to_the_last_value(self) -> None:
        self.write(self.personal, '{"version": 1, "tools": {"mcp:a": {"tier": 4, "owner": "x", "tier": 1}}}')
        entry, _, problems = ai_tools.lookup("mcp", "a", None)
        self.assertIsNone(entry)
        self.assertTrue(any("a field is listed more than once" in p for p in problems))
        self.write(self.personal,
                   '{"tools": {"mcp:b": {"tier": 4, "owner": "x"}}, "tools": {"mcp:b": {"tier": 1, "owner": "x"}}}')
        entry, _, problems = ai_tools.lookup("mcp", "b", None)
        self.assertIsNone(entry)
        self.assertTrue(any("top-level key is listed more than once" in p for p in problems))

    def test_set_refuses_a_file_with_duplicates_instead_of_erasing_them(self) -> None:
        text = '{"version": 1, "tools": {"mcp:x": {"tier": 4, "owner": "a"}, "mcp:x": {"tier": 1, "owner": "a"}}}'
        self.write(self.personal, text)
        r = self.cli("set", "mcp:other", "--tier", "2", "--owner", "a", "--personal")
        self.assertEqual(r.returncode, 2)
        self.assertIn("listed more than once", r.stderr)
        with open(self.personal) as f:
            self.assertEqual(f.read(), text)
        self.assertIn("unclassified (tier 3)", self.cli("show", "mcp:x").stdout)


    def test_broken_project_file_makes_every_tool_unclassified(self) -> None:
        self.write(self.personal, {"version": 1, "tools": {"mcp:db": {"tier": 1, "owner": "alice"}}})
        self.write(self.shared, "{not json")
        entry, path, problems = ai_tools.lookup("mcp", "db", self.project)
        self.assertIsNone(entry)
        self.assertEqual(path, self.shared)
        self.assertTrue(any("every tool counts as unclassified" in p for p in problems))

    def test_broken_personal_file_leaves_project_entries_working(self) -> None:
        self.write(self.personal, "{not json")
        self.write(self.shared, {"version": 1, "tools": {"mcp:db": {"tier": 4, "owner": "lead"}}})
        entry, _, _ = ai_tools.lookup("mcp", "db", self.project)
        self.assertEqual(entry["tier"], 4)


if __name__ == "__main__":
    unittest.main()
