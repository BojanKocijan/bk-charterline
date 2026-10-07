# Plan — rename Design Forge to BK Charterline (#199)

Spec: [spec.md](spec.md) · Gate tier: Significant · Branches: `feat/rename-1-paths` … `feat/rename-5-release` · Issue: #199
Work pile: judgment-heavy (every install depends on it), built in this session, not split across agents
Approved-by: <pending>

## How it ships

Nothing reaches users until the last PR. `dforge-update` installs the newest release tag, and only PR 5 bumps the version. So PRs 1 to 4 merge to `main` one by one, each green and each leaving a working install, and users get them all at once as v3.0.0. Every PR is opened against `main`, stacked by commits, and says "merge in order".

| PR | Branch | What | Size |
|---|---|---|---|
| 0 | `docs/issue-199-spec` | This plan and the spec | ~250 |
| 1 | `feat/rename-1-paths` | Code finds the install under either name; the hook guards both | ~300 |
| 2 | `feat/rename-2-install` | `install.sh` installs the new name and moves an old install; `charterline-update` and the `dforge-update` pointer | ~350 |
| 3 | `feat/rename-3-rules` | The rules files: `CLAUDE.md`, `CLAUDE_LAWS.md`, `AGENTS.md`, including what `update rules` runs | ~250 |
| 4 | `feat/rename-4-docs` | README, knowledge, skills, agents, the other docs and templates | ~350 |
| 5 | `feat/rename-5-release` | The plugin manifests, a test that only history keeps the old name, release v3.0.0 | ~150 |

## PR 1: code finds the install under either name

| File | Change |
|---|---|
| `.claude/hooks/rules_home.py` (new) | `rules_home()`: `~/.bk-charterline` when it exists, else `~/.design-forge`. `INSTALL_NAMES` lists both. It imports nothing from the repo, so there's no import cycle. It lives under `.claude/hooks/`, where `dforge-update` shows the diff (Law 28) |
| `.claude/hooks/enforce-laws.py` | The installed-clone guardrail, its data-file exceptions and the git check cover both paths, after resolving links. `APPROVE_RE` accepts `charterline-update` or `dforge-update`. Its messages use the new names |
| `.claude/hooks/hook_log.py`, `scripts/ai_tools.py`, `scripts/ai_inventory.py` | Personal files under `rules_home()` instead of a fixed `~/.design-forge` |
| `tests/test_enforce_laws.py`, `tests/test_ai_tools.py`, `tests/test_ai_inventory.py`, the hook-log tests | Each case runs under the new name, the old name, and the old name as a link to the new one |

**Done when:** a fake home with only `~/.design-forge`, only `~/.bk-charterline`, or both with the link all pass. `charterline-update --approve` asks.

## PR 2: the install and the move

| File | Change |
|---|---|
| `install.sh` | New name and URL; new block markers; the hook registered at the new path; `charterline-update` in the shell rc file; `dforge-update` as a one-release pointer. The move, steps 1 to 7 of the spec, each checking before it acts. `~/.claude/settings.json` gets a backup (`settings.json.bk-charterline.bak`) before its hook entries are re-pointed, and only entries whose command is our hook change |
| `tests/test_dforge_update.py` → `tests/test_update.py` | A fake home: an install on v2.36.x with every personal data file, then `update rules` through the old function. It ends under the new name with every file byte for byte. A second run changes nothing. Both folders present, or local edits: nothing moves. Another tool's settings entries stay byte for byte |

**Edge cases:**
- **The move runs from inside the folder it moves.** `bash` keeps reading `install.sh` through its open file, so the script switches to the new path only after the move.
- **An open shell still has the old function.** Its last line reads `CLAUDE_LAWS.md` through the old-path link, so it still works; a new shell gets `charterline-update`.
- **A failed step stops the install,** names the step and how to finish it by hand, and leaves the old name working.

**Done when:** the tests pass, and `bash install.sh` in a throwaway home (a temp `HOME`) moves a real v2.36.2 clone end to end.

## PR 3: the rules files

`CLAUDE.md`, `CLAUDE_LAWS.md`, `AGENTS.md`: the name, the paths, the update command, the `Rules loaded: BK CHARTERLINE v…` line and the "Design Forge update available" line. The `update rules` trigger runs `"$SHELL" -ic charterline-update` when that function exists, else `dforge-update`.

**Done when:** `laws_cost.py --budget 33000` passes and markdownlint is clean. The rules' token count goes in the PR.

## PR 4: the docs

`README.md`, `CONTRIBUTING.md`, `FOR_COMPANIES.md`, `docs/MAINTAINER.md`, `knowledge/*.md`, `skills/*/SKILL.md`, `agents/*.md`, `.github/ISSUE_TEMPLATE/*`, the PR template and `projects.example.yaml`. The README gets a short "Renamed from Design Forge" note at the top. If this goes past 400 lines, it splits into 4a (README and the top-level docs) and 4b (knowledge, skills, agents).

**Done when:** markdownlint is clean and every link resolves.

## PR 5: the release

| File | Change |
|---|---|
| `.claude-plugin/plugin.json`, `marketplace.json` | Name `bk-charterline`, the new URLs, v3.0.0 |
| `CLAUDE_LAWS.md` | Version 3.0.0 |
| `RELEASES.md` | `## v3.0.0`: the new name; `update rules` handles the move; plugin users remove `design-forge` and add `bk-charterline`; the old path link and `dforge-update` pointer last one release; the rules' token count |
| `tests/test_old_name.py` (new) | The old name appears only in history (release notes before v3.0.0, `docs/features/`), the migration code and its tests, and the README's rename note |

**Done when:** `release_version.py check` passes at `3.0.0` and the whole suite is green.

## Manual steps for you (Law 35)

1. ~~Rename the repo on GitHub~~ (done, 2026-10-07).
2. Merge PRs 0 to 5 in order. Nothing reaches users before PR 5.
3. After PR 5, the Release Tag workflow tags `v3.0.0`. Then type `update rules` and approve the hook diff when asked.
4. Check: the session starts with `Rules loaded: BK CHARTERLINE v3.0.0`; `ls -la ~ | grep -e charterline -e design-forge` shows the new folder and the old name as a link.
5. If you use the plugin install: remove `design-forge`, then add `bk-charterline`.
6. Optional: rename your local checkout folder. If you do, move Claude's project memory folder too (I'll give the exact command then).
7. Before the page launches: a trademark search for "BK Charterline" (USPTO, EUIPO, BOIP).

## Proof

- **Tests:** as listed per PR, all run with a temp `HOME`, so no test touches your real install.
- **An end-to-end run:** a copy of a v2.36.2 clone in a temp home, moved by PR 2's `install.sh`. The output goes in the PR.
- **Commands:** `python3 -m unittest discover -s tests`, markdownlint, `release_version.py check`, `laws_cost.py --budget 33000`.
- **Visual evidence:** none, no UI. `Screenshots: not applicable`.

## Risks

- **The move breaks an install.** → Each step checks first and can run twice; `settings.json` is backed up; the old-path link stays for v3.0.0; the end-to-end run proves it before release.
- **A session running during the update** still has the old hook path. → The link keeps that path valid.
- **Old-name references left behind.** → PR 5's test fails on any current file that still uses it.
- **Two open #177 PRs (#196, #197) mention the old name.** → They're internal (a docstring, generated data). PR 4 or the page PRs update them.

## Ruled out

- **One big PR:** about 1,600 lines across 60 files; nobody can review that (Law 31).
- **Renaming history:** past records would stop matching their commits and PRs (spec).
- **Keeping `~/.design-forge` as the real folder with a new name on top:** the old name would stay in every path, which is what the rename removes.
- **Copying the folder instead of moving it:** two clones would drift, and the hook would guard the wrong one.
