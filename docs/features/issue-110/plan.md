# Plan — Law 5 check reads the right repo in worktrees and after `cd;`

Spec: [#110](https://github.com/BojanKocijan/design-forge/issues/110) · Gate tier: Standard · Branch: `fix/hook-worktree-cwd` · Issue: #110
Work pile: delegable (fully specified, one script, verifiable with temp repos)
Approved-by: BojanKocijan, 2026-10-05, chat

## Files to change

| File | Change |
|---|---|
| `.claude/hooks/enforce-laws.py` | `main()` uses the payload `cwd` (falls back to `os.getcwd()`) and passes it to `check_bash` and `resolve_cwd`; `CD_RE` stops at `;`, `&`, `\|`; `resolve_cwd` scans heredoc-stripped text and walks every `cd` in order, moving only to existing directories |
| `tests/test_enforce_laws.py` | New `WorkingDirectoryTests` class |
| `CLAUDE_LAWS.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Version 2.21.2 (2.21.1 is reserved for #107) |
| `RELEASES.md` | v2.21.2 entry |

## Order of work

1. Commit this plan. Done when it is on the branch.
2. Change the hook. Done when the reproduction cases below behave as expected.
3. Add the tests. Done when they pass, and the "allowed" cases fail against the old hook.
4. Bump versions and add the `RELEASES.md` entry.
5. Open the PR with the Intake block.

## Proof

- Tests to add: in `WorkingDirectoryTests`, these are allowed: payload `cwd` = feature repo (process in a `main` repo), `cd <feat>; git commit -m "fix: x"`, `cd <feat> && git commit` with `; cd foo` in a heredoc body, and a trailing `cd -`. These are still blocked: payload `cwd` = the `main` repo, and `cd <main-repo>; git commit` run from the feature repo.
- Both temp repos get an initial commit. Without one, `git rev-parse --abbrev-ref HEAD` fails and the hook allows everything, which would hide the bug.
- Commands that must pass: `python3 -m unittest discover -s tests -v`, `python3 -m py_compile .claude/hooks/enforce-laws.py`.
- Visual evidence: none (no UI).

## Risks

- The payload `cwd` reflects the shell's cwd before the command runs. A `cd` in the command still has to be followed, which `resolve_cwd` does.
- Add/add conflict in `tests/test_enforce_laws.py` and `RELEASES.md` with #107. The PR that merges second resolves it.

## Ruled out

- Taking the last `cd` that resolves to a directory, instead of walking each `cd` in order. That breaks a relative `cd` that comes after an absolute one.
- Stacking on #107. Its branch isn't pushed, and this same bug blocks its commit.
