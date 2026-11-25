# Plan: Anthropic's code-review plugin on every Standard and Significant PR (#307)

Gate tier: Standard (Law 37's review step changes for every project; no hook change)

Approved-by: BojanKocijan, 2026-11-25, chat

## Goal

Every session under BK Charterline runs Anthropic's official **Code Review** plugin (`code-review@claude-plugins-official`) on its Standard and Significant PRs, so the owner gets one more independent check before merging.

## Why this plugin

The owner asked for "a plugin from Anthropic, code reviewer" and chose the official plugin over the engineering plugin's `engineering:code-review` (2026-11-25).

- **4 agents on the PR:** two check the change against the CLAUDE.md files, which is where the BK Charterline laws load; two look for bugs and logic errors in the changed code.
- **A validation pass:** each bug is checked again by its own agent, and only high-confidence findings are reported. Pre-existing issues, nitpicks and what a linter catches are dropped.
- **It reads the PR, not the working tree** (`gh pr view`, `gh pr diff`), so it runs once the PR is open. It skips closed and draft PRs.

## Where it runs

| Step | Before | After |
|---|---|---|
| Before the PR | built-in `/code-review <default-branch>...HEAD` (Standard, Significant) | unchanged |
| Significant, independent reviewer | fresh subagent, `engineering:code-review` when installed | unchanged |
| The PR is open, not a draft | nothing | `/code-review:code-review <PR>` (Standard, Significant); fix or answer each finding, push, then the PR-ready summary |
| `--comment` | only with the owner's yes | same for the plugin |
| Trivial | CI green and a glance | unchanged (the plugin skips trivial PRs anyway) |

The plugin's command is called with its plugin prefix, `/code-review:code-review`, because Claude Code's built-in `/code-review` has the same name.

## Files

| File | Change |
|---|---|
| `CLAUDE_LAWS.md` | Law 37 §4: the plugin runs on the open PR for Standard and Significant work; offered once when missing. |
| `knowledge/HUMAN_IN_THE_LOOP.md` | §5 table and *The reviewers*: a bullet for the plugin. §8 surface table: a column for it. Changelog 1.4.0. |
| `knowledge/TEAM_WORKFLOW.md` | §8: `code-review` in the plugin list and the Review row. Changelog 1.4.0. |
| `knowledge/FULLSTACK_WORKFLOW.md` | The review steps name the plugin on the open PR. |
| `skills/human-in-the-loop/SKILL.md` | Description names the plugin. |
| `agents/lead.md` | Step 5: run the plugin once the PR is open. |
| `README.md` | Optional plugins: `/plugin install code-review@claude-plugins-official`. |
| `RELEASES.md` | Unreleased entry. |

No version bump (the owner asks for releases). No hook change. The public page (`site/index.html`) isn't in this PR: its check only requires that the page names nothing the rules don't, so it stays correct. Adding the plugin there is a follow-up.

## Edge cases

- **Not installed** (missing from Claude's skill list): the built-in `/code-review` still runs. Claude offers the install once per session (TEAM_WORKFLOW §8) and never installs it itself. The PR's Decision log says the plugin didn't run.
- **Name clash with the built-in `/code-review`:** the rules always write `/code-review:code-review`. The built-in keeps its own name and levels.
- **Draft PR:** the plugin skips it. Claude runs it once the PR is ready for review, or says in the PR that it didn't run.
- **It posts nothing by default:** findings go to the terminal. `--comment` posts on GitHub, which is public, so only with the owner's yes.
- **Findings after the PR is open:** Claude pushes the fixes to the same branch and updates the Decision log. A finding Claude disagrees with is answered there, never silently dropped.
- **claude.ai web:** no plugins. The PR says the plugin review didn't run (HUMAN_IN_THE_LOOP §8).
- **Cost:** about 8–10 agent runs per PR on the session's usage, not billed credits like `/code-review ultra`.

## Tests

Docs only. `tests/test_laws_structure.py` (links and law items), `tests/test_skill_headers.py` (the skill description stays quoted text), markdown lint, and the site's §8 check (the page names nothing that §8 doesn't).

## PR

One PR, base `main`: the 8 files above and this plan. Built-in `/code-review main...HEAD` before opening, then the plugin on the open PR once it's installed (Law 37, Standard).
