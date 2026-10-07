"""Tests for the Law 32 PreToolUse hook (`.claude/hooks/enforce-laws.py`).

Each test pipes hook JSON into the script, the way Claude Code does, and
checks the exit code (0 allow, 2 block). Commits run inside temporary
repos with an initial commit, so the Law 5 check sees a real branch.

Run: python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import base64
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
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


class SkipAndForceTests(unittest.TestCase):
    """Never skip git hooks; never force-push the default branch (#117)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.feat = os.path.join(self.tmp.name, "feat-repo")
        make_repo(self.feat, "feat/x")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_hook(self, command: str) -> subprocess.CompletedProcess:
        payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": self.feat}
        return subprocess.run(
            [sys.executable, HOOK], input=json.dumps(payload),
            capture_output=True, text=True, cwd=self.feat, env=env_with_home(self.tmp.name),
        )

    def assertBlocked(self, command: str, needle: str) -> None:
        result = self.run_hook(command)
        self.assertEqual(result.returncode, 2, f"{command!r}: {result.stderr}")
        self.assertIn(needle, result.stderr)

    def assertAllowed(self, command: str) -> None:
        result = self.run_hook(command)
        self.assertEqual(result.returncode, 0, f"{command!r}: {result.stderr}")

    def test_skipping_git_hooks_is_blocked(self) -> None:
        for command in (
            'git commit --no-verify -m "fix: x"',
            'git commit -n -m "fix: x"',
            'git commit -an -m "fix: x"',
            'git -C . commit --no-verify -m "fix: x"',
            "git push --no-verify origin feat/x",
            'git add . && git commit -n -m "fix: x"',
        ):
            self.assertBlocked(command, "--no-verify")

    def test_review_bypasses_of_the_hook_skip_check_are_blocked(self) -> None:
        for command in (
            'git commit -m "fix: x" -n',
            'git commit -m "fix: x" --no-verify',
            'git commit -am "fix: x" -n',
            'git commit -F msg.txt --no-verify',
            'HUSKY=0 git commit --no-verify -m "fix: x"',
            'command git commit -n -m "fix: x"',
            'env CI=1 git commit -n -m "fix: x"',
            'git -c core.hooksPath=/dev/null commit -m "fix: x"',
            'git -ccore.hooksPath=/dev/null commit -m "fix: x"',
            'GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/dev/null git commit -m "fix: x"',
        ):
            self.assertBlocked(command, "--no-verify")

    def test_untracked_files_flag_is_not_no_verify(self) -> None:
        self.assertAllowed('git commit -uno -m "fix: x"')
        self.assertAllowed('git -c user.name=x commit -m "fix: x"')

    def test_dry_run_and_flag_text_in_messages_are_allowed(self) -> None:
        self.assertAllowed("git push -n origin feat/x")
        self.assertAllowed('git commit -m "fix: document the -n flag"')
        self.assertAllowed('git commit -m "fix: x" -m "mentions --no-verify in prose"')

    def test_force_push_to_default_is_blocked(self) -> None:
        for command in (
            "git push --force origin main",
            "git push -f origin HEAD:main",
            "git push -uf origin main",
            "git push --force-with-lease=main origin main",
            "git push --force-if-includes origin main",
            "git push origin +main",
            "git push origin +HEAD:main",
        ):
            self.assertBlocked(command, "force-push")

    def test_review_bypasses_of_the_push_checks_are_blocked(self) -> None:
        main_repo = os.path.join(self.tmp.name, "main-repo")
        make_repo(main_repo, "main")
        for command, cwd in (
            ("git push --force-with-lease=main:abc123 origin main", self.feat),
            ("git push --force-with-lease=main:abc123 origin main", main_repo),
            ("git push -o ci.skip=a:b origin main", self.feat),
            ("git push -f origin HEAD", main_repo),
            ("git push origin HEAD", main_repo),
        ):
            payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd}
            result = subprocess.run([sys.executable, HOOK], input=json.dumps(payload), capture_output=True,
                                    text=True, cwd=cwd, env=env_with_home(self.tmp.name))
            self.assertEqual(result.returncode, 2, f"{command!r} in {cwd}: {result.stderr}")
        self.assertAllowed("git push origin HEAD")  # feature branch

    def test_force_push_to_a_feature_branch_is_allowed(self) -> None:
        self.assertAllowed("git push --force origin feat/x")
        self.assertAllowed("git push --force-with-lease origin feat/x")
        self.assertAllowed("git push origin +feat/x")


class HookRunner:
    """Pipes a payload into the hook and reads its decision."""

    def run_payload(self, payload: dict, cwd: str | None = None) -> subprocess.CompletedProcess:
        payload.setdefault("cwd", cwd or self.project)
        return subprocess.run(
            [sys.executable, HOOK], input=json.dumps(payload), capture_output=True,
            text=True, cwd=cwd or self.project, env=env_with_home(self.home),
        )

    def decision(self, result: subprocess.CompletedProcess) -> str:
        if result.returncode == 2:
            return "block"
        self.assertEqual(result.returncode, 0, result.stderr)
        if not result.stdout.strip():
            return "allow"
        return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]

    def edit(self, path: str, tool: str = "Edit") -> str:
        key = "notebook_path" if tool == "NotebookEdit" else "file_path"
        return self.decision(self.run_payload({"tool_name": tool, "tool_input": {key: path}}))

    def bash(self, command: str, cwd: str | None = None) -> str:
        return self.decision(self.run_payload({"tool_name": "Bash", "tool_input": {"command": command}}, cwd))


class GuardrailAskTests(HookRunner, unittest.TestCase):
    """Changing a guardrail file hands the call to the user (#117)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.realpath(os.path.join(self.tmp.name, "home"))
        self.forge = os.path.join(self.home, ".design-forge")
        os.makedirs(os.path.join(self.forge, "skills", "ux-writing"))
        os.makedirs(os.path.join(self.forge, "knowledge"))
        os.makedirs(os.path.join(self.home, ".claude", "skills"))
        os.symlink(os.path.join(self.forge, "skills", "ux-writing"),
                   os.path.join(self.home, ".claude", "skills", "ux-writing"))
        self.project = os.path.realpath(os.path.join(self.tmp.name, "project"))
        make_repo(self.project, "feat/x")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @unittest.skipUnless(sys.platform == "darwin", "case-insensitive file systems")
    def test_wrong_case_paths_still_ask_on_macos(self) -> None:
        self.assertEqual(self.edit(f"{self.home}/.Claude/Settings.json", "Write"), "ask")
        self.assertEqual(self.edit(f"{self.home}/.DESIGN-FORGE/CLAUDE_LAWS.md", "Write"), "ask")
        self.assertEqual(self.edit(f"{self.home}/.design-forge/Hook-Log.jsonl", "Write"), "allow")

    def test_non_object_payload_fails_open(self) -> None:
        for raw in ("[]", '"x"', "null", "42"):
            result = subprocess.run([sys.executable, HOOK], input=raw, capture_output=True, text=True,
                                    cwd=self.project, env=env_with_home(self.home))
            self.assertEqual((result.returncode, result.stdout), (0, ""), raw)

    def test_editing_a_guardrail_file_asks(self) -> None:
        h = self.home
        for path in (
            f"{h}/.claude/settings.json",
            f"{h}/.claude/settings.local.json",
            f"{h}/.claude/CLAUDE.md",
            f"{self.project}/.claude/settings.local.json",
            f"{self.forge}/CLAUDE_LAWS.md",
            f"{self.forge}/.claude/hooks/enforce-laws.py",
            f"{h}/.claude/skills/ux-writing/SKILL.md",  # symlink into the installed clone
        ):
            for tool in ("Edit", "Write", "MultiEdit"):
                self.assertEqual(self.edit(path, tool), "ask", f"{tool} {path}")
        self.assertEqual(self.edit(f"{self.forge}/x.ipynb", "NotebookEdit"), "ask")

    def test_ask_carries_a_reason_for_the_prompt(self) -> None:
        result = self.run_payload({"tool_name": "Write", "tool_input": {"file_path": f"{self.home}/.claude/settings.json"}})
        reason = json.loads(result.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("Law 32", reason)
        self.assertIn("your Claude Code settings", reason)

    def test_data_files_dev_checkouts_and_normal_files_are_free(self) -> None:
        dev = os.path.join(self.tmp.name, "design-forge-dev", ".claude", "hooks", "enforce-laws.py")
        for path in (
            f"{self.forge}/hook-log.jsonl",
            f"{self.forge}/hook-log.1.jsonl",
            f"{self.forge}/ai-inventory.md",
            f"{self.forge}/projects.yaml",
            f"{self.forge}/knowledge/PATTERNS.md",
            dev,
            f"{self.project}/src/app.ts",
            f"{self.project}/.claude/agents/helper.md",
        ):
            self.assertEqual(self.edit(path, "Write"), "allow", path)
        self.assertEqual(self.edit(f"{self.project}/notebook.ipynb", "NotebookEdit"), "allow")

    def test_bash_writes_to_guardrail_files_ask(self) -> None:
        for command in (
            "echo '{}' > ~/.claude/settings.json",
            "echo x >> ~/.claude/CLAUDE.md",
            "echo x | tee ~/.claude/settings.local.json",
            "sed -i '' 's/a/b/' ~/.design-forge/CLAUDE_LAWS.md",
            "cp /tmp/evil.json ~/.claude/settings.json",
            "mv ~/.design-forge/CLAUDE_LAWS.md /tmp/x",
            "rm ~/.design-forge/.claude/hooks/enforce-laws.py",
            "chmod 777 .claude/settings.local.json",
        ):
            self.assertEqual(self.bash(command), "ask", command)

    def test_review_bypasses_of_the_write_guard_ask(self) -> None:
        os.makedirs(os.path.join(self.home, ".claude"), exist_ok=True)
        for command in (
            'echo x >> "$HOME/.claude/CLAUDE.md"',
            "cp /tmp/x.py $HOME/.design-forge/.claude/hooks/enforce-laws.py",
            'rm -rf "$HOME/.design-forge/.claude/hooks"',
            "cp /tmp/settings.json ~/.claude/",
            "mv /tmp/settings.json ~/.claude",
            "cp -t ~/.claude /tmp/settings.json",
            "perl -pi -e 's/a/b/' ~/.claude/settings.json",
            "sed --in-place 's/a/b/' ~/.claude/settings.json",
            "sed -Ei 's/a/b/' ~/.claude/settings.json",
            "ln -sf /tmp/evil.json ~/.claude/settings.json",
            "install -m 644 /tmp/x ~/.claude/settings.json",
            "unlink ~/.claude/settings.json",
            "truncate -s 0 ~/.claude/CLAUDE.md",
            "chown root ~/.claude/settings.json",
            "echo x 2> ~/.claude/settings.json",
            "echo x &> ~/.claude/settings.json",
            "echo x >| ~/.claude/settings.json",
            "HOME_COPY=1 tee ~/.claude/settings.json < /tmp/x",
            "cp /tmp/settings.json ~/.claude/settings.json 2>/dev/null",
            "cp /tmp/settings.json ~/.claude/ 2>/dev/null",
            "cp /tmp/settings.json ~/.claude/settings.json > /dev/null 2>&1",
        ):
            self.assertEqual(self.bash(command), "ask", command)
        self.assertEqual(self.edit(f"{self.forge}/hook-logger.py", "Write"), "ask")

    def test_law_38_registry_and_approvals_ask(self) -> None:
        for path, what in (
            (f"{self.forge}/ai-tools.json", "your Law 38 tool registry"),
            (f"{self.forge}/ai-approvals.jsonl", "your Law 38 approvals"),
            (f"{self.forge}/ai-approvals.jsonl.tmp", "your Law 38 approvals"),
            (f"{self.project}/.claude/ai-tools.json", "a project's Law 38 tool registry"),
        ):
            result = self.run_payload({"tool_name": "Write", "tool_input": {"file_path": path}})
            self.assertEqual(self.decision(result), "ask", path)
            self.assertIn(what, json.loads(result.stdout)["hookSpecificOutput"]["permissionDecisionReason"])
        for command in (
            "echo '{}' > ~/.design-forge/ai-tools.json",
            "echo x >> ~/.design-forge/ai-approvals.jsonl",
            "cp /tmp/x.json .claude/ai-tools.json",
            "mv stage .claude",
            "ln -s stage .claude",
            "mv /tmp/stage ~/.claude",
        ):
            self.assertEqual(self.bash(command), "ask", command)

    def test_registry_set_asks_and_show_is_free(self) -> None:
        for command in (
            "python3 ~/.design-forge/scripts/ai_tools.py set mcp:db --tier 2 --owner a --personal",
            "python ~/.design-forge/scripts/ai_tools.py set mcp:db --tier 2 --owner a --personal",
            "python3.12 -B scripts/ai_tools.py set mcp:db --tier 2 --owner a --personal",
            "python3 -W ignore scripts/ai_tools.py set mcp:db --tier 2 --owner a --personal",
            "./scripts/ai_tools.py set mcp:db --tier 2 --owner a --personal",
            "cd scripts && python3 -m ai_tools set mcp:db --tier 2 --owner a --personal",
            "env FOO=1 python3 scripts/ai_tools.py set mcp:db --tier 2 --owner a --personal",
            'bash -c "python3 scripts/ai_tools.py set mcp:db --tier 1 --owner a --personal"',
            "sh -c 'cd scripts && ./ai_tools.py set mcp:db --tier 1 --owner a --personal'",
            "uv run scripts/ai_tools.py set mcp:db --tier 1 --owner a --personal",
            "uv run python3 scripts/ai_tools.py set mcp:db --tier 1 --owner a --personal",
        ):
            self.assertEqual(self.bash(command), "ask", command)
        result = self.run_payload({"tool_name": "Bash", "tool_input": {
            "command": "python3 scripts/ai_tools.py set mcp:db --tier 2 --owner a --personal"}})
        reason = json.loads(result.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("Law 38", reason)
        for command in (
            "python3 ~/.design-forge/scripts/ai_tools.py show mcp:db",
            "python3 scripts/ai_tools.py show set",
            "python3 scripts/ai_inventory.py --project . --session set",
            "grep set scripts/ai_tools.py",
        ):
            self.assertEqual(self.bash(command), "allow", command)

    def test_registry_write_is_logged_under_law_38(self) -> None:
        self.bash("python3 scripts/ai_tools.py set mcp:db --tier 2 --owner a --personal")
        with open(os.path.join(self.forge, "hook-log.jsonl")) as f:
            [record] = [json.loads(line) for line in f]
        self.assertEqual((record["type"], record["law"], record["check"]), ("ask", 38, "registry-write"))

    def test_relative_write_is_judged_before_a_later_cd(self) -> None:
        self.assertEqual(self.bash("echo x > .claude/settings.local.json && cd /tmp"), "ask")

    def test_quoted_redirect_text_is_not_a_write(self) -> None:
        self.assertEqual(self.bash('git commit -m "docs: mention > ~/.claude/settings.json"'), "allow")
        self.assertEqual(self.bash("echo x 2>&1 | tee build.log"), "allow")

    def test_bash_reads_and_updates_are_free(self) -> None:
        for command in (
            "cat ~/.claude/settings.json",
            "grep -n hooks ~/.claude/settings.json",
            "cp ~/.claude/settings.json /tmp/settings-backup.json",
            '"$SHELL" -ic dforge-update',  # git by hand in the clone asks now (#170)
            "python3 ~/.design-forge/scripts/ai_tools.py show mcp:db",
            "echo hi > notes.txt",
        ):
            self.assertEqual(self.bash(command), "allow", command)

    def test_a_block_always_wins_over_an_ask(self) -> None:
        main_repo = os.path.join(self.tmp.name, "main-repo")
        make_repo(main_repo, "main")
        self.assertEqual(
            self.bash('echo x > ~/.claude/settings.json && git commit -m "fix: x"', main_repo), "block"
        )

    def test_asks_are_logged_as_asks(self) -> None:
        self.edit(f"{self.home}/.claude/settings.json", "Write")
        with open(os.path.join(self.forge, "hook-log.jsonl")) as f:
            [record] = [json.loads(line) for line in f]
        self.assertEqual((record["type"], record["law"], record["check"]), ("ask", 32, "guardrail-edit"))
        summary = subprocess.run([sys.executable, "-B", HOOK_LOG, "--summary"], capture_output=True,
                                 text=True, env=env_with_home(self.home)).stdout
        self.assertIn("Permission prompts (asks): 1 — guardrail-edit: 1", summary)

    def test_a_listed_mode_turns_the_ask_into_a_deny(self) -> None:
        patched = os.path.join(self.tmp.name, "hook-patched.py")
        with open(HOOK) as f:
            code = f.read().replace('ASK_DENIED_MODES: set[str] = set()', 'ASK_DENIED_MODES: set[str] = {"bypassPermissions"}')
        with open(patched, "w") as f:
            f.write(code)
        payload = {"tool_name": "Write", "tool_input": {"file_path": f"{self.home}/.claude/settings.json"},
                   "cwd": self.project, "permission_mode": "bypassPermissions"}
        result = subprocess.run([sys.executable, patched], input=json.dumps(payload), capture_output=True,
                                text=True, cwd=self.project, env=env_with_home(self.home))
        out = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("switch permission mode", out["permissionDecisionReason"])
        payload["permission_mode"] = "default"
        result = subprocess.run([sys.executable, patched], input=json.dumps(payload), capture_output=True,
                                text=True, cwd=self.project, env=env_with_home(self.home))
        self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_unparsable_input_fails_open(self) -> None:
        self.assertEqual(self.bash("echo 'unbalanced > ~/.claude/settings.json"), "allow")
        self.assertEqual(self.decision(self.run_payload({"tool_name": "Write", "tool_input": {}})), "allow")


class InstalledCloneGitTests(HookRunner, unittest.TestCase):
    """git that changes the installed ~/.design-forge asks the user, since
    it skips dforge-update's reviewed-diff gate (#170)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.realpath(os.path.join(self.tmp.name, "home"))
        self.forge = os.path.join(self.home, ".design-forge")
        make_repo(self.forge, "main")
        os.makedirs(os.path.join(self.forge, "knowledge"))
        self.project = os.path.realpath(os.path.join(self.tmp.name, "project"))
        make_repo(self.project, "feat/x")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_moving_the_clone_asks(self) -> None:
        link = os.path.join(self.tmp.name, "forge-link")
        os.symlink(self.forge, link)
        for command in (
            "git -C ~/.design-forge checkout v2.27.0",
            "cd ~/.design-forge && git pull",
            "cd ~/.design-forge\ngit fetch && git reset --hard origin/main",
            'git -C "$HOME/.design-forge" switch main',
            "git -C ~/.design-forge/knowledge restore .",
            "git -C ~ -C .design-forge merge origin/main",
            f"git -C {link} rebase origin/main",
            "git --git-dir ~/.design-forge/.git --work-tree ~/.design-forge checkout v2.27.0",
            "git --work-tree=$HOME/.design-forge checkout .",
            "GIT_WORK_TREE=~/.design-forge git checkout x",
            'bash -c "cd ~/.design-forge && git switch main"',
            '"$SHELL" -ic "git -C ~/.design-forge pull --ff-only"',
            "git -C ~/.design-forge stash pop",
            "git -C ~/.design-forge stash",
            "git -C ~/.design-forge clean -fdx",
            "git -C ~/.design-forge cherry-pick abc123",
            "git -C ~/.design-forge apply /tmp/x.patch",
        ):
            self.assertEqual(self.bash(command), "ask", command)

    def test_the_ask_names_the_command_and_is_logged(self) -> None:
        result = self.run_payload({"tool_name": "Bash", "tool_input": {"command": "git -C ~/.design-forge pull"}})
        reason = json.loads(result.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("`git pull`", reason)
        self.assertIn("dforge-update", reason)
        with open(os.path.join(self.forge, "hook-log.jsonl")) as f:
            [record] = [json.loads(line) for line in f]
        self.assertEqual((record["type"], record["law"], record["check"]), ("ask", 32, "guardrail-git"))

    def test_reads_exceptions_and_updates_are_free(self) -> None:
        for command in (
            "git -C ~/.design-forge status",
            "git -C ~/.design-forge log -1 --format=%ct",
            "git -C ~/.design-forge fetch --tags",
            "git -C ~/.design-forge ls-remote --tags origin 'v*'",
            "git -C ~/.design-forge describe --tags",
            "git -C ~/.design-forge tag --list",
            "git -C ~/.design-forge rev-parse HEAD",
            "git -C ~/.design-forge stash list",
            "git -C ~/.design-forge stash show -p",
            "dforge-update",
            "dforge-update --main",
            '"$SHELL" -ic dforge-update',
        ):
            self.assertEqual(self.bash(command), "allow", command)

    def test_other_repos_are_free(self) -> None:
        dev = os.path.join(self.tmp.name, "design-forge")
        make_repo(dev, "main")
        for command in (
            f"git -C {dev} pull",
            f"cd {dev} && git checkout -b feat/x",
            "git reset --hard HEAD",
            "git -C ~/.design-forge-old checkout x",
        ):
            self.assertEqual(self.bash(command), "allow", command)
        self.assertEqual(self.bash("git pull", self.forge), "ask")

    def test_a_block_still_wins(self) -> None:
        self.assertEqual(self.bash("cd ~/.design-forge && git pull && git push"), "block")

    def test_unbalanced_quotes_fail_open(self) -> None:
        self.assertEqual(self.bash("git -C ~/.design-forge checkout 'x"), "allow")


class UpdateApproveTests(HookRunner, unittest.TestCase):
    """`dforge-update --approve` applies a hook change; the app's prompt
    is the user's approval (#170)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.realpath(os.path.join(self.tmp.name, "home"))
        os.makedirs(os.path.join(self.home, ".design-forge"))
        self.project = os.path.realpath(os.path.join(self.tmp.name, "project"))
        make_repo(self.project, "feat/x")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_approve_asks_in_every_form(self) -> None:
        for command in (
            "dforge-update --approve 3021c61aa",
            "dforge-update --main --approve 3021c61aa",
            "\"$SHELL\" -ic 'dforge-update --approve 3021c61aa'",
            'bash -c "dforge-update --approve 3021c61aa"',
            "cd ~ && dforge-update --approve 3021c61aa",
        ):
            self.assertEqual(self.bash(command), "ask", command)

    def test_the_ask_is_logged_under_law_28(self) -> None:
        self.bash("dforge-update --approve 3021c61aa")
        with open(os.path.join(self.home, ".design-forge", "hook-log.jsonl")) as f:
            [record] = [json.loads(line) for line in f]
        self.assertEqual((record["type"], record["law"], record["check"]), ("ask", 28, "update-approve"))

    def test_plain_updates_stay_free(self) -> None:
        for command in ("dforge-update", "dforge-update --main", "\"$SHELL\" -ic dforge-update",
                        "dforge-update --help", "echo use --approve later"):
            self.assertEqual(self.bash(command), "allow", command)


class HostingCliTests(HookRunner, unittest.TestCase):
    """Netlify and Vercel CLI commands act with the user's account: anything
    but a verified read or local command asks, on every call (#173)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.realpath(os.path.join(self.tmp.name, "home"))
        os.makedirs(os.path.join(self.home, ".design-forge"))
        self.project = os.path.realpath(os.path.join(self.tmp.name, "project"))
        make_repo(self.project, "feat/x")
        os.makedirs(os.path.join(self.project, "site"))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_writes_secrets_and_unknown_commands_ask(self) -> None:
        for command in (
            "netlify deploy --prod",
            "ntl deploy",
            "netlify env:set KEY value",
            "netlify env:list",
            "netlify api rollbackSiteDeploy --data '{}'",
            "netlify database migrations apply",
            "netlify db reset",
            "netlify sites:delete",
            "netlify blobs:set store key value",
            "netlify login",
            "netlify frobnicate",
            "vercel",
            "vercel --prod",
            "vc ./site",
            "vercel deploy",
            "vercel promote dpl_1",
            "vercel rollback",
            "vercel env pull",
            "vercel env ls",
            "vercel pull",
            "vercel dns rm rec_1",
            "vercel --scope ls deploy",
            "vercel --name ls",
            "vercel -S team",
            "vercel api /v2/user",
            "vercel frobnicate",
        ):
            self.assertEqual(self.bash(command), "ask", command)

    def test_runners_wrappers_and_nesting_ask(self) -> None:
        for command in (
            "npx netlify-cli deploy",
            "npx -y vercel@latest --prod",
            "npx -p netlify-cli netlify deploy",
            "pnpm dlx vercel deploy",
            "pnpm vercel deploy",
            "yarn netlify deploy",
            "bunx vercel",
            "bun x vercel",
            "npm exec -- netlify deploy",
            "npm exec netlify-cli -- deploy",
            "./node_modules/.bin/vercel --prod",
            "NETLIFY_AUTH_TOKEN=x netlify deploy",
            'bash -c "netlify deploy"',
            "\"$SHELL\" -ic 'vercel --prod'",
            "cd site && vercel --prod",
            "npm run build && netlify deploy --dir dist",
            "URL=$(vercel deploy --prod)",
            "echo y | vercel env add NAME production",
        ):
            self.assertEqual(self.bash(command), "ask", command)

    def test_reads_local_work_and_mentions_are_free(self) -> None:
        for command in (
            "netlify",
            "netlify --help",
            "netlify deploy --help",
            "netlify -v",
            "netlify logs --since 1h --json",
            "netlify logs:deploy",
            "netlify status --json",
            "netlify watch",
            "netlify sites:list",
            "netlify blobs:get store key",
            "netlify api listSiteDeploys",
            "netlify api getSite --data '{}'",
            "netlify api --list",
            "netlify db status",
            "netlify dev",
            "netlify build",
            "netlify functions:invoke hello",
            "netlify link",
            "vercel --version",
            "vercel whoami",
            "vercel ls",
            "vercel inspect dpl_1",
            "vercel logs dpl_1",
            "vercel dns ls",
            "vercel promote status",
            "vercel dev",
            "vercel build",
            "vercel --scope team ls",
            "vercel --token=x whoami",
            "npx vercel whoami",
            'echo "$(vercel whoami)"',
            "echo netlify deploy",
            "echo '$(vercel deploy)'",
            'git commit -m "docs: vercel deploy"',
            "grep -n vercel package.json",
            "npm i -g netlify-cli",
            "command -v vercel",
        ):
            self.assertEqual(self.bash(command), "allow", command)

    def test_the_ask_names_the_command_and_is_logged(self) -> None:
        result = self.run_payload({"tool_name": "Bash", "tool_input": {"command": "netlify api deleteSite"}})
        reason = json.loads(result.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("`netlify api deleteSite`", reason)
        with open(os.path.join(self.home, ".design-forge", "hook-log.jsonl")) as f:
            [record] = [json.loads(line) for line in f]
        self.assertEqual((record["type"], record["law"], record["check"]), ("ask", 38, "hosting-write"))

    def test_a_block_still_wins(self) -> None:
        main_repo = os.path.join(self.tmp.name, "main-repo")
        make_repo(main_repo, "main")
        self.assertEqual(self.bash("netlify deploy && git push", main_repo), "block")

    def test_unbalanced_quotes_fail_open(self) -> None:
        self.assertEqual(self.bash("netlify deploy --message 'x"), "allow")


class TrackedDeleteTests(unittest.TestCase):
    """Deleting a file git tracks asks the user (Law 8, #117)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        os.makedirs(self.home)
        self.repo = os.path.realpath(os.path.join(self.tmp.name, "repo"))
        make_repo(self.repo, "feat/x")
        os.makedirs(os.path.join(self.repo, "src"))
        for name, text in (("tracked.txt", "t"), ("src/app.ts", "a"), (".gitignore", "build/\n")):
            with open(os.path.join(self.repo, name), "w") as f:
                f.write(text)
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
                        "commit", "-q", "-m", "chore: files"], cwd=self.repo, check=True)
        os.makedirs(os.path.join(self.repo, "build"))
        for name in ("untracked.txt", "build/out.js"):
            with open(os.path.join(self.repo, name), "w") as f:
                f.write("x")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def bash(self, command: str) -> str:
        payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": self.repo}
        result = subprocess.run([sys.executable, HOOK], input=json.dumps(payload), capture_output=True,
                                text=True, cwd=self.repo, env=env_with_home(self.home))
        if result.returncode == 2:
            return "block"
        if not result.stdout.strip():
            return "allow"
        return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]

    def test_deleting_tracked_files_asks(self) -> None:
        for command in ("rm tracked.txt", "rm -f tracked.txt", "git rm tracked.txt",
                        "rm -r src", "unlink tracked.txt", "ls && rm tracked.txt"):
            self.assertEqual(self.bash(command), "ask", command)

    def test_untracked_ignored_outside_and_cached_are_free(self) -> None:
        for command in ("rm untracked.txt", "rm -rf build", "rm /tmp/not-in-repo.txt",
                        "git rm --cached tracked.txt", "rm -rf node_modules"):
            self.assertEqual(self.bash(command), "allow", command)

    def test_review_bypasses_of_the_delete_guard_ask(self) -> None:
        outside = os.path.join(self.tmp.name, "elsewhere")
        os.makedirs(outside)
        for command, cwd in (
            ("rm tracked.txt && cd /tmp", self.repo),
            (f"rm {self.repo}/tracked.txt", outside),
            (f"git -C {self.repo} rm tracked.txt", outside),
            ("rm ~/../repo/tracked.txt", outside),
            ('rm "$HOME/../repo/src/app.ts"', outside),
            (f"rm -r {self.repo}/src", outside),
            ("sudo rm tracked.txt", self.repo),
            ("rm -- tracked.txt", self.repo),
        ):
            payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd}
            result = subprocess.run([sys.executable, HOOK], input=json.dumps(payload), capture_output=True,
                                    text=True, cwd=cwd, env=env_with_home(self.home))
            decision = json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] if result.stdout.strip() else "allow"
            self.assertEqual(decision, "ask", f"{command!r} from {cwd}")

    def test_globs_match_like_the_shell(self) -> None:
        self.assertEqual(self.bash("rm -f *.md"), "allow")  # only src/ has tracked files, none .md here
        self.assertEqual(self.bash("rm -f *.txt"), "ask")   # tracked.txt
        self.assertEqual(self.bash("rm -f src/*.ts"), "ask")

    def test_tracked_delete_is_logged_under_law_8(self) -> None:
        self.bash("rm tracked.txt")
        with open(os.path.join(self.home, ".design-forge", "hook-log.jsonl")) as f:
            [record] = [json.loads(line) for line in f]
        self.assertEqual((record["type"], record["law"], record["check"]), ("ask", 8, "tracked-delete"))


class McpTierTests(unittest.TestCase):
    """Law 38 tier 3 and 4 asks for MCP tool calls (#138)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.realpath(os.path.join(self.tmp.name, "home"))
        self.forge = os.path.join(self.home, ".design-forge")
        os.makedirs(self.forge)
        self.project = os.path.realpath(os.path.join(self.tmp.name, "project"))
        make_repo(self.project, "feat/x")
        self.write_registry(os.path.join(self.forge, "ai-tools.json"), {
            "mcp:notes": {"tier": 1, "owner": "alice"},
            "mcp:mail": {"tier": 2, "owner": "alice", "label": "Mail", "overrides": {"send_message": 3}},
            "mcp:wiki": {"tier": 3, "owner": "bob"},
            "mcp:db": {"tier": 4, "owner": "carol", "label": "Prod DB", "overrides": {"list_tables": 2}},
        })

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_registry(self, path: str, tools: dict) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({"version": 1, "tools": tools}, f)

    def run_event(self, tool: str, event: str = "PreToolUse", session: str | None = "s1",
                  hook: str = HOOK, **extra) -> subprocess.CompletedProcess:
        payload = {"hook_event_name": event, "tool_name": tool, "tool_input": {}, "cwd": self.project, **extra}
        if session is not None:
            payload["session_id"] = session
        return subprocess.run([sys.executable, "-B", hook], input=json.dumps(payload), capture_output=True,
                              text=True, cwd=self.project, env=env_with_home(self.home))

    def decision(self, tool: str, session: str | None = "s1", hook: str = HOOK) -> str:
        result = self.run_event(tool, session=session, hook=hook)
        self.assertEqual(result.returncode, 0, result.stderr)
        if not result.stdout.strip():
            return "allow"
        return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]

    def ran(self, tool: str, session: str | None = "s1") -> None:
        result = self.run_event(tool, event="PostToolUse", session=session)
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def log_checks(self) -> list[tuple[str, str]]:
        with open(os.path.join(self.forge, "hook-log.jsonl")) as f:
            return [(r["type"], r["check"]) for r in map(json.loads, f)]

    def test_tier_1_and_2_get_no_output(self) -> None:
        self.assertEqual(self.decision("mcp__notes__search"), "allow")
        self.assertEqual(self.decision("mcp__mail__search_threads"), "allow")

    def test_tier_4_asks_every_call_and_is_never_recorded(self) -> None:
        result = self.run_event("mcp__db__execute_sql")
        reason = json.loads(result.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("tier 4 (Prod DB, owner carol)", reason)
        self.ran("mcp__db__execute_sql")
        self.assertEqual(self.decision("mcp__db__execute_sql"), "ask")
        self.assertFalse(os.path.exists(os.path.join(self.forge, "ai-approvals.jsonl")))

    def test_tier_3_asks_until_it_ran_in_that_session(self) -> None:
        self.assertEqual(self.decision("mcp__wiki__create_page"), "ask")
        self.ran("mcp__wiki__create_page")
        self.assertEqual(self.decision("mcp__wiki__create_page"), "allow")
        self.assertEqual(self.decision("mcp__wiki__create_page", session="s2"), "ask")
        self.assertEqual(self.decision("mcp__wiki__delete_page"), "ask")

    def test_no_session_id_means_no_session_memory(self) -> None:
        self.ran("mcp__wiki__create_page", session=None)
        self.assertEqual(self.decision("mcp__wiki__create_page", session=None), "ask")
        self.assertFalse(os.path.exists(os.path.join(self.forge, "ai-approvals.jsonl")))

    def test_unclassified_counts_as_tier_3(self) -> None:
        result = self.run_event("mcp__new_server__do_thing")
        reason = json.loads(result.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("unclassified", reason)
        self.assertIn("ai classify", reason)
        self.ran("mcp__new_server__do_thing")
        self.assertEqual(self.decision("mcp__new_server__do_thing"), "allow")

    def test_overrides_raise_or_lower_one_tool(self) -> None:
        self.assertEqual(self.decision("mcp__mail__send_message"), "ask")
        self.assertEqual(self.decision("mcp__db__list_tables"), "allow")

    def test_project_entry_wins_and_invalid_entries_count_as_tier_3(self) -> None:
        registry = os.path.join(self.project, ".claude", "ai-tools.json")
        self.write_registry(registry, {"mcp:notes": {"tier": 4, "owner": "dana"}})
        self.assertEqual(self.decision("mcp__notes__search"), "ask")
        self.write_registry(registry, {"mcp:mail": {"tier": 9, "owner": "dana"}})
        self.assertEqual(self.decision("mcp__mail__search_threads"), "ask")

    def test_a_broken_project_registry_makes_everything_tier_3(self) -> None:
        os.makedirs(os.path.join(self.project, ".claude"))
        with open(os.path.join(self.project, ".claude", "ai-tools.json"), "w") as f:
            f.write("{ not json")
        self.assertEqual(self.decision("mcp__notes__search"), "ask")
        self.assertEqual(self.decision("mcp__db__execute_sql"), "ask")

    def test_registry_import_failure_counts_as_tier_3(self) -> None:
        # A copy of the hook with no scripts/ folder next to it.
        hooks = os.path.join(self.tmp.name, "bare", ".claude", "hooks")
        os.makedirs(hooks)
        for name in ("enforce-laws.py", "hook_log.py", "ai_approvals.py"):
            shutil.copy(os.path.join(HOOKS_DIR, name), hooks)
        self.assertEqual(self.decision("mcp__notes__search", hook=os.path.join(hooks, "enforce-laws.py")), "ask")

    def test_names_that_dont_split_count_as_tier_3(self) -> None:
        for tool in ("mcp__notes", "mcp____search", "mcp__notes__"):
            self.assertEqual(self.decision(tool), "ask", tool)

    def test_post_tool_use_records_only_tier_3(self) -> None:
        for tool in ("mcp__notes__search", "mcp__mail__search_threads", "mcp__db__execute_sql"):
            self.ran(tool)
        self.assertFalse(os.path.exists(os.path.join(self.forge, "ai-approvals.jsonl")))
        self.ran("mcp__wiki__create_page")
        with open(os.path.join(self.forge, "ai-approvals.jsonl")) as f:
            self.assertEqual([json.loads(line)["tool"] for line in f], ["mcp__wiki__create_page"])

    def test_post_tool_use_is_silent_for_other_tools_and_bad_payloads(self) -> None:
        result = self.run_event("Bash", event="PostToolUse", tool_input={"command": "git push origin main"})
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
        result = self.run_event("mcp__wiki__create_page", event="PostToolUse", session=["not", "a", "string"])
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

    def test_asks_are_logged_with_their_check_ids(self) -> None:
        self.decision("mcp__db__execute_sql")
        self.decision("mcp__wiki__create_page")
        self.assertEqual(self.log_checks(), [("ask", "tier4-unapproved"), ("ask", "tier3-first-use")])

    def test_a_listed_mode_turns_the_mcp_ask_into_a_deny(self) -> None:
        patched = os.path.join(HOOKS_DIR, f"hook-patched-{os.getpid()}.py")
        with open(HOOK) as f:
            code = f.read().replace('ASK_DENIED_MODES: set[str] = set()', 'ASK_DENIED_MODES: set[str] = {"bypassPermissions"}')
        with open(patched, "w") as f:
            f.write(code)
        self.addCleanup(os.remove, patched)
        result = self.run_event("mcp__db__execute_sql", hook=patched, permission_mode="bypassPermissions")
        self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")


def load_hook():
    """The hook as a module, for unit tests of its helpers."""
    spec = importlib.util.spec_from_file_location("enforce_laws", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Fake secrets are assembled at run time, so no whole token sits in this
# file: the hook's own commit check and GitHub's push protection would
# otherwise block the commit that adds these tests (#119).
MIX = "a1B2c3D4e5F6g7H8i9J0"  # 20 mixed letters and digits


def fake_jwt(payload: dict) -> str:
    def part(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")
    return ".".join((part({"alg": "HS256", "typ": "JWT"}), part(payload), "s1G2n3A4t5U6r7E8x9Y0"))


def fake_secrets() -> dict[str, str]:
    m36 = (MIX * 2)[:36]
    return {
        "a private key": "-----BEGIN " + "RSA PRIVATE KEY-----\n" + "MIIE" + "a1B2" * 15 + "\n-----END RSA PRIVATE KEY-----",
        "an AWS access key": "AK" + "IA" + "Q3B7XN2M4P5R6S8T",
        "a GitHub token": "gh" + "p_" + m36,
        "a GitLab token": "gl" + "pat-" + MIX,
        "a Slack token": "xo" + "xb-" + "1234567890-" + MIX,
        "a Stripe live key": "sk" + "_live_" + MIX + "Zz",
        "an Anthropic key": "sk" + "-ant-" + "api03-" + MIX,
        "an OpenAI key": "sk" + "-proj-" + MIX + MIX,
        "a Google API key": "AI" + "za" + (MIX * 2)[:35],
        "a Supabase key": "sb" + "_secret_" + MIX + "xY",
        "a Netlify token": "nf" + "p_" + m36,
        "an npm token": "np" + "m_" + m36,
        "a Figma token": "fi" + "gd_" + MIX + MIX,
        "a JWT": fake_jwt({"role": "service_role"}),
        "a credential assignment": "STRIPE_SECRET" + "_KEY=" + "r9" + MIX,
    }


class SecretPatternTests(unittest.TestCase):
    """One shared find_secret for Law 14 and Law 39 (#119)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.hook = load_hook()

    def test_every_kind_is_caught(self) -> None:
        for kind, value in fake_secrets().items():
            with self.subTest(kind=kind):
                found = self.hook.find_secret(f"config = 1\nvalue: {value}\n")
                self.assertIsNotNone(found, kind)
                self.assertEqual(found[0], kind)

    def test_more_shapes_are_caught(self) -> None:
        for text in (
            "-----BEGIN " + "PRIVATE KEY-----\\n" + "MIIE" + "a1B2" * 15,  # a key in a .env value
            "-----BEGIN " + "OPENSSH PRIVATE KEY-----\n" + "b3Bl" * 12,
            "AS" + "IA" + "Q3B7XN2M4P5R6S8T",
            "gh" + "s_" + (MIX * 2)[:36],
            "github" + "_pat_" + (MIX * 4)[:60],
            "xo" + "xp-" + MIX,
            "xa" + "pp-" + MIX,
            "rk" + "_live_" + MIX,
            "sb" + "p_" + "0123456789abcdef" * 2 + "01234567",
            'client_secret: "' + MIX + '"',
            "DB_PASSWORD=" + MIX,
            '{"api_key": "' + MIX + '"}',
            'DB_PASSWORD="S3cure!' + 'Pass#2024xyz"',  # symbols in a quoted value
            "gh" + "u_" + (MIX * 2)[:36],
            "gh" + "r_" + (MIX * 2)[:36],
            "-----BEGIN " + "ENCRYPTED PRIVATE KEY-----\n" + "MIIE" + "a1B2" * 15,
            "-----BEGIN " + "PGP PRIVATE KEY BLOCK-----\n\n" + "lQdG" + "a1B2" * 15,
        ):
            with self.subTest(text=text[:12]):
                self.assertIsNotNone(self.hook.find_secret(text))

    def test_placeholders_references_and_public_values_pass(self) -> None:
        for text in (
            "gh" + "p_" + "x" * 36,
            "AK" + "IA" + "IOSFODNN7" + "EXAMPLE",
            "-----BEGIN " + "RSA PRIVATE KEY-----",
            "-----BEGIN " + "PRIVATE KEY-----\n-----END PRIVATE KEY-----",
            'api_key: "${{ secrets.API_KEY }}"',
            "SECRET_KEY=${SECRET_KEY}",
            "password=process.env.DATABASE_PASSWORD_VALUE",
            "token = import.meta.env.VITE_TOKEN_VALUE_X1",
            "client_secret=os.environ['CLIENT_SECRET']",
            "GITHUB_TOKEN=" + "gh" + "p_" + "x" * 36,
            "STRIPE_SECRET_KEY=" + "sk" + "_test_" + MIX,
            "PUBLISHABLE_TOKEN=" + "pk" + "_live_" + MIX,
            "supabase_token=" + "sb" + "_publishable_" + MIX,
            'commit_token = "' + "0123456789abcdef" * 2 + "01234567" + '"',
            'session_token: "123e4567-e89b-' + '12d3-a456-426614174000"',  # split: the old pattern misread UUIDs
            'integrity_token: "sha512-' + "a1B2" * 10 + '"',
            fake_jwt({"role": "anon", "iss": "supabase"}),
            "anon_token=" + fake_jwt({"role": "anon"}),
            'token_type: "refresh-token-name"',
            "page_token = 1",
            'API_TOKEN="${SECRET_VALUE_FROM_CI}"',
            "STRIPE_SECRET_KEY=" + "rk" + "_test_" + MIX,
            "xo" + "xb-" + "x" * 12 + "-" + "x" * 13 + "-" + "x" * 24,
            "sk" + "-ant-" + "api03-" + "x" * 40,
            "sk" + "-ant-" + "your-api-key-goes-here",
            # design tokens, files and model names under a token or secret name
            "token: color.primary.500",
            '<Badge token="semantic.success.bg2" />',
            "secretName: tls-secret-prod-2024",
            'tokenizer: "bert-base-uncased-v2"',
            'token_file = "credentials/token_v2.json"',
        ):
            with self.subTest(text=text[:16]):
                self.assertIsNone(self.hook.find_secret(text))

    def test_a_token_in_an_assignment_reports_its_own_kind(self) -> None:
        self.assertEqual(self.hook.find_secret("GITHUB_TOKEN=" + "gh" + "p_" + (MIX * 2)[:36])[0], "a GitHub token")

    def test_large_and_crafted_inputs_are_quick(self) -> None:
        for text in (  # about 1 MB each
            "lorem ipsum dolor sit amet 0123456789 token count = 3\n" * 20000,
            "eyJ-" * 250000,
            "token=" * 166666,
        ):
            start = time.monotonic()
            self.assertIsNone(self.hook.find_secret(text))
            self.assertLess(time.monotonic() - start, 1.0, text[:8])

    def test_added_lines_reads_only_what_a_diff_adds(self) -> None:
        diff = "\n".join((
            "diff --git a/old.txt b/new.txt", "similarity index 90%", "rename from old.txt", "rename to new.txt",
            "--- a/old.txt", "+++ b/new.txt", "@@ -1,3 +1,3 @@", " kept", "-gone", "++ starts with a plus",
            "\\ No newline at end of file", "diff --git a/img.png b/img.png", "Binary files a/img.png and b/img.png differ",
        ))
        self.assertEqual(self.hook.added_lines(diff), [("new.txt", "+ starts with a plus")])


class CommitSecretTests(HookRunner, unittest.TestCase):
    """The Law 14 commit check reads only the lines a commit adds (#119)."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.realpath(os.path.join(self.tmp.name, "home"))
        os.makedirs(os.path.join(self.home, ".design-forge"))
        self.project = os.path.realpath(os.path.join(self.tmp.name, "project"))
        make_repo(self.project, "feat/x")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def stage(self, name: str, text: str) -> None:
        with open(os.path.join(self.project, name), "w") as f:
            f.write(text)
        subprocess.run(["git", "add", name], cwd=self.project, check=True)

    def commit_directly(self, message: str) -> None:
        subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
                        "commit", "-q", "-m", message], cwd=self.project, check=True)

    def test_added_secrets_block_and_name_kind_and_file(self) -> None:
        secrets = fake_secrets()
        for kind in ("a GitLab token", "a Slack token"):  # missed before #119
            with self.subTest(kind=kind):
                self.stage("config.py", f"TOKEN_NAME = 'x'\nvalue = '{secrets[kind]}'\n")
                result = self.run_payload({"tool_name": "Bash", "tool_input": {"command": 'git commit -m "feat: x"'}})
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(kind, result.stderr)
                self.assertIn("config.py", result.stderr)
                self.assertNotIn(secrets[kind], result.stderr)

    def test_removing_a_secret_is_allowed(self) -> None:
        self.stage("config.py", f"value = '{fake_secrets()['a GitHub token']}'\n")
        self.commit_directly("chore: add")
        self.stage("config.py", "value = None\n")
        self.assertEqual(self.bash('git commit -m "fix: remove the leaked token"'), "allow")

    def test_a_key_body_added_under_a_committed_header_blocks(self) -> None:
        header, footer = "-----BEGIN " + "RSA PRIVATE KEY-----", "-----END RSA PRIVATE KEY-----"
        self.stage("key.pem", f"{header}\n{footer}\n")
        self.commit_directly("chore: add")
        self.stage("key.pem", f"{header}\n" + "MIIE" + "a1B2" * 15 + f"\n{footer}\n")
        self.assertEqual(self.bash('git commit -m "feat: x"'), "block")

    def test_color_or_an_external_diff_doesnt_hide_a_secret(self) -> None:
        subprocess.run(["git", "config", "color.ui", "always"], cwd=self.project, check=True)
        subprocess.run(["git", "config", "diff.external", "false"], cwd=self.project, check=True)
        self.stage("config.py", f"value = '{fake_secrets()['a GitLab token']}'\n")
        self.assertEqual(self.bash('git commit -m "feat: x"'), "block")

    def test_a_staged_env_file_still_blocks_and_removing_one_doesnt(self) -> None:
        self.stage(".env", "DEBUG=1\n")
        self.assertEqual(self.bash('git add .env && git commit -m "feat: x"'), "block")
        self.commit_directly("chore: add")
        subprocess.run(["git", "rm", "-q", "--cached", ".env"], cwd=self.project, check=True)
        self.assertEqual(self.bash('git status .env && git commit -m "fix: x"'), "allow")


class CommitContentsTests(HookRunner, unittest.TestCase):
    """The check reads what the commit will contain: what `git add`, `-a` or
    commit paths add in the same call, not only what was staged before (#187)."""

    setUp, tearDown = CommitSecretTests.setUp, CommitSecretTests.tearDown
    stage, commit_directly = CommitSecretTests.stage, CommitSecretTests.commit_directly

    def write(self, name: str, text: str | bytes) -> None:
        path = os.path.join(self.project, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb" if isinstance(text, bytes) else "w") as f:
            f.write(text)

    def tracked(self, name: str, text: str = "value = None\n") -> None:
        self.stage(name, text)
        self.commit_directly("chore: add")

    def secret(self, kind: str = "a GitLab token") -> str:
        return f"value = '{fake_secrets()[kind]}'\n"

    def test_add_in_the_same_call_blocks_and_names_kind_and_file(self) -> None:
        self.write("config.py", self.secret())
        result = self.run_payload({"tool_name": "Bash", "tool_input": {
            "command": 'git add config.py && git commit -m "feat: x"'}})
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("a GitLab token", result.stderr)
        self.assertIn("config.py", result.stderr)
        self.assertNotIn(fake_secrets()["a GitLab token"], result.stderr)

    def test_add_of_a_tracked_file_in_the_same_call_blocks(self) -> None:
        self.tracked("config.py")
        self.write("config.py", self.secret())
        self.assertEqual(self.bash('git add config.py && git commit -m "feat: x"'), "block")

    def test_add_all_blocks_on_untracked_files_but_not_ignored_ones(self) -> None:
        self.tracked(".gitignore", "*.log\n")
        self.write("debug.log", self.secret())
        self.assertEqual(self.bash('git add -A && git commit -m "feat: x"'), "allow")
        self.write("notes/new.txt", self.secret("a Slack token"))
        self.assertEqual(self.bash('git add . && git commit -m "feat: x"'), "block")

    def test_add_runs_in_its_own_folder(self) -> None:
        self.write("sub/f.txt", self.secret())
        self.assertEqual(self.bash('cd sub && git add f.txt && cd .. && git commit -m "feat: x"'), "block")

    def test_commit_all_reads_unstaged_changes(self) -> None:
        self.tracked("config.py")
        self.write("config.py", self.secret())
        for command in ('git commit -am "feat: x"', 'git commit --all -m "feat: x"'):
            with self.subTest(command=command):
                self.assertEqual(self.bash(command), "block")

    def test_commit_paths_read_their_working_tree(self) -> None:
        self.tracked("config.py")
        self.write("config.py", self.secret())
        for command in ('git commit config.py -m "feat: x"', 'git commit -m "feat: x" -- config.py',
                        'git commit -i config.py -m "feat: x"'):
            with self.subTest(command=command):
                self.assertEqual(self.bash(command), "block")

    def test_unrelated_unstaged_changes_dont_block(self) -> None:
        self.tracked("b.txt")
        self.write("b.txt", self.secret())
        self.stage("a.txt", "fine\n")
        self.assertEqual(self.bash('git commit -m "feat: x"'), "allow")
        self.write("a.txt", "still fine\n")
        self.assertEqual(self.bash('git add a.txt && git commit -m "feat: x"'), "allow")
        self.assertEqual(self.bash('git commit a.txt -m "feat: x"'), "allow")

    def test_add_after_the_commit_doesnt_count(self) -> None:
        self.write("config.py", self.secret())
        self.assertEqual(self.bash('git commit -m "feat: x" && git add config.py'), "allow")

    def test_env_files_the_commit_adds_block_and_envrc_doesnt(self) -> None:
        self.write(".envrc", "use nix\n")
        self.assertEqual(self.bash('git add -A && git commit -m "feat: x"'), "allow")
        self.write(".env.local", "DEBUG=1\n")
        self.assertEqual(self.bash('git add -A && git commit -m "feat: x"'), "block")

    def test_a_staged_env_file_blocks_without_naming_it(self) -> None:
        self.stage(".env", "DEBUG=1\n")
        self.assertEqual(self.bash('git commit -m "feat: x"'), "block")

    def test_removing_a_secret_with_commit_all_is_allowed(self) -> None:
        self.tracked("config.py", self.secret())
        self.write("config.py", "value = None\n")
        self.assertEqual(self.bash('git commit -am "fix: remove the leaked token"'), "allow")

    def test_binary_and_unparsable_commands_dont_crash(self) -> None:
        self.write("img.bin", b"\x00\x01" + fake_secrets()["a GitLab token"].encode())
        self.assertEqual(self.bash('git add img.bin && git commit -m "feat: x"'), "allow")
        self.assertEqual(self.bash('git add -p && git commit -m "feat: x"'), "allow")
        self.assertEqual(self.bash('git add "unclosed && git commit -m "feat: x"'), "allow")


if __name__ == "__main__":
    unittest.main()
