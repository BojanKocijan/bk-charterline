# Spec — A SessionStart hook runs the session-start checks (#270)

Intent: [intent.md](intent.md) · Gate tier: Significant · Issue: #270
Approved-by: <pending>

## Behavior

### When it runs

A `SessionStart` command hook with matchers `startup`, `clear` and `compact`. It runs `python3 <rules>/.claude/hooks/session_start.py`, using the same fallback as the Law 32 hook (#268): the installed copy, else `$CLAUDE_PROJECT_DIR`'s copy, else nothing. It's registered in three places:

- `install.sh`, in `~/.claude/settings.json`
- this repo's `.claude/settings.json`
- the plugin's `hooks/hooks.json` with `${CLAUDE_PLUGIN_ROOT}`

### What it prints

It prints plain text on stdout (exit 0), which Claude Code adds as context. It's one block, under 2,000 characters in practice and always under the 10,000 cap:

```
BK Charterline session start (from the SessionStart hook; print the confirmation from this, make no tool calls for these checks):
Rules: v3.6.1
Update: v3.6.2 available. Run `update rules` to pull and reload.        ← only when newer
Project: bk-charterline (worktree)                                      ← "not a git repo" outside one
Registered: design-forge on port 5176                                   ← "Registered … (new)" when the hook just added it
Language: english-only                                                  ← or "any", or "not set: ask the Law 1 question first"
GitHub: BojanKocijan                                                    ← or "unauthenticated"
Knowledge: PROJECT_KNOWLEDGE.md — <§1 one-line summary>                 ← only when the file exists
Feature: <id · title · status>                                          ← only when §11 has an active feature not handed-off
Open PRs: #281 fix(hook): …; #282 docs(…): …                            ← "none"; at most 10, then "and N more"
Merged branches to delete: fix/a, docs/b                                ← only when there are some (Law 25 step 3)
Dashboard: ~/.bk-charterline/dashboard/index.html                       ← only when built
Skipped: <check> (<reason>)                                             ← only when a check failed or timed out
```

### Each check

| Line | How | Fails as |
|---|---|---|
| Rules | the `**Version:**` header of the loaded `CLAUDE_LAWS.md` (installed copy, else repo copy) | line left out |
| Update | `git ls-remote --tags origin 'v*'` in the rules clone, highest `vX.Y.Z`, 4 s timeout; fallback: last pull older than 24 h → "run `update rules`" | `Skipped: update check (timeout)` |
| Project | `basename` of the main folder (parent of `git rev-parse --git-common-dir`), plus `(worktree)` when it differs from the top level | `not a git repo` |
| Registered | match `projects.yaml` by `repo` (`owner/repo` from `origin`), else by name. If neither matches and the folder is a git repo with an `origin`, append an entry with the next port (highest + 1, or 5173). `projects: []` becomes `projects:`. A file that can't be parsed is never written | `Skipped: registration (projects.yaml can't be parsed)` |
| Language | `settings.language` in `projects.yaml` | `not set` |
| GitHub | `gh auth status`, 4 s timeout, the `Logged in … account <login>` line | `unauthenticated` (gh missing or logged out); a timeout → `Skipped` |
| Knowledge, Feature | read `PROJECT_KNOWLEDGE.md` in the top level: §1's first sentence, §11's Active row | line left out |
| Open PRs | `gh pr list --repo <owner/repo> --state open --json number,title`, 4 s timeout | `Skipped: open PRs (…)` |
| Merged branches | `git branch --merged origin/<default>` for local branches, excluding the default branch and the current one. Reads only: no fetch, no prune | line left out |
| Dashboard | runs `my_metrics.py --local-only --if-changed` in the background (detached, never waited on). Prints the path if `index.html` exists | line left out |

- **Total time budget: about 8 seconds.** The network checks (tags, auth, PR list) run in parallel threads. Anything still running at the deadline is reported as `Skipped`.
- **Fails open.** Any exception in a check drops that line. An exception outside the checks prints nothing and exits 0. The hook never exits 2 and never prints to stderr on success.
- **Cloud sessions** (`CLAUDE_CODE_REMOTE=true`): it runs the same checks. Those that need the install (`Update`, `Registered`, `Language`, `Dashboard`) report `Skipped: … (cloud session)`.

### What changes for Claude

`CLAUDE.md`'s "Session-start behavior" becomes:

1. If the context has the hook's block, print the confirmation from it. Make no tool calls for these checks. Then:
   - If Language says `not set`, the Law 1 question is the whole first reply.
   - If `Merged branches to delete` is present, delete them (Law 9 checks) after the confirmation.
2. If there is no block (claude.ai web, an old install, or the hook failed), do the steps yourself, as listed in `knowledge/SESSION_START.md`. That's the current text, moved out of always-loaded context.

The confirmation format doesn't change.

## Acceptance criteria

- [ ] `tests/test_session_start.py` covers each line's normal case and its failure case, using fake `git` / `gh` on `PATH` and a temp `HOME`, including:
  - a check that times out after the deadline still exits 0 with the other lines
  - `projects.yaml` missing, unparseable, `projects: []`, matching by repo and by name, a new registration picking the next port, and a second run writing nothing
  - a worktree, and a non-git folder
  - the output stays under 10,000 characters even with 500 open PRs
- [ ] Running the hook on this machine prints a block that matches what Claude printed by hand at the start of this session.
- [ ] `install.sh` registers the hook once (a second run adds nothing), and `update rules` adds it. `claude plugin validate .` passes with `hooks/hooks.json`.
- [ ] A new session in a registered project shows the confirmation with **0 tool calls** before the first reply, checked in the session log.
- [ ] `scripts/laws_cost.py` shows `CLAUDE.md` smaller by the moved steps. The number goes in the PR.
- [ ] The Law 28 update gate covers the new hook file (it's under `.claude/hooks/`, so it already does). GUARDRAILS.md lists the new hook.

## Policy check

- **Law 2 / 24:** no change. The hook replaces only the session-start chores, not the announce-and-wait step.
- **Law 8:** the hook deletes nothing. Branch deletion stays with Claude.
- **Law 14:** the hook's output never includes a token, only the login name.
- **Law 20:** registration stays automatic and local. The hook does it instead of Claude.
- **Law 28:** the new hook file is behind the same approval gate.
- **Law 32:** the Law 32 hook is unchanged. This is a separate script, and an `install.sh` change in the same PR goes through the update gate.
- **Law 38:** no MCP calls (`mcp_tool` hooks are skipped at launch anyway).

## Out of scope

- Moving the laws themselves into the hook's context (the 10,000-character slot). That's #275.
- The preview footer and one approval stop per task. That's #273.
- Starting `npm run dev` (Law 18). It still starts only when code work begins.
