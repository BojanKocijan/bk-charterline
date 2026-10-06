# Spec — one session, one worktree: parallel sessions never share a checkout (#182)

Intent: [#182](https://github.com/BojanKocijan/design-forge/issues/182) (the issue is the intent; the owner said "add it to the design forge", 2026-10-06, chat)
Design: none (a law sentence, a knowledge section and a skill; no UI)
Approved-by: BojanKocijan, 2026-10-06, chat

## What happened (the case this prevents)

On 2026-10-06, two sessions worked in `~/Documents/GitHub/design-forge`. The #122 session ran `git checkout -b docs/secret-leak-runbook` a few seconds before the #173 session's `git commit`, so the #173 plan commit landed on the #122 branch and went into PR #180. Both PRs also claimed v2.32.0. The #173 session recovered by moving into its own worktree. This spec turns that recovery, and how to avoid needing it, into a rule.

## Behavior

### When a session counts the folder as shared

Before it creates a branch (Law 5), and again whenever a sign below appears, a session checks:

1. **Peers:** `ListAgents` lists another session on this machine for the same project, by its name or title, or the session can't tell which project it's on. `ListAgents` doesn't show a peer's folder, so any doubt counts as shared.
2. **The owner says** sessions run in parallel.
3. **Signs of a collision:** the branch changed between two of your own commands, commits you didn't make, or changes in files you didn't touch.

Shared → branch work happens in the session's own worktree. Not shared → nothing changes.

Already isolated, no change: a cloud session with one assigned branch (Law 5), and a session whose folder is already under `.claude/worktrees/` (the app can start sessions there).

### Setting up a worktree

1. `git fetch origin <default>`.
2. Path: `.claude/worktrees/<issue-or-branch>` in the repo. Confirm it's ignored with `git check-ignore -q .claude/worktrees/x`; if it isn't, add `/.claude/worktrees/` to `$(git rev-parse --git-common-dir)/info/exclude`, which is local and never committed.
3. `git worktree add <path> -b <branch> origin/<default>` for a new branch (then `git branch --unset-upstream`, so the branch doesn't track the default branch), or `git worktree add <path> <branch>` for an existing one.
4. Work from inside it: in Claude Code, `EnterWorktree` with `path`; otherwise `cd` into it before every command.
5. Per worktree: install dependencies (`npm ci`); `node_modules` isn't shared. Untracked local files (`.env.local` and the like) aren't there either; ask the owner before copying one, since it may hold secrets (Law 14).

### Working in it

- One branch per worktree; git refuses to check out a branch another worktree has.
- **Never bare `git stash` / `git stash pop`:** the stash is shared by every worktree of the repo. Prefer a WIP commit; if a stash is unavoidable, `git stash push -u -m <unique-tag>` and apply it by SHA.
- **Plain git commands:** a Claude Code session isolated in a worktree may refuse a compound git command it can't verify stays inside the worktree, `git -C` into another worktree, and any nested shell. Run git commands one at a time from the worktree.
- **`update rules` runs outside the worktree:** `dforge-update` is a shell function, so an isolated session can't start it. The session asks the owner, steps out of the worktree (keeping it), runs `update rules`, and steps back in. It runs no git command in the shared folder meanwhile.
- **Previews (Law 18):** the session in the main folder keeps the project's locked port. A worktree session runs `npm run dev -- --port <locked + 1>` (then +2 … +9 if taken; `strictPort` stays on, so it fails loudly instead of drifting) and writes that port in its `Preview:` footer, marked `(worktree)`.

### Recovering when two sessions collided

1. **Stop.** No commit, reset, checkout or push until you know what happened.
2. **Find out:** `git branch --show-current`, `git log --oneline -5`, `git branch -a --contains <commit>`, `git worktree list`, `ListAgents`.
3. **Save your own uncommitted work** as a patch: `git diff > <scratch>/wip.patch`. It changes nothing.
4. **Move to your own worktree** for your branch, `git cherry-pick` your commits that landed elsewhere, and `git apply` the patch.
5. **Take only your edits out of the shared folder:** `git apply -R <patch>`. Never `git reset --hard`, `git checkout -- .`, `git clean` or `git stash` there: they would wipe the other session's work.
6. **Foreign commits on someone else's branch or PR:** tell the owner, and message that session (`SendMessage`) to drop them. Never rewrite another session's branch yourself.
7. **Versions:** when two PRs claim the same version, the one that merges second takes the next number and stays a draft until the first merges. A newer release tagged before an older one would never reach `dforge-update`.
8. **Report the merge order** for every open PR involved, with any rebase step between them (Law 35).

### Cleanup after the merge (Law 9)

A branch checked out in a worktree can't be deleted. After the merge, from another worktree: `git worktree remove <path>` without `--force`, which refuses a worktree with changes, so it doubles as the check. Then the usual branch cleanup. If it refuses, stop and ask.

## Where it lives

| File | Change |
|---|---|
| `CLAUDE_LAWS.md` | **Law 5**, one sentence: when another session may share the folder, create the branch in your own worktree (`knowledge/SKILLS.md` §6.b, skill `parallel-sessions`); never share one checkout with another session. **Law 18**, one sentence: the main folder keeps the locked port; a worktree session previews on the next free port above it. Version bump |
| `knowledge/SKILLS.md` | New **§6.b "Parallel sessions: one worktree each"**: the rules above, short. Changelog entry |
| `skills/parallel-sessions/SKILL.md` (new) | `name`, `description`, `license` frontmatter (Law 27). The step-by-step commands for setup, recovery and cleanup. Its description triggers on: parallel sessions, another session in the same repo, worktrees, a branch that changed by itself, commits you didn't make |
| `CLAUDE.md` | Knowledge table: the SKILLS.md row also loads for parallel sessions and worktrees |
| `README.md` | Skills count 17 → 18 (two places), version badge |
| `RELEASES.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Release and version sync |

## Acceptance criteria

- [ ] Law 5 and Law 18 each gain the sentence above, nothing more.
- [ ] SKILLS.md §6.b covers when, setup, working, recovery and cleanup, and links the skill.
- [ ] The skill has valid frontmatter and is linked by `install.sh` (it links every `skills/*`), so `dforge-update` reports 18 skills.
- [ ] No step in §6.b or the skill uses `reset --hard`, `checkout -- .`, `clean`, bare `stash` / `stash pop`, or a push to another session's branch.
- [ ] The version follows #180 (v2.32.0) and #181 (v2.33.0): v2.34.0, and it's rebased on whatever lands first.
- [ ] markdownlint and the test suite pass; every relative link resolves.
- [ ] Dry run: this change is built in `.claude/worktrees/issue-182`, set up with the steps above; the PR records the commands and their results.
- [ ] Independent review by a fresh-context subagent before merge (Significant).

## Policy check

- Component library, accessibility, copy: not applicable (no UI).
- **Conflicts flagged for the owner:**
  1. **Detection is best effort.** `ListAgents` shows peers, not their folders. The rule treats any peer on the same project, or any doubt, as sharing. A false positive costs one worktree; a miss costs today's collision.
  2. **Law 18 changes slightly:** the locked port belongs to the main folder; worktree previews use +1 … +9. Without this, two worktrees of one project can't both preview.
  3. **Each worktree costs** a dependency install and disk space. It's created only when the folder is shared.
  4. **No hook:** the hook can't see which sessions share a folder, so this is a rule plus a skill, not an enforced check.

## Amendment 1 — after the independent review (2026-10-07)

Approved-by: BojanKocijan, 2026-10-07, chat

A fresh-context review of the built change found gaps this spec missed:

1. **No checkout or pull in a shared folder.** Law 5 steps 2–3, Law 9's "pull the default branch" and Law 25's session-start `git checkout main && git pull` all run in the folder, and a checkout there moves the other session's branch: that's how the collision happened. Law 5's paragraph becomes: before step 2, check whether another session may use the folder; if so, skip steps 2–3 there, fetch, create the branch in your own worktree, and never check out, switch or pull in the shared folder. This overrides the checkouts and pulls in Laws 9 and 25 and in FULLSTACK_WORKFLOW. Laws 9 and 25 each get a short pointer to it.
2. **Preview ports +100 … +109, not +1 … +9.** Law 20 gives projects consecutive ports (5173, 5174 and 5175 on this machine), so +1 is another project's locked port.
3. **The project is named from the main folder.** In a worktree, `git rev-parse --show-toplevel` ends in the worktree's name (`issue-182`), so session start and Law 20 would register it as a new project. Use the main folder's name: the parent of `git rev-parse --git-common-dir`.
4. **Recovery covers staged and new files.** The patch holds only your files (`git diff HEAD --binary -- <your files>`). New untracked files are moved to your worktree, not left behind. `git restore --staged -- <your files>` runs before `git apply -R`, so nothing of yours stays in the shared index for the other session's next commit.
5. **Wording fixes:** dropping a foreign commit is `git rebase --onto <commit>^ <commit> <branch>` with `--force-with-lease`; the PR that merges second takes the next number (`gh pr ready --undo` turns an open PR back into a draft); a squash-merged branch counts as merged when its PR shows `MERGED` (Law 9); `git worktree add --no-track` replaces the separate unset-upstream step; a session the app started inside a worktree asks the owner to run `update rules` from another session or a terminal, because `ExitWorktree` does nothing there; recovery announces what it found and waits after step 2 (Law 2); removing a clean worktree is Law 9 cleanup, not a Law 8 deletion; if your branch is still checked out in the shared folder, the owner decides which session moves.

## Out of scope

- A hook or script that detects other sessions.
- Changing the app's own worktree settings.
- Moving the open PRs #180 and #181; the recovery for those is already under way.
