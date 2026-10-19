#!/usr/bin/env python3
"""Tests for .claude/hooks/session_start.py (#270): the SessionStart hook runs
the session-start checks, reads only, stays fast without a network, and gives
Claude one block it never has to cut."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(REPO, ".claude", "hooks", "session_start.py")
REAL_GIT = shutil.which("git") or "git"

GH_STUB = """#!/bin/sh
case "$GH_STUB_MODE" in hang) sleep 10;; fail) exit 1;; esac
case "$1 $2" in
  "api user") echo alice-example;;
  "pr list") cat "$GH_STUB_PRS";;
esac
"""
GIT_STUB = """#!/bin/sh
if [ -n "$GIT_STUB_HANG" ] && [ "$3" = "ls-remote" ]; then sleep 10; fi
exec "{git}" "$@"
"""

KNOWLEDGE = """# Project knowledge

## 1. Project purpose
A demo dashboard for example data

## 11. Active feature
| ID | Title | Status | Branch | JTBD |
|---|---|---|---|---|
| F-1 | Demo flow | in-progress | feat/demo | see the demo |

### Paused features
"""


def git(cwd: str, *args: str) -> str:
    return subprocess.run([REAL_GIT, *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env={**os.environ, "GIT_AUTHOR_NAME": "Alice Chen", "GIT_AUTHOR_EMAIL": "alice@example.com",
                               "GIT_COMMITTER_NAME": "Alice Chen", "GIT_COMMITTER_EMAIL": "alice@example.com"}).stdout


class SessionStartTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.home = os.path.join(root, "home")
        self.rules = os.path.join(self.home, ".bk-charterline")
        self.tmpdir = os.path.join(root, "tmp")
        self.repo = os.path.join(root, "demo-app")
        self.bin = os.path.join(root, "bin")
        for d in (self.rules, self.tmpdir, self.repo, self.bin):
            os.makedirs(d)
        self.stub("gh", GH_STUB)
        self.stub("git", GIT_STUB.format(git=REAL_GIT))
        self.prs = os.path.join(root, "prs.json")
        self.write_prs([{"number": 7, "title": "feat: add the demo chart"}])
        git(self.repo, "init", "-q", "-b", "main")
        self.write(self.repo, "README.md", "demo\n")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "-q", "-m", "chore: start")
        self.env = {**os.environ, "HOME": self.home, "TMPDIR": self.tmpdir, "GH_STUB_PRS": self.prs,
                    "PATH": self.bin + os.pathsep + os.environ.get("PATH", "")}
        for key in ("CLAUDE_CODE_REMOTE", "CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR", "GH_STUB_MODE", "GIT_STUB_HANG"):
            self.env.pop(key, None)
        self.session = 0

    def tearDown(self) -> None:
        self.tmp.cleanup()

    # helpers
    def stub(self, name: str, body: str) -> None:
        path = os.path.join(self.bin, name)
        with open(path, "w") as f:
            f.write(body)
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)

    def write(self, folder: str, name: str, text: str | bytes) -> str:
        path = os.path.join(folder, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb" if isinstance(text, bytes) else "w") as f:
            f.write(text)
        return path

    def write_prs(self, prs: list[dict]) -> None:
        with open(self.prs, "w") as f:
            json.dump(prs, f)

    def projects(self, language: str | None = "english-only", port: int | None = 5174, name: str = "demo-app") -> None:
        text = "settings:\n" + (f"  language: {language}\n" if language else "  # language: english-only\n")
        text += "\nprojects:\n"
        if port:
            text += f"  - name: {name}\n    repo: alice/{name}\n    port: {port}\n"
        self.write(self.rules, "projects.yaml", text)

    def run_hook(self, source: str = "startup", session: str | None = None, stdin: str | None = None,
                 cwd: str | None = None) -> tuple[subprocess.CompletedProcess, float]:
        if session is None:
            self.session += 1
            session = f"s{self.session}"
        event = json.dumps({"session_id": session, "hook_event_name": "SessionStart", "source": source,
                            "cwd": cwd or self.repo})
        started = time.monotonic()
        done = subprocess.run([sys.executable, HOOK], input=event if stdin is None else stdin, capture_output=True,
                              text=True, env=self.env, cwd=cwd or self.repo, timeout=30)
        return done, time.monotonic() - started

    def context(self, **kwargs) -> str:
        done, _ = self.run_hook(**kwargs)
        self.assertEqual(done.returncode, 0, done.stderr)
        out = json.loads(done.stdout)["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "SessionStart")
        return out["additionalContext"]

    def snapshot(self, folder: str) -> tuple:
        files = {}
        for base, _dirs, names in os.walk(folder):
            for name in names:
                path = os.path.join(base, name)
                with open(path, "rb") as f:
                    files[os.path.relpath(path, folder)] = hashlib.sha256(f.read()).hexdigest()
        return (files, git(folder, "status", "--porcelain"), git(folder, "for-each-ref"))

    def installed_clone(self, tag: str) -> None:
        """An installed rules clone whose origin (a local bare repo) has a release tag."""
        origin = os.path.join(self.tmp.name, "origin.git")
        git(self.tmp.name, "init", "-q", "--bare", origin)
        self.write(self.rules, "CLAUDE_LAWS.md", "# Laws\n\n**Version:** 3.6.1\n")
        git(self.rules, "init", "-q", "-b", "main")
        git(self.rules, "add", "CLAUDE_LAWS.md")
        git(self.rules, "commit", "-q", "-m", "chore: laws")
        git(self.rules, "remote", "add", "origin", origin)
        git(self.rules, "tag", tag)
        git(self.rules, "push", "-q", "origin", "main", "--tags")

    # the full block
    def test_full_confirmation(self) -> None:
        self.projects()
        self.write(self.repo, "PROJECT_KNOWLEDGE.md", KNOWLEDGE)
        self.write(self.repo, "CLAUDE.md", "@./PROJECT_KNOWLEDGE.md\n")
        self.write(self.rules, "dashboard/index.html", "<p>dashboard</p>")
        text = self.context()
        for line in ("Rules loaded: BK CHARTERLINE v", "Project: demo-app", "Persona: Frontend",
                     "GitHub: alice-example", "Knowledge: PROJECT_KNOWLEDGE.md — A demo dashboard for example data",
                     "Feature: F-1 · Demo flow · in-progress", "Dashboard: ~/.bk-charterline/dashboard/index.html",
                     "Ready.", "#7 feat: add the demo chart", "Reply language: english-only", "Preview port: 5174"):
            self.assertIn(line, text)
        self.assertIn("make no tool calls", text)
        self.assertNotIn("Register demo-app", text)
        self.assertNotIn("Language not set", text)

    def test_rules_version_comes_from_the_laws(self) -> None:
        with open(os.path.join(REPO, "CLAUDE_LAWS.md")) as f:
            version = next(line for line in f if line.startswith("**Version:**")).split()[-1]
        self.assertIn(f"Rules loaded: BK CHARTERLINE v{version}", self.context())

    # when it stays quiet
    def test_quiet_on_resume_compact_and_fork(self) -> None:
        for source in ("resume", "compact", "fork"):
            done, _ = self.run_hook(source=source)
            self.assertEqual((done.returncode, done.stdout), (0, ""), source)

    def test_clear_runs_like_startup_also_in_the_same_session(self) -> None:
        self.assertIn("Ready.", self.context(session="same"))
        self.assertIn("Ready.", self.context(source="clear", session="same"))

    def test_runs_once_per_session(self) -> None:
        self.assertIn("Ready.", self.context(session="same"))
        done, _ = self.run_hook(session="same")
        self.assertEqual((done.returncode, done.stdout), (0, ""))
        self.assertIn("Ready.", self.context(session="other"))

    def test_marker_stays_out_of_the_project(self) -> None:
        self.context(session="abc")
        self.assertTrue(any("abc" in name for name in os.listdir(self.tmpdir)))

    def test_malformed_input_is_silent(self) -> None:
        for stdin in ("not json", "", "[]"):
            done, _ = self.run_hook(stdin=stdin)
            self.assertEqual((done.returncode, done.stdout), (0, ""), stdin)

    # read-only
    def test_changes_nothing_in_the_project(self) -> None:
        self.projects(port=None)
        before = self.snapshot(self.repo)
        text = self.context()
        self.assertIn("Register demo-app", text)  # it reports the step and doesn't take it
        self.assertEqual(before, self.snapshot(self.repo))
        self.assertFalse(os.path.exists(os.path.join(self.repo, "CLAUDE.md")))
        with open(os.path.join(self.rules, "projects.yaml")) as f:
            self.assertNotIn("demo-app", f.read())

    # the network
    def test_update_available(self) -> None:
        self.installed_clone("v9.9.9")
        self.assertIn("BK Charterline update available: v3.6.1 → v9.9.9", self.context())

    def test_no_update_line_when_current(self) -> None:
        self.installed_clone("v3.6.1")
        self.assertNotIn("update available", self.context())

    def test_hanging_network_stays_under_five_seconds(self) -> None:
        self.installed_clone("v9.9.9")
        self.env.update(GH_STUB_MODE="hang", GIT_STUB_HANG="1")
        done, elapsed = self.run_hook()
        self.assertLess(elapsed, 5)
        text = json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Ready.", text)
        self.assertNotIn("update available", text)
        self.assertNotIn("Open PRs", text)
        self.assertIn("GitHub: unknown", text)  # slow, not logged out

    def test_github_in_a_cloud_session(self) -> None:
        self.env.update(GH_STUB_MODE="fail", CLAUDE_CODE_REMOTE="true")
        text = self.context()
        self.assertIn("GitHub: via connector", text)
        self.assertNotIn("Open PRs", text)

    def test_github_unauthenticated_locally(self) -> None:
        self.env["GH_STUB_MODE"] = "fail"
        self.assertIn("GitHub: unauthenticated", self.context())

    def test_long_pr_list_is_never_cut(self) -> None:
        self.write_prs([{"number": n, "title": "x" * 200} for n in range(1, 11)])
        self.write(self.repo, "PROJECT_KNOWLEDGE.md", KNOWLEDGE)
        self.write(self.repo, "SESSION_NOTE.md", "note\n")
        text = self.context()
        self.assertLess(len(text), 2000)
        self.assertNotIn("x" * 61, text)
        self.assertIn("#1 ", text)
        self.assertTrue(text.rstrip().endswith("(Laws 5, 9, 25)."))  # the last step survives

    # missing or odd files
    def test_language_not_set(self) -> None:
        self.projects(language=None)
        text = self.context()
        self.assertIn("Language not set", text)
        self.assertIn("Law 1", text)

    def test_projects_yaml_missing(self) -> None:
        text = self.context()
        self.assertIn("Language not set", text)
        self.assertIn("Register demo-app in projects.yaml on port 5173", text)

    def test_projects_yaml_broken(self) -> None:
        self.write(self.rules, "projects.yaml", b"\xff\xfe broken")
        text = self.context()
        self.assertIn("projects.yaml can't be read", text)
        self.assertIn("Law 1 question", text)
        self.assertNotIn("Register demo-app", text)

    def test_projects_yaml_empty_is_not_broken(self) -> None:
        self.write(self.rules, "projects.yaml", "# nothing yet\n")
        text = self.context()
        self.assertNotIn("can't be read", text)
        self.assertIn("Language not set", text)
        self.assertIn("Register demo-app in projects.yaml on port 5173", text)

    def test_entries_in_any_key_order(self) -> None:
        self.write(self.rules, "projects.yaml", "settings:\n  language: any\nprojects:\n"
                   "  - name: other\n    port: 5173\n  - repo: alice/demo-app\n    name: demo-app\n    port: 5180\n")
        self.assertIn("Preview port: 5180", self.context())

    def test_entry_without_a_port(self) -> None:
        self.write(self.rules, "projects.yaml", "projects:\n  - name: demo-app\n    repo: alice/demo-app\n")
        text = self.context()
        self.assertIn("Add port: 5173 to demo-app's entry", text)
        self.assertNotIn("Register demo-app", text)

    def test_next_free_port(self) -> None:
        self.projects(port=5180, name="other-app")
        self.assertIn("Register demo-app in projects.yaml on port 5181", self.context())

    def test_no_project_knowledge(self) -> None:
        text = self.context()
        self.assertNotIn("Knowledge:", text)
        self.assertIn("Create PROJECT_KNOWLEDGE.md from its template and a one-line local CLAUDE.md", text)  # for when code work starts

    def test_existing_claude_md_is_not_created_again(self) -> None:
        self.write(self.repo, "CLAUDE.md", "@./PROJECT_KNOWLEDGE.md\n")
        text = self.context()
        self.assertIn("Create PROJECT_KNOWLEDGE.md from its template (Law 11).", text)
        self.assertNotIn("local CLAUDE.md", text)

    def test_placeholder_and_comments_are_not_the_purpose(self) -> None:
        self.write(self.repo, "PROJECT_KNOWLEDGE.md", "## 1. Project purpose\n<!--\nFill this in\n-->\n"
                   "<one-line description>\n")
        self.assertNotIn("Knowledge:", self.context())

    def test_handed_off_feature_is_left_out(self) -> None:
        self.write(self.repo, "PROJECT_KNOWLEDGE.md", KNOWLEDGE.replace("in-progress", "handed-off"))
        self.assertNotIn("Feature:", self.context())

    def test_session_note(self) -> None:
        self.write(self.repo, "SESSION_NOTE.md", "note\n")
        self.assertIn("SESSION_NOTE.md exists", self.context())

    def test_not_a_git_repo(self) -> None:
        plain = os.path.join(self.tmp.name, "plain")
        os.makedirs(plain)
        text = self.context(cwd=plain)
        self.assertIn("Project: not a git repo", text)
        self.assertNotIn("Pull the default branch", text)

    def test_worktree_uses_the_main_folder_name(self) -> None:
        tree = os.path.join(self.tmp.name, "demo-app-tree")
        git(self.repo, "worktree", "add", "-q", "-b", "feat/x", tree)
        self.assertIn("Project: demo-app", self.context(cwd=tree))


class RegistrationTests(unittest.TestCase):
    """The three registrations (#270, PR 2): this repo's settings, install.sh and the plugin."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        os.makedirs(self.home)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def entry(self, path: str) -> dict:
        with open(os.path.join(REPO, path)) as f:
            [entry] = json.load(f)["hooks"]["SessionStart"]
        self.assertEqual(entry["matcher"], "startup|clear")
        self.assertEqual(entry["hooks"][0]["timeout"], 10)
        return entry["hooks"][0]

    def run_command(self, command: str, **env: str) -> subprocess.CompletedProcess:
        event = json.dumps({"session_id": f"reg-{len(env)}-{os.getpid()}", "source": "startup", "cwd": REPO})
        return subprocess.run(["sh", "-c", command], input=event, capture_output=True, text=True, timeout=30,
                              env={**os.environ, "HOME": self.home, "TMPDIR": self.tmp.name, **env})

    def test_repo_settings_fall_back_to_the_repo_copy(self) -> None:
        done = self.run_command(self.entry(".claude/settings.json")["command"], CLAUDE_PROJECT_DIR=REPO)
        self.assertEqual(done.returncode, 0)
        self.assertIn("Ready.", json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"])

    def test_repo_settings_stay_quiet_without_any_copy(self) -> None:
        done = self.run_command(self.entry(".claude/settings.json")["command"], CLAUDE_PROJECT_DIR=self.tmp.name)
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))

    def test_plugin_hook_runs_from_the_plugin_root(self) -> None:
        done = self.run_command(self.entry("hooks/hooks.json")["command"], CLAUDE_PLUGIN_ROOT=REPO)
        self.assertEqual(done.returncode, 0)
        self.assertIn("Ready.", json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"])

    def test_installed_command_stays_quiet_when_the_script_is_missing(self) -> None:
        with open(os.path.join(REPO, "install.sh")) as f:
            command = re.search(r'^START_COMMAND="(.*)"$', f.read(), re.M).group(1).replace('\\"', '"')
        done = self.run_command(command.replace("${LOCAL_DIR}", "$HOME/.bk-charterline"))
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))


if __name__ == "__main__":
    unittest.main()
