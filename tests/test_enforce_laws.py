"""Tests for the Law 32 PreToolUse hook (`.claude/hooks/enforce-laws.py`).

Each test pipes hook JSON into the script, the way Claude Code does, and
checks the exit code (0 allow, 2 block). Commits run inside temporary
repos with an initial commit, so the Law 5 check sees a real branch.

Run: python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

HOOKS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".claude", "hooks"
)
HOOK = os.path.join(HOOKS_DIR, "enforce-laws.py")
HOOK_LOG = os.path.join(HOOKS_DIR, "hook_log.py")


def env_with_home(home: str) -> dict:
    """The block log lives under $HOME. Tests point HOME at a temp
    folder so they never touch the real ~/.design-forge log."""
    return {**os.environ, "HOME": home}


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
            env=env_with_home(self.tmp.name),
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
            env=env_with_home(self.tmp.name),
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


class HookLogTests(unittest.TestCase):
    """The block log module: locking, rotation and the CLI (#113)."""

    APPEND = (
        "import sys; sys.path.insert(0, sys.argv[1]); import hook_log; "
        "sys.exit(0 if hook_log.append_block(5, 'commit-on-default', '/repo', "
        "'main', sys.argv[2]) else 3)"
    )

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = self.tmp.name
        self.dir = os.path.join(self.home, ".design-forge")
        self.log = os.path.join(self.dir, "hook-log.jsonl")
        self.old_log = os.path.join(self.dir, "hook-log.1.jsonl")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def append(self, command: str = 'git commit -m "secret-marker-xyz"') -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-B", "-c", self.APPEND, HOOKS_DIR, command],
            capture_output=True, text=True, env=env_with_home(self.home),
        )

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-B", HOOK_LOG, *args],
            capture_output=True, text=True, env=env_with_home(self.home),
        )

    def records(self, path: str | None = None) -> list[dict]:
        with open(path or self.log) as f:
            return [json.loads(line) for line in f]

    def write_records(self, path: str, records: list[dict]) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in records)

    def test_append_writes_one_line_without_the_command(self) -> None:
        self.assertEqual(self.append().returncode, 0)
        [record] = self.records()
        self.assertEqual(
            {k: record[k] for k in ("type", "law", "check", "cwd", "branch")},
            {"type": "block", "law": 5, "check": "commit-on-default",
             "cwd": "/repo", "branch": "main"},
        )
        self.assertEqual(len(record["command_sha256"]), 64)
        with open(self.log) as f:
            self.assertNotIn("secret-marker-xyz", f.read())

    def test_concurrent_appends_leave_valid_lines(self) -> None:
        procs = [
            subprocess.Popen(
                [sys.executable, "-B", "-c", self.APPEND, HOOKS_DIR, f"cmd {i}"],
                env=env_with_home(self.home),
            )
            for i in range(20)
        ]
        for p in procs:
            self.assertEqual(p.wait(), 0)
        self.assertEqual(len(self.records()), 20)  # every line parses as JSON

    def test_held_lock_skips_the_line(self) -> None:
        import fcntl

        os.makedirs(self.dir)
        with open(os.path.join(self.dir, "hook-log.lock"), "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self.assertEqual(self.append().returncode, 3)
        self.assertFalse(os.path.exists(self.log))

    def test_rotation_at_one_megabyte(self) -> None:
        filler = {"ts": "2000-01-01T00:00:00Z", "type": "block", "law": 7,
                  "check": "merge", "cwd": "/x", "branch": "main", "command_sha256": "0" * 64}
        self.write_records(self.log, [filler] * 5500)  # about 1.06 MB
        self.assertGreater(os.path.getsize(self.log), 1_000_000)
        self.append()
        self.assertEqual(len(self.records(self.old_log)), 5500)
        self.assertEqual(len(self.records()), 1)
        self.write_records(self.log, [filler] * 5500)
        self.append()
        self.assertEqual(len(self.records(self.old_log)), 5500)  # replaced, not appended
        self.assertEqual(len(self.records()), 1)

    def test_false_positive_marks_the_latest_block(self) -> None:
        self.append("first")
        self.append("second")
        result = self.run_cli("--false-positive", "worktree", "case")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        *_, last_block, mark = self.records()
        self.assertEqual(mark["type"], "false_positive")
        self.assertEqual(mark["ref_ts"], last_block["ts"])
        self.assertEqual(mark["command_sha256"], last_block["command_sha256"])
        self.assertEqual(mark["note"], "worktree case")

    def test_false_positive_without_blocks_fails(self) -> None:
        self.assertEqual(self.run_cli("--false-positive", "x").returncode, 1)

    def test_summary_counts_both_files_inside_the_window(self) -> None:
        now = datetime.now(timezone.utc)
        recent = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        stale = (now - timedelta(days=40)).strftime("%Y-%m-%dT%H:%M:%SZ")

        def rec(ts: str, law: int, check: str) -> dict:
            return {"ts": ts, "type": "block", "law": law, "check": check}

        self.write_records(self.old_log, [rec(stale, 7, "merge"), rec(recent, 5, "commit-on-default")])
        self.write_records(self.log, [
            rec(recent, 5, "commit-on-default"), rec(recent, 13, "commit-message"),
            {"ts": recent, "type": "false_positive", "ref_ts": recent,
             "check": "commit-message", "note": "heredoc"},
        ])
        out = self.run_cli("--summary").stdout
        self.assertIn("Law 5 · commit-on-default: 2", out)
        self.assertIn("Law 13 · commit-message: 1", out)
        self.assertNotIn("merge", out)
        self.assertIn("Total: 3 blocks, 1 marked false positive.", out)
        self.assertIn("heredoc", out)


class BlockLogWiringTests(unittest.TestCase):
    """The hook writes a block-log line, and logging never changes the
    decision (#113)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        os.makedirs(self.home)
        self.main_repo = os.path.join(self.tmp.name, "main-repo")
        self.feat_repo = os.path.join(self.tmp.name, "feat-repo")
        make_repo(self.main_repo, "main")
        make_repo(self.feat_repo, "feat/x")
        self.log = os.path.join(self.home, ".design-forge", "hook-log.jsonl")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_hook(self, command: str, cwd: str, hook: str = HOOK) -> subprocess.CompletedProcess:
        payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd}
        return subprocess.run(
            [sys.executable, hook], input=json.dumps(payload),
            capture_output=True, text=True, cwd=cwd, env=env_with_home(self.home),
        )

    def test_block_writes_one_line(self) -> None:
        result = self.run_hook('git commit -m "fix: x"', self.main_repo)
        self.assertEqual(result.returncode, 2, result.stderr)
        with open(self.log) as f:
            [record] = [json.loads(line) for line in f]
        self.assertEqual((record["law"], record["check"], record["branch"]),
                         (5, "commit-on-default", "main"))
        self.assertEqual(os.path.realpath(record["cwd"]), os.path.realpath(self.main_repo))

    def test_allowed_call_writes_nothing(self) -> None:
        self.assertEqual(self.run_hook('git commit -m "fix: x"', self.feat_repo).returncode, 0)
        self.assertFalse(os.path.exists(self.log))

    def test_commit_message_is_not_logged(self) -> None:
        result = self.run_hook('git commit -m "secret-marker-xyz"', self.feat_repo)
        self.assertEqual(result.returncode, 2, result.stderr)
        with open(self.log) as f:
            log = f.read()
        self.assertIn('"check": "commit-message"', log)
        self.assertNotIn("secret-marker-xyz", log)

    def test_unwritable_log_still_blocks(self) -> None:
        with open(os.path.join(self.home, ".design-forge"), "w") as f:
            f.write("not a folder")
        result = self.run_hook('git commit -m "fix: x"', self.main_repo)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Blocked (Law 5)", result.stderr)

    def test_missing_module_still_blocks(self) -> None:
        lone = os.path.join(self.tmp.name, "lone")
        os.makedirs(lone)
        shutil.copy(HOOK, lone)
        result = self.run_hook('git commit -m "fix: x"', self.main_repo,
                               os.path.join(lone, "enforce-laws.py"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("Blocked (Law 5)", result.stderr)

    def test_hook_leaves_no_bytecode_next_to_it(self) -> None:
        self.run_hook('git commit -m "fix: x"', self.main_repo)
        self.assertFalse(os.path.exists(os.path.join(HOOKS_DIR, "__pycache__")))


if __name__ == "__main__":
    unittest.main()
