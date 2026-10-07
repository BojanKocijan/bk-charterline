# Plan — the Law 14 check reads what the commit will contain (#187)

Spec: [#187](https://github.com/BojanKocijan/design-forge/issues/187) (the issue) · Gate tier: Standard · Branch: `fix/issue-187-commit-contents` · Issue: #187
Work pile: delegable (one hook check; machine-verifiable with temporary repos)
Approved-by: BojanKocijan, 2026-10-07, chat (both decisions as recommended)

## The gap

The hook runs **before** the command, so `git diff --cached` shows the staging area as it was before the command started. Three ways to commit content the check never reads:

| Command | What it commits that the check misses |
|---|---|
| `git add X && git commit -m …` in one call | `X`, staged by the same call |
| `git commit -a` / `--all` (also in a cluster such as `-am`) | every unstaged change to a tracked file |
| `git commit X`, `--only X`, `-i` / `--include X` | the working-tree content of `X` |

The `.env` check has the same gap, and one more: it runs only when the command line contains `.env`, so `git add -A && git commit` with an untracked `.env` passes.

## What the check reads after the fix

The check still reads `git diff --cached`. It also reads:

1. **`git add` earlier in the same call.** For each `git add` (or `git stage`) segment before the commit, in the same repo, the hook runs `git add --dry-run` with the same pathspecs and the flags that change what gets selected (`-A` / `--all`, `-u` / `--update`, `-f` / `--force`, `--no-ignore-removal`), in that segment's folder. Git itself then answers which files the add would stage, honoring `.gitignore`, `.`, globs and `-f`, and the hook changes nothing. The hook reads those files:
   - **tracked:** their lines in `git diff` (working tree against the index), one call, filtered to those files
   - **untracked:** the whole file, read directly, as added lines
2. **`git commit -a` / `--all`:** all of `git diff` (unstaged changes to tracked files). Staged plus unstaged is what `-a` commits. The issue suggests `git diff HEAD`; this pair gives the same lines and also works before the first commit, when there is no `HEAD`.
3. **`git commit <path>…`, `--only`, `-i` / `--include`:** `git diff -- <paths>`, with the pathspecs as written, in the commit's folder.

Everything goes through `added_lines` and `find_secret` as today, so removals stay allowed, and the block reason and log check id (`secret`) don't change.

**The `.env` check** reads the file names from the same sources: staged, the dry-run list, and `git diff --name-only` for `-a` and commit paths. It runs on every commit, not only when the command contains `.env`. It matches `.env` and `.env.<anything>` except `.env.example`. Today it matches any name that starts with `.env`, but the command-line gate means `.envrc` never actually triggers it. Without the gate, `.envrc` (direnv) would start to block, so the name rule narrows to keep it passing. **This is decision 1 below.**

## Files to change

| File | Change |
|---|---|
| `.claude/hooks/enforce-laws.py` | New `git_add_dry_run(args, cwd)`: the files a `git add` would stage, or `[]` on any error. New `commit_pathspecs(args)`: `-a` and the pathspecs of one `git commit`, skipping option values (reuses `COMMIT_VALUE_FLAGS` and the cluster rules in `commit_skips_hooks`). New `commit_contents(segments, base, cwd)`: the diff text plus `(path, text)` pairs for untracked files, and the file names. The Law 14 block in `check_bash` uses it for the secret check and the `.env` check |
| `tests/test_enforce_laws.py` | New tests in `CommitSecretTests` (see Proof) |
| `CLAUDE_LAWS.md` | Law 32's Law 14 row: "the lines the commit adds, including what `git add`, `-a` or commit paths add in the same call", and "a `.env` file it adds". Version 2.36.1 |
| `RELEASES.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | v2.36.1, with the rules' token estimate |
| `docs/features/issue-187/plan.md` | This plan |

About 6 files and 200 lines.

## Order of work

1. Tests first, each failing on `main` for the right reason, done when they fail without the fix.
2. `commit_pathspecs`, `git_add_dry_run`, `commit_contents`, done when the new tests pass and the old ones still do.
3. The `.env` check on the same file list, done when its tests pass.
4. Law text, release files, done when `release_version.py check` and markdownlint pass.

## Edge cases

- **Unparsable command** (unbalanced quotes, a subshell, `bash -c`): the segment isn't recognised, so the hook falls back to the staged diff alone (fails open, as today).
- **`git add -p`, `-i`, `-e`:** `--dry-run` refuses them, so they add nothing to the check. Claude can't run interactive commands anyway.
- **A pathspec that matches nothing, or an ignored file without `-f`:** the dry run fails, and so would the real `git add`; nothing extra is read.
- **A `git add` after the commit,** or in a different repo than the commit's: not counted, because it can't change that commit.
- **`git add -A` over a huge untracked tree** (an unignored `node_modules`): files with a NUL byte in the first 8 KB are binary and skipped. Each file is read up to 1 MB, and at most 2,000 untracked files are read; the rest are not checked (fails open), so the hook stays fast.
- **File names with spaces, quotes or non-ASCII characters:** git prints them unescaped as `add '<path>'`, relative to the repo root, and the parser takes everything between the first and the last quote. A name with a line break isn't matched and is skipped.
- **`--pathspec-from-file`:** the commit reads all of `git diff`, a superset, rather than guessing which paths the file names.

## Proof

- **Tests to add** (in `CommitSecretTests`, with the fake secrets from #119):
  - `git add config.py && git commit -m "…"` with a secret in an untracked `config.py`: blocks, and the reason names the kind and `config.py`
  - the same with `config.py` already tracked and the secret unstaged: blocks
  - `git add -A && git commit`: blocks on an untracked file; an ignored file holding a secret doesn't block
  - `cd sub && git add f.txt && cd .. && git commit`: blocks (the add's own folder)
  - `git commit -am "…"` and `git commit --all -m "…"` with an unstaged secret in a tracked file: blocks
  - `git commit config.py -m "…"` and `git commit -m "…" -- config.py`: blocks
  - a plain `git commit` with an unstaged secret in another file: allowed
  - `git add a.txt && git commit` with an unstaged secret in `b.txt`: allowed
  - `git commit -m "…" && git add config.py` (add after the commit): allowed
  - `git add -A && git commit` with an untracked `.env`: blocks; with an untracked `.envrc`: allowed
  - removing a secret through `git commit -a`: allowed
  - a binary untracked file: allowed, and the check doesn't crash
- **Tests edited:** none. `test_a_staged_env_file_still_blocks_and_removing_one_doesnt` keeps its commands and results.
- **Commands that must pass:** `python3 -m unittest discover -s tests`, `python3 scripts/release_version.py check`, markdownlint, `python3 scripts/laws_cost.py --budget 33000`.
- **Visual evidence:** none, no UI change. The PR body says `Screenshots: not applicable`.

## Risks

- **The hook now runs `git add --dry-run` and reads files on every commit that has a `git add` in the same call.** → Read-only, bounded by the caps above, and one `git diff` call for all tracked files.
- **More blocks than before:** a secret that used to slip through now blocks, including in repos where a `git add -A && git commit` habit hid one. → That's the fix; the reason names the file, and removing it is never blocked.
- **The hook changes, so `update rules` asks you to approve its diff** after this merges (Law 28).

## Ruled out

- **Asking or blocking whenever `git add` and `git commit` share one call** ("split them into two calls"). It's simpler, but it adds a prompt or a block to the most common commit idiom, even when nothing is wrong, which teaches routing around the hook. Reading ahead costs one dry run.
- **Replaying `git add` into a temporary index** (`GIT_INDEX_FILE`). It's exact, but `git add` writes blobs into `.git/objects`, so a blocked secret would still land in the object store. `--dry-run` writes nothing.
- **Parsing pathspecs in Python** to find the files an add touches. That would mean re-implementing `.gitignore`, globs, `.` and `-f`; git's own dry run gets them right.
- **Replaying the user's `-c` options** in the hook's git calls: `-c core.fsmonitor=…` can run a command. Only `-C <dir>` is honored, through the segment's folder.

## Decisions for the owner

1. **The `.env` check runs on every commit and on the same file list,** and its name rule narrows to `.env` and `.env.*` (except `.env.example`), so `.envrc` keeps passing. Recommended: yes. It's the same gap, about 10 lines. The alternative is to leave the `.env` check as it is and open a separate issue.
2. **The caps for untracked files:** 1 MB per file, 2,000 files. Recommended as is. A lower file cap is faster; a higher one checks more of a large `git add -A`.
