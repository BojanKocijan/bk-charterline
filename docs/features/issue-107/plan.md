# Plan — Law 32 hook checks only the commit's own message

Spec: [#107](https://github.com/BojanKocijan/design-forge/issues/107) (the issue is the intent and the spec)   ·   Gate tier: Significant, lowered by the owner with `skip gates` (no reason given)   ·   Branch: `fix/hook-commit-msg-segment`   ·   Issue: #107
Work pile: delegable (specified, isolated to one script, machine-verifiable)
Approved-by: BojanKocijan, 2026-10-05, chat

Written after the code, at the owner's request. It records what was built so the review can check the diff against it.

## Files to change

| File | Change |
|---|---|
| `.claude/hooks/enforce-laws.py` | Replace `extract_commit_message` with `split_segments` + `extract_commit_messages`. Heredoc bodies collapse to placeholders on the opener's line; the command splits on `&&`, `\|\|`, `;`, `\|`, `&` and newlines outside quotes, `$(...)`, `(...)` and backticks; each `git commit` segment yields its heredoc, `-m`/`--message` (including combined flags such as `-am`), or `-F <file>` message. Every message is checked. Unbalanced quoting or an unreadable `-F` file returns no message (fail open). |
| `tests/test_enforce_laws.py` (new) | Stdlib `unittest`. Runs the hook as a subprocess with hook JSON on stdin inside a temporary repo on `feat/x`. |
| `.github/workflows/hook-tests.yml` (new) | On push to `main` and on pull requests: checkout, setup-python 3.12, `python3 -m unittest discover -s tests -v`. |
| `README.md` | Contributing: CI runs the hook tests, and how to run them locally. |
| `RELEASES.md` | v2.21.1 entry. |
| `CLAUDE_LAWS.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Version 2.21.1 (Law 27 version sync). |

## Order of work

1. Rewrite the message extraction in the hook — done when the reported command is allowed and bad messages are still blocked.
2. Add the regression tests — done when they pass on the fix and the chained case fails on the old hook.
3. Add the CI workflow, README line, release entry and version bump — done when markdown lint passes and both manifests parse as JSON.

## Proof

- Tests added: commit chained with a `gh pr create` heredoc body → allowed; heredoc commit chained with a PR heredoc → allowed; heredoc commit with a non-conventional first line → blocked; `git commit -m "bad message"` → blocked; a valid commit followed by an invalid one → blocked. No existing tests edited (there were none).
- Checked by hand: `git commit -F - <<'EOF'` good and bad, `-F <file>` bad, `-F` missing file (allowed), unbalanced quote (allowed), `--message='…'`, `git merge -m "…"` before a valid commit (allowed), `-am "wip"` (blocked).
- Commands that must pass: `python3 -m unittest discover -s tests -v`; `npx markdownlint-cli2 --config .markdownlint.json "**/*.md"`.
- Visual evidence: none, no UI change. The PR body carries `Screenshots: not applicable`.

## Risks

- The splitter is a small hand-written shell tokenizer, so it can misread unusual syntax → anything it can't balance skips the Law 13 check instead of blocking; the other laws' checks don't use it.
- A heredoc whose opener isn't the last thing on its line (`cat <<EOF > f && git commit …`) isn't recognised, same as before → its body is read as commands. Rare in practice; not addressed here.
- `git commit -m "$(printf '…')"` is still blocked, because the captured message starts with `$(`. That fix belongs to PR 4 of the issue-102 plan.
- This PR takes v2.21.1, which the issue-102 plan gave to its PR 2 → that plan's PR 2 and PR 4 move to 2.21.2 and 2.21.3, and its PR 3 extends the test file and workflow added here. The issue-102 plan needs a revision and re-approval for this.

## Ruled out

- **Checking only the first `-m` before any heredoc.** It still picks up `-m` flags from other commands, like an earlier `git merge -m`.
- **A real shell parser (`shlex`).** `shlex` doesn't understand heredocs or `$(...)`, and the hook must stay dependency-free.
- **Fixing the hook's working-directory bug in this PR.** That's a different bug, with its own task and PR (Law 31).
