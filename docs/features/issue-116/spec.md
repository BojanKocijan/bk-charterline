# Spec — `dforge-update` installs tagged releases and asks before a hook change (#116)

Intent: [#116](https://github.com/BojanKocijan/design-forge/issues/116) (the issue is the intent) · Roadmap: #123
Design: none (no UI; shell function, CI workflows)
Approved-by: <pending>

## Decisions already taken (owner, 2026-10-05, chat)

- **Tags come from a GitHub Action.** A workflow tags `main` when a merge changes the version. Claude never pushes release tags after this one-time `v2.26.0` tag.
- **No terminal, no hook change.** When `dforge-update` can't ask (Claude runs it through Bash), it shows the diff, applies nothing and tells you to run it in your own terminal.
- **"Hook change" means everything the hook runs:** `.claude/hooks/`, `scripts/ai_tools.py`, `install.sh` and `.claude/settings.json`.

## Behavior

### `dforge-update` (default: newest release)

1. Checks that `~/.design-forge` is a git clone, as today.
2. Refuses if the clone has local changes to tracked files (`git status --porcelain --untracked-files=no` is not empty), and names them. The gitignored data files (`projects.yaml`, `hook-log*`, `ai-tools.json`, …) never count.
3. `git fetch --tags --quiet origin`. If the fetch fails, it says so and stops: nothing changes.
4. Picks the target: the highest `vX.Y.Z` tag by version order (`git tag --list 'v*' --sort=-v:refname`, first match of `^v[0-9]+\.[0-9]+\.[0-9]+$`).
   - No tag at all: warns once and falls back to `origin/main`, as `--main` does.
   - Target is the commit already checked out: prints `dforge: already on vX.Y.Z.`, re-runs `install.sh` as today (so a missing registration is repaired) and stops.
   - Target is **older** than what's checked out (the clone was following `main` past the last release): prints both versions and stays put. It says `--main` keeps following `main`, and that the next release tag will move it. It never downgrades silently.
5. **Hook-change gate:** `git diff --stat` and `git diff` of the hook paths between `HEAD` and the target.
   - No change in those paths: continue.
   - A change, with a terminal (`[ -t 0 ]`): print the stat and the diff (through `less -FRX` when available), then ask `Apply this hook change? [y/N]`. Anything but `y`/`yes` stops with nothing changed.
   - A change, no terminal: print the stat and the diff, then `dforge: the hook changed. Nothing was applied. Run dforge-update in your own terminal to review and approve it.` Exit code 1.
6. `git checkout --quiet --detach <tag>`. The clone sits on a detached HEAD at the tag.
7. Re-runs `install.sh` with `DFORGE_UPDATE=1`, as today, and prints `dforge: ready (DESIGN_FORGE vX.Y.Z, tag vX.Y.Z).`

### `dforge-update --main`

Follows `main` as today: `git checkout --quiet main` (from a detached HEAD too), `git pull --ff-only`, the same hook-change gate between `HEAD` and `origin/main`, then `install.sh`. The summary says `(DESIGN_FORGE vX.Y.Z, main)`.

### `dforge-update --help`, unknown flags

`--help` prints the two modes in four lines. An unknown flag prints the same and exits 2. No other flags (Law 21).

### `update rules` (in-session trigger)

Unchanged: Claude runs `dforge-update`. When it stops on a hook change, Claude reports the stat lines and asks you to run `dforge-update` in your terminal. Claude never runs it with `--main` unless you asked for that.

### Session-start update check (Law 28)

Compares the loaded version with the **newest tag** on the remote (`git ls-remote --tags origin 'v*'`) instead of `origin/main`, so you're told about releases, not every merge.

### Auto-tag workflow (`.github/workflows/release-tag.yml`)

- **Trigger:** `push` to `main` with a path filter on `CLAUDE_LAWS.md`.
- **Steps:**
  1. Read `**Version:**` from `CLAUDE_LAWS.md`.
  2. Check that `.claude-plugin/plugin.json` and both versions in `.claude-plugin/marketplace.json` match it, and that `RELEASES.md` has a `## vX.Y.Z` heading. A mismatch fails the job and names the file. Nothing is tagged.
  3. If tag `vX.Y.Z` already exists, succeed without changing it. It never moves or deletes a tag.
  4. Otherwise create an annotated tag `vX.Y.Z` on the pushed commit, with the message `Design Forge vX.Y.Z`, and push it.
- **Permissions:** `contents: write` for that job only. It uses the built-in `GITHUB_TOKEN`, no new secret.

### Actions pinned to SHAs

Every `uses:` line in `.github/workflows/*.yml` becomes `owner/action@<40-char SHA> # vN.N.N`. Dependabot (already configured for `github-actions`) updates SHA pins and their comments.

### Docs

- README install and update sections: tags by default, `--main`, the hook-change gate.
- Law 28: "newest release tag" instead of `main`.
- Law 27: tagging is done by the workflow.
- Law 32 "Where it lives": a hook change waits for your yes in a terminal.
- `RELEASES.md` entry and version sync (v2.27.0).

## Acceptance criteria

- [ ] With tags `v2.26.0` and `v2.27.0` on the remote, `dforge-update` from `main` or from `v2.26.0` ends on `v2.27.0` (detached), and prints that version.
- [ ] `dforge-update --main` ends on `main` at `origin/main`, also from a detached HEAD.
- [ ] A hook-path change between `HEAD` and the target prints its diff. Without a terminal, it exits 1 and the checkout is unchanged. With a terminal, `n` leaves it unchanged and `y` applies it.
- [ ] A law-only or docs-only change applies without a question.
- [ ] No tags: a warning, then it behaves as `--main`.
- [ ] A fetch failure or local changes stop it with the checkout unchanged.
- [ ] A target older than the current checkout doesn't downgrade.
- [ ] The workflow tags `vX.Y.Z` once when the version changes on `main`, fails on a version mismatch, and leaves an existing tag alone.
- [ ] Every `uses:` line is pinned to a SHA with a version comment.
- [ ] README, Laws 27, 28 and 32, and `RELEASES.md` are updated, and `bash -n install.sh` passes.
- [ ] Tests: a shell test script runs `dforge-update` against a local bare repo with tags (fixture under a temp `HOME`) for each criterion above, and runs in the Hook Tests CI job.

## Policy check

- Component library, accessibility, copy: not applicable (no UI). Messages follow the existing `dforge:` style: one line, says what happened and what to do.
- Laws:
  - Law 7: the workflow pushes a tag, never to `main`, and never merges.
  - Law 14: no new secret.
  - Law 21: two modes, no other flags.
  - Law 32: the hook's "`dforge-update` stays free" still holds; the gate lives in `dforge-update` itself.
- Conflicts flagged for the owner:
  - The installed clone moves from the `main` branch to a detached HEAD. `git -C ~/.design-forge pull` by hand then fails until `dforge-update --main` or `git checkout main`. The README says so.
  - The first `dforge-update` after this ships is still the **old** function, which pulls `main`. The new function only takes over on the run after that.

## Out of scope

- Signed tags or commit-signature verification.
- Pinning `install.sh`'s first clone to a tag (it still clones `main`; the first `dforge-update` moves it to the newest tag).
- Backfilling tags for v2.21.0–v2.25.0.
- The plugin install path (`/plugin`), which Claude Code updates on its own.
