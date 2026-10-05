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


if __name__ == "__main__":
    unittest.main()
