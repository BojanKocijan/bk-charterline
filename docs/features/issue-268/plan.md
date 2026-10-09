# Plan — The hook falls back to the repo copy when the installed one is missing (#268)

Spec: [#268](https://github.com/BojanKocijan/bk-charterline/issues/268), part of epic [#267](https://github.com/BojanKocijan/bk-charterline/issues/267) · Gate tier: Standard · Branch: `fix/hook-repo-fallback` · Issue: #268
Work pile: delegable (one config file plus a test, checked by the machine), built in this session
Skip gates: Significant → Standard at the owner's request (2026-10-09, chat). Reason: a narrow fix for a blocker, since cloud sessions in this repo can't run any tool
Approved-by: BojanKocijan, 2026-10-09, chat

## Why

This repo's `.claude/settings.json` registers the Law 32 hook with a fixed path:

```
python3 "$HOME/.bk-charterline/.claude/hooks/enforce-laws.py"
```

A cloud session has no `~/.bk-charterline` and no `~/.claude/settings.json` from `install.sh`, so this repo file is the only hook registration there. `python3` can't open the missing script and exits 2, and for `PreToolUse` an exit code of 2 means **block**. Every Bash, Edit/Write and MCP call fails. The hook is designed to fail open (Law 32), but here it fails closed.

The `UserPromptSubmit` entry (`persona_log.py`) already ends in `|| true`, so it doesn't block anything. It stays as it is.

## Behavior

For each of the four `enforce-laws.py` entries in `.claude/settings.json` (three `PreToolUse`, one `PostToolUse`):

1. **Installed copy found** (`$HOME/.bk-charterline/.claude/hooks/enforce-laws.py`): it runs, as today. Local sessions don't change, and the installed copy is still the one whose updates you approve (Law 28).
2. **No installed copy, repo copy found** (`$CLAUDE_PROJECT_DIR/.claude/hooks/enforce-laws.py`): the repo copy runs. This is the cloud case.
3. **Neither found:** the call is allowed (exit 0), and the hook prints `{"systemMessage": "BK Charterline: the Law 32 hook wasn't found, so its checks are off for this call."}`, which the app shows to the user (owner decision 2026-10-09).

The command (one line in the JSON; shown wrapped here):

```sh
f="$HOME/.bk-charterline/.claude/hooks/enforce-laws.py";
[ -f "$f" ] || f="$CLAUDE_PROJECT_DIR/.claude/hooks/enforce-laws.py";
if [ -f "$f" ]; then exec python3 "$f"; fi;
echo '{"systemMessage": "BK Charterline: the Law 32 hook wasn'"'"'t found, so its checks are off for this call."}'
```

`exec` keeps the script's own exit code and stdout, so blocks and asks still work. `install.sh` keeps writing its own fixed-path command to `~/.claude/settings.json`. That covers other projects, where the repo copy doesn't exist.

## Files to change

| File | Change |
|---|---|
| `.claude/settings.json` | The four `enforce-laws.py` commands use the fallback above |
| `tests/test_enforce_laws.py` | A new test class that runs the registered command through `sh -c` in the three cases |
| `knowledge/GUARDRAILS.md` | One line under "where it's installed": the repo's own registration falls back to the repo copy, and allows the call with a warning when no copy is found |
| `RELEASES.md` | An `Unreleased` fix entry (the patch release comes after #269, per the epic) |

## Order of work

1. Write the test first, and check that it fails today: the "repo copy" case exits 2 — done when the red run is recorded in the PR.
2. Change `.claude/settings.json` — done when the test passes and `python3 -m json.tool .claude/settings.json` is clean.
3. Update the GUARDRAILS line and RELEASES.md — done when `tests/test_laws_structure.py` passes.
4. `/code-review main...HEAD`, fix the findings, open the PR.

## Proof

- **Tests to add:** in `tests/test_enforce_laws.py`, read each `enforce-laws.py` command from `.claude/settings.json` and run it with `sh -c`, giving it a payload of `gh pr merge 1` (which the hook must block):
  - `HOME` = an empty temp folder, `CLAUDE_PROJECT_DIR` = the repo → blocked (exit 2, Law 7 message). Today this case blocks only because the script is missing, so the test also checks that the message is the hook's own.
  - `HOME` holding a fake installed `enforce-laws.py` that prints a marker → the marker runs, and the repo copy doesn't.
  - `HOME` and `CLAUDE_PROJECT_DIR` both empty → exit 0, and stdout is the `systemMessage` JSON.
  - A harmless payload (`ls`) with the repo copy → exit 0, empty stdout.
- **Existing tests edited:** none.
- **Commands that must pass:** `python3 -m unittest discover -s tests -v`, `python3 -m json.tool .claude/settings.json`, `claude plugin validate .`.
- **Visual evidence:** none (no UI change).

## Risks

- **`$CLAUDE_PROJECT_DIR` isn't set in some session type** → the repo copy isn't found and the call is allowed with the warning. That's the decided fallback, not a block.
- **Locally, the repo copy never runs while an install exists.** So a hook change on a branch isn't live until it's released and installed (Law 28), same as today.
- **The hook runs twice in this repo locally** (global plus repo registration), as it does today. Not in scope; #269 handles the double load, and it can look at this too.
- **The warning prints on every call when no copy is found.** That only happens with a broken checkout, because the repo always has its copy, so I'm not adding a once-per-session limit (Law 21).
- **The hook-update gate (Law 28) diffs `.claude/settings.json`**, so this release asks for the owner's approval in `update rules`. That's expected.

## Ruled out

- **Point the repo registration at the repo copy only.** In local sessions that would run an unreleased hook from whatever branch is checked out, skipping the Law 28 approval.
- **A launcher script in the repo.** It would itself need a path that works in cloud, which is the same problem.
- **Changing `install.sh`'s global command.** Global settings apply to every project, where `$CLAUDE_PROJECT_DIR` has no hook copy. The fixed path is right there.
- **The plugin's own `hooks/hooks.json` with `${CLAUDE_PLUGIN_ROOT}`.** It's a separate install path, and #270 (SessionStart hook) will look at how the plugin ships hooks.
