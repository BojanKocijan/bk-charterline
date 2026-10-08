"""Tests for `scripts/my_metrics.py`, the private dashboard's pages (#120)."""
from __future__ import annotations

import json, os, re, sys, tempfile, time, unittest  # noqa: E401

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, SCRIPTS)
sys.dont_write_bytecode = True
import my_metrics  # noqa: E402

NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class MyMetricsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        os.makedirs(self.home)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, name: str, text: str) -> None:
        with open(os.path.join(self.home, name), "w") as f:
            f.write(text)

    def busy_user(self) -> None:
        log = [{"ts": NOW, "type": "block", "law": 13, "check": "commit-message"},
               {"ts": NOW, "type": "ask", "law": 38, "check": "tier4-unapproved", "tool": "mcp__db__execute_sql"},
               {"ts": NOW, "type": "ask", "law": 38, "check": "tier3-first-use", "tool": "mcp__mail__create_draft"}]
        self.write("hook-log.jsonl", "".join(json.dumps(r) + "\n" for r in log))
        self.write("ai-tools.json", json.dumps({"version": 1, "tools": {
            "mcp:db": {"tier": 4, "owner": "alice", "label": "Supabase"},
            "mcp:mail": {"tier": 3, "owner": "alice", "label": "Gmail", "overrides": {"send_message": 4}},
            "mcp:viz": {"tier": 1, "owner": "alice", "label": "Inline visuals"}}}))
        self.write("ai-inventory.json", json.dumps({"mcp|session|db": {}, "mcp|session|chat": {}}))

    def build(self, **kw) -> str:
        return my_metrics.build(self.home, network=False, **kw)

    def read(self, name: str) -> str:
        with open(os.path.join(self.home, "dashboard", name)) as f:
            return f.read()

    def test_both_pages_and_their_files_are_built(self) -> None:
        self.busy_user()
        self.assertTrue(self.build().endswith(os.path.join("dashboard", "index.html")))
        for name in ("index.html", "tools.html", "dashboard.css", "styles.css", "site.js", "charts.js"):
            self.assertTrue(os.path.exists(os.path.join(self.home, "dashboard", name)), name)

    def test_every_tool_once_under_its_severity(self) -> None:
        self.busy_user()
        self.build()
        page = self.read("tools.html")
        sections = dict(re.findall(r'<section class="section" id="(critical|high|low|minimal)">(.*?)</section>', page, re.S))
        self.assertIn("Supabase", sections["critical"])
        self.assertIn("Send an email", sections["critical"])  # Gmail's raised action
        self.assertIn("Read, draft and label mail", sections["high"])
        self.assertIn("Inline visuals", sections["minimal"])
        self.assertEqual(sections["high"].count("<h3>Gmail</h3>"), 1)

    def test_the_unrated_note_and_its_copy_button(self) -> None:
        self.busy_user()
        self.build()
        page = self.read("index.html")
        self.assertIn("1 new tools not rated yet", page)
        self.assertIn('data-copy="cmd-classify"', page)
        self.assertIn("Paste it into Claude Code and press Enter.", page)
        self.write("ai-inventory.json", json.dumps({"mcp|session|db": {}}))
        self.build()
        self.assertNotIn("not rated yet", self.read("index.html"))

    def test_calls_name_the_tool_and_its_severity(self) -> None:
        self.busy_user()
        self.build()
        page = self.read("tools.html")
        self.assertRegex(page, r"sev-critical.*?Supabase.*?execute_sql")
        self.assertRegex(page, r"sev-high.*?Gmail.*?Draft an email")

    def test_a_new_user_gets_friendly_empty_states(self) -> None:
        self.build()
        page = self.read("index.html") + self.read("tools.html")
        self.assertIn("Your first blocked or approved call shows up here.", page)
        self.assertIn("Run ai inventory, then ai classify", page)

    def test_nothing_points_to_another_site(self) -> None:
        self.busy_user()
        self.build()
        for name in ("index.html", "tools.html"):
            self.assertNotRegex(self.read(name), r'(src|href)="https?://')

    def test_merge_times_read_in_minutes_or_hours(self) -> None:
        self.assertEqual([my_metrics.duration(h) for h in (None, 0.12, 0.004, 2.25)], ["–", "7 min", "1 min", "2.2 h"])

    def test_if_changed_skips_an_unchanged_build(self) -> None:
        self.busy_user()
        self.build()
        self.assertEqual(self.build(if_changed=True), "unchanged")
        with open(os.path.join(self.home, "hook-log.jsonl"), "a") as f:
            f.write(json.dumps({"ts": NOW, "type": "block", "law": 5, "check": "commit-on-default"}) + "\n")
        self.assertNotEqual(self.build(if_changed=True), "unchanged")
        self.assertIn("Commit on main", self.read("index.html"))
