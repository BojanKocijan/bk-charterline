# Plan — `dforge-update` installs tagged releases and asks before a hook change (#116)

Spec: [spec.md](./spec.md) (approved) · Gate tier: Significant · Issue: #116 · Roadmap: #123
Branches: `chore/pin-actions-to-shas`, `feat/tagged-updates-1-release-tag`, `feat/tagged-updates-2-dforge-update`, each targeting `main`, merged in that order
Work pile: judgment-heavy for the update function and its gate; delegable for the SHA pins and the tests
Approved-by: BojanKocijan, 2026-10-05, PR #159

## Design

### Release check and auto-tag (PR 2)

- **New `scripts/release_version.py`** (stdlib only):
  - `python3 scripts/release_version.py check` reads `**Version:**` from `CLAUDE_LAWS.md`, checks `plugin.json`, both versions in `marketplace.json` and a `## vX.Y.Z` heading in `RELEASES.md`, and prints `X.Y.Z`.
  - On a mismatch it names each file that disagrees and exits 1.
  - No other subcommands (Law 21).
- **New `.github/workflows/release-tag.yml`:**
  - `on: push: branches: [main], paths: [CLAUDE_LAWS.md]`. Job permissions `contents: write`; workflow default `contents: read`.
  - Steps: checkout (SHA-pinned, `fetch-depth: 0`, `fetch-tags: true`), `release_version.py check`. If `git rev-parse -q --verify refs/tags/vX.Y.Z` finds the tag, the job succeeds and does nothing. Otherwise it runs `git tag -a vX.Y.Z -m "Design Forge vX.Y.Z" $GITHUB_SHA && git push origin vX.Y.Z`, with the committer set to `github-actions[bot]`.
- Law 27's version-sync bullet: "the release-tag workflow tags the merge; Claude doesn't push release tags."

### The update function (PR 3)

The function stays a shell function in the rc file, not a script in the clone, so `git checkout` never changes the file that's running. It has to run in **both zsh and bash**: plain `[ ]` tests, `local`, `printf` + `read -r reply` (no `read -p`, which differs in zsh), and no arrays.

```text
dforge-update [--main | --help]
  1. clone check (as today)
  2. local changes:  git status --porcelain --untracked-files=no  → non-empty: name them, return 1
  3. git fetch --quiet --tags origin  → failure: "dforge: fetch failed, nothing changed", return 1
  4. target:
       --main  → origin/main
       default → first of `git tag --list 'v*' --sort=-v:refname` matching ^v[0-9]+\.[0-9]+\.[0-9]+$
                 none → warn "no release tags yet, following main" and use origin/main
  5. same commit as HEAD → "already on <label>", run install.sh, done
     default mode and target is an ancestor of HEAD (older) → print both versions, say --main or the next
     release moves it, return 0 with nothing changed
  6. hook gate: git diff --stat HEAD <target> -- .claude/hooks scripts/ai_tools.py install.sh .claude/settings.json
       empty → continue
       non-empty and [ -t 0 ] and [ -t 1 ] → stat + full diff (less -FRX if present), "Apply this hook change? [y/N]",
                                             not y/yes → "nothing changed", return 1
       non-empty, no terminal → stat + full diff, "the hook changed. Nothing was applied. Run dforge-update in
                                your own terminal to review and approve it.", return 1
  7. default: git checkout --quiet --detach <tag>
     --main:  git checkout --quiet main && git merge --quiet --ff-only origin/main (fails → return 1)
  8. DFORGE_UPDATE=1 bash install.sh, then "dforge: ready (DESIGN_FORGE vX.Y.Z, tag vX.Y.Z | main)."
```

- **`install.sh` on a detached clone** (run by hand, not through `dforge-update`): it currently runs `git pull --ff-only`, which fails on a detached HEAD. When `git symbolic-ref -q HEAD` fails, it skips the pull and prints "On release vX.Y.Z; run dforge-update to update."
- **Session-start check** (`CLAUDE.md` step 1, Law 28): `git -C ~/.design-forge ls-remote --tags origin 'v*'`, take the highest `vX.Y.Z` and compare it with the loaded version. The fallback (last fetch older than 24 h) stays.

## Files to change

| File | Change | PR |
|---|---|---|
| `.github/workflows/hook-tests.yml`, `markdown-lint.yml` | `uses:` → `@<SHA> # vN.N.N`, SHAs resolved with `gh api repos/<owner>/<action>/commits/<tag>` | 1 |
| `scripts/release_version.py` | New: `check` | 2 |
| `tests/test_release_version.py` | New: match, each mismatch named, missing `RELEASES.md` heading, unreadable file | 2 |
| `.github/workflows/release-tag.yml` | New, SHA-pinned | 2 |
| `CLAUDE_LAWS.md` | Law 27 tagging bullet | 2 |
| `install.sh` | New `dforge-update` function; detached-clone path in step 2 | 3 |
| `tests/test_dforge_update.py` | New (cases under Proof) | 3 |
| `CLAUDE.md` | Session-start step 1 compares with the newest tag | 3 |
| `CLAUDE_LAWS.md` | Law 28 (newest release tag), Law 32 "Where it lives" (the update gate) | 3 |
| `README.md` | Install and update sections: tags, `--main`, the gate, the detached HEAD | 3 |
| `RELEASES.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | v2.28.0, version sync. The PR 2 workflow tags it on merge | 3 |

Expected sizes: PR 1 ~10 lines, PR 2 ~150, PR 3 ~350. All under Law 31's 400-line ceiling. If PR 3 goes over, the docs move into a PR 4.

## Order of work

1. **PR 1, SHA pins:** both workflows. Done when CI is green on the PR and every `uses:` line matches `@[0-9a-f]{40} # v`.
2. **PR 2, release check and workflow:** done when the unit tests pass and the workflow passes `actionlint` if available (otherwise a YAML parse). Merged before PR 3, so PR 3's merge is the workflow's first real run.
3. **PR 3, update function:** done when the tests pass under bash (and zsh where installed), `bash -n install.sh` passes, and `claude plugin validate .` reports nothing new.
4. **Independent review:** a fresh-context subagent reviews PR 2 and PR 3 together against the spec and this plan before PR 3 opens. Findings get fixed or brought to you.
5. **Your checks after merge**, listed in the deploy steps:
   - the `v2.28.0` tag appears by itself after PR 3 merges;
   - the first `dforge-update` (still the old function) then the second one (the new function) lands on `v2.28.0`;
   - one gate prompt in your own terminal.

## Proof

- **`tests/test_dforge_update.py`.** Each test builds a fixture:
  - a bare "origin" repo with commits and tags, a stub `install.sh` that writes a marker file, `CLAUDE_LAWS.md` with a version line and a stub `.claude/hooks/enforce-laws.py`;
  - a clone at `<tmp HOME>/.design-forge`;
  - the `dforge-update` function extracted from `install.sh` between its `design-forge:fn` markers and run with `bash -c`, and `zsh -c` when `zsh` is on the path. `HOME` points at the temp dir.
  - Cases:
    - from `main` → newest tag, detached, summary names it; install marker written
    - from an older tag → newest tag
    - `--main` from a detached tag → on `main` at `origin/main`
    - already on the newest tag → "already on", install marker written, HEAD unchanged
    - no tags → warning, ends on `origin/main`
    - target older than HEAD (clone on `main` past the last tag) → nothing changes, return 0
    - version order: `v2.10.0` beats `v2.9.0`; `v2.10.0-rc1` and `vfoo` are ignored
    - hook change, no terminal (stdin a pipe) → diff printed, exit 1, HEAD unchanged, no install marker
    - hook change with a terminal (`pty` from the standard library): `n` → unchanged; `y` → applied
    - law-only change → applied with no question
    - local change to a tracked file → refused and named, HEAD unchanged; a changed gitignored `projects.yaml` doesn't count
    - fetch failure (origin removed) → message, HEAD unchanged
    - `--help` → usage, exit 0; `--bogus` → usage, exit 2
    - `install.sh` run directly on a detached clone → no pull error, prints the "On release" line
- **Existing tests:** none edited.
- **Commands that must pass:** `python3 -m unittest discover -s tests -v`, `bash -n install.sh`, `python3 -m json.tool` on both manifests, markdownlint, `claude plugin validate .`.
- **Visual evidence:** none (no UI). Screenshots: not applicable.

## Risks

- **The first update after shipping still runs the old function**, which pulls `main`; `install.sh` then installs the new function → the deploy steps say to run `dforge-update` twice. The README says so too.
- **Moving a clone that's on `main` onto a tag looks like a downgrade** when `main` is ahead of the last tag → step 5 never downgrades; the auto-tag after PR 3 makes the newest tag equal to `main` at that moment.
- **`less` hiding the prompt** → it's only used with a terminal, with `-F` (quit if one screen) and `-X` (keep the output on screen).
- **zsh vs bash differences** → tests run both when zsh is present. CI runs bash only, which is noted in the PR, and the zsh run is local proof.
- **The workflow token can't push a tag.** The repo's default token permission is `read` (checked 2026-10-05). The job's own `permissions: contents: write` overrides that default, so no setting change is needed. If an org or repo policy blocks it later, the workflow fails loudly and no tag is made.
- **A user editing the clone by hand** → step 2 refuses with the file names instead of losing the edits.

## Ruled out

- **The update logic in a script inside the clone:** `git checkout` could rewrite the script while bash is still reading it.
- **A test-only flag to fake a terminal:** a flag Claude could pass would weaken the gate. Tests use a real pseudo-terminal.
- **Signed tags:** out of scope in the spec.
- **A separate CI job for the shell tests:** the Python tests run them inside the existing Hook Tests job.
