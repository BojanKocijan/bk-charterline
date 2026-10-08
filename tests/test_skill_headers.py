"""Every skill's header keeps its name and description as plain text (#239).

An unquoted description containing ": " parses as a nested mapping, so the
skill loads with no description and never triggers. Dependency-free: a
plain description must not contain ": " or start with a YAML indicator.
"""
from __future__ import annotations

import glob, os, re, unittest  # noqa: E401

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SkillHeaderTests(unittest.TestCase):
    def test_every_description_is_text(self) -> None:
        problems = []
        for path in sorted(glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md"))):
            with open(path, encoding="utf-8") as f:
                head = f.read().split("---")[1]
            name = os.path.basename(os.path.dirname(path))
            if not re.search(rf"^name: {re.escape(name)}$", head, re.M):
                problems.append(f"{name}: name missing or not the folder name")
            m = re.search(r"^description: (.+)$", head, re.M)
            if not m:
                problems.append(f"{name}: no description")
                continue
            d = m.group(1)
            quoted = (d.startswith('"') and d.endswith('"')) or (d.startswith("'") and d.endswith("'"))
            if not quoted and (": " in d or d[0] in "\"'[{&*!|>%@`#"):
                problems.append(f"{name}: unquoted description with ': ' or a YAML indicator")
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
