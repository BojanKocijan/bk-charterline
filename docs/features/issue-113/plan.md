# Plan — log every Law 32 block

Spec: [#113](https://github.com/BojanKocijan/design-forge/issues/113) (the issue is the spec) · Gate tier: Standard · Branch: `feat/hook-block-log` · Issue: #113 · Roadmap: #123
Work pile: delegable (two scripts plus docs, verifiable with tests)
Approved-by: BojanKocijan, 2026-10-05, chat (revision 2; revision 1 approved the same day)

## Revision 2 — why

The owner asked for the three accepted risks to be fixed rather than accepted: log growth, concurrent writes, and the hook script doing two jobs. Changes from revision 1:

1. **Rotation.** At 1 MB the log moves to `hook-log.1.jsonl`, replacing any older one. That caps disk use at about 2 MB. `--summary` and `--false-positive` read both files.
2. **Locking.** Every append and rotation runs under an exclusive `fcntl.flock` on `~/.design-forge/hook-log.lock`. The hook waits at most 200 ms for the lock. If it can't get it, it skips logging rather than slowing the Bash call. Where `fcntl` doesn't exist (Windows), it appends without a lock.
3. **A separate log module.** All log code moves to `.claude/hooks/hook_log.py`, which is also the CLI (`python3 ~/.design-forge/.claude/hooks/hook_log.py --summary`). `enforce-laws.py` only imports `append_block()` from it. If the import fails, logging is skipped and the decision is unchanged, so the hook keeps one job.
4. **PR split (Law 31).** The extra module brings the change to 11 files, over the 10-file ceiling. This plan ships as its own docs PR first (as #103 did for #102), and the implementation PR follows with 10 files. If that PR measures over 400 changed lines, I stop and split it: first the module and its tests, then the hook wiring, docs and version.

## Behavior

- **Every block writes one line** to `~/.design-forge/hook-log.jsonl`, rotated to `hook-log.1.jsonl` at 1 MB. Allowed calls write nothing. The folder is created if it's missing, because plugin users may not have it.

  ```json
  {"ts": "2026-10-05T12:00:00Z", "type": "block", "law": 5, "check": "commit-on-default", "cwd": "/path/to/repo", "branch": "main", "command_sha256": "…"}
  ```

  - `check` is a fixed id per block site: `merge`, `graphql-merge`, `screenshots`, `commit-on-default`, `push-default`, `commit-message`, `secret`, `env-file`.
  - `cwd` and `branch` are the repo the hook judged (`resolve_cwd` on the payload `cwd`).
  - **No command text, commit message or block reason is stored.** The Law 13 reason contains the commit message's first line, so the log keeps the `check` id instead. The command hash lets repeats of the same command be counted.
- **Logging can't change a decision.** Any error while writing the log (unwritable file, full disk, `~/.design-forge` being a file, a missing or broken `hook_log.py`, the lock held for more than 200 ms) is swallowed, and the hook still exits 2 with the same message on stderr.
- **Concurrent sessions.** Appends and rotation are serialised by an exclusive lock on `hook-log.lock`. Two sessions never interleave a line or both rotate at once.
- **`--false-positive "<note>"`:** run as `python3 ~/.design-forge/.claude/hooks/hook_log.py --false-positive "…"`. It appends a `{"type": "false_positive", "ref_ts": …, "check": …, "command_sha256": …, "note": …}` line pointing at the latest block (in either file), and prints which block it marked. If there's no block in the log, it says so and exits 1.
- **`--summary`** (`hook_log.py --summary`): prints blocks per law and check for the last 30 days across both files, the total, how many were marked false positives, and the notes. If there's no log, it says so.
- **Claude's behavior:**
  - **`hook log`:** a new trigger. Claude runs `--summary` and reports the result.
  - **A wrong block:** when the user says a block was wrong, Claude runs `--false-positive` with a one-line note and offers to open a bug issue. Claude never marks a block as a false positive on its own judgment.
- The log is local-only. `hook-log*` (log, rotated log, lock file) is added to `.gitignore`, because the files sit at the root of the `~/.design-forge` clone.

## Files to change

| File | Change |
|---|---|
| `.claude/hooks/enforce-laws.py` | `block(reason, check)` raises a `Blocked` exception. `main()` catches it, calls `hook_log.append_block()` (import and call both guarded), prints the reason and exits 2. No command-line options. |
| `.claude/hooks/hook_log.py` (new) | `append_block()` with lock and rotation, `read_records()` over both files, `summary()`, `mark_false_positive()`, and the `--summary` / `--false-positive` CLI. Stdlib only. |
| `tests/test_enforce_laws.py` | Every `run_hook` sets `HOME` to a temp folder, so tests never write to the real log. New `BlockLogTests` class (see Proof). |
| `.gitignore` | `hook-log*` |
| `CLAUDE_LAWS.md` | Law 32: a "Block log" paragraph, plus one line in "Claude's behavior on a block" (mark a false positive only when the user says so, then offer a bug issue). Version 2.22.0. |
| `CLAUDE.md` | `hook log` row in the trigger table |
| `README.md` | `hook log` row in the trigger table |
| `RELEASES.md` | v2.22.0 entry |
| `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Version 2.22.0 (a new feature, so a minor bump) |

Implementation PR: 10 files, estimated at about 380 changed lines. This plan ships in its own PR first.

## Order of work

1. Open the plan PR (this file only) once revision 2 is approved. Done when it's open; the implementation branch rebases after it merges.
2. Refactor `block()` into a `Blocked` exception with a `check` id, with no behavior change. Done when the existing 11 tests pass.
3. Add `hook_log.py` with lock, rotation, summary and false-positive marking, and wire `append_block()` into the hook. Done when the new tests pass.
4. Docs, `.gitignore`, versions, `RELEASES.md`. Done when markdownlint passes and both manifests parse.
5. Measure the diff. Over 400 lines → split as described in revision 2. Then open the PR(s) with the Intake block. Done when CI is green (markdownlint + Hook Tests).

## Proof

- **Tests to add** in `BlockLogTests`, with `HOME` set to a temp folder:
  - A blocked commit on `main` writes exactly one `block` line with `law: 5`, `check: commit-on-default`, the repo `cwd` and `branch`.
  - An allowed commit on a feature branch writes nothing.
  - A Law 13 block on `git commit -m "secret-marker-xyz"` leaves no `secret-marker-xyz` anywhere in the log.
  - With `~/.design-forge` created as a *file* (so it can't be written to), the block still exits 2 with the same stderr.
  - **Rotation:** with a log pre-filled past 1 MB, a block moves it to `hook-log.1.jsonl` and starts a new file with one line. A second rotation replaces the old `.1` file. `--summary` counts lines from both files.
  - **Locking:** 20 hook processes blocking at the same time leave exactly 20 valid JSON lines.
  - **Lock held:** with the test holding the lock, a block still exits 2 within 1 s and writes no line.
  - **Missing module:** with `hook_log.py` absent next to the hook (a copy of the hook in a temp folder), a block still exits 2.
  - `--false-positive "note"` appends one `false_positive` line whose `ref_ts` and `command_sha256` match the latest block. It exits 1 when the log is empty.
  - `--summary` reports the right counts per law, and the false-positive count, for a log with lines inside and outside the 30-day window.
- **Existing tests:** none edited except that `run_hook` passes `env` with a temp `HOME`. No assertion changes.
- **Commands that must pass:** `python3 -m unittest discover -s tests -v`, `python3 -m py_compile .claude/hooks/enforce-laws.py .claude/hooks/hook_log.py`, `npx markdownlint-cli2 --config .markdownlint.json "**/*.md"`.
- **By hand after merge and `dforge-update`:** trigger one real block in a scratch repo on `main`, then check the log line and `hook log`.
- **Visual evidence:** none (no UI). The PR body carries `Screenshots: not applicable`.

## Risks

- **Rotation keeps only one old file**, so blocks older than about 8,000 lines back are dropped. `--summary` looks at 30 days, which is far less than that at any realistic block rate.
- **The lock adds up to 200 ms to a blocked call** when another session holds it. That only happens on blocks, never on allowed calls.
- **No lock on Windows.** Lines may interleave there. Design Forge's install targets macOS and Linux shells.
- **The `cwd` path reveals local folder names.** The file stays local and gitignored, and it never leaves the machine.
- **The hook now depends on a second file.** A partial update could leave `hook_log.py` missing or out of step. The guarded import makes that skip logging, never break blocking, and a test covers it.

## Ruled out

- **Storing the block reason or command text.** The issue forbids it, and the Law 13 reason carries the commit message.
- **Claude editing log lines in place to flag false positives.** Append-only records are safer with concurrent sessions and keep the history.
- **An env var to override the log path.** Tests can set `HOME` instead, so an override would be an extra option nobody needs.
- **Claude summarising the raw JSONL ad hoc for `hook log`.** `--summary` is deterministic, testable and cheaper in tokens.
- **A `dforge` CLI on the `PATH`.** It would need `install.sh` changes and a plugin-install story. `python3 <path>/hook_log.py` works in both install modes today.
- **Locking the log file itself.** Rotation renames the file, so a lock on it doesn't serialise rotation. A separate lock file does.
- **Blocking until the lock is free.** A stuck process would then stall every blocked Bash call. A 200 ms limit and skipping the log line keep the hook fast.
