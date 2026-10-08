"""The laws keep their shape when text moves out of them (#239).

Every law 1-38 (and 5a) starts its own list item with a bold title, after a
blank line, so no law can be swallowed into the paragraph above it, and
every link to a knowledge file points at a file that exists.
"""
from __future__ import annotations

import os, re, unittest  # noqa: E401

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class LawsStructureTests(unittest.TestCase):
    def setUp(self) -> None:
        with open(os.path.join(ROOT, "CLAUDE_LAWS.md"), encoding="utf-8") as f:
            self.text = f.read()

    def test_every_law_starts_its_own_item(self) -> None:
        for n in [str(i) for i in range(1, 39)] + ["5a"]:
            m = re.search(rf"(^|\n)(.*)\n{re.escape(n)}\. \*\*[^*]", self.text)
            self.assertIsNotNone(m, f"Law {n} has no bold title")
            self.assertEqual(m.group(2).strip(), "", f"Law {n} doesn't follow a blank line")

    def test_knowledge_links_resolve(self) -> None:
        for path in set(re.findall(r"\]\(\./(knowledge/[A-Z_]+\.md)", self.text)):
            self.assertTrue(os.path.exists(os.path.join(ROOT, path)), path)


if __name__ == "__main__":
    unittest.main()
