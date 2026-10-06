# Plan — the hook asks before git moves the installed ~/.design-forge, and hook updates are approved in the app (#170)

Spec: [#170](https://github.com/BojanKocijan/design-forge/issues/170) (the issue), plus the owner's addition in chat (2026-10-06): approve a hook update in the app instead of typing `y` in a terminal · Gate tier: Standard · Issue: #170
Work pile: delegable (one hook check, specified, machine-verifiable), done in this session
Approved-by: BojanKocijan, 2026-10-06, chat

## PRs (Law 31: two concerns, two PRs, both based on `main`)

1. **`feat/hook-ask-clone-git`** — the hook asks before git changes the installed clone. v2.30.0. About 220 lines, 8 files. Everything from "Files to change" to "Ruled out" below.
2. **`feat/update-approve-in-app`** — `update rules` no longer needs a terminal for a hook change. v2.31.0. About 150 lines, 7 files. See "PR 2" at the end. Opened after PR 1 merges (both bump the version).

## Files to change (PR 1)

| File | Change |
|---|---|
| `.claude/hooks/enforce-laws.py` | New `moves_installed_clone(segment, cwd) -> str \| None`: returns the git subcommand when the segment would change the installed clone's working tree, else None. Called in `check_bash`'s existing per-segment loop, so the ask is held until every block check has run. Check id `guardrail-git`, reason names Law 32 and suggests `dforge-update` |
| `tests/test_enforce_laws.py` | New `InstalledCloneGitTests` (see Proof). One existing assertion moves (see Tests touched) |
| `CLAUDE_LAWS.md` | Law 32 asks table: a new row. Law 28: "git commands run by hand in `~/.design-forge` skip it" becomes "… the hook asks before they change the clone (#170)". Version 2.30.0 |
| `README.md` | The "Plain git commands in `~/.design-forge` skip this check" line, the Law 32 summary row, version badge |
| `RELEASES.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | v2.30.0, version sync |
| `docs/features/issue-170/plan.md` | This plan |

## How the check decides

1. **Tokenise** the segment (`shlex`); unbalanced quotes → None (fail open). A nested `bash|sh|zsh -c "<inner>"` is checked segment by segment, like `writes_registry`.
2. **Read env prefixes** `GIT_DIR=` and `GIT_WORK_TREE=`, then strip prefixes as today.
3. **Walk git's global options:** each `-C <dir>` (chained, each relative to the one before), `--git-dir[=]<dir>`, `--work-tree[=]<dir>`, `-c <k=v>`, other flags. The repo dir is the work tree if given, else the git dir's parent, else the `-C` chain applied to the segment's cwd.
4. **Installed clone?** `realpath(repo dir)` equals `realpath(~/.design-forge)` or lies under it (case-folded on macOS, like `protected_target`). A Design Forge development checkout isn't the installed copy and stays free.
5. **Subcommand asks** if it's one of: `checkout`, `switch`, `pull`, `reset`, `merge`, `rebase`, `restore`, `cherry-pick`, `am`, `apply`, `clean`, `revert`, `stash`.
6. **Allow list** (`CLONE_GIT_ALLOWED`, each entry with its reason and a test): `stash list` and `stash show` (read only). A command that turns out to ask wrongly is added here rather than loosening steps 1–5.

Everything else stays free: `status`, `log`, `diff`, `show`, `fetch`, `ls-remote`, `describe`, `tag --list`, `rev-parse`, and `dforge-update` itself (including `"$SHELL" -ic dforge-update`), whose own gate is the approval.

## Order of work

1. `moves_installed_clone` and the wiring. Done when the new tests pass.
2. Laws, README, release. Done when `release_version.py check` prints `2.30.0` and markdownlint is clean.

## Proof

- **Tests to add:** asks for `git -C ~/.design-forge checkout v2.27.0`, `cd ~/.design-forge && git pull`, `git -C ~/.design-forge reset --hard origin/main`, a subfolder (`git -C ~/.design-forge/knowledge restore .`), a symlink to the clone, `--git-dir`/`--work-tree`, `GIT_WORK_TREE=~/.design-forge git checkout x`, `bash -c "cd ~/.design-forge && git switch main"`, `stash pop`, `clean -fdx`. Stays free: `status`, `log`, `fetch`, `ls-remote`, `describe`, `stash list`, `dforge-update`, `"$SHELL" -ic dforge-update`, the same commands in a dev checkout and in a project repo, unbalanced quotes. The ask is logged as Law 32 `guardrail-git`. A block still wins: `cd ~/.design-forge && git pull && git push` on the default branch blocks.
- **Tests touched:** `GuardrailAskTests.test_bash_reads_and_updates_are_free` lists `git -C ~/.design-forge pull --ff-only` as free. That's the behavior #170 changes, so the line moves to the new ask tests. No assertion is loosened.
- **Commands:** `python3 -m unittest discover -s tests`, `python3 scripts/release_version.py check`, markdownlint.
- **Visual evidence:** none (no UI). `Screenshots: not applicable`.

## Risks

- **False asks while working on the installed clone on purpose** (repairing it). → That's what the ask is for: one click.
- **String parsing can be evaded** (a script, an alias, `python -c "subprocess…"`). → Law 32 is a backstop, not a sandbox; stated already.
- **`git -C` with `~` or `$HOME`:** `shlex` leaves them literal. → `expanduser` and `expandvars` before resolving, as `protected_target` does.
- **`dforge-update` changes:** it runs git inside the function, which the hook never sees. → A test pins that it stays free.

## Ruled out

- **Blocking instead of asking:** repairing a broken clone has to stay possible (issue constraint).
- **Asking for every git command in the clone:** reads would prompt constantly and teach clicking through.
- **Matching `.design-forge` by name:** the dev checkout and other folders would match; the realpath comparison is exact.

## PR 2 — approve a hook update in the app

**Flow:**

1. `update rules` runs `"$SHELL" -ic dforge-update` as today. With no hook change, it installs and is done.
2. With a hook change and no terminal, `dforge-update` prints the diff, then `dforge: to approve in the app, run dforge-update --approve <sha>`, where `<sha>` is the exact commit it reviewed. It applies nothing.
3. Claude shows the diff in chat, then runs `"$SHELL" -ic 'dforge-update --approve <sha>'`.
4. **The hook asks** on any command containing `dforge-update … --approve` (check id `update-approve`, Law 28). The app's permission prompt appears; only your click lets it run. A refusal means nothing changes.
5. `dforge-update --approve <sha>` applies the update only if `<sha>` is still exactly the commit it would install. If a newer release appeared in between, it stops and shows the new diff, so you never approve one diff and get another.

**Safety rails:**

- `--approve` is refused when `~/.claude/settings.json` doesn't register `enforce-laws.py`, because then nothing would ask you. A plugin install without the hook keeps the terminal `y`.
- The terminal `y` still works as today.
- The hook asks on `--approve` even inside `"$SHELL" -ic '…'` or `bash -c`, and even with a block elsewhere in the command (the block still wins).

| File | Change |
|---|---|
| `install.sh` (the `dforge-update` function) | `--approve <sha>` option, the "run --approve" hint, the SHA match, the hook-registered check |
| `.claude/hooks/enforce-laws.py` | Ask on `dforge-update … --approve` (`update-approve`) |
| `tests/test_dforge_update.py`, `tests/test_enforce_laws.py` | Tests below |
| `CLAUDE.md` | The `update rules` row: on a hook change, show the diff, then run `--approve <sha>`; never retry another way |
| `CLAUDE_LAWS.md` | Law 28: "needs a `y` in your own terminal, or your click in the app's prompt for `--approve`". Law 32 asks table: a row. Version 2.31.0 |
| `README.md`, `RELEASES.md`, `plugin.json`, `marketplace.json` | Docs, v2.31.0 |

**Proof (PR 2):** no terminal and no `--approve` → nothing applied, the hint names the SHA. `--approve` with the right SHA → applied. A wrong or stale SHA → nothing applied. `--approve` with the hook not registered → refused. The hook asks for `dforge-update --approve x`, `"$SHELL" -ic 'dforge-update --approve x'` and `bash -c "dforge-update --approve x"`; plain `dforge-update` stays free. All under bash 3.2.

**Note:** PR 2 changes `install.sh`, so installing it needs one last terminal `y`. After that, hook updates are approved in the app.
