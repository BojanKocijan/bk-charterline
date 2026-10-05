"""Tests for `scripts/release_version.py`, the release version check (#116).

Each test writes the four version files into a temp folder and runs the
script there as a subprocess, as the release-tag workflow does.

Run: python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "release_version.py")


class ReleaseVersionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        os.makedirs(os.path.join(self.root, ".claude-plugin"))
        self.write("CLAUDE_LAWS.md", "# Laws\n\n**Version:** 2.28.0\n**Last Updated:** 2026-10-05\n")
        self.write_json(".claude-plugin/plugin.json", {"name": "design-forge", "version": "2.28.0"})
        self.write_json(".claude-plugin/marketplace.json", {
            "metadata": {"version": "2.28.0"},
            "plugins": [{"name": "design-forge", "version": "2.28.0"}],
        })
        self.write("RELEASES.md", "# Releases\n\n---\n\n## v2.28.0 — October 5, 2026\n\n- x\n\n## v2.27.0 — x\n")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, rel: str, text: str) -> None:
        with open(os.path.join(self.root, rel), "w", encoding="utf-8") as f:
            f.write(text)

    def write_json(self, rel: str, data: dict) -> None:
        self.write(rel, json.dumps(data))

    def run_check(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-B", SCRIPT, *(args or ("check",))],
                              capture_output=True, text=True, cwd=self.root)

    def test_matching_versions_print_the_version(self) -> None:
        result = self.run_check()
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "2.28.0\n", ""))

    def test_each_mismatch_is_named(self) -> None:
        self.write_json(".claude-plugin/plugin.json", {"version": "2.27.0"})
        self.write_json(".claude-plugin/marketplace.json", {
            "metadata": {"version": "2.28.0"},
            "plugins": [{"version": "2.27.0"}],
        })
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn(".claude-plugin/plugin.json version is '2.27.0'", result.stderr)
        self.assertIn(".claude-plugin/marketplace.json plugins[0].version is '2.27.0'", result.stderr)
        self.assertNotIn("metadata.version", result.stderr)

    def test_missing_releases_heading_fails(self) -> None:
        self.write("RELEASES.md", "# Releases\n\n## v2.27.0 — x\n\nMentions v2.28.0 in passing.\n")
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("RELEASES.md: no `## v2.28.0` heading", result.stderr)

    def test_a_longer_version_heading_does_not_count(self) -> None:
        self.write("RELEASES.md", "# Releases\n\n## v2.28.01 — x\n")
        self.assertEqual(self.run_check().returncode, 1)

    def test_missing_version_line_fails(self) -> None:
        self.write("CLAUDE_LAWS.md", "# Laws\n\nVersion: 2.28.0\n")
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("CLAUDE_LAWS.md: no `**Version:** X.Y.Z` line", result.stderr)

    def test_unreadable_or_broken_files_fail(self) -> None:
        self.write(".claude-plugin/plugin.json", "{not json")
        os.remove(os.path.join(self.root, ".claude-plugin", "marketplace.json"))
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn(".claude-plugin/plugin.json: can't read it", result.stderr)
        self.assertIn(".claude-plugin/marketplace.json: can't read it", result.stderr)

    def test_missing_laws_file_fails(self) -> None:
        os.remove(os.path.join(self.root, "CLAUDE_LAWS.md"))
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("CLAUDE_LAWS.md: can't read it", result.stderr)

    def test_wrong_arguments_print_usage(self) -> None:
        for args in (("show",), ("check", "--x")):
            result = self.run_check(*args)
            self.assertEqual(result.returncode, 2, args)
            self.assertIn("usage:", result.stderr)

    def test_the_repo_itself_agrees(self) -> None:
        repo = os.path.dirname(os.path.dirname(SCRIPT))
        result = subprocess.run([sys.executable, "-B", SCRIPT, "check"], capture_output=True, text=True, cwd=repo)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
