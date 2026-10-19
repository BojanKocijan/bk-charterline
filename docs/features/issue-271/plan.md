# Plan — Move Laws 10, 27, 28, 31 and 35 into on-demand files (#271)

Spec: [#271](https://github.com/BojanKocijan/bk-charterline/issues/271), part of epic [#267](https://github.com/BojanKocijan/bk-charterline/issues/267), follows [#239](./../issue-239/plan.md) · Gate tier: Significant (it restructures the laws; the issue is the intent, this plan carries the spec) · Branch: `claude/intelligent-johnson-0hdbwq` (assigned) · Issue: #271
Work pile: judgment-heavy (choosing which sentences stay binding at session start), built in this session
Plan page: https://claude.ai/artifact/X2FfuceCMBAS7K2yhFsQW7
Approved-by: BojanKocijan, 2026-10-19, chat

## Why

`laws_cost.py` today: `CLAUDE_LAWS.md` ~20,200 tokens, `CLAUDE.md` ~6,600, total ~26,800 on every session. These five laws apply only to specific work, yet they are ~13,300 bytes (~4,800 tokens) of the laws:

| Law | Scope | Bytes today |
|---|---|---|
| 10 | `new project` | 1,056 |
| 27 | a change or release of BK Charterline itself | 1,668 |
| 28 | the update notice and `update rules` | 2,134 |
| 31 | sizing and shaping a PR | 4,548 |
| 35 | a change with steps beyond "merge the PR" | 3,860 |

## The rule for every move

Issue #239 moved only explanation. This issue goes one step further, as it asks: each law keeps its **number, bold title and one short binding paragraph**: what Claude must or must never do, in a sentence or three. The rest of the body (tables, lists of requirements, examples, procedures) moves **word for word** to the file named in the pointer, which loads when the scope fires (Law 4). Moved text stays binding there (Law 4). Nothing is reworded except the new binding paragraphs. Law numbers don't change, and the hook isn't touched.

A sentence stays in the law, not just in the file, when breaking it is costly and it can apply before the file is loaded: never open a PR with red CI, never pull without a go-ahead, never run SQL on a hosted database.

## What stays and where the rest goes

**Law 10** → new `knowledge/PROJECT_SCAFFOLD.md` §0a *What every new project ships with (Law 10)* (loads on `new project`).
> **Every new project Claude builds ships with CI and tests.** CI on every push and PR, a GitHub Pages preview, and Dependabot, as listed in [PROJECT_SCAFFOLD.md §0a](./knowledge/PROJECT_SCAFFOLD.md). Claude never opens a PR with red CI, in any project; if `npm run ci` fails locally, Claude fixes it first.

**Law 27** → new `docs/MAINTAINER.md` section *Plugin compliance (Law 27)*. It applies only inside this repo, so the pointer is the trigger (no new row in `CLAUDE.md`, which #272 is shrinking).
> **BK Charterline stays a valid, submittable Claude Code plugin.** Every change keeps the repo installable through `install.sh` and as a plugin. A version bump updates `plugin.json`, `marketplace.json`, this file's header and `RELEASES.md` in the same PR; Claude never pushes release tags. Before changing the manifest, layout or version, Claude reads [`docs/MAINTAINER.md` → Plugin compliance](./docs/MAINTAINER.md#plugin-compliance-law-27).

**Law 28** → `skills/update-rules/SKILL.md`, new section *How updates work (Law 28)* (loads on `update rules`).
> **Notify consuming sessions when a new rules version ships.** When the session-start hook reports a newer release, Claude shows its one update line and carries on with the loaded version. Claude never pulls or installs without the user's go-ahead, and an update that changes the hook installs only after the user's own approval in their terminal or the app's prompt. How `update rules` and `charterline-update` work: [`skills/update-rules/SKILL.md`](./skills/update-rules/SKILL.md).

**Law 31** → new `knowledge/HUMAN_IN_THE_LOOP.md` §7 *PR size and shape (Law 31)* (loads when drafting a PR).
> **Small, atomic PRs.** Every PR does one thing: under 400 lines changed and 10 files, no mixed concerns, tests in the same PR as their code, every commit atomic. Bigger work is split into a numbered stack of PRs that each leave the default branch green. A PR that changes user-facing behavior updates `README.md` and `RELEASES.md` in the same PR. Sizing table, splitting strategies, pre-PR self-check, PR body and repo hygiene: [HUMAN_IN_THE_LOOP.md §7](./knowledge/HUMAN_IN_THE_LOOP.md).

**Law 35** → new `knowledge/FULLSTACK_WORKFLOW.md` §9 *Ordered deploy steps (Law 35)*, next to the existing *Why* section (loads on any production PR). Most of this law is obligation, so its paragraph is the longest.
> **Explicit, ordered deploy steps whenever a change needs more than "merge the PR."** Claude's PR-ready summary then includes a numbered checklist in merge order with the literal command, SQL or dashboard path, an undo for each step, and what means roll back. Claude never applies a migration or runs writing SQL on a hosted database: it writes the migration in the repo and pastes the complete SQL and a check query in chat. Example, undo rules and details: [FULLSTACK_WORKFLOW.md §9](./knowledge/FULLSTACK_WORKFLOW.md).

## Files to change

| File | Change |
|---|---|
| `CLAUDE_LAWS.md` | Laws 10, 27, 28, 31, 35 shrink to the paragraphs above |
| `knowledge/PROJECT_SCAFFOLD.md` | §0a: Law 10's list, moved |
| `docs/MAINTAINER.md` | *Plugin compliance (Law 27)*: Law 27's list, moved |
| `skills/update-rules/SKILL.md` | *How updates work (Law 28)*: Law 28's bullets, moved |
| `knowledge/HUMAN_IN_THE_LOOP.md` | §7: Law 31's body, moved |
| `knowledge/FULLSTACK_WORKFLOW.md` | §9: Law 35's body, moved; the *Why* section links to §9 and to HUMAN_IN_THE_LOOP §7 |
| `tests/test_old_name.py` | Allowlist: the `dforge-update` line moves from `CLAUDE_LAWS.md` (1 → 0, entry removed) to `skills/update-rules/SKILL.md` (1 → 2) |
| `RELEASES.md` | `Unreleased` entry with the measured saving |
| `docs/features/issue-271/plan.md` | This plan |

9 files. Expected diff ~300 lines, mostly moved lines (Law 31 ceiling 400 / 10).

## Order of work

1. Move each law's body to its file, word for word, one law at a time — done when `git diff --word-diff` shows the moved text unchanged apart from heading levels.
2. Write the five binding paragraphs — done when each matches this plan.
3. Update `tests/test_old_name.py` and `RELEASES.md` — done when the full test suite passes.
4. Measure with `laws_cost.py`, record the before/after in the PR and `RELEASES.md`.
5. `/code-review main...HEAD` plus an independent subagent review given only this plan and the diff (Significant tier); fix the findings, open the PR.

## Proof

- **Tests to change:** `tests/test_old_name.py` (allowlist counts only, as above). No test added: the existing `test_laws_structure.py` already checks that every law keeps its bold title and that knowledge links resolve.
- **Commands that must pass:** `python3 -m unittest discover -s tests`, `python3 scripts/laws_cost.py`, `python3 scripts/release_version.py check`, `claude plugin validate .` (if the CLI is available), the markdown-lint workflow in CI.
- **Measured result:** `CLAUDE_LAWS.md` drops from ~20,200 to ~16,300 tokens (~3,900 saved; the exact figure goes in the PR). `CLAUDE.md` unchanged.
- **No text lost:** a script check that every sentence removed from `CLAUDE_LAWS.md` appears in one of the five target files or in a binding paragraph. The output goes in the PR.
- **Hook unchanged:** `git diff main -- .claude/ hooks/` is empty.
- **Visual evidence:** none (no UI change).

## Risks

- **An obligation now loads only when its scope fires.** For example, the "README in the same PR" rule could be missed in a session that never reads HUMAN_IN_THE_LOOP. → The costly or always-applicable sentences stay in the binding paragraphs (see *The rule for every move*), and the CLAUDE.md table already loads HUMAN_IN_THE_LOOP when drafting any PR.
- **Law 27's file isn't in Law 4's knowledge list.** → The law's pointer is its trigger, and the obligation that matters most (four-file version sync) stays in the law.
- **Law 35 inside FULLSTACK_WORKFLOW** loads on production PRs, not on a frontend session that writes SQL. → Never running SQL, pasting it in chat and the checklist all stay in the law.
- **Anchors from other files** (`CLAUDE.md`, `README.md`, the `site/`) that link into these laws. → grep for `Law 10`/`27`/`28`/`31`/`35` links before and after; the law numbers stay, so plain references keep working.
- **This release changes no hook file**, so `update rules` won't ask for approval.

## Ruled out

- **Moving the whole body with only a pointer left.** The issue asks for a binding sentence, and "never run SQL on a hosted DB" must not depend on a file loading.
- **Rewording the moved text to shorten it.** That would mix a rewrite with a move and make the diff hard to check (Law 31: one concern).
- **Law 27 into a new knowledge file.** One more file and one more row in `CLAUDE.md` for a law that only maintainers of this repo need; `docs/MAINTAINER.md` already holds the release steps.
- **One PR for #271 and #272.** Owner decision 2026-10-19: #271 first, #272 after it merges.
