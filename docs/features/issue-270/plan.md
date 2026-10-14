# Plan — A SessionStart hook runs the session-start checks (#270)

Spec: [spec.md](./spec.md) · Gate tier: Significant · Branches: `docs/session-start-hook-plan`, `feat/session-start-hook-1a-local`, `feat/session-start-hook-1b-network`, `feat/session-start-hook-2-register`, `feat/session-start-hook-3-rules` · Issue: #270
Work pile: PRs 1a and 1b are delegable (a script and its tests, checked by machine); PRs 2 and 3 are judgment-heavy (install paths, rule text). All built in this session.
Plan page: https://claude.ai/artifact/3AugBiJ42e5kt8VeUYJR84
Approved-by: <pending> (re-approval after the split below; first approved BojanKocijan, 2026-10-14, chat)

## Change after approval (2026-10-14)

PR 1 came out at 853 lines: the script is 299, its tests 297, and the intent, spec and plan 253. That is over Law 31's 400-line ceiling, so the first estimate was wrong. On the owner's choice, PR 1 splits into three: the docs, the local checks, then the network checks. PRs 2 and 3 don't change.

## Shape: five stacked PRs

Each PR leaves `main` working and stays under Law 31's 400 lines.

| PR | What | Why on its own |
|---|---|---|
| 0/5 `docs(plan)` | `intent.md`, `spec.md` and `plan.md` for #270 (about 255 lines). | The approved decisions are on `main` before any code. |
| 1a/5 `feat(hook)` | `session_start.py` with the local checks (version, project, `projects.yaml`, `PROJECT_KNOWLEDGE.md`, the marker, the block) and their tests (about 360 lines). `GitHub: unknown` until 1b. Not registered. | The logic can be reviewed and tested with no effect on any session. |
| 1b/5 `feat(hook)` | The network checks: newest release, GitHub login, open PRs, in parallel with 3 s limits and process-group kill, and their tests (about 240 lines). Not registered. | The part that can hang gets its own review. |
| 2/5 `feat(install)` | Register it: this repo's `.claude/settings.json`, `install.sh`, the plugin's new `hooks/hooks.json`, the update diff paths, GUARDRAILS, README | Turning it on is a separate, reversible step that `update rules` asks you to approve. |
| 3/5 `docs(laws)` | The rule text: `CLAUDE.md` session start shrinks to "print the hook's block", plus the fallback. Laws 16, 20, 25 and 28 move their steps to "when code work starts". | The rule change you flagged gets its own review (spec decision). |

## Files to change

| PR | File | Change |
|---|---|---|
| 0 | `docs/features/issue-270/` | `intent.md`, `spec.md`, `plan.md` |
| 1a | `.claude/hooks/session_start.py` | **New.** Stdlib only, like `persona_log.py`. Reads the event from stdin. Returns nothing unless `source` is `startup` or `clear` and no marker exists for this `session_id`. Writes the marker `bk-charterline-session-start-<session_id>` in `tempfile.gettempdir()` (atomic create). Runs the local checks from the spec (1, 3–7, 10, 11). Builds the block and prints `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": …}}`. Any exception → exit 0 with no output. The block is cut to 1,900 characters. |
| 1a | `tests/test_session_start.py` | **New.** Unittest, with a fake `HOME` and a temporary git repo: the local cases from Proof. |
| 1a | `RELEASES.md` | `Unreleased` entry |
| 1b | `.claude/hooks/session_start.py` | The network checks (2, 8, 9): `git ls-remote`, `gh api user` and `gh pr list` in a `ThreadPoolExecutor`, each with a 3 s timeout; a timed-out command's process group is killed so a hung child can't hold the pipe. PR titles are cut to 60 characters, and PR lines are dropped first when the block runs long. |
| 1b | `tests/test_session_start.py` | `PATH` stubs for `gh` and `git ls-remote`: the network cases from Proof. |
| 1b | `RELEASES.md` | The `Unreleased` entry updated |
| 2 | `.claude/settings.json` | A `SessionStart` entry, matcher `startup\|clear`, `timeout: 10`, with the #268 fallback: installed copy, else the repo copy, else nothing |
| 2 | `install.sh` | Registers the same `SessionStart` entry in `~/.claude/settings.json`, the way it registers `enforce-laws.py` (idempotent) |
| 2 | `install.sh` (`charterline-update`) | Adds `hooks/hooks.json` to the paths it diffs and asks about (Law 28) |
| 2 | `hooks/hooks.json` | **New.** The plugin's `SessionStart` entry, using `"${CLAUDE_PLUGIN_ROOT}"/.claude/hooks/session_start.py` |
| 2 | `tests/test_update.py` | Install registers the entry once (run twice to check); a change to `hooks/hooks.json` asks for approval |
| 2 | `knowledge/GUARDRAILS.md`, `README.md`, `RELEASES.md` | The new hook: what it reads, that it never blocks, and how to switch it off |
| 3 | `CLAUDE.md` | "Session-start behavior" becomes: print the hook's block; if there's no block, the fallback from the spec. Step 6's confirmation format stays. |
| 3 | `CLAUDE_LAWS.md` | Laws 16, 20, 25 and 28: who runs the check, and "when code work starts" for the steps that change things (spec, Policy check) |
| 3 | `tests/test_laws_structure.py` | Only if a heading it checks changes (Law 25's title) |
| 3 | `RELEASES.md` | `Unreleased` entry with the measured token cut |

## Order of work

1. **PR 1 (built 2026-10-14, before the split):** the tests were written first and failed (23 of 23), then the script; 24 tests pass, the full suite passes, and the hook prints the block for this repo in 0.7 s. The split cuts that work into PRs 0, 1a and 1b, with no new logic.
2. Open PR 0 (docs), then 1a and 1b, each stacked on the one before. For each: `/code-review`, fix the findings, then open it with the stack in its body — done when CI is green on each.
3. **PR 2,** branched from PR 1: registration and docs — done when `claude plugin validate .` passes, `test_update.py` passes, and a cloud session in this repo (which uses the repo copy) prints the confirmation with 0 tool calls before it. The transcript goes in the PR.
4. **PR 3,** branched from PR 2: rule text — done when `laws_cost.py` shows the cut, the laws structure test passes, and the PR names each law sentence it changes.
5. Your merge order: 0 → 1a → 1b → 2 → 3. After 2 merges, `update rules` asks you to approve the hook change (Law 28).

## Proof

- **Tests to add (`tests/test_session_start.py`):**
  - `startup` in a temp git repo with `PROJECT_KNOWLEDGE.md` (§1 and §11 filled in) and a fake `projects.yaml` → the block has every confirmation line, and its text matches the spec's example shape.
  - `resume`, `compact`, `fork` → no output. A second `startup` with the same `session_id` → no output (marker).
  - Read-only: `git status --porcelain`, `git for-each-ref` and a hash of every file in the temp repo are the same before and after.
  - Network stubs that sleep 10 s → finishes in under 5 s, with no update or PR line.
  - `gh` fails with `CLAUDE_CODE_REMOTE=true` → `GitHub: via connector`; without it → `GitHub: unauthenticated`.
  - Language unset, `projects.yaml` missing, `projects.yaml` broken, project not registered (shows the next free port), no `PROJECT_KNOWLEDGE.md`, not a git repo → the right lines each.
  - 10 open PRs with 200-character titles → block under 2,000 characters.
  - Malformed stdin → exit 0, no output.
- **Existing tests edited:** `tests/test_update.py` (PR 2) gets new cases, and none of its current cases change. `tests/test_laws_structure.py` (PR 3) changes only if Law 25's heading changes; it will be named in the PR.
- **Commands that must pass:** `python3 -m unittest discover -s tests`, `npx markdownlint-cli2` on the changed `.md` files, `python3 scripts/laws_cost.py --budget 28000`, and `claude plugin validate .` (PR 2).
- **Visual evidence:** none. No UI (Law 34). The proof is the session transcript showing the confirmation with 0 tool calls before it.

## Risks

- **A slow network delays the first reply** → each network check has a 3 s limit and they run in parallel; the hook timeout is 10 s; a test fakes a hang.
- **The confirmation shows twice** (global install, plugin and repo registration) → the per-session marker; a test runs the hook twice.
- **The hook crashes or isn't installed** → no output, never blocks (a `SessionStart` hook can't); `CLAUDE.md` keeps the fallback (PR 3).
- **The plugin's first hook breaks plugin validation** → `claude plugin validate .` in PR 2's proof. The path uses `"${CLAUDE_PLUGIN_ROOT}"` in quotes.
- **The update approval misses the new plugin file** → PR 2 adds `hooks/hooks.json` to the diffed paths, and a test checks it.
- **Claude still runs the old checks** until PR 3 lands → harmless (the same result, just slower). PR 3 is what removes them.
- **The guardrail hook asks before edits to `.claude/hooks/` or `.claude/settings.json`** (Law 32) → expected; you approve those prompts while I build PRs 1 and 2.

## Ruled out

- **Doing the steps that change things in the hook** (pull, register, create `CLAUDE.md`): owner decision, read-only only.
- **A shell script instead of Python:** the other hooks are Python with stdlib only, and the YAML-free `projects.yaml` parsing already exists in Python (`scripts/my_metrics_data.py`).
- **One PR:** over 400 lines, and it would mix a mechanism with a rule change (Law 31).
- **PR 1 as one PR with a recorded size exception:** about 600 lines of code and tests; the owner chose the split.
- **Running the network checks one after another:** worst case 9 s, not 3 s.
- **`git fetch` to report "main is N commits behind":** a network write to `.git`. Law 5 pulls before every branch anyway.
