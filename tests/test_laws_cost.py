"""Tests for `scripts/laws_cost.py`, what loading the rules costs (#188).

The estimate runs as a subprocess in a temp folder, as CI runs it. The
--measure arithmetic is tested on recorded results; --measure itself is
only ever started here to check that it refuses under CI.

Run: python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "laws_cost.py")
spec = importlib.util.spec_from_file_location("laws_cost", SCRIPT)
laws_cost = importlib.util.module_from_spec(spec)
spec.loader.exec_module(laws_cost)


def cli_result(fresh: int, write: int, read: int, model: str = "claude-opus-5-5") -> dict:
    """A trimmed `claude -p --output-format json` result."""
    return {
        "usage": {"input_tokens": fresh, "cache_creation_input_tokens": write,
                  "cache_read_input_tokens": read, "output_tokens": 5},
        "modelUsage": {model: {"inputTokens": fresh, "cacheCreationInputTokens": write,
                               "cacheReadInputTokens": read}},
    }


class EstimateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.write("CLAUDE.md", "a" * 2423)
        self.write("CLAUDE_LAWS.md", "word " * 5544)  # 27,720 bytes

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, rel: str, text: str) -> None:
        with open(os.path.join(self.root, rel), "w", encoding="utf-8") as f:
            f.write(text)

    def run_script(self, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-B", SCRIPT, *args], capture_output=True,
                              text=True, cwd=self.root, env=env)

    def test_estimate_divides_each_file_by_its_own_ratio(self) -> None:
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        expected_laws = round(27720 / laws_cost.BYTES_PER_TOKEN["CLAUDE_LAWS.md"])
        self.assertIn("CLAUDE.md           2,423       1           1,000", result.stdout)
        self.assertIn(f"{expected_laws:>16,}", result.stdout)
        self.assertIn(f"{1000 + expected_laws:>16,}", result.stdout.splitlines()[3])

    def test_under_budget_says_so_without_a_warning(self) -> None:
        result = self.run_script("--budget", "20000")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Within the 20,000-token budget.", result.stdout)
        self.assertNotIn("::warning", result.stdout)

    def test_over_budget_warns_and_still_exits_zero(self) -> None:
        result = self.run_script("--budget", "5000")
        self.assertEqual(result.returncode, 0)
        self.assertIn("::warning title=Rules token budget::", result.stdout)
        self.assertIn("over the 5,000 budget", result.stdout)

    def test_a_missing_file_fails(self) -> None:
        os.remove(os.path.join(self.root, "CLAUDE_LAWS.md"))
        result = self.run_script()
        self.assertEqual(result.returncode, 1)
        self.assertIn("CLAUDE_LAWS.md: can't read it", result.stderr)

    def test_bad_arguments_print_usage(self) -> None:
        for args in (["--budget"], ["--budget", "lots"], ["--bogus"],
                     ["--measure", "--budget", "1"], ["--model", "opus"]):
            with self.subTest(args=args):
                result = self.run_script(*args)
                self.assertEqual(result.returncode, 2)
                self.assertIn("usage:", result.stderr)

    def test_measure_refuses_under_ci_before_starting_the_cli(self) -> None:
        marker = os.path.join(self.root, "started")
        fake = os.path.join(self.root, "fake-claude")
        self.write("fake-claude", f"#!/bin/sh\ntouch '{marker}'\n")
        os.chmod(fake, 0o755)
        result = self.run_script("--measure", "--claude", fake, env={**os.environ, "CI": "true"})
        self.assertEqual(result.returncode, 2)
        self.assertIn("refuses to run in CI", result.stderr)
        self.assertFalse(os.path.exists(marker))


class MeasureArithmeticTests(unittest.TestCase):
    def test_input_tokens_add_fresh_cache_write_and_cache_read(self) -> None:
        self.assertEqual(laws_cost.input_tokens(cli_result(2, 32812, 531)), 33345)
        self.assertEqual(laws_cost.input_tokens({}), 0)

    def test_the_marker_run_cancels_the_wrapper(self) -> None:
        marker = cli_result(2, 33222, 0)
        runs = {"CLAUDE.md": cli_result(2, 40692, 0), "CLAUDE_LAWS.md": cli_result(2, 55875, 0)}
        self.assertEqual(laws_cost.exact_counts(marker, runs),
                         {"CLAUDE.md": 7470, "CLAUDE_LAWS.md": 22653})

    def test_main_model_is_the_one_that_read_the_most(self) -> None:
        run = cli_result(2, 30000, 500)
        run["modelUsage"]["claude-haiku-4-5"] = {"inputTokens": 400}
        self.assertEqual(laws_cost.main_model(run), "claude-opus-5-5")
        self.assertEqual(laws_cost.main_model({}), "unknown")


if __name__ == "__main__":
    unittest.main()
