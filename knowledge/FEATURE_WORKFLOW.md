# Feature Workflow — BK Charterline

**Version:** 1.0.0
**Last Updated:** 2026-06-06
**Binding:** Yes — this file is a law (see [`CLAUDE_LAWS.md`](../CLAUDE_LAWS.md) Law 4). Claude follows it whenever a designer is starting, continuing, or finishing a piece of UI work.

> The feature workflow is the **session-level discipline** that ties every UI change to a clear "what am I working on, and why" answer. Without it, branches get named randomly, commits drift from the original goal, and the handoff at the end has nothing to anchor against. With it, every commit message, every PR title, every screenshot, and every handoff carries the same ID — so the audit trail follows itself.

---

## 1. The lifecycle

```
[ start ] → in-design → in-mockup → in-prototype → in-review → ready-for-handoff → handed-off → [ end ]
                                     ↓
                               (designer iterates — status stays the same)

[ pause feature ] ← (urgent fix, switching attention) ← any state
       │
       └──→ paused state (sits in §11 paused_features) → resume feature → returns to last state
```

States are advisory, not gates. Claude doesn't refuse to move work forward when the status row says one thing and the designer is doing another — but the status nudges the conversation toward "should we move it?".

---

## 2. Two modes — bootstrap vs steady-state

| Mode | When | ID source | Handoff target |
|---|---|---|---|
| **Bootstrap** | Exploring what should exist, no external issue tracker required | Synthetic ID `<PROJECT>-BOOT-<NNN>` (e.g. `MY-APP-BOOT-001`) | None yet — the UX project IS the exploration |
| **Steady-state** | Designing real improvements with an existing issue | Any issue ID: GitHub issue `#123`, Linear `ENG-456`, Jira `PROJ-789`, etc. | Per `PROJECT_KNOWLEDGE.md §9 Downstream dev repo` |

Both modes follow the same lifecycle. The only differences are:

- **ID format** — bootstrap allows any `<PROJECT>-BOOT-<NNN>`; steady-state uses whatever the user's issue tracker provides.
- **Handoff destination** — bootstrap stops at "handed-off" within the same repo; steady-state opens a tracking issue in the GitHub Issues repo.

Claude detects the mode from the answer to triage question Q2: if the user provides a tracker ID, it's steady-state. If they say "bootstrap" / "no issue" / "just exploring", Claude generates the next available `<PROJECT>-BOOT-<NNN>`.

---

## 3. The triage Q&A — 3 questions, capped

When the designer says `start feature` (or any paraphrase), Claude asks **exactly three questions**, in order.

### Q1. Feature or improvement?

> "Is this a **new feature**, an **improvement to existing**, or a **refactor**?"

| Answer | Branch prefix |
|---|---|
| New feature | `feat/` |
| Improvement | `fix/` or `feat/` (Claude asks if ambiguous) |
| Refactor | `refactor/` |

### Q2. Do you have an issue ID?

> "Do you have an issue ID for this work (GitHub #123, Linear ENG-456, Jira PROJ-789, etc.)? Or should I generate a bootstrap ID?"

Two paths:
- **Yes** → Claude notes the ID, validates format is non-empty, and continues. Any format is valid.
- **No / bootstrap** → Claude generates `<PROJECT>-BOOT-<NNN>` where `<PROJECT>` is the kebab-case repo name uppercased and `<NNN>` is the next integer after the last bootstrap entry in `PROJECT_KNOWLEDGE.md §12`.

### Q3. One-line JTBD

> "In one sentence: who is the user, what do they want to do, and why? (Job-to-be-done format)"

Example: *"As a dashboard admin, I want to export table data as CSV so I can share it with stakeholders who don't have app access."*

Claude writes this to `PROJECT_KNOWLEDGE.md §11 Active feature` immediately.

---

## 4. The `§11 Active feature` row

```markdown
## 11. Active feature

| ID | Title | Status | Branch | JTBD |
|---|---|---|---|---|
| MYAPP-BOOT-001 | Export CSV | in-mockup | feat/export-csv | As a dashboard admin, I want to export table data as CSV so I can share it with stakeholders. |
```

**One active feature at a time.** If a feature is already active and not `handed-off`, Claude asks: *"You have an active feature: <title>. Pause it and start a new one, or finish it first?"*

---

## 5. Status transitions

| Status | Meaning | Common trigger |
|---|---|---|
| `in-design` | Figma frames being built or critiqued | Start of work |
| `in-mockup` | React mockup being built | "Let's code this up" |
| `in-prototype` | Interactive prototype — state, transitions, mock data | "Make it clickable" |
| `in-review` | Ready for design review / stakeholder check | "It's ready to show" |
| `ready-for-handoff` | Approved — packaging for dev | "Let's hand it off" |
| `handed-off` | `docs/handoffs/<id>.md` created, tracking issue opened | `handoff <id>` trigger |

Claude updates the status row in `PROJECT_KNOWLEDGE.md §11` whenever a transition is implied by the conversation or explicitly requested.

---

## 6. Pause and resume

### `pause feature`

> *"Moving the current feature to the Paused list so you can work on something else."*

Moves the `§11 Active feature` row (preserving all columns) to `§11 Paused features`. Clears the Active row.

### `resume feature`

If there is exactly one paused feature, Claude resumes it without asking. If there are multiple:

> *"Which paused feature would you like to resume?*
> 1. MYAPP-BOOT-001 — Export CSV (in-mockup)
> 2. MYAPP-BOOT-002 — Dark mode (in-design)"*

The chosen one returns to `§11 Active`. If something was active, Claude pauses it first.

---

## 7. Finish feature

`finish feature` trigger:

1. If status is `ready-for-handoff`, run `handoff <id>` automatically.
2. Archive the row to `PROJECT_KNOWLEDGE.md §12 Feature audit log`.
3. Clear `§11 Active`.

```markdown
## 12. Feature audit log

| ID | Title | Handed off | Notes |
|---|---|---|---|
| MYAPP-BOOT-001 | Export CSV | 2026-06-10 | Handoff at docs/handoffs/MYAPP-BOOT-001.md |
```

---

## 8. Rules-staleness check at feature transitions

At `finish feature` and `handoff <id>`, Claude checks if the loaded rules version is older than what's in `~/.bk-charterline`. If stale, Claude surfaces one recommendation — *"BK Charterline rules may be updated. Run `charterline-update` before handing off?"* — and waits for an explicit yes before running it.

---

## Changelog

- **1.0.0 (2026-06-06)** — Initial release. Generic issue-ID support (any tracker: GitHub, Linear, Jira, etc.) or bootstrap mode. Full lifecycle, 3-question triage, pause/resume/finish flow, §11 active-feature row format, and feature audit log.
