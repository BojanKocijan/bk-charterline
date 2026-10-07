"""Tests for `scripts/ai_inventory.py` (#114).

Each test builds a fake HOME and project with planted secrets, runs the
script as a subprocess and checks the Markdown and the JSON state.

Run: python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "ai_inventory.py"
)

# Values that must never appear in any output.
SECRETS = [
    "env-secret-value-1234567890",
    "header-secret-value-0987654321",
    "url-path-secret",
    "url-query-secret",
    "sk-arg0123456789abcdefghij",
    "ghp_permtoken0123456789",
    "desktop-config-marker",
]

# Fake secrets are assembled at run time, so no whole token sits in this
# file: the hook's commit check would block the commit that adds them (#119).
MIX = "a1B2c3D4e5F6g7H8i9J0"  # 20 mixed letters and digits
FAKE = {
    "github": "gh" + "p_" + (MIX * 2)[:36],
    "gitlab": "gl" + "pat-" + MIX,
    "slack": "xo" + "xb-" + "1234567890-" + MIX,
    "openai": "sk" + "-" + MIX + "T3Blbk" + "FJ" + MIX,  # a legacy key
}


def write(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(data if isinstance(data, str) else json.dumps(data))


class AiInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        self.project = os.path.realpath(os.path.join(self.tmp.name, "project"))
        os.makedirs(self.home)
        os.makedirs(self.project)
        self.df = os.path.join(self.home, ".bk-charterline")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_inventory(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-B", SCRIPT, "--project", self.project, *extra],
            capture_output=True, text=True, env={**os.environ, "HOME": self.home},
        )

    def outputs(self) -> str:
        with open(os.path.join(self.df, "ai-inventory.md")) as md, \
                open(os.path.join(self.df, "ai-inventory.json")) as state:
            return md.read() + state.read()

    def plant_everything(self) -> None:
        h, p = self.home, self.project
        write(os.path.join(h, ".claude.json"), {
            "mcpServers": {"user-db": {
                "command": "/usr/local/bin/db-mcp",
                "args": ["--api-key", "sk-arg0123456789abcdefghij"],
                "env": {"DB_PASSWORD": "env-secret-value-1234567890"},
            }},
            "projects": {p: {
                "mcpServers": {"local-api": {
                    "type": "http",
                    "url": "https://api.example.com/url-path-secret?key=url-query-secret",
                    "headers": {"Authorization": "header-secret-value-0987654321"},
                }},
                "enabledMcpjsonServers": ["team-tracker"],
            }},
            "pluginUsage": {"engineering@inline": {}},
        })
        write(os.path.join(p, ".mcp.json"), {"mcpServers": {"team-tracker": {"command": "npx"}}})
        desk = os.path.join(h, "Library", "Application Support", "Claude")
        write(os.path.join(desk, "config.json"), {"oauth:tokenCache": "desktop-config-marker"})
        write(os.path.join(desk, "Claude Extensions", "ext1", "manifest.json"),
              {"name": "notes-ext", "version": "1.2.0"})
        write(os.path.join(h, ".claude", "settings.json"), {
            "enabledPlugins": {"design@market": True},
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
                {"type": "command", "command": 'python3 "/x/enforce-laws.py" --token ghp_permtoken0123456789'}
            ]}]},
            "permissions": {"allow": ["Bash(npm run *)", "Bash(curl -H token=ghp_permtoken0123456789)"]},
        })
        write(os.path.join(p, ".claude", "settings.local.json"), {"permissions": {"deny": ["Read(.env)"]}})
        os.makedirs(os.path.join(h, "skill-src", "ux-writing"))
        os.makedirs(os.path.join(h, ".claude", "skills"))
        os.symlink(os.path.join(h, "skill-src", "ux-writing"), os.path.join(h, ".claude", "skills", "ux-writing"))
        write(os.path.join(h, ".claude", "agents", "tester.md"), "# tester")

    def test_lists_every_source(self) -> None:
        self.plant_everything()
        result = self.run_inventory("--session", "gmail", "supabase")
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        for expected in [
            "| user-db | user | stdio · db-mcp |",
            "| local-api | local | http · api.example.com |",
            "| team-tracker | project | stdio · npx · enabled |",
            "| notes-ext | desktop | v1.2.0 |",
            "| engineering@inline | desktop | used |",
            "| design@market | user | enabled |",
            "| ux-writing | user | → ~/skill-src/ux-writing |",
            "| tester | user | local |",
            "| PreToolUse · Bash · enforce-laws.py | user |",
            "| Bash(npm run \\*) | user | allow |".replace("\\*", "*"),
            "| Read(.env) | local | deny |",
            "| gmail | session |",
            "| supabase | session |",
            "Session servers: 2",
        ]:
            self.assertIn(expected, out)

    def test_no_secret_ever_reaches_the_output(self) -> None:
        self.plant_everything()
        self.assertEqual(self.run_inventory("--session", "gmail").returncode, 0)
        everything = self.outputs()
        for secret in SECRETS:
            self.assertNotIn(secret, everything)
        self.assertIn("[masked]", everything)

    def test_empty_home_writes_a_valid_inventory(self) -> None:
        result = self.run_inventory()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0 items (first run)", result.stdout)
        self.assertIn("Session servers not provided", result.stdout)
        self.assertEqual(result.stdout.count("_None found._"), 7)

    def test_broken_file_is_reported_and_the_rest_collected(self) -> None:
        self.plant_everything()
        write(os.path.join(self.home, ".claude.json"), "{not json")
        result = self.run_inventory()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("## Couldn't parse", result.stdout)
        self.assertIn("`~/.claude.json`", result.stdout)
        self.assertIn("| tester | user |", result.stdout)

    def test_first_seen_new_and_removed(self) -> None:
        self.plant_everything()
        self.run_inventory()
        second = self.run_inventory().stdout
        self.assertNotIn("**new**", second)
        self.assertIn("0 new · 0 removed", second)

        write(os.path.join(self.project, ".mcp.json"),
              {"mcpServers": {"team-tracker": {"command": "npx"}, "docs-search": {"command": "uvx"}}})
        third = self.run_inventory().stdout
        self.assertEqual(third.count("**new**"), 1)
        self.assertIn("| docs-search | project | stdio · uvx | ", third)

        write(os.path.join(self.project, ".mcp.json"), {"mcpServers": {"team-tracker": {"command": "npx"}}})
        fourth = self.run_inventory().stdout
        self.assertIn("## Removed since last run", fourth)
        self.assertIn("mcp · project · docs-search", fourth)
        self.assertNotIn("Removed since last run", self.run_inventory().stdout)

    def test_session_servers_survive_a_run_without_session(self) -> None:
        self.run_inventory("--session", "gmail")
        without = self.run_inventory().stdout
        self.assertNotIn("Removed since last run", without)
        with open(os.path.join(self.df, "ai-inventory.json")) as f:
            self.assertIn("mcp|session|gmail", json.load(f))


class TierColumnTests(unittest.TestCase):
    """`ai inventory` shows Law 38 tiers and owners (#115)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        self.project = os.path.realpath(os.path.join(self.tmp.name, "project"))
        os.makedirs(self.home)
        os.makedirs(self.project)
        write(os.path.join(self.project, ".mcp.json"), {"mcpServers": {
            "db": {"command": "db-mcp"}, "tracker": {"command": "npx"},
        }})
        self.personal = os.path.join(self.home, ".bk-charterline", "ai-tools.json")
        self.shared = os.path.join(self.project, ".claude", "ai-tools.json")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_inventory(self) -> str:
        result = subprocess.run(
            [sys.executable, "-B", SCRIPT, "--project", self.project],
            capture_output=True, text=True, env={**os.environ, "HOME": self.home},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_classified_row_shows_tier_owner_and_overrides(self) -> None:
        write(self.personal, {"version": 1, "tools": {"mcp:db": {
            "tier": 2, "owner": "alice", "overrides": {"execute_sql": 4}}}})
        out = self.run_inventory()
        self.assertIn("| Name | Scope | Detail | Tier | Owner | Source |", out)
        self.assertIn("| db | project | stdio · db-mcp · overrides: execute_sql → 4 | 2 | alice |", out)

    def test_unclassified_rows_are_flagged_and_counted(self) -> None:
        write(self.personal, {"version": 1, "tools": {"mcp:db": {"tier": 2, "owner": "alice"}}})
        out = self.run_inventory()
        self.assertIn("| tracker | project | stdio · npx | unclassified (tier 3) |  |", out)
        self.assertIn("· 1 unclassified", out)

    def test_project_entry_wins(self) -> None:
        write(self.personal, {"version": 1, "tools": {"mcp:db": {"tier": 2, "owner": "alice"}}})
        write(self.shared, {"version": 1, "tools": {"mcp:db": {"tier": 4, "owner": "team-lead"}}})
        self.assertIn("| db | project | stdio · db-mcp | 4 | team-lead |", self.run_inventory())

    def test_broken_registry_is_reported(self) -> None:
        write(self.personal, "{not json")
        out = self.run_inventory()
        self.assertIn("## Couldn't parse", out)
        self.assertIn("~/.bk-charterline/ai-tools.json", out)
        self.assertIn("· 2 unclassified", out)


    def test_invalid_project_entry_shows_unclassified_not_personal(self) -> None:
        write(self.personal, {"version": 1, "tools": {"mcp:db": {"tier": 1, "owner": "alice"}}})
        write(self.shared, {"version": 1, "tools": {"mcp:db": {"tier": "4", "owner": "lead"}}})
        out = self.run_inventory()
        self.assertIn("| db | project | stdio · db-mcp | unclassified (tier 3) |", out)
        self.assertNotIn("| 1 | alice |", out)

    def test_masked_names_are_never_looked_up(self) -> None:
        write(self.personal, {"version": 1, "tools": {"mcp:[masked]": {"tier": 1, "owner": "alice"}}})
        result = subprocess.run(
            [sys.executable, "-B", SCRIPT, "--project", self.project,
             "--session", FAKE["github"]],
            capture_output=True, text=True, env={**os.environ, "HOME": self.home},
        )
        self.assertIn("| [masked] | session | connected in this session | unclassified (tier 3) |", result.stdout)
        self.assertIn("· 3 unclassified", result.stdout)  # db, tracker and the masked server

    def test_label_is_shown_and_unclassified_counts_unique_tools(self) -> None:
        write(self.personal, {"version": 1, "tools": {"mcp:db": {"tier": 2, "owner": "alice", "label": "Database"}}})
        write(os.path.join(self.home, ".claude.json"),
              {"projects": {self.project: {"mcpServers": {"tracker": {"command": "npx"}}}}})
        out = self.run_inventory()
        self.assertIn("| db | project | Database · stdio · db-mcp | 2 | alice |", out)
        self.assertIn("· 1 unclassified", out)  # tracker appears in two scopes, counted once


    def test_hand_edited_secrets_in_the_registry_are_masked(self) -> None:
        write(self.personal, {"version": 1, "tools": {"mcp:db": {
            "tier": 2, "owner": FAKE["github"], "label": "token=r9" + MIX,
            "overrides": {FAKE["openai"]: 4}}}})
        out = self.run_inventory()
        for secret in (FAKE["github"], MIX, FAKE["openai"]):
            self.assertNotIn(secret, out)
        self.assertIn("| db | project | [masked] · stdio · db-mcp · overrides: [masked] → 4 | 2 | [masked] |", out)

    def test_gitlab_and_slack_tokens_are_masked(self) -> None:
        write(self.personal, {"version": 1, "tools": {"mcp:db": {
            "tier": 2, "owner": FAKE["slack"], "label": FAKE["gitlab"]}}})  # missed before #186
        out = self.run_inventory()
        for secret in (FAKE["gitlab"], FAKE["slack"]):
            self.assertNotIn(secret, out)
        self.assertIn("| db | project | [masked] · stdio · db-mcp | 2 | [masked] |", out)


    def test_broken_project_file_shows_every_tool_unclassified(self) -> None:
        write(self.personal, {"version": 1, "tools": {"mcp:db": {"tier": 1, "owner": "alice"}}})
        write(self.shared, "{not json")
        out = self.run_inventory()
        self.assertIn("| db | project | stdio · db-mcp | unclassified (tier 3) |", out)
        self.assertIn("every tool counts as unclassified (tier 3) until this file is fixed", out)
        self.assertIn("· 2 unclassified", out)


if __name__ == "__main__":
    unittest.main()
