# Plan — context-menu card pattern works by keyboard

Spec: [#124](https://github.com/BojanKocijan/design-forge/issues/124) (the issue is the spec) · Gate tier: Standard (changes a knowledge file) · Branch: `fix/card-pattern-keyboard` · Issue: #124
Work pile: delegable (a reviewed text change, no code)
Approved-by: BojanKocijan, 2026-10-05, chat

## Files to change

| File | Change |
|---|---|
| `knowledge/COMPONENT_PATTERNS.md` | §20 "3-dot context menu": apply the owner's local edit word for word. The heading becomes "hover AND keyboard"; the trigger gains `group-focus-within:opacity-100`; a "Known miss" note is added; a new "Card body must be a `<button>`, not a `<div>`" rule (WCAG 2.1.1) is added; the "No event conflict" example uses the button body. Version 1.6.1 plus a changelog line. |
| `RELEASES.md` | v2.21.4 entry |
| `CLAUDE_LAWS.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Version 2.21.4 (Law 27 version sync; a fix to a binding pattern, so a patch bump) |

## Order of work

1. Apply the patch taken from `git -C ~/.design-forge diff knowledge/COMPONENT_PATTERNS.md`. Done when the diff of §20 matches it exactly.
2. Version header, changelog, `RELEASES.md`, version sync. Done when markdownlint passes and both manifests parse.
3. Open the PR with the Intake block. Done when CI is green.

## Proof

- Tests: none (documentation only).
- Commands that must pass: `npx markdownlint-cli2 --config .markdownlint.json "**/*.md"`, `python3 -m json.tool` on both manifests.
- Fidelity: `git diff` of §20 compared with the saved local patch, with no other line changed.
- Visual evidence: none (no UI). The PR body carries `Screenshots: not applicable`.

## Risks

- **The installed copy still has the edit uncommitted after merge.** Because this PR also changes the version header and changelog, the file on `main` won't match the local copy, and `git pull --ff-only` refuses. → Deploy checklist: after merge, discard the local edit in `~/.design-forge` (it's on `main` now), then run `dforge-update`.
- **Version collision with #113**, which plans 2.22.0. → No collision: 2.21.4 ships first, and #113 bumps from whatever `main` has.

## Ruled out

- **Rewriting the pattern in house style.** The owner wrote and validated it in a real project, so ship it as written and only add the version and changelog.
- **No version bump.** It corrects a binding pattern that produced inaccessible UI, so it's a `fix:` and needs a `RELEASES.md` entry (Law 31).
