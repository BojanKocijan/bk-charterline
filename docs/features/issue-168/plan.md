# Plan — one update run lands on the newest release (#168)

Spec: [#168](https://github.com/BojanKocijan/design-forge/issues/168) (the issue) · Gate tier: Standard · Branch: `fix/one-run-update` · Issue: #168
Work pile: delegable (small, specified, machine-verifiable)
Approved-by: BojanKocijan, 2026-10-06, chat

## Files to change

| File | Change |
|---|---|
| `install.sh` | New step 2b after the clone/pull step: when the clone is on a branch, has no local edits to tracked files, and `HEAD` is exactly the newest local `vX.Y.Z` tag's commit, `git checkout --detach <tag>`. Otherwise do nothing. Runs on every install path, including the old function's `DFORGE_UPDATE=1` re-run |
| `CLAUDE.md` | `update rules` runs `"$SHELL" -ic dforge-update`, so the function comes from the rc file, not the session's cached copy |
| `README.md` | Replace "run `dforge-update` twice" with the one-run behavior |
| `tests/test_dforge_update.py` | `InstallScriptTests` cases (see Proof) |
| `RELEASES.md`, `CLAUDE_LAWS.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | v2.28.1, version sync |

## Order of work

1. Step 2b and its tests. Done when the suite passes under bash 3.2.
2. `CLAUDE.md`, README, release. Done when `release_version.py check` prints `2.28.1` and markdownlint is clean.

## Proof

- **Tests:** the real `install.sh` against a temp HOME, with:
  - on `main` at the newest tag → ends detached on the tag;
  - `main` ahead of the newest tag → stays on `main`;
  - local edits to a tracked file → stays on `main`;
  - no tags → stays on `main`;
  - already on a tag → unchanged, and prints the existing "On release" line.
- **Commands:** `python3 -m unittest discover -s tests`, `/bin/bash -n install.sh`, `python3 scripts/release_version.py check`, markdownlint.
- **Visual evidence:** none (no UI).

## Risks

- **A tag created after the pull** (as in the 2026-10-05 Actions outage): that run stays on `main`, and the next run moves it. That's acceptable; nothing is lost.
- **`"$SHELL" -ic` loads the user's whole interactive rc** (prompts, plugins). It's slower, and a noisy rc adds output. Without a terminal, the gate still stops hook changes, so nothing gets past it.
- **`set -euo pipefail` in `install.sh`:** the tag pipeline ends in `|| true`, and every check fails safe to "do nothing".

## Ruled out

- **Fetching tags in `install.sh`:** it would add a network call to every install. `git pull` already brings the tags that point into the pulled history.
- **Telling users to start a new session after updating:** easy to forget, and the stale function skips the gate in the meantime.
