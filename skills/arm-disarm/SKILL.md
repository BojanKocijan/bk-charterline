---
name: arm-disarm
description: Toggle BK Charterline governance on or off for this session. "disarm" suspends all binding laws so Claude operates without governance constraints — useful for quick explorations or unconstrained pair-programming. "arm" restores the full ruleset. Hard-safety rails (never merge, no secrets, no PII) survive disarm and cannot be toggled off.
license: GPL-3.0-only
---

# Arm / Disarm — BK Charterline governance toggle

## What this skill does

`disarm` suspends all BK Charterline laws for the current session.
`arm` restores them (also the default at every session start).

This exists for moments where governance overhead is unwanted:
- Fast explorations / throwaway prototypes
- Unconstrained pair-programming where the human is the safety layer
- Non-code sessions (pure conversation, research, docs)

---

## Disarmed state

When disarmed, Claude:

- **Skips** the Law 2 pre-execution announcement
- **Skips** the Law 5 branch + issue requirement
- **Skips** the Law 2 approval gate (acts immediately on instruction)
- **Skips** the Law 17 triage-first question before non-trivial UI
- **Skips** the Law 18 localhost preview footer
- **Skips** the Law 26 `dry run` git-command pause
- **Skips** all persona restrictions (Laws 4, 12, 21, 24, 30)

Claude **always** prints this banner at the top of every response while disarmed:

```
⚠ DISARMED — BK Charterline governance suspended. Type `arm` to restore.
```

---

## Hard-safety rails — survive disarm, cannot be toggled off

These three survive `disarm` under any circumstance:

| Rail | Why it survives |
|---|---|
| **Never merge** (Law 7) — Claude never runs `gh pr merge` or any merge automation | Merging the default branch is irreversible; only the human merges |
| **Secret scan** (Law 14) — stop and refuse if secrets found in staged diff | A leaked credential can't be un-leaked |
| **No real PII in mock data** (Law 15) — fictional names, `@example.com`, RFC 5737 IPs | PII in committed code is a compliance failure |

---

## Trigger phrases

| Phrase | Action |
|---|---|
| `disarm` | Suspend all laws (except hard-safety rails above). Print disarmed banner on every response. |
| `arm` | Restore full BK Charterline governance. Print `✓ ARMED — full BK Charterline governance restored.` once, then continue normally. |

State resets to **armed** at every new session start — disarm never persists across sessions.
