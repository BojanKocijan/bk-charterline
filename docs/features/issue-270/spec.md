# Spec — A SessionStart hook runs the session-start checks (#270)

Intent: [intent.md](./intent.md) (approved 2026-10-14)
Design: none. No UI. The output is the existing session-start confirmation (`CLAUDE.md`, "Session-start behavior", step 6).
Approved-by: BojanKocijan, 2026-10-14, chat (with the two flagged points as proposed: the rule text changes in a second PR, and the temp-folder marker)

## What the Claude Code docs settle (checked 2026-10-14)

- A `SessionStart` hook's `hookSpecificOutput.additionalContext` reaches Claude before the first prompt. The cap is 10,000 characters; anything longer is cut to a 2,000-character preview.
- Exit code 2 doesn't block a `SessionStart` hook; stderr is only shown to the user. The first response waits for startup hooks to finish. The default timeout is 600 s, so we set our own.
- Matchers: `startup`, `resume`, `clear`, `compact`, `fork`.
- A plugin ships hooks in `hooks/hooks.json`, using `${CLAUDE_PLUGIN_ROOT}`. A `CLAUDE.md` inside a plugin isn't loaded, so a `SessionStart` hook is the only always-on context a plugin has. BK Charterline ships no plugin hooks today; this is the first.

## Behavior

### When it runs

- **On `startup` and `clear`:** it runs every check below and returns the session-start block.
- **On `resume`, `compact` and `fork`:** it returns nothing. The conversation already has the confirmation, and printing it again would be noise.
- **Once per session.** The hook can be registered more than once: by `install.sh`, by the plugin, and by this repo's own `.claude/settings.json`. The first run writes a marker in the system temp folder, keyed by `session_id`, and later runs that find the marker return nothing.

### What it checks

Every check only reads; the hook changes no file in the project and no git state. Network checks run in parallel, each with a **3-second** limit (owner decision). A check that fails or times out leaves its line out, or says `unknown`. The hook's own `timeout` is 10 s.

| # | Check | Source | Replaces |
|---|---|---|---|
| 1 | Rules version | `CLAUDE_LAWS.md` header from the rules home: the installed clone, else the plugin root, else this repo | `CLAUDE.md` step 3 |
| 2 | Newer release | `git ls-remote --tags origin 'v*'` in the installed clone, newest `vX.Y.Z` (network) | step 1, Law 28 |
| 3 | Project | basename of the main worktree (the parent of `git rev-parse --git-common-dir`), or `not a git repo` | step 4, Law 18 |
| 4 | Language | `settings.language` in `~/.bk-charterline/projects.yaml`: `english-only`, `any` or `not set` | step 4.9, Law 1 |
| 5 | Registration and port | the project's entry in `projects.yaml`; if missing, the next free port | Law 20, Law 18 |
| 6 | Knowledge | the `## 1.` line of `PROJECT_KNOWLEDGE.md`, and whether a local `CLAUDE.md` exists | step 4.5, 4.6, Law 11 |
| 7 | Active feature | the first data row under `## 11. Active feature`, unless its status is `handed-off` | step 4.8 |
| 8 | GitHub login | `gh api user -q .login` (network). On failure: `via connector` in a cloud session (`CLAUDE_CODE_REMOTE=true`), else `unauthenticated` (owner decision) | step 5, Law 16 |
| 9 | Open PRs | `gh pr list --json number,title --limit 10` (network), skipped when the login failed | Law 25 step 2 |
| 10 | Dashboard | whether `~/.bk-charterline/dashboard/index.html` exists | step 6 line |
| 11 | Session note | whether `SESSION_NOTE.md` exists in the project root | Law 33 |

### What it gives Claude

One block under 2,000 characters, so it is never cut. The first part is the confirmation, ready to print; the second is what Claude does next:

```text
BK Charterline session start (from the SessionStart hook; these checks are done, make no tool calls for them).
Print this confirmation as your first reply:

Rules loaded: BK CHARTERLINE v3.6.1
Project: bk-charterline
Persona: Frontend
GitHub: via connector
Knowledge: PROJECT_KNOWLEDGE.md — <§1 line>
Feature: <id · title · status>
Dashboard: ~/.bk-charterline/dashboard/index.html
Ready.

Before it:
- BK Charterline update available: v3.6.1 → v3.7.0. Run `update rules` to pull and reload.
- Language not set: ask the Law 1 question as your whole first reply instead, and print the confirmation in the next one.

When code work starts (not before):
- Open PRs: #301 <title> (Law 5a / 25).
- Register bk-charterline in projects.yaml on port 5174 (Law 20).
- Create the one-line local CLAUDE.md (Law 11).
- Pull the default branch, sweep merged branches (Laws 5, 25).
- SESSION_NOTE.md exists: summarize it and ask whether to resume (Law 33).
```

Lines whose check had nothing to report are left out, the same as the confirmation's own optional lines today.

### Steps that change things, now done when code work starts

Owner decision: the hook only reports these, and Claude does them when code work starts, never at session start:

- **Law 25:** pull the default branch and sweep merged branches. Law 5 already pulls before every new branch.
- **Law 20:** register the project in `projects.yaml`. The port is needed only for the preview (Law 18).
- **Law 11:** create the one-line local `CLAUDE.md`.
- **Dashboard refresh (step 4.95):** runs after the next pull of the default branch, as Law 9 already says.

### When there's no hook output

On claude.ai web, or with the hook missing or failed, there is no block. Claude then follows a short fallback in `CLAUDE.md`: read the version from the loaded laws, print the confirmation with what it knows without tools (`GitHub: unknown`), and ask the Law 1 question if nothing says the language is set. A session with a shell may run the old checks. One sentence names them.

### Where it's registered

| Install | Registration | Path |
|---|---|---|
| Global (`install.sh`) | `SessionStart` entry in `~/.claude/settings.json`, matcher `startup\|clear`, timeout 10 | `~/.bk-charterline/.claude/hooks/session_start.py` |
| Plugin | new `hooks/hooks.json` | `${CLAUDE_PLUGIN_ROOT}/.claude/hooks/session_start.py` |
| This repo (and cloud sessions) | `.claude/settings.json` | installed copy, else `$CLAUDE_PROJECT_DIR` copy, else nothing (the #268 fallback) |

`charterline-update` already asks before any change under `.claude/hooks/`, `install.sh` or `.claude/settings.json` (Law 28). The new script and its registration go through that same approval. `hooks/hooks.json` is added to the paths it diffs.

## Acceptance criteria

- [ ] A fresh `startup` session in a project, with the hook installed, prints the confirmation in its first reply with **0 tool calls** before it. Checked by hand in a local session and a cloud session; the transcripts are in the PR.
- [ ] `session_start.py` changes no file in the project and no git state. A test runs it in a temporary repo and compares `git status --porcelain` and every ref before and after.
- [ ] With the network off, or `gh` and `git ls-remote` faked to hang, the hook finishes in under 5 s and leaves the update and PR lines out.
- [ ] On `resume`, `compact` and `fork`, and on a second run in the same session, it prints nothing.
- [ ] Unset language, a missing `projects.yaml`, a broken `projects.yaml`, a missing `PROJECT_KNOWLEDGE.md` and "not a git repo" each give the right lines. Each has a test.
- [ ] The block stays under 2,000 characters even with 10 open PRs, because titles are cut short.
- [ ] `claude plugin validate .` passes with the new `hooks/hooks.json`.
- [ ] `CLAUDE.md`'s session-start section shrinks, and `laws_cost.py` shows the token cut in the PR.
- [ ] Every existing test still passes.

## Policy check

- Component library, accessibility: n/a (no UI).
- Copy: the confirmation keeps its current fields and order. New lines follow the existing style: one line each, plain words, with the law named in brackets.
- Laws whose text changes (only who runs the check, never what's required): `CLAUDE.md` steps 1–6; Law 16 (where the login comes from); Law 20 ("at session start" becomes "when code work starts"); Law 25 (pull and sweep move to when code work starts; open PRs come from the hook); Law 28 (the hook does the check); GUARDRAILS (the new hook, and that it never blocks).
- **Conflicts flagged for the owner:**
  1. **Law 25's title and Law 20's "at session start" change meaning.** This follows from your read-only decision, but it is a rule change, not only a mechanism change. Its rule-text PR also needs your approval.
  2. **The marker file in the system temp folder** is the hook's only write. It sits outside the project, but it is a write. The alternative is accepting a doubled block in this repo, where the global install and the repo registration both run.

## Out of scope

- Loading the laws themselves through the hook, so plugin installs get always-on rules. A follow-up issue under #267.
- Shipping the Law 32 guardrail hook in the plugin.
- Every step that changes things (listed above). They stay with Claude, when code work starts.
- #273's one-stop approvals and preview footer.
