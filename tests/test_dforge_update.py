"""Tests for the `dforge-update` shell function in install.sh (#116).

Each test builds a throwaway "origin" repo with commits and release tags,
clones it to <temp HOME>/.design-forge, and runs the function, extracted
from install.sh between its `design-forge:fn` markers, under bash and
(when installed) zsh. The fixture's install.sh is a stub that leaves a
marker file, so a run that applies an update is visible. The hook gate
is driven through a real pseudo-terminal, never a test-only flag.

Run: python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import os
import pty
import select
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALL = os.path.join(REPO, "install.sh")
SHELLS = [s for s in ("bash", "zsh") if shutil.which(s)]


def function_source() -> str:
    with open(INSTALL) as f:
        text = f.read()
    start = text.index("# design-forge:fn:begin\n")
    end = text.index("# design-forge:fn:end\n")
    return text[start:end]


class Fixture:
    """An origin repo, its bare copy and a clone at HOME/.design-forge."""

    def __init__(self, tmp: str) -> None:
        self.tmp = tmp
        self.home = os.path.join(tmp, "home")
        self.work = os.path.join(tmp, "work")
        self.origin = os.path.join(tmp, "origin.git")
        self.clone = os.path.join(self.home, ".design-forge")
        os.makedirs(self.home)
        self.fn = os.path.join(tmp, "dforge-update.sh")
        with open(self.fn, "w") as f:
            f.write(function_source())
        self.env = {
            "HOME": self.home, "PATH": os.environ["PATH"], "LANG": "C", "GIT_PAGER": "cat",
            "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
            "GIT_CONFIG_NOSYSTEM": "1",
        }
        self.git("init", "-q", "-b", "main", self.work, cwd=tmp)
        self.write(".gitignore", "projects.yaml\n")
        self.write("install.sh", 'echo ran > "$HOME/install-ran"\n')
        self.write(".claude/hooks/enforce-laws.py", "# hook v1\n")

    def git(self, *args: str, cwd: str | None = None) -> str:
        return subprocess.run(["git", *args], cwd=cwd or self.work, env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def write(self, rel: str, text: str) -> None:
        path = os.path.join(self.work, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)

    def release(self, version: str, tag: str | None = "default", hook: str | None = None) -> str:
        """Commit a version (optionally a hook change), tag it, publish it."""
        self.write("CLAUDE_LAWS.md", f"# Laws\n\n**Version:** {version}\n")
        if hook is not None:
            self.write(".claude/hooks/enforce-laws.py", hook)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", f"release {version}")
        if tag:
            self.git("tag", "-a", f"v{version}" if tag == "default" else tag, "-m", version)
        self.publish()
        return self.git("rev-parse", "HEAD")

    def publish(self) -> None:
        if not os.path.isdir(self.origin):
            self.git("clone", "-q", "--bare", self.work, self.origin, cwd=self.tmp)
        else:
            self.git("push", "-q", "--tags", self.origin, "main")

    def make_clone(self, at: str | None = None) -> None:
        self.git("clone", "-q", self.origin, self.clone, cwd=self.tmp)
        if at:
            self.git("checkout", "-q", "--detach", at, cwd=self.clone)

    def head(self) -> str:
        return self.git("rev-parse", "HEAD", cwd=self.clone)

    def branch(self) -> str:
        return subprocess.run(["git", "symbolic-ref", "-q", "--short", "HEAD"], cwd=self.clone,
                              capture_output=True, text=True).stdout.strip()

    def installed(self) -> bool:
        path = os.path.join(self.home, "install-ran")
        found = os.path.exists(path)
        if found:
            os.remove(path)
        return found

    def command(self, shell: str, *args: str) -> list[str]:
        return [shell, "-c", f'. "{self.fn}"; dforge-update "$@"', "dforge-update", *args]

    def run(self, shell: str, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(self.command(shell, *args), env=self.env, cwd=self.home,
                              capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)

    def run_tty(self, shell: str, answer: str, *args: str, at_prompt=None) -> tuple[int, str]:
        """Run with stdin and stdout on a pseudo-terminal and type `answer`.
        `at_prompt` runs once the y/N prompt shows, before the answer."""
        master, slave = pty.openpty()
        proc = subprocess.Popen(self.command(shell, *args), env=self.env, cwd=self.home,
                                stdin=slave, stdout=slave, stderr=slave)
        os.close(slave)
        out = b""
        if at_prompt is None:
            os.write(master, (answer + "\n").encode())
        else:
            while b"[y/N]" not in out:
                ready, _, _ = select.select([master], [], [], 30)
                if not ready:
                    break
                try:
                    out += os.read(master, 4096)
                except OSError:
                    break
            at_prompt()
            os.write(master, (answer + "\n").encode())
        while True:
            ready, _, _ = select.select([master], [], [], 30)
            if not ready:
                proc.kill()
                break
            try:
                chunk = os.read(master, 4096)
            except OSError:
                break
            if not chunk:
                break
            out += chunk
        os.close(master)
        return proc.wait(timeout=30), out.decode(errors="replace")


@unittest.skipUnless(SHELLS, "needs bash or zsh")
class DforgeUpdateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def fixture(self) -> Fixture:
        sub = tempfile.mkdtemp(dir=self._tmp.name)
        return Fixture(os.path.realpath(sub))

    def each_shell(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                yield shell, self.fixture()

    def test_from_main_moves_to_the_newest_tag(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0")
            fx.make_clone()
            newest = fx.release("2.1.0")
            result = fx.run(shell)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((fx.head(), fx.branch()), (newest, ""))
            self.assertIn("ready (DESIGN_FORGE v2.1.0, tag v2.1.0)", result.stdout)
            self.assertTrue(fx.installed())

    def test_from_an_older_tag_moves_to_the_newest(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0")
            fx.make_clone(at="v2.0.0")
            newest = fx.release("2.1.0")
            self.assertEqual(fx.run(shell).returncode, 0)
            self.assertEqual(fx.head(), newest)

    def test_main_flag_follows_main_from_a_tag(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0")
            fx.make_clone(at="v2.0.0")
            tip = fx.release("2.1.0-dev", tag=None)
            result = fx.run(shell, "--main")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((fx.head(), fx.branch()), (tip, "main"))
            self.assertIn(", main).", result.stdout)

    def test_already_on_the_newest_tag(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0")
            fx.make_clone(at="v2.0.0")
            before = fx.head()
            result = fx.run(shell)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("already on v2.0.0", result.stdout)
            self.assertEqual(fx.head(), before)
            self.assertTrue(fx.installed())

    def test_no_tags_follows_main_with_a_warning(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0", tag=None)
            fx.make_clone()
            tip = fx.release("2.1.0", tag=None)
            result = fx.run(shell)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("no release tags yet", result.stderr)
            self.assertEqual((fx.head(), fx.branch()), (tip, "main"))

    def test_never_downgrades_a_clone_ahead_of_the_last_release(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0")
            fx.release("2.1.0", tag=None)
            fx.make_clone()
            before = fx.head()
            result = fx.run(shell)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("ahead of the latest release, v2.0.0 (on v2.1.0)", result.stdout)
            self.assertEqual((fx.head(), fx.branch()), (before, "main"))
            self.assertFalse(fx.installed())

    def test_version_order_and_tag_shape(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.9.0")
            fx.make_clone(at="v2.9.0")
            ten = fx.release("2.10.0")
            fx.release("2.11.0-rc1", tag="v2.11.0-rc1")
            fx.release("3.0.0", tag="vfoo")
            self.assertEqual(fx.run(shell).returncode, 0)
            self.assertEqual(fx.head(), ten)

    def test_hook_change_without_a_terminal_applies_nothing(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0")
            fx.make_clone(at="v2.0.0")
            before = fx.head()
            fx.release("2.1.0", hook="# hook v2\n")
            result = fx.run(shell)
            self.assertEqual(result.returncode, 1)
            self.assertIn("+# hook v2", result.stdout)
            self.assertIn("Nothing was applied. Run dforge-update in your own terminal", result.stderr)
            self.assertEqual(fx.head(), before)
            self.assertFalse(fx.installed())

    def test_hook_change_in_a_terminal_asks(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0")
            fx.make_clone(at="v2.0.0")
            before = fx.head()
            newest = fx.release("2.1.0", hook="# hook v2\n")
            code, out = fx.run_tty(shell, "n")
            self.assertEqual(code, 1, out)
            self.assertIn("Apply this hook change? [y/N]", out)
            self.assertEqual(fx.head(), before)
            code, out = fx.run_tty(shell, "y")
            self.assertEqual(code, 0, out)
            self.assertEqual(fx.head(), newest)
            self.assertTrue(fx.installed())

    def register_hook(self, fx: Fixture) -> None:
        os.makedirs(os.path.join(fx.home, ".claude"), exist_ok=True)
        with open(os.path.join(fx.home, ".claude", "settings.json"), "w") as f:
            f.write('{"hooks": {"PreToolUse": [{"hooks": [{"command": "python3 ~/.design-forge/.claude/hooks/enforce-laws.py"}]}]}}')

    def test_without_a_terminal_names_the_commit_to_approve(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0")
            fx.make_clone(at="v2.0.0")
            newest = fx.release("2.1.0", hook="# hook v2\n")
            result = fx.run(shell)
            self.assertEqual(result.returncode, 1)
            self.assertIn(f"dforge-update --approve {newest}", result.stderr)

    def test_approve_applies_exactly_that_commit(self) -> None:
        for shell, fx in self.each_shell():
            self.register_hook(fx)
            fx.release("2.0.0")
            fx.make_clone(at="v2.0.0")
            newest = fx.release("2.1.0", hook="# hook v2\n")
            result = fx.run(shell, "--approve", newest[:12])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("+# hook v2", result.stdout)
            self.assertIn("applying the hook change you approved", result.stdout)
            self.assertEqual(fx.head(), newest)
            self.assertTrue(fx.installed())

    def test_approve_refuses_a_stale_or_short_commit(self) -> None:
        for shell, fx in self.each_shell():
            self.register_hook(fx)
            fx.release("2.0.0")
            fx.make_clone(at="v2.0.0")
            before = fx.head()
            reviewed = fx.release("2.1.0", hook="# hook v2\n")
            newest = fx.release("2.2.0", hook="# hook v3 unreviewed\n")
            for commit in (reviewed, newest[:6], "0000000000"):
                result = fx.run(shell, "--approve", commit)
                self.assertEqual(result.returncode, 1, commit)
                self.assertIn("isn't the update on offer", result.stderr)
                self.assertEqual(fx.head(), before)
                self.assertFalse(fx.installed())

    def test_approve_needs_the_hook_registered(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0")
            fx.make_clone(at="v2.0.0")
            before = fx.head()
            newest = fx.release("2.1.0", hook="# hook v2\n")
            result = fx.run(shell, "--approve", newest)
            self.assertEqual(result.returncode, 1)
            self.assertIn("--approve needs the Law 32 hook", result.stderr)
            self.assertEqual(fx.head(), before)
            self.assertFalse(fx.installed())

    def test_approve_without_a_commit_is_a_usage_error(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0")
            fx.make_clone(at="v2.0.0")
            result = fx.run(shell, "--approve")
            self.assertEqual(result.returncode, 2)
            self.assertIn("usage: dforge-update", result.stderr)

    def test_the_terminal_prompt_shows_the_diff_without_a_pager(self) -> None:
        for shell, fx in self.each_shell():
            marker = os.path.join(fx.home, "pager-ran")
            fx.env["GIT_PAGER"] = f'touch "{marker}"; cat'
            fx.release("2.0.0")
            fx.make_clone(at="v2.0.0")
            fx.release("2.1.0", hook="# hook v2\n")
            code, out = fx.run_tty(shell, "n")
            self.assertEqual(code, 1, out)
            self.assertIn("+# hook v2", out)
            self.assertFalse(os.path.exists(marker), "the diff went through a pager")

    def test_other_hook_paths_count(self) -> None:
        for path in ("scripts/ai_tools.py", "install.sh", ".claude/settings.json"):
            for shell, fx in self.each_shell():
                fx.release("2.0.0")
                fx.make_clone(at="v2.0.0")
                fx.write(path, "# changed\n")
                fx.release("2.1.0")
                self.assertEqual(fx.run(shell).returncode, 1, path)

    def test_main_flag_is_gated_too(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0")
            fx.make_clone(at="v2.0.0")
            before = fx.head()
            fx.release("2.1.0", tag=None, hook="# hook v2\n")
            self.assertEqual(fx.run(shell, "--main").returncode, 1)
            self.assertEqual(fx.head(), before)

    def test_applies_the_reviewed_commit_when_main_moves_during_the_prompt(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0")
            fx.make_clone(at="v2.0.0")
            reviewed = fx.release("2.1.0", tag=None, hook="# hook v2\n")

            def main_moves() -> None:
                fx.release("2.2.0", tag=None, hook="# hook v3 unreviewed\n")
                fx.git("fetch", "-q", "origin", cwd=fx.clone)

            code, out = fx.run_tty(shell, "y", "--main", at_prompt=main_moves)
            self.assertEqual(code, 0, out)
            self.assertEqual(fx.head(), reviewed)

    def test_applies_the_reviewed_commit_when_the_tag_moves_during_the_prompt(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0")
            fx.make_clone(at="v2.0.0")
            reviewed = fx.release("2.1.0", hook="# hook v2\n")

            def tag_moves() -> None:
                fx.release("2.1.1", tag=None, hook="# hook v3 unreviewed\n")
                fx.git("tag", "-f", "-a", "v2.1.0", "-m", "moved")
                fx.git("push", "-q", "--force", fx.origin, "refs/tags/v2.1.0")
                fx.git("fetch", "-q", "--force", "--tags", "origin", cwd=fx.clone)

            code, out = fx.run_tty(shell, "y", at_prompt=tag_moves)
            self.assertEqual(code, 0, out)
            self.assertEqual(fx.head(), reviewed)

    def test_main_flag_refuses_local_main_commits(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0")
            fx.make_clone()
            with open(os.path.join(fx.clone, ".claude/hooks/enforce-laws.py"), "w") as f:
                f.write("# local hook\n")
            fx.git("commit", "-q", "-am", "local", cwd=fx.clone)
            fx.git("checkout", "-q", "--detach", "v2.0.0", cwd=fx.clone)
            before = fx.head()
            result = fx.run(shell, "--main")
            self.assertEqual(result.returncode, 1)
            self.assertIn("local main has commits", result.stderr)
            self.assertEqual(fx.head(), before)

    def test_already_on_the_tag_from_a_branch_detaches(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0")
            fx.make_clone()
            self.assertEqual(fx.run(shell).returncode, 0)
            self.assertEqual(fx.branch(), "")

    def test_a_deleted_tag_is_not_installed(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0")
            fx.make_clone(at="v2.0.0")
            fx.release("2.1.0")
            fx.git("fetch", "-q", "--tags", "origin", cwd=fx.clone)
            fx.git("push", "-q", fx.origin, ":refs/tags/v2.1.0")
            result = fx.run(shell)
            self.assertIn("already on v2.0.0", result.stdout)

    def test_strict_user_shell_options_and_aliases(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0", tag=None)
            fx.make_clone()
            setup = "set -e -o pipefail; alias grep='grep --color=always'; alias git='false'"
            if shell == "zsh":
                setup = "setopt errexit pipefail aliases; alias grep='grep --color=always'; alias git='false'"
            cmd = [shell, "-c", f'{setup}; . "{fx.fn}"; dforge-update; echo "shell survived"']
            result = subprocess.run(cmd, env=fx.env, cwd=fx.home, capture_output=True, text=True,
                                    stdin=subprocess.DEVNULL, timeout=60)
            self.assertIn("shell survived", result.stdout, result.stderr)

    def test_law_only_change_applies_without_asking(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0")
            fx.make_clone(at="v2.0.0")
            fx.write("README.md", "docs\n")
            newest = fx.release("2.1.0")
            result = fx.run(shell)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("hook", result.stdout.lower())
            self.assertEqual(fx.head(), newest)

    def test_local_changes_are_refused(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0")
            fx.make_clone(at="v2.0.0")
            fx.release("2.1.0")
            with open(os.path.join(fx.clone, "projects.yaml"), "w") as f:
                f.write("mine: true\n")  # gitignored: doesn't count
            before = fx.head()
            with open(os.path.join(fx.clone, "CLAUDE_LAWS.md"), "a") as f:
                f.write("my edit\n")
            result = fx.run(shell)
            self.assertEqual(result.returncode, 1)
            self.assertIn("has local changes", result.stderr)
            self.assertIn("CLAUDE_LAWS.md", result.stderr)
            self.assertNotIn("projects.yaml", result.stderr)
            self.assertEqual(fx.head(), before)
            subprocess.run(["git", "checkout", "-q", "CLAUDE_LAWS.md"], cwd=fx.clone, check=True)
            self.assertEqual(fx.run(shell).returncode, 0)

    def test_fetch_failure_changes_nothing(self) -> None:
        for shell, fx in self.each_shell():
            fx.release("2.0.0")
            fx.make_clone(at="v2.0.0")
            before = fx.head()
            shutil.rmtree(fx.origin)
            result = fx.run(shell)
            self.assertEqual(result.returncode, 1)
            self.assertIn("fetch failed. Nothing changed.", result.stderr)
            self.assertEqual(fx.head(), before)

    def test_help_and_unknown_flags(self) -> None:
        for shell, fx in self.each_shell():
            result = fx.run(shell, "--help")
            self.assertEqual(result.returncode, 0)
            self.assertIn("usage: dforge-update [--main]", result.stdout)
            for args in (("--bogus",), ("--main", "--bogus")):
                result = fx.run(shell, *args)
                self.assertEqual(result.returncode, 2, args)
                self.assertIn("usage:", result.stderr)
            self.assertIn("is not a git clone", fx.run(shell).stderr)  # no clone yet


@unittest.skipUnless(shutil.which("bash"), "needs bash")
class InstallScriptTests(unittest.TestCase):
    """The real install.sh, run against a temp HOME."""

    def test_detached_clone_is_not_pulled_and_the_function_is_installed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(os.path.realpath(tmp))
            fx.release("2.0.0")
            fx.make_clone(at="v2.0.0")
            env = dict(fx.env, SHELL="/bin/bash")
            result = subprocess.run(["bash", INSTALL], env=env, capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("On release v2.0.0; run dforge-update to update.", result.stdout)
            with open(os.path.join(fx.home, ".bashrc")) as f:
                rc = f.read()
            self.assertIn(function_source().strip(), rc)

    def install(self, fx: Fixture, update: bool = True) -> subprocess.CompletedProcess:
        env = dict(fx.env, SHELL="/bin/bash", **({"DFORGE_UPDATE": "1"} if update else {}))
        result = subprocess.run(["bash", INSTALL], env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_one_old_style_run_ends_on_the_release_tag(self) -> None:
        # The pre-v2.28 function pulls main, then runs install.sh with DFORGE_UPDATE=1.
        for update in (True, False):
            with self.subTest(dforge_update=update), tempfile.TemporaryDirectory() as tmp:
                fx = Fixture(os.path.realpath(tmp))
                tag = fx.release("2.0.0")
                fx.make_clone()
                self.assertIn("On release v2.0.0.", self.install(fx, update).stdout)
                self.assertEqual((fx.head(), fx.branch()), (tag, ""))

    def test_otherwise_the_clone_stays_where_it_is(self) -> None:
        cases = {
            "main ahead of the tag": lambda fx: fx.release("2.1.0", tag=None),
            "no tags": None,
            "local edits": "edit",
        }
        for name, setup in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                fx = Fixture(os.path.realpath(tmp))
                fx.release("2.0.0", tag=None if name == "no tags" else "default")
                if callable(setup):
                    setup(fx)
                fx.make_clone()
                if setup == "edit":
                    with open(os.path.join(fx.clone, "CLAUDE_LAWS.md"), "a") as f:
                        f.write("my edit\n")
                before = fx.head()
                self.assertNotIn("On release", self.install(fx).stdout)
                self.assertEqual((fx.head(), fx.branch()), (before, "main"))


if __name__ == "__main__":
    unittest.main()
