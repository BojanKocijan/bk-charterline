#!/usr/bin/env python3
"""Tests for .claude/hooks/session_start.py (#270): the SessionStart hook runs
the session-start checks, reads only, stays fast without a network, and gives
Claude one block it never has to cut. The network checks and their tests
come in part 1b."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(REPO, ".claude", "hooks", "session_start.py")
REAL_GIT = shutil.which("git") or "git"

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
        for d in (self.rules, self.tmpdir, self.repo):
            os.makedirs(d)
        git(self.repo, "init", "-q", "-b", "main")
        self.write(self.repo, "README.md", "demo\n")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "-q", "-m", "chore: start")
        self.env = {**os.environ, "HOME": self.home, "TMPDIR": self.tmpdir}
        for key in ("CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR"):
            self.env.pop(key, None)
        self.session = 0

    def tearDown(self) -> None:
        self.tmp.cleanup()

    # helpers
    def write(self, folder: str, name: str, text: str | bytes) -> str:
        path = os.path.join(folder, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb" if isinstance(text, bytes) else "w") as f:
            f.write(text)
        return path

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

    def test_full_confirmation(self) -> None:
        self.projects()
        self.write(self.repo, "PROJECT_KNOWLEDGE.md", KNOWLEDGE)
        self.write(self.repo, "CLAUDE.md", "@./PROJECT_KNOWLEDGE.md\n")
        self.write(self.rules, "dashboard/index.html", "<p>dashboard</p>")
        text = self.context()
        for line in ("Rules loaded: BK CHARTERLINE v", "Project: demo-app", "Persona: Frontend",
                     "GitHub: unknown", "Knowledge: PROJECT_KNOWLEDGE.md — A demo dashboard for example data",
                     "Feature: F-1 · Demo flow · in-progress", "Dashboard: ~/.bk-charterline/dashboard/index.html",
                     "Ready.", "Reply language: english-only", "Preview port: 5174"):
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


if __name__ == "__main__":
    unittest.main()
