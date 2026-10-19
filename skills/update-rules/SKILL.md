---
name: update-rules
description: Run `update rules` — install the newest BK Charterline release, re-import the rules and reprint the session confirmation, with the owner's approval when the update changes the hook (Law 28). Invoke when the user says "update rules", "update the rules" or "charterline-update".
license: GPL-3.0-only
---

# Update rules

Run `"$SHELL" -ic 'if command -v charterline-update >/dev/null; then charterline-update; else dforge-update; fi'` via the Bash tool (the new command, or on an install from before v3.0.0 the old one, which moves it to the new name) (a fresh shell, so the function comes from the rc file and not this session's cached copy, #168), then re-import every `@./...` in `CLAUDE.md`, then reprint the confirmation with the new version. If it stops because the hook changed, show the user its diff in chat (the stat lines, then what each hunk changes), then run the same command with `--approve <commit>` (`charterline-update --approve <commit>`, or `dforge-update --approve <commit>` on an install from before v3.0.0) with the exact commit it printed. The hook makes the app ask, and only the user's click approves (Law 28); a refusal means stop. If `--approve` is refused (the hook isn't registered, or a newer commit is on offer), report why; the user can still run `charterline-update` in their own terminal. Never retry with `--main` unless asked.

## How updates work (Law 28)

*Moved from Law 28 in `CLAUDE_LAWS.md` (#271). Binding when this file is in scope (Law 4); the law keeps its core rule.*

BK Charterline loads globally — every project shares one `~/.bk-charterline` clone — so a single update reaches all consuming projects at once. The session-start hook compares the loaded version against the newest release tag (`vX.Y.Z`) on the remote and, if a newer release exists, Claude surfaces **one line** before proceeding:

```
BK Charterline update available: v<loaded> → v<remote>. Run `update rules` to pull and reload.
```

- The update command is **`update rules`** in-session (runs `charterline-update`, or `dforge-update` on an install from before v3.0.0, which moves it to the new name; then re-imports the rules and reprints the confirmation with the new version). The shell equivalent is **`charterline-update`**; `dforge-update` points to it for v3.0.0 only.
- **`charterline-update` installs the newest release tag** (the clone sits on a detached HEAD); `charterline-update --main` follows `main` instead. Before switching, it diffs everything the Law 32 hook runs (`.claude/hooks/`, `hooks/hooks.json`, `scripts/ai_tools.py`, `install.sh`, `.claude/settings.json`). A change there needs the user's yes: a `y` typed in their own terminal (the diff prints without a pager), or their click in the app's permission prompt for `charterline-update --approve <commit>`, which the Law 32 hook raises. Without a terminal and without `--approve`, it shows the diff, applies nothing, names the commit to approve and exits 1. `--approve` installs only that exact commit, and only when the hook is registered in `~/.claude/settings.json`; otherwise it changes nothing. It never downgrades, refuses when the clone has local edits, and checks out exactly the commit whose diff was shown. Git commands run by hand in `~/.bk-charterline` skip that gate, so the Law 32 hook asks before any that would change the clone's files (#170).
- Claude **never auto-pulls** without the user's go-ahead — it notifies and continues on the current version until the user runs the command.
- On claude.ai web (no clone) this check is skipped.
