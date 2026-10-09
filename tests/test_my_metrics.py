"""Tests for `scripts/my_metrics.py`, the private dashboard's pages (#120)."""
from __future__ import annotations

import json, os, re, sys, tempfile, time, unittest  # noqa: E401

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, SCRIPTS)
sys.dont_write_bytecode = True
import my_metrics  # noqa: E402

def read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class MyMetricsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        os.makedirs(self.home)
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.tmp.name, "claude")  # never the real session logs

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

    def test_both_pages_are_built_and_nothing_else(self) -> None:
        self.busy_user()
        self.assertTrue(self.build().endswith(os.path.join("dashboard", "index.html")))
        self.assertEqual(sorted(os.listdir(os.path.join(self.home, "dashboard"))), ["fingerprint.json", "index.html", "tools.html"])

    def test_each_page_carries_its_own_styles_and_scripts(self) -> None:
        self.busy_user()
        self.build()
        for name in ("index.html", "tools.html"):
            page = self.read(name)
            self.assertNotRegex(page, r"<link[^>]*stylesheet")
            self.assertNotIn("<script src=", page)
            styles = re.findall(r"<style>(.*?)</style>", page, re.S)
            self.assertEqual([s.strip() for s in styles], [read(p).strip() for p in my_metrics.CSS])
            self.assertTrue(my_metrics.CSS[-1].endswith("dashboard.css"))
            for path in my_metrics.JS:
                self.assertIn(read(path), page)
            self.assertLess(page.index("</main>"), page.index(read(my_metrics.JS[0])))

    def test_a_closing_tag_inside_a_file_is_refused(self) -> None:
        path = os.path.join(self.tmp.name, "bad.js")
        with open(path, "w") as f:
            f.write('var s = "</script>";\n')
        with self.assertRaises(ValueError):
            my_metrics.inline("script", [path])

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

    def test_the_governance_numbers_match_the_site(self) -> None:
        self.busy_user()
        with open(os.path.join(self.home, "hook-log.jsonl"), "a") as f:
            f.write(json.dumps({"ts": NOW, "type": "false_positive", "ref_ts": NOW, "check": "commit-message"}) + "\n")
        self.build()
        page = self.read("index.html")
        self.assertIn("<dt>Blocks marked wrong</dt><dd><span>1 (100%)</span>", page)
        self.assertIn("<dt>AI tools classified</dt><dd><span>3 of 4</span>", page)
        self.assertIn("all registered projects", page)
        tiers = re.search(r"AI tools per Law 38 tier</figcaption>(.*?)</figure>", page, re.S).group(1)
        self.assertEqual(re.findall(r'<th scope="row">(.*?)</th><td>(\d+)</td>', tiers), [
            ("1 · Local", "1"), ("2 · Reads", "0"), ("3 · Writes", "1"), ("4 · Production", "1"), ("Unclassified", "1")])

    def test_the_usage_section_shows_the_rules_cost(self) -> None:
        self.build()
        page = self.read("index.html")
        self.assertRegex(page, r"<dt>Rules' share per session</dt><dd><span>[\d,]+</span>")
        self.assertIn("release history couldn&#x27;t be read", page)  # this home isn't a git clone
        self.assertIn("session logs weren&#x27;t found on this machine", page)

    def test_the_usage_section_shows_sessions_skills_and_personas(self) -> None:
        logs = os.path.join(self.tmp.name, "claude", "projects", "-proj")
        os.makedirs(logs)
        when = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        rows = [{"type": "user", "timestamp": when, "message": {"content": "tester mode"}},
                {"type": "assistant", "timestamp": when, "message": {"id": "m1", "usage": {"input_tokens": 2_400_000},
                 "content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "ux-writing"}}]}}]
        with open(os.path.join(logs, "s1.jsonl"), "w") as f:
            f.write("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows))
        self.build()
        page = self.read("index.html")
        self.assertIn("<dt>Tokens per session</dt><dd><span>2.4M</span>", page)
        self.assertIn("<dt>Sessions</dt><dd><span>1</span>", page)
        self.assertRegex(page, r"Sessions per persona</figcaption>.*?<th scope=\"row\">Tester</th><td>1</td>")
        self.assertRegex(page, r"Skill runs</figcaption>.*?<th scope=\"row\">ux-writing</th><td>1</td>")
        self.assertIn("Tokens per session, weekly median, in millions", page)
        self.assertRegex(page, r"weekly median, in millions</figcaption>.*?<td>2\.4</td>")  # one unit, no "M"

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

    def test_checks_with_one_label_share_one_row(self) -> None:
        log = [{"ts": NOW, "type": "ask", "law": 32, "check": c} for c in ("guardrail-write", "guardrail-edit", "guardrail-edit")]
        self.write("hook-log.jsonl", "".join(json.dumps(r) + "\n" for r in log))
        self.build()
        page = self.read("index.html")
        self.assertEqual(page.count('<th scope="row">Edit to a guardrail</th>'), 1)
        self.assertIn('<th scope="row">Edit to a guardrail</th><td>3</td>', page)

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

    def test_the_rules_refresh_it_after_every_merge_and_pull(self) -> None:
        with open(os.path.join(os.path.dirname(SCRIPTS), "CLAUDE_LAWS.md")) as f:
            laws = f.read()
        law = lambda n: re.search(rf"^\s*{n}\. \*\*.*?(?=^\s*{n + 1}\. \*\*)", laws, re.S | re.M).group(0)  # noqa: E731
        self.assertIn("scripts/my_metrics.py` in the background", law(9))
        self.assertIn("refresh the dashboard (Law 9)", law(5))
        self.assertIn("refresh the dashboard (Law 9)", law(25))

