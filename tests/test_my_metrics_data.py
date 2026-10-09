"""Tests for `scripts/my_metrics_data.py`, the private dashboard's data (#120).

Run: python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import datetime
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, SCRIPTS)
sys.dont_write_bytecode = True
import my_metrics_data as data  # noqa: E402

NOW = datetime.datetime(2026, 10, 8, 12, 0, tzinfo=datetime.timezone.utc)
FAKE_GH = '''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.environ["FAKE_GH_LOG"], "a") as f:
    f.write(json.dumps(args) + "\\n")
repo = args[args.index("--repo") + 1]
if repo == "acme/broken":
    sys.exit(1)
since = args[args.index("--search") + 1].split(">=")[1]
prs = json.load(open(os.environ["FAKE_GH_DATA"])).get(repo, [])
print(json.dumps([p for p in prs if p["mergedAt"][:10] >= since]))
'''


def ts(days: float) -> str:
    return (NOW - datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def pr(n: int, lines: int, merged_days: float, hours: float = 2, title: str = "feat: x", body: str = "") -> dict:
    merged = NOW - datetime.timedelta(days=merged_days)
    return {"number": n, "additions": lines, "deletions": 0, "title": title, "body": body,
            "createdAt": (merged - datetime.timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "mergedAt": merged.strftime("%Y-%m-%dT%H:%M:%SZ")}


class MyMetricsDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        os.makedirs(self.home)
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.tmp.name, "claude")  # never the real session logs
        self.gh = os.path.join(self.tmp.name, "gh")
        with open(self.gh, "w") as f:
            f.write(FAKE_GH)
        os.chmod(self.gh, os.stat(self.gh).st_mode | stat.S_IEXEC)
        self.gh_log = os.path.join(self.tmp.name, "gh.log")
        self.gh_data = os.path.join(self.tmp.name, "prs.json")
        os.environ.update(FAKE_GH_LOG=self.gh_log, FAKE_GH_DATA=self.gh_data)
        self.serve({"acme/shop": [pr(1, 120, 3, hours=4), pr(2, 900, 2, title='Revert "feat: x"'),
                                  pr(3, 60, 1, hours=1, body="Generated with [Claude Code]")]})

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def serve(self, prs: dict) -> None:
        with open(self.gh_data, "w") as f:
            json.dump(prs, f)

    def write(self, name: str, text: str) -> None:
        with open(os.path.join(self.home, name), "w") as f:
            f.write(text)

    def busy_user(self) -> None:
        log = [{"ts": ts(40), "type": "block", "law": 7, "check": "merge"},  # outside the 30 days
               {"ts": ts(5), "type": "block", "law": 13, "check": "commit-message"},
               {"ts": ts(4), "type": "block", "law": 13, "check": "commit-message"},
               {"ts": ts(3), "type": "ask", "law": 38, "check": "tier4-unapproved", "tool": "mcp__db__execute_sql"},
               {"ts": ts(2), "type": "ask", "law": 38, "check": "tier3-first-use", "tool": "mcp__mail__create_draft"},
               {"ts": ts(1), "type": "ask", "law": 32, "check": "guardrail-write"},
               {"ts": ts(1), "type": "false_positive", "ref_ts": ts(4), "check": "commit-message", "note": "x"},
               {"ts": ts(1), "type": "false_positive", "ref_ts": ts(40), "check": "merge", "note": "x"}]  # its block is outside
        self.write("hook-log.jsonl", "".join(json.dumps(r) + "\n" for r in log) + "{damaged\n")
        approvals = [{"session": "s", "tool": "mcp__mail__create_draft", "ts": ts(2)},  # the same call as the log's
                     {"session": "s", "tool": "mcp__docs__edit", "ts": ts(6)}]  # before the hook named tools
        self.write("ai-approvals.jsonl", "".join(json.dumps(r) + "\n" for r in approvals))
        self.write("ai-tools.json", json.dumps({"version": 1, "tools": {
            "mcp:db": {"tier": 4, "owner": "alice", "label": "Database"},
            "mcp:mail": {"tier": 3, "owner": "alice", "label": "Mail", "overrides": {"send": 4}}}}))
        self.write("ai-inventory.json", json.dumps({"mcp|session|db": {}, "mcp|session|chat": {},
                                                    "plugin|desktop|notes@synced": {}, "skill|user|x": {}}))
        self.write("projects.yaml", "projects:\n  - name: shop\n    repo: acme/shop\n  - name: notes  # no repo\n    port: 5174\n")

    def collect(self, **kw) -> dict:
        return data.collect(self.home, gh=self.gh, now=NOW, **kw)

    def gh_calls(self) -> list[list[str]]:
        if not os.path.exists(self.gh_log):
            return []
        with open(self.gh_log) as f:
            return [json.loads(line) for line in f]

    def test_activity_counts_the_last_30_days(self) -> None:
        self.busy_user()
        a = self.collect(network=False)["activity"]
        self.assertEqual(a["blocks"], [{"law": 13, "check": "commit-message", "count": 2}])
        self.assertEqual({x["check"]: x["count"] for x in a["asks"]},
                         {"tier4-unapproved": 1, "tier3-first-use": 1, "guardrail-write": 1})
        self.assertEqual(sum(d["count"] for d in a["days"]), 5)

    def test_calls_name_the_tool_once(self) -> None:
        self.busy_user()
        calls = self.collect(network=False)["activity"]["calls"]
        self.assertEqual([(c["tool"], c["critical"]) for c in calls], [
            ("mcp__mail__create_draft", False), ("mcp__db__execute_sql", True), ("mcp__docs__edit", False)])

    def test_tools_and_what_is_not_rated(self) -> None:
        self.busy_user()
        t = self.collect(network=False)["tools"]
        self.assertEqual([(x["label"], x["tier"]) for x in t["tools"]], [("Database", 4), ("Mail", 3)])
        self.assertEqual(t["unrated"], ["chat", "notes@synced"])  # a skill is never rated
        self.assertEqual((t["classified"], t["known"]), (2, 4))

    def test_false_positives_are_counted_apart(self) -> None:
        self.busy_user()
        a = self.collect(network=False)["activity"]
        self.assertEqual(a["false_positives"], 1)
        self.assertEqual(sum(b["count"] for b in a["blocks"]), 2)

    def test_pull_requests_per_project(self) -> None:
        self.busy_user()
        [shop] = self.collect()["pull_requests"]["projects"]
        self.assertEqual((shop["name"], shop["merged"], shop["median_lines"], shop["within_400"]), ("shop", 3, 120, 67))
        self.assertEqual((shop["reverts"], shop["claude_share"], shop["median_hours"]), (1, 33, 2.0))

    def test_collection_is_incremental(self) -> None:
        self.busy_user()
        self.collect()
        self.serve({"acme/shop": [pr(3, 60, 1), pr(4, 30, 0.5)]})
        [shop] = self.collect()["pull_requests"]["projects"]
        self.assertEqual(shop["merged"], 4)  # PR 3 isn't counted twice
        first, second = self.gh_calls()
        self.assertEqual(first[first.index("--search") + 1], "merged:>=" + ts(30)[:10])
        self.assertEqual(second[second.index("--search") + 1], "merged:>=" + ts(1)[:10])

    def test_local_only_never_calls_gh(self) -> None:
        self.busy_user()
        self.collect(network=False)
        self.assertEqual(self.gh_calls(), [])

    def test_a_gh_failure_stays_in_its_project(self) -> None:
        self.busy_user()
        self.write("projects.yaml", "projects:\n  - name: shop\n    repo: acme/shop\n  - name: old\n    repo: acme/broken\n")
        shop, old = self.collect()["pull_requests"]["projects"]
        self.assertEqual((shop["error"], shop["merged"]), (None, 3))
        self.assertIn("gh auth login", old["error"])

    def test_a_new_user_gets_messages_not_errors(self) -> None:
        result = self.collect()
        for name in ("activity", "tools", "pull_requests"):
            self.assertIn("error", result[name], name)
        self.assertIn("first blocked or approved call", result["activity"]["error"])
        self.assertGreater(result["rules"]["tokens"], 0)
        self.assertIn("release history couldn't be read", result["rules_cost"]["error"])

    def test_rules_cost_per_release_reads_each_tag_once(self) -> None:
        def git(*args: str) -> None:
            subprocess.run(["git", "-C", self.home, *args], check=True, capture_output=True)
        git("init", "-q")
        git("config", "user.email", "alice@example.com")
        git("config", "user.name", "Alice Chen")
        for tag, laws in (("v1.0.0", "a" * 2772), ("v1.1.0", "a" * 5544)):
            self.write("CLAUDE.md", "@./CLAUDE_LAWS.md\n@./knowledge/X.md\n")
            self.write("CLAUDE_LAWS.md", laws)
            os.makedirs(os.path.join(self.home, "knowledge"), exist_ok=True)
            self.write("knowledge/X.md", "b" * 270)
            git("add", "-A")
            git("commit", "-qm", tag)
            git("tag", tag)
        git("tag", "not-a-release")
        releases = self.collect(network=False)["rules_cost"]["releases"]
        base = round(len("@./CLAUDE_LAWS.md\n@./knowledge/X.md\n") / 2.423) + 100  # CLAUDE.md, then X.md at 2.7
        self.assertEqual(releases, [{"tag": "v1.0.0", "tokens": base + 1000}, {"tag": "v1.1.0", "tokens": base + 2000}])
        cache = os.path.join(self.home, "dashboard", "rules-cost.json")
        with open(cache, "w") as f:
            json.dump({"v1.0.0": 7, "v1.1.0": 8}, f)  # a measured tag is never read again
        self.assertEqual([r["tokens"] for r in self.collect(network=False)["rules_cost"]["releases"]], [7, 8])

    def test_a_broken_file_stays_in_its_section(self) -> None:
        self.busy_user()
        self.write("ai-tools.json", "{not json")
        result = self.collect(network=False)
        self.assertIn("Couldn't read this", result["tools"]["error"])
        self.assertEqual(len(result["activity"]["calls"]), 3)
