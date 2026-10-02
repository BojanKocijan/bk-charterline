# Plan — Law 37, human gates in the agentic loop

Spec: no separate `spec.md`. The intent is [#74](https://github.com/BojanKocijan/design-forge/issues/74), and the
content was supplied as a finished playbook, skill and law text, so the source files are the spec.
Gate tier: Significant · Branch: `feat/law-37-1-knowledge`, `feat/law-37-2-law` · Issue: #74
Work pile: delegable (fully specified, docs only, checked by markdownlint)
Approved-by: <pending>

> **Written after the fact.** The change shipped in v2.17.0 (#75, #77), before Law 37 required this file.
> At the time, the Law 2 announcement in chat served as the plan and was approved there. This file records
> that plan in the template from `knowledge/HUMAN_IN_THE_LOOP.md` §2.4 as a reference example.

## Files to change

| File | Change |
|---|---|
| `knowledge/HUMAN_IN_THE_LOOP.md` | Add the playbook; remove the third-party attribution from its changelog |
| `skills/human-in-the-loop/SKILL.md` | Add the on-demand trigger skill (`name` + `description` frontmatter) |
| `CLAUDE_LAWS.md` | Append Law 37; add the `**Gate tier:**` line to the Law 2 announcement; list `HUMAN_IN_THE_LOOP` in Law 4; bump the version header |
| `CLAUDE.md` | One knowledge row; four trigger rows (`approve <stage>`, `review queue`, `review cap`, `skip gates`) |
| `.github/PULL_REQUEST_TEMPLATE.md` | Intake and Decision log blocks under `## Summary` |
| `RELEASES.md` | v2.17.0 entry |
| `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Bump to `2.17.0` (Law 27) |

## Order of work

1. Pull `main`, open issue #74 — done when the issue exists and the branch is cut from current `main`.
2. PR 1: knowledge file and skill — done when markdownlint passes and the files contain no third-party references.
3. PR 2, stacked on PR 1: the law text, hooks into Laws 2 and 4, `CLAUDE.md`, the PR template, the release notes and the version bump — done when all four version locations read `2.17.0` and the JSON validates.
4. Before PR 2 is merged, change its base to `main` (pattern P-001) — done when PR 2's diff shows only its own commit against `main`.
5. After both merge, tag `v2.17.0` on the merge commit — done when the tagged `CLAUDE_LAWS.md` reads `2.17.0`.

## Proof

- Tests to add or change: none (docs-only repo)
- Commands that must pass: `npx markdownlint-cli2` on changed files; `python3 -m json.tool` on both plugin JSON files
- Reference check: `git grep -i -E 'digital|ux-claude-laws|agility|dot.components'` returns nothing
- Visual evidence: none, there is no UI change

## Risks

- Version collision: `main` moves during the work → re-check the version after pulling (it did move, from 2.13.0 to 2.16.0, so the release became 2.17.0)
- Stacked PR merged into its base instead of `main` → retarget it before merging (this happened with #76 and was recovered in #77)
- Tag created before the merge points at old content → tag only after verifying `main` has the new version (this happened once and was fixed)

## Ruled out

- One PR for everything: about 370 lines that mix content with the law and the release, so it was split per Law 31
- Restating PR size limits in Law 37: Law 31 already owns them
- Writing `intent.md` and `spec.md`: issue #74 and the supplied source files already answered them (reuse before you write)
