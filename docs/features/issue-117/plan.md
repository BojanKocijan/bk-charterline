# Plan — the hook guards the guardrails (#117)

Spec: [spec.md](./spec.md) (approved) · Gate tier: Significant · Branch: `feat/guardrail-tamper` · Issue: #117 · Roadmap: #123
Work pile: judgment-heavy for the guard boundaries; delegable for the checks and tests
Approved-by: <pending>

## Design

- **One script, two matchers.** `enforce-laws.py` keeps handling `Bash`, and also handles `Edit`, `Write`, `MultiEdit` and `NotebookEdit` (the path comes from `file_path`, or `notebook_path` for notebooks).
- **Two decisions:**
  - `block(reason, check)`: exit 2, unchanged.
  - New `ask(reason, check)`: raises `Asked`. `main()` prints `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": …}}` and exits 0. If the live mode test (below) finds a mode where `"ask"` doesn't prompt, `main()` returns `"deny"` with the spec's message for that mode instead, keyed on the payload's `permission_mode` field (its presence is confirmed in the same test).
- **`is_protected(path)`:** `realpath` of the target, compared with the protected set from the spec. The exclusions under `~/.design-forge` are `hook-log*`, `ai-inventory*`, `ai-tools.json`, `projects.yaml` and `knowledge/PATTERNS.md`. A path that can't be resolved counts as not protected (fail open).
- **Bash checks**, run on heredoc-stripped text per segment, using the existing `split_segments` and `resolve_cwd`:
  - `no-verify`: `git commit` with `--no-verify` or a short flag cluster containing `n` (`-n`, `-an`); `git push --no-verify`.
  - `force-push-default`: `git push` with `--force`, `-f`, `--force-with-lease[=…]`, `--force-if-includes` or a `+`-prefixed refspec, where `push_targets_default()` (existing) says the target is the default branch.
  - `guardrail-write`: a segment whose command is a write verb (`tee`, `sed -i`, `perl -i`, `cp`, `mv`, `ln`, `install`, `rm`, `unlink`, `truncate`, `chmod`) with a protected path argument, or any segment with `>` / `>>` redirection to a protected path. Arguments are resolved against the segment's cwd and `~` is expanded.
  - `tracked-delete`: `rm`, `unlink` or `git rm` (not `--cached`) whose arguments match tracked files, checked with `git ls-files -- <arg>` in that cwd (non-empty output means tracked). Covers directories and pathspecs.
- **Logging:** `hook_log.append_block()` gains `record_type="block" | "ask"`, and `log_block()` passes it. `--summary` counts asks separately.

## Files to change — PRs all targeting `main`, stacked by commits

**PR 0 — artifacts:** `spec.md` and `plan.md`.

**PR A — deny checks** (about 140 lines): `enforce-laws.py` (`no-verify`, `force-push-default`) and their tests in `tests/test_enforce_laws.py`.

**PR B — ask: guardrail files** (about 330 lines):
- `enforce-laws.py`: `Asked` and `ask()`, the `main()` dispatch by tool, `is_protected`, Edit/Write handling, `guardrail-write`.
- `hook_log.py`: `record_type`, and asks in `--summary`.
- Tests.
- `install.sh`: registers a second `PreToolUse` entry, matcher `Edit|Write|MultiEdit|NotebookEdit`, merged idempotently like the Bash entry.
- `.claude/settings.json`: the same entry.

**PR C — ask: tracked deletes, plus the law and the release** (about 170 lines):
- `enforce-laws.py` (`tracked-delete`) and tests.
- `CLAUDE_LAWS.md`: the Law 32 table rows, an "ask versus deny" paragraph, and the permission-mode results. Version 2.25.0.
- `RELEASES.md`, `plugin.json`, `marketplace.json`.

If a PR measures over 400 lines or 10 files, I split it again before opening it.

## Order of work

1. Commit this plan; owner approves.
2. **Mode probe first,** before the main build, because its result shapes `main()`:
   - A scratch project gets a protected `.claude/settings.local.json`.
   - A temporary settings JSON registers the branch's hook for `Edit|Write`, with a tiny probe that returns `"ask"` and records the payload's keys.
   - Run `claude -p "add a key to .claude/settings.local.json" --settings <tmp> --permission-mode <mode>` once per mode: default, acceptEdits, auto, dontAsk, plan, bypassPermissions.
   - **Record:** did the file change (a silent allow), and is `permission_mode` in the payload? The results go into the PR and Law 32.
   - Headless `-p` runs can't show a prompt, so "denied" there is the expected safe outcome. The question is only whether any mode **writes** anyway.
3. PR A: deny checks plus tests.
4. PR B: ask infrastructure, the file guard, Bash writes, logging, registration, tests, and the per-mode deny fallback the probe calls for.
5. PR C: tracked deletes, the law, the release.
6. **Independent review** by a fresh-context subagent of the whole series against `spec.md`. I fix or answer its findings.
7. Open the PRs against `main` with Intake blocks and the review summary.

## Proof

- **Tests to add** (stdlib `unittest`, temp `HOME`, temp repos), each asserting the exit code, and for asks the printed JSON:
  - **Deny:** `commit --no-verify`, `commit -n`, `commit -an`, `push --no-verify`; force-push in four forms to `main`. A force-push to `feat/x` and `push -n` are allowed.
  - **Ask on Edit and Write:** each protected path (global settings, a project's `settings.local.json`, `~/.claude/CLAUDE.md`, a file in `~/.design-forge/`), plus a symlink into `~/.design-forge`. Allowed: each excluded data file, a development checkout's hook, an ordinary project file, and `NotebookEdit` on a normal notebook.
  - **Ask on Bash writes:** `>`, `>>`, `tee`, `sed -i`, `cp` and `rm` on a protected path. Allowed: `cat`, `grep`, `git -C ~/.design-forge pull`.
  - **Tracked deletes:** `rm` of a tracked file, `git rm` of a file, `rm -r` of a directory containing tracked files. Allowed: an untracked file, a file outside the repo, `git rm --cached`.
  - **Logging:** one `ask` line per ask, with the right check id; `--summary` shows asks.
  - **Fail open:** an unparsable command, or an unresolvable path, is allowed.
  - **Existing tests:** unchanged and passing.
- **Live:** the mode probe (step 2), with results in the PR.
- **Commands that must pass:** `python3 -m unittest discover -s tests -v`, `bash -n install.sh`, markdownlint, manifest JSON, `claude plugin validate`.
- **`install.sh`:** run against a scratch `HOME` twice. Both entries are present once, and nothing else in `settings.json` changes.
- **Visual evidence:** none (no UI). PR bodies carry `Screenshots: not applicable`.

## Risks

- **A mode might turn `"ask"` into a silent allow.** → The probe finds it before release, and that mode gets deny.
- **False positives in normal work,** for example `rm` of a generated file that happens to be tracked. → It's a prompt, not a block; the block log (#113) counts asks, so tuning is data-driven.
- **The probe costs a few headless runs.** → Six short prompts, run once.
- **`install.sh` editing `settings.json`.** → The same merge pattern as the existing entry, tested twice against a scratch `HOME`.

## Ruled out

- **Blocking instead of asking for guardrail edits and deletes.** You chose ask.
- **A separate script for file edits:** one script keeps a single install path and one log.
- **Parsing Python or other interpreters for writes:** out of reach for a string backstop. The spec's flagged conflict 2 accepts this.
