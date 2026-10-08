---
name: update-rules
description: Run `update rules` — install the newest BK Charterline release, re-import the rules and reprint the session confirmation, with the owner's approval when the update changes the hook (Law 28). Invoke when the user says "update rules", "update the rules" or "charterline-update".
license: GPL-3.0-only
---

# Update rules

Run `"$SHELL" -ic 'if command -v charterline-update >/dev/null; then charterline-update; else dforge-update; fi'` via the Bash tool (the new command, or on an install from before v3.0.0 the old one, which moves it to the new name) (a fresh shell, so the function comes from the rc file and not this session's cached copy, #168), then re-import every `@./...` in `CLAUDE.md`, then reprint the confirmation with the new version. If it stops because the hook changed, show the user its diff in chat (the stat lines, then what each hunk changes), then run the same command with `--approve <commit>` (`charterline-update --approve <commit>`, or `dforge-update --approve <commit>` on an install from before v3.0.0) with the exact commit it printed. The hook makes the app ask, and only the user's click approves (Law 28); a refusal means stop. If `--approve` is refused (the hook isn't registered, or a newer commit is on offer), report why; the user can still run `charterline-update` in their own terminal. Never retry with `--main` unless asked.
