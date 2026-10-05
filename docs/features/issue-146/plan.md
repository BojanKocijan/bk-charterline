# Plan — laws for cloud sessions

Spec: [#146](https://github.com/BojanKocijan/design-forge/issues/146) (the issue is the spec) · Gate tier: Standard (changes the laws) · Branch: `claude/review-open-prs-5p8k5o` (assigned by the cloud session) · Issue: #146
Work pile: judgment-heavy (law wording)
Approved-by: <pending>

## Behavior

1. **Assigned branch** (Laws 5 and 9).
   - When the environment assigns Claude a branch and allows pushing nowhere else (a cloud session), Claude uses that branch instead of creating `feat/…`.
   - Before new work, and after each merge, Claude starts the branch again from the latest default branch: `git fetch origin <default> && git checkout -B <assigned> origin/<default>`.
   - **Never** new commits on top of already-merged history. If the branch still has unmerged commits, Claude keeps them (rebases them onto the new base) instead of discarding them.
   - Law 9's step "delete the remote branch" is skipped for an assigned branch. GitHub usually deletes it on merge, and the next push recreates it.
2. **Hand over SQL; never run it** (Law 35).
   - Claude never applies a migration or runs writing SQL on a hosted (shared or production) database, not even with a tool that allows it.
   - It writes the migration in the repo (idempotent where possible) and hands the owner:
     - the SQL to run;
     - a short **check query** with its expected result (for example "1 row: 13").
   - The dependent PR is merged only after the owner confirms the check result. Law 38's tier 4 still applies to any read-only call Claude makes.
3. **CI that can't run** (Law 7's "PR ready" summary).
   - The `CI:` line gains a fourth state: `not run ⚠ (<reason>)`.
   - Below it, Claude lists the local checks that passed (for example "lint, typecheck, 862 tests, build").
   - Claude never writes `green` for checks that did not run on GitHub.
4. **Images in a new message** (`knowledge/SKILLS.md` §6 Git hygiene is the wrong place, so a new short §6.a "Working in a cloud session", next to it).
   - Images a user sends while Claude is still working may not be saved in a cloud session.
   - When an image Claude needs is missing from disk, Claude asks for it to be sent again in a new message. It never guesses what the image showed.

## Files to change — one PR (6 files, about 40 lines)

| File | Change |
|---|---|
| `CLAUDE_LAWS.md` | Law 5: an "assigned branch" paragraph. Law 9: the skip for an assigned branch. Law 7: the `not run` CI state. Law 35: the "never run it, hand over SQL plus a check query" paragraph. Version 2.25.0 |
| `knowledge/SKILLS.md` | New §6.a "Working in a cloud session" (images in a new message; link to the assigned-branch rule in Law 5) |
| `RELEASES.md` | v2.25.0 entry |
| `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Version 2.25.0 |
| `docs/features/issue-146/plan.md` | This plan |

## Order of work

1. Commit this plan; the owner approves it (`approve plan`).
2. Write the four changes and the version sync. Done when markdownlint passes and both manifests parse.
3. Open one PR against `main` that closes #146, with the Law 37 intake block.

## Proof

- **Tests:** none. Wording only; the Law 32 hook doesn't change. The hook test suite (`tests/test_enforce_laws.py`) must still pass, because Law 5's text changes near rules the hook enforces.
- **Commands that must pass:**
  - markdownlint (the repo's `.markdownlint.json`);
  - `python3 -m json.tool` on both manifests;
  - `python3 -m pytest tests/` (or `python3 -m unittest`, whichever the CI job uses).
- **Visual evidence:** none (no UI). The PR body says `Screenshots: not applicable`.

## Risks

- **The assigned-branch rule could be read as permission to skip Law 5 everywhere.** → It applies only when the environment allows pushing to one branch only, and it says so.
- **Rebasing kept commits.** Restarting the branch must never drop unmerged work. → The rule says: keep and rebase unmerged commits, and reset only when the branch holds nothing but merged history.
- **Overlap with the open PR #145** (README badges). → This PR doesn't touch `README.md`. The README badge still says 2.19.1 on `main`; #145 fixes it to 2.24.0. Whichever merges second gets one line updated to 2.25.0.

## Ruled out

- **"A default stands if the owner doesn't object."** It conflicts with Law 2 (silence is not approval).
- **A per-project "working rules" section.** The owner removed it (sports-training-api#233): rules for how Claude works belong here.
- **A hook check for SQL calls.** Law 38's mechanical enforcement is already tracked in #138.
