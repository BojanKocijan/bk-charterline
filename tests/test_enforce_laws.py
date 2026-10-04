"""Tests for the Law 32 PreToolUse hook (`.claude/hooks/enforce-laws.py`).

Each test pipes hook JSON into the script, the way Claude Code does, and
checks the exit code (0 allow, 2 block). Commits run inside temporary
repos with an initial commit, so the Law 5 check sees a real branch.

Run: python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".claude", "hooks", "enforce-laws.py",
)


PR_CREATE = '''gh pr create --title "docs(readme): x" --body "$(cat <<'EOF'
## Summary

Fixes the "quoted" thing && more; see notes.

Screenshots: not applicable
EOF
)"'''


def make_repo(path: str, branch: str) -> None:
    # An initial commit matters: without one `git rev-parse --abbrev-ref
    # HEAD` fails, the hook sees no branch and allows every commit.
    subprocess.run(["git", "init", "-q", "-b", branch, path], check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
         "commit", "-q", "--allow-empty", "-m", "chore: init"],
        cwd=path, check=True,
    )


class WorkingDirectoryTests(unittest.TestCase):
    """The Law 5 check reads the repo the command runs in, not the hook
    process's own cwd (#110)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.main_repo = os.path.join(self.tmp.name, "main-repo")
        self.feat_repo = os.path.join(self.tmp.name, "feat-repo")
        make_repo(self.main_repo, "main")
        make_repo(self.feat_repo, "feat/x")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_hook(
        self, command: str, process_cwd: str, payload_cwd: str | None = None
    ) -> subprocess.CompletedProcess:
        payload = {"tool_name": "Bash", "tool_input": {"command": command}}
        if payload_cwd is not None:
            payload["cwd"] = payload_cwd
        return subprocess.run(
            [sys.executable, HOOK], input=json.dumps(payload),
            capture_output=True, text=True, cwd=process_cwd,
        )

    def assertAllowed(self, result: subprocess.CompletedProcess) -> None:
        self.assertEqual(result.returncode, 0, result.stderr)

    def assertBlockedLaw5(self, result: subprocess.CompletedProcess) -> None:
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("Law 5", result.stderr)

    def test_payload_cwd_on_feature_branch_is_allowed(self) -> None:
        self.assertAllowed(self.run_hook(
            'git commit -m "fix: x"', self.main_repo, self.feat_repo
        ))

    def test_payload_cwd_on_main_is_blocked(self) -> None:
        self.assertBlockedLaw5(self.run_hook(
            'git commit -m "fix: x"', self.feat_repo, self.main_repo
        ))

    def test_cd_with_semicolon_is_followed(self) -> None:
        self.assertAllowed(self.run_hook(
            f'cd {self.feat_repo}; git commit -m "fix: x"', self.main_repo
        ))

    def test_cd_with_semicolon_into_main_is_blocked(self) -> None:
        self.assertBlockedLaw5(self.run_hook(
            f'cd {self.main_repo}; git commit -m "fix: x"', self.feat_repo
        ))

    def test_cd_inside_heredoc_body_is_ignored(self) -> None:
        self.assertAllowed(self.run_hook(
            f"cd {self.feat_repo} && git commit -F - <<'EOF'\n"
            "fix: x\n\nWas blocked; cd foo resolved to the wrong repo.\n"
            "cd bar\nEOF",
            self.main_repo,
        ))

    def test_trailing_cd_dash_is_ignored(self) -> None:
        self.assertAllowed(self.run_hook(
            f'cd {self.feat_repo} && git commit -m "fix: x" && cd -',
            self.main_repo,
        ))


class CommitMessageTests(unittest.TestCase):
    """The Law 13 check reads only each commit's own message (#107)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        make_repo(self.tmp.name, "feat/x")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_hook(self, command: str) -> subprocess.CompletedProcess:
        payload = {"tool_name": "Bash", "tool_input": {"command": command}}
        return subprocess.run(
            [sys.executable, HOOK], input=json.dumps(payload),
            capture_output=True, text=True, cwd=self.tmp.name,
        )

    def assertAllowed(self, command: str) -> None:
        result = self.run_hook(command)
        self.assertEqual(result.returncode, 0, result.stderr)

    def assertBlockedLaw13(self, command: str, got: str) -> None:
        result = self.run_hook(command)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("Law 13", result.stderr)
        self.assertIn(repr(got), result.stderr)

    def test_commit_chained_with_pr_heredoc_is_allowed(self) -> None:
        self.assertAllowed(
            'git commit -m "docs(readme): make the story funnier" && '
            "git push -u origin feat/x && " + PR_CREATE
        )

    def test_heredoc_commit_chained_with_pr_heredoc_is_allowed(self) -> None:
        self.assertAllowed(
            '''git commit -m "$(cat <<'EOF'
fix(hook): read the commit's own message

Body with "quotes" && a ; semicolon.
EOF
)" && ''' + PR_CREATE
        )

    def test_heredoc_commit_with_bad_first_line_is_blocked(self) -> None:
        self.assertBlockedLaw13(
            '''git commit -m "$(cat <<'EOF'
Update the readme

Body.
EOF
)"''',
            "Update the readme",
        )

    def test_plain_bad_message_is_blocked(self) -> None:
        self.assertBlockedLaw13('git commit -m "bad message"', "bad message")

    def test_second_commit_with_bad_message_is_blocked(self) -> None:
        self.assertBlockedLaw13(
            'git commit -m "fix(a): ok"; git commit -m "oops"', "oops"
        )


if __name__ == "__main__":
    unittest.main()
