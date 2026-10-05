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
        self.df = os.path.join(self.home, ".design-forge")

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


if __name__ == "__main__":
    unittest.main()
