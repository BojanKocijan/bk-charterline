# Plan — Remove the tables CLAUDE.md duplicates (#272)

Spec: [#272](https://github.com/BojanKocijan/bk-charterline/issues/272), part of epic [#267](https://github.com/BojanKocijan/bk-charterline/issues/267), follows [#271](./../issue-271/plan.md) · Gate tier: Significant (it changes the always-loaded entry point; the issue is the intent, this plan carries the spec) · Branch: `claude/intelligent-johnson-0hdbwq` (assigned) · Issue: #272
Work pile: judgment-heavy (deciding which copy is the one to keep), built in this session
Plan page: https://claude.ai/artifact/A6P1iYDc21ztf5or79myts
Approved-by: BojanKocijan, 2026-10-20, chat

## Why

After #271, `laws_cost.py` reports `CLAUDE.md` at ~6,600 tokens (15,995 bytes) and `CLAUDE_LAWS.md` at ~16,370. Both load in every session, and so do the 20 skill descriptions. `CLAUDE.md` repeats text that one of those already carries:

| `CLAUDE.md` section | Bytes | Already in |
|---|---|---|
| Non-negotiables | 612 | `CLAUDE_LAWS.md` (Laws 2, 5, 7, 8, 12, 14, 15, 17, 18, 35) |
| What Claude will refuse | 537 | `CLAUDE_LAWS.md` (Laws 1, 2, 5, 7, 8, 12, 14, 15) |
| The personas (two tables) | 1,566 | The trigger table (each persona's trigger and its `agents/*.md` link) and the laws' *The Personas* line (team vs supporting roles, default Frontend) |
| Trigger rows that restate a skill | ~1,700 | The skill's always-loaded description, plus its body on demand |

## The rule

The issue's own test: **no table or list in `CLAUDE.md` repeats another always-loaded file.** One copy stays, and every removed copy either has a link to the one that stays or is already covered by a law. Nothing binding is dropped: any sentence that exists only in `CLAUDE.md` moves to the kept copy first. The trigger table stays as the one list of trigger phrases, because nothing else lists them all.

## Changes

**1. Delete *Non-negotiables*.** The laws load right above it, so a ten-item summary of them is a second copy. The line under *Loaded rules* already says the laws are binding.

**2. Delete *What Claude will refuse*.** Same reason. Its closing pointer ("Full set in CLAUDE_LAWS.md") is already in the footer.

**3. Replace *The personas* with two lines.** Every persona's trigger and file are already in the trigger table. The laws' *The Personas* line says which roles are team roles and which are supporting, and that Frontend is the default. Two facts appear only in the persona tables, and they move:
- "Design: implied by Figma/design tasks" → the laws' *The Personas* line.
- Each persona's one-line scope → it is already the first paragraph of `agents/<persona>.md`, which loads on activation. Nothing is lost.

The laws' line changes from "Full table + triggers in CLAUDE.md" to "Triggers in CLAUDE.md; each persona's scope in `agents/`."

**4. Shorten the trigger rows that restate a skill to the trigger plus a link.** Each row keeps the safeguards #239 kept in `CLAUDE.md` and that `tests/test_trigger_skills.py` checks: show the hook diff in chat, a refusal means stop, never counts as approval, never classify on your own judgment.

| Row | Keeps | The rest is already in |
|---|---|---|
| `update rules` | link, "show the user the diff in chat", "a refusal means stop", never `--main` unless asked | `skills/update-rules/SKILL.md` |
| `ai inventory` | link, read-only | `skills/ai-tools/SKILL.md` |
| `ai classify` | link, "never counts as approval", "Never classify on your own judgment" | `skills/ai-tools/SKILL.md` |
| `disarm` / `arm` | link, the hard-safety rails that survive (never merge, no secrets, no PII) | `skills/arm-disarm/SKILL.md` |
| `handoff <id>` | link | `skills/developer-handoff/SKILL.md` (the 13-section file, issue, cross-link, §10 row) |

Before deleting a row's text, I diff it against the skill. Any sentence the skill doesn't have moves into the skill in this PR. If more than two need to move, I stop and ask.

**5. Carried over from #271:**
- The FULLSTACK_WORKFLOW row in the *Knowledge* table also fires on "a change with steps beyond merging the PR (Law 35)".
- README: "about 27,000 tokens" becomes the new measured figure.

## Files to change

| File | Change |
|---|---|
| `CLAUDE.md` | Changes 1–4, the FULLSTACK_WORKFLOW row, and the header's claude.ai web line (paste the laws with it) |
| `CLAUDE_LAWS.md` | *The Personas* line: the Design trigger, and its pointer to `agents/` |
| `README.md` | Token count |
| `RELEASES.md` | `Unreleased` entry with the measured saving |
| `docs/features/issue-272/plan.md` | This plan |
| `skills/*/SKILL.md` | Only if step 4's diff finds a sentence that exists only in `CLAUDE.md` (at most two skills) |

5 to 7 files. Expected diff ~150 lines.

## Order of work

1. For each row in change 4, diff the row against its skill and list any sentence found only in the row — done when the list is in the PR (expected: empty).
2. Changes 1–3 — done when `CLAUDE.md` has no *Non-negotiables*, *What Claude will refuse* or persona tables, and the laws' *The Personas* line names the Design trigger and `agents/`.
3. Change 4 — done when `tests/test_trigger_skills.py` passes unchanged.
4. Change 5, then measure with `laws_cost.py` and record before/after in the PR, `RELEASES.md` and the README.
5. `/code-review main...HEAD` plus an independent subagent review that sees only this plan and the diff; fix the findings, open the PR.

## Proof

- **Tests:** none added or edited. `tests/test_trigger_skills.py` already pins the safeguards that must stay in `CLAUDE.md`, and `tests/test_laws_structure.py` checks the laws' links.
- **Commands that must pass:** `python3 -m unittest discover -s tests`, markdownlint with `.markdownlint.json`, `python3 scripts/laws_cost.py`, `python3 scripts/release_version.py check`.
- **Measured result:** `CLAUDE.md` drops from ~6,600 to ~5,100 tokens (~1,500 saved; the exact figure goes in the PR).
- **No rule lost:** a script lists every sentence removed from `CLAUDE.md` with the file and line where it still exists. The output goes in the PR.
- **The issue's "done when":** a script checks that every table and list left in `CLAUDE.md` has no row repeated in `CLAUDE_LAWS.md`. Output in the PR.
- **Hook unchanged:** `git diff main -- .claude/ hooks/` is empty. The session-start confirmation comes from the hook, not from these sections.
- **Visual evidence:** none (no UI change).

## Risks

- **A session without the laws.** `CLAUDE.md`'s header says it "works as Custom Instructions for a claude.ai web Project". There, `@./CLAUDE_LAWS.md` doesn't resolve, so someone who pastes only `CLAUDE.md` has had only the two summaries, and now has none. → That header line changes to: paste `CLAUDE_LAWS.md` together with `CLAUDE.md`. A 10-line summary was never the full set anyway.
- **Personas are less visible at a glance.** → The trigger table names every persona and its file, and the laws name the roles and the default. Only the one-line scopes move behind activation, and they are already in `agents/`.
- **`AGENTS.md` has its own *Non-negotiables*.** It is for other tools, never loaded by Claude, so it is out of scope.
- **The confirmation template in `CLAUDE.md` still says `v1.0.0`.** That is pre-existing and harmless, since the hook prints the real version. It is not touched here (one concern per PR).

## Ruled out

- **Deleting the trigger table and relying on skill descriptions.** Not every trigger has a skill (`dry run`, `stop preview`, `review cap`), and the table is the one place that lists them all.
- **Keeping the persona tables and deleting the laws' *The Personas* line.** The laws are the binding file, and the line is one sentence.
- **Also removing the *Session-start behavior* section.** It isn't a duplicate. The hook prints the block, and this section tells Claude what to do with it.
