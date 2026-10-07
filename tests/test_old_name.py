"""The old name, Design Forge, appears only where it belongs (#199): the
history, the code that moves an old install and its tests, the fallbacks to
the old update command, and the README's rename note.

Run: python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import os
import re
import subprocess
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLD = re.compile(r"design.forge|dforge", re.IGNORECASE)

# Each place that may keep the old name, and why. A count is the most lines
# it may have; None means the whole file (history, or code about the move).
ALLOWED = {
    "RELEASES.md": None,  # history; the v3.0.0 note explains the rename
    "install.sh": None,  # moves an install from before v3.0.0
    ".claude/hooks/rules_home.py": None,  # finds an install under either name
    ".claude/hooks/enforce-laws.py": 4,  # guards the old path; accepts dforge-update --approve
    ".claude/hooks/hook_log.py": 1,  # says where the log lives before the move
    "CLAUDE.md": 1,  # update rules falls back to dforge-update
    "CLAUDE_LAWS.md": 2,  # Law 28's update line and Law 32's --approve row
    "README.md": 1,  # the rename note
    "tests/test_enforce_laws.py": None,  # tests of the old path
    "tests/test_update.py": None,  # tests of the move
    "tests/test_old_name.py": None,  # this test
}


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True)
    return out.stdout.splitlines() if out.returncode == 0 else []


class OldNameTests(unittest.TestCase):
    def test_the_old_name_appears_only_where_it_belongs(self) -> None:
        files = tracked_files()
        if not files:
            self.skipTest("not a git checkout")
        problems = []
        for path in files:
            if path.startswith("docs/features/"):
                continue  # history
            try:
                with open(os.path.join(REPO, path), encoding="utf-8") as f:
                    lines = [n for n, line in enumerate(f, 1) if OLD.search(line)]
            except (UnicodeDecodeError, OSError):
                continue
            limit = ALLOWED.get(path, 0)
            if lines and limit is not None and len(lines) > limit:
                problems.append(f"{path}: lines {lines[:10]} (allowed {limit})")
        self.assertEqual(problems, [], "the old name outside history and the move code")
