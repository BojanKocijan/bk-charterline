"""The trigger steps that moved from CLAUDE.md into skills (#239) still run the
same commands, and CLAUDE.md still links to them and keeps their safeguards."""
from __future__ import annotations

import os, unittest  # noqa: E401

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts: str) -> str:
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class TriggerSkillTests(unittest.TestCase):
    def test_the_skills_run_the_same_commands(self) -> None:
        update = read("skills", "update-rules", "SKILL.md")
        for needle in ("charterline-update", "--approve <commit>", "a refusal means stop", "Never retry with `--main`"):
            self.assertIn(needle, update)
        tools = read("skills", "ai-tools", "SKILL.md")
        for needle in ("scripts/ai_inventory.py", "scripts/ai_tools.py set", "never counts as approval", "Never classify on your own judgment"):
            self.assertIn(needle, tools)

    def test_claude_md_links_and_keeps_the_safeguards(self) -> None:
        claude = read("CLAUDE.md")
        for needle in ("./skills/update-rules/SKILL.md", "./skills/ai-tools/SKILL.md", "show the user the diff in chat",
                       "a refusal means stop", "never counts as approval", "Never classify on your own judgment"):
            self.assertIn(needle, claude)


if __name__ == "__main__":
    unittest.main()
