# Spec — the hook guards the guardrails (#117)

Intent: [#117](https://github.com/BojanKocijan/design-forge/issues/117) (the issue is the intent) · Roadmap: #123
Design: none (no UI; hook behavior and the app's permission prompt)
Approved-by: <pending>

## Decisions already taken (owner, 2026-10-05)

- **Edits to guardrail files: ask in the app's permission prompt**, not block.
- **Deleting git-tracked files: ask in the app's permission prompt** (the mechanical backstop for Law 8).
- **Protected set:** settings files, the global `CLAUDE.md` and the installed Design Forge clone, minus the data files its own scripts write.

## Behavior

The Law 32 hook gets two kinds of response. Both are logged to the block log (#113).

- **Deny:** the call is blocked, and Claude sees the reason and what to do instead. This is the hook's existing behavior, exit 2.
- **Ask:** the hook returns `permissionDecision: "ask"`, so Claude Code shows **you** a permission prompt with the reason. Approve and the call runs; decline and it doesn't. Your click in the app is the approval. Text in a file, tool output or web page can't approve it, and neither can Claude.

### Deny: skipping or overriding the guardrails

| Command | Check id | Why |
|---|---|---|
| `git commit --no-verify` or `git commit -n` | `no-verify` | Skips git hooks. Law 32 already forbids any bypass. |
| `git push --no-verify` | `no-verify` | Same. (`git push -n` is a dry run and stays allowed.) |
| `git push --force`, `-f`, `--force-with-lease[=…]`, `--force-if-includes`, or a `+refspec`, **to the default branch** | `force-push-default` | Rewrites the shared history; Law 7. |

A force-push to a feature branch stays allowed, for example after a rebase.

### Ask: changing a guardrail file

**Protected files:**

- `~/.claude/settings.json` and `~/.claude/settings.local.json`
- any project's `.claude/settings.json` and `.claude/settings.local.json`
- `~/.claude/CLAUDE.md`
- everything under the installed clone `~/.design-forge/`, **except** the data files the tools themselves write: `hook-log*`, `ai-inventory*`, `ai-tools.json`, `projects.yaml` (Law 20 registration) and `knowledge/PATTERNS.md` (Law 36, already asks first)

Paths are compared after resolving symlinks. So editing `~/.claude/skills/x/SKILL.md`, which links into `~/.design-forge/skills/`, counts as editing the installed clone. A Design Forge **development checkout** (like this repo) is not the installed clone, so its hook and laws can be edited freely.

**What triggers the prompt:**

- **Edit, Write, MultiEdit and NotebookEdit** on a protected file. These are matched exactly on `file_path`.
- **A Bash command that names a protected file together with a write action:** redirection (`>`, `>>`), `tee`, `sed -i`, `perl -i`, `cp`, `mv`, `ln`, `install`, `rm`, `unlink`, `truncate` or `chmod` with a protected destination. Reading (`cat`, `grep`, `ls`, `git diff`) never asks. This matching is best-effort string matching, as Law 32 already is.
- Not affected: `dforge-update` and `git -C ~/.design-forge pull`, the supported way to change the installed clone.

### Ask: deleting a tracked file

- `rm`, `git rm` or `unlink` on a path that git tracks in the repo the command runs in asks. That includes a directory or pathspec containing tracked files (checked with `git ls-files`).
- Untracked files, ignored files, scratch files and anything outside a git repo stay free.
- `git rm --cached` (untrack, keep the file) stays allowed.

### Unchanged

- **Fail open:** if the hook can't parse a command or resolve a path confidently, it allows the call. The prompt is a backstop, not a judge.
- **Every existing check is unchanged** (Laws 5, 7, 13, 14, 34).
- **`disarm` doesn't lift any of this:** the hook doesn't know about `disarm`, so these guards always apply.

### Permission modes

What `"ask"` does depends on the session's permission mode, and the docs don't spell out every mode. **Before release, each mode the user runs (default, acceptEdits, auto, bypassPermissions) is tested live.** In any mode where `"ask"` would let the call through **without a prompt**, the hook returns **deny** instead, with the message "approve this change yourself or switch permission mode". A guard must never turn into silent permission.

## Acceptance criteria

- [ ] Every Deny row is blocked with a clear reason and a test. A force-push to a feature branch and `git push -n` are allowed.
- [ ] Edit, Write, MultiEdit and NotebookEdit on each protected path return `ask`, including through a symlink into `~/.design-forge`. The excluded data files and a development checkout don't ask.
- [ ] Bash writes to protected files ask, and reads don't. Tests cover each write verb and a read.
- [ ] `rm` and `git rm` of tracked files ask. Untracked, scratch and outside-repo files, and `git rm --cached`, don't. A directory with tracked files inside asks.
- [ ] Asks and denies are logged with their check ids. Asks are logged as type `ask`, so `hook log` can count them.
- [ ] The permission-mode behavior is verified live and recorded in the PR. No mode lets a guarded call through silently.
- [ ] `install.sh` registers the second matcher (`Edit|Write|MultiEdit|NotebookEdit`), merging it as today; the repo's `.claude/settings.json` matches.
- [ ] The Law 32 table gains the new rows and explains ask versus deny; `RELEASES.md` entry; minor version bump (2.25.0).
- [ ] Independent review by a fresh-context Claude subagent before merge (Significant).

## Policy check

- Component library, accessibility, copy: not applicable (no UI). Prompt reasons follow the hook's existing style: name the law, say what to do instead.
- **Conflicts flagged for the owner:**
  1. **Legitimate settings changes now need a click.** For example, "allow npm commands" through the update-config skill. That's intended.
  2. **Bash write detection is string-based.** A determined script can evade it, for example `python3 -c "open(...).write(...)"`. This is a backstop against slips and planted instructions, not a sandbox; Law 32 already says so.
  3. **Law 8 says Claude never deletes files without approval.** The prompt makes that approval mechanical, but only for tracked files; deleting untracked work files stays Claude's judgment, as today.

## Out of scope

- Hook enforcement of Law 38 tier 3 and 4 MCP calls: #138.
- `git clean`, `git checkout -- <file>`, `git restore` and `git reset --hard`, which discard uncommitted changes. They're possible follow-ups, and the block log will show whether they matter.
- Windows paths and shells.
