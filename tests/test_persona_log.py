#!/usr/bin/env python3
"""Tests for .claude/hooks/persona_log.py (#256): a mode command is logged
without its text, nothing else is, the hook never fails a prompt, and
install.sh registers it once."""
from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(REPO, ".claude", "hooks", "persona_log.py")
sys.path.insert(0, os.path.join(REPO, "scripts"))
import my_metrics_sessions as sessions  # noqa: E402


class PersonaLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        self.rules = os.path.join(self.home, ".bk-charterline")
        os.makedirs(self.rules)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def submit(self, prompt, stdin: str | None = None) -> subprocess.CompletedProcess:
        event = json.dumps({"session_id": "s1", "hook_event_name": "UserPromptSubmit", "prompt": prompt})
        return subprocess.run([sys.executable, HOOK], input=event if stdin is None else stdin, capture_output=True,
                              text=True, env={**os.environ, "HOME": self.home})

    def lines(self) -> list[dict]:
        path = os.path.join(self.rules, "persona-log.jsonl")
        if not os.path.exists(path):
            return []
        with open(path) as f:
            return [json.loads(line) for line in f]

    def test_a_mode_command_is_logged_without_its_text(self) -> None:
        done = self.submit("  Tester   MODE\n")
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))
        [row] = self.lines()
        self.assertEqual((row["session_id"], row["persona"]), ("s1", "Tester"))
        self.assertEqual(set(row), {"ts", "session_id", "persona"})

    def test_any_other_prompt_writes_nothing(self) -> None:
        for prompt in ("tester mode please", "switch to tester mode", "", None, 42):
            self.assertEqual(self.submit(prompt).returncode, 0)
        self.assertEqual(self.lines(), [])

    def test_it_never_fails_a_prompt(self) -> None:
        self.assertEqual(self.submit(None, stdin="{not json").returncode, 0)
        os.chmod(self.rules, 0o500)  # the log can't be written
        try:
            done = self.submit("team")
        finally:
            os.chmod(self.rules, 0o700)
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))

    def test_the_dashboard_counts_a_logged_session_whose_log_is_gone(self) -> None:
        self.submit("backend mode")
        root = os.path.join(self.tmp.name, "projects")
        os.makedirs(os.path.join(root, "-p"))
        now = datetime.datetime.now(datetime.timezone.utc)
        when = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        with open(os.path.join(root, "-p", "s2.jsonl"), "w") as f:
            f.write(json.dumps({"type": "assistant", "timestamp": when, "message": {"id": "m", "usage": {"input_tokens": 10}}}) + "\n")
        r = sessions.sessions(self.rules, now, now - datetime.timedelta(days=30), root)
        self.assertEqual(r["personas"], [{"persona": "Backend", "sessions": 1}, {"persona": "Frontend", "sessions": 1}])
        self.assertEqual((r["sessions"], r["median_tokens"]), (1, 10))  # tokens only from logs still on disk

    def test_install_registers_it_once(self) -> None:
        with open(os.path.join(REPO, "install.sh")) as f:
            script = next(b for b in re.findall(r"<<'PYEOF'\n(.*?)\nPYEOF\n", f.read(), re.S) if "wanted = [" in b)
        settings = os.path.join(self.tmp.name, "settings.json")
        with open(settings, "w") as f:
            json.dump({"hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": "other"}]}]}}, f)
        args = [settings, 'python3 "/x/enforce-laws.py"', 'python3 "/old/enforce-laws.py"', 'python3 "/x/persona_log.py"']
        for _ in range(2):
            subprocess.run([sys.executable, "-", *args], input=script, text=True, check=True)
        with open(settings) as f:
            hooks = json.load(f)["hooks"]
        self.assertEqual(hooks["UserPromptSubmit"], [
            {"hooks": [{"type": "command", "command": "other"}]},
            {"hooks": [{"type": "command", "command": 'python3 "/x/persona_log.py"'}]}])
        self.assertEqual([e["matcher"] for e in hooks["PreToolUse"]], ["Bash", "Edit|Write|MultiEdit|NotebookEdit", "mcp__.*"])


if __name__ == "__main__":
    unittest.main()
