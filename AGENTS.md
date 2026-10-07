# AGENTS.md — BK Charterline

This repository is governed by **BK Charterline**. Any AI coding agent that reads `AGENTS.md` (Claude Code, Cursor, Codex CLI, Copilot, Aider, Gemini CLI, Windsurf, …) must follow the binding laws in [`CLAUDE_LAWS.md`](./CLAUDE_LAWS.md) — that file is the source of truth; this is a short pointer.

## Non-negotiables (full set in CLAUDE_LAWS.md)

- **Announce before executing.** State what you understood and the plan, then wait for explicit approval before any git/gh write. Silence ≠ approval. (Law 2)
- **Branch + issue before code.** Pull `main`, branch, open an issue, then write. (Law 5)
- **PRs only — never push to `main`.** (Law 7)
- **Never merge — under any phrasing.** No merge button, `gh pr merge`, API, squash/rebase/fast-forward, or local merge. "merge it"/"ship it"/"done" = open or finish the PR and stop. Merging is the human's action. (Law 7)
- **No file deletion** without explicit human approval. (Law 8)
- **Conventional Commits**, and **scan the staged diff for secrets** before every commit. (Laws 13–14)
- **No real PII** in mock data or fixtures. (Law 15)
- **No inline styles** in `*.tsx` — four-file component folders. (Law 12)
- **WCAG 2.2 AA** on every component. (Law 4 / SKILLS)

## Where to look

| Topic | File |
|---|---|
| All binding laws | [`CLAUDE_LAWS.md`](./CLAUDE_LAWS.md) |
| Session behavior, personas, triggers | [`CLAUDE.md`](./CLAUDE.md) |
| Frontend standards | [`knowledge/FRONTEND_GUIDE.md`](./knowledge/FRONTEND_GUIDE.md) |
| New-project scaffold | [`knowledge/PROJECT_SCAFFOLD.md`](./knowledge/PROJECT_SCAFFOLD.md) |
| Fullstack PR runbook + backend checklist | [`knowledge/FULLSTACK_WORKFLOW.md`](./knowledge/FULLSTACK_WORKFLOW.md) |
| Component patterns | [`knowledge/COMPONENT_PATTERNS.md`](./knowledge/COMPONENT_PATTERNS.md) |

When in doubt, read `CLAUDE_LAWS.md` and ask before acting.
