---
name: parallel-sessions
description: Run parallel Claude sessions safely — each session that does branch work while another may use the same repo folder works in its own git worktree. Sets up the worktree, recovers when two sessions collided (a branch that changed by itself, commits or edits you didn't make, a commit on the wrong branch or PR), and cleans up after the merge. Invoke before creating a branch when ListAgents shows another session on the same project or the owner says sessions run in parallel, and on any sign of a collision.
license: GPL-3.0-only
---

# Parallel sessions: one worktree each

Read [`knowledge/SKILLS.md`](../../knowledge/SKILLS.md) §6.b for the rules (when the folder counts as shared, the working rules, why), then follow the procedure that fits. Run git commands one at a time: a session isolated in a worktree may refuse compound ones.

**In the shared folder, never check out, switch or pull** (Law 5, "Parallel sessions"). Fetching is fine.

## A. Set up your worktree

From the repo's main folder, before creating the branch:

1. Find and fetch the default branch:
   `git symbolic-ref refs/remotes/origin/HEAD` (strip `refs/remotes/origin/`), then `git fetch origin <default>`.
2. Make sure git ignores the worktree folder:
   `git check-ignore -q .claude/worktrees/x`. If that fails, append `/.claude/worktrees/` to `<common-dir>/info/exclude` (`git rev-parse --git-common-dir` prints the directory), then check again. Never add it to a tracked `.gitignore`.
3. Create the worktree, one per branch:
   - new branch: `git worktree add --no-track -b <branch> .claude/worktrees/<issue-id> origin/<default>`. `--no-track` keeps the branch from pushing to the default branch.
   - existing branch: `git worktree add .claude/worktrees/<issue-id> <branch>`
4. Enter it: `EnterWorktree` with `path` set to the worktree's absolute path. From here on, every command runs there. Push the new branch with `git push -u origin <branch>`.
5. Install dependencies if the project has them: `npm ci`. If the work needs an untracked local file (`.env.local` and the like), ask the owner before copying it in.
6. Name the project from the main folder (Laws 18 and 20): the parent of `git rev-parse --git-common-dir`, not the worktree's folder name.
7. Preview (Law 18): `npm run dev -- --port <locked + 100>` (up to +109 if taken), and write `(worktree)` after the URL in your `Preview:` footer.

To run `update rules` later: ask the owner, call `ExitWorktree` with `action: "keep"`, run it, then `EnterWorktree` with the same `path` again. Run no git command in the shared folder meanwhile. If the app started this session inside the worktree, `ExitWorktree` does nothing: ask the owner to run `update rules` from another session, or `dforge-update` in a terminal.

## B. Recover from a collision

Signs: the branch changed between two of your commands, commits you didn't make, or edits in files you didn't touch.

1. **Stop.** No commit, reset, checkout or push yet.
2. **Find out what happened:**
   - `git branch --show-current` and `git log --oneline -5`
   - `git branch -a --contains <your-commit>`: which branches carry your commit
   - `git worktree list` and `ListAgents`: who else is here
   - `gh pr list`: whether a PR already carries your commit

   Tell the owner what you found and the steps below you plan to take, and wait for a go-ahead (Law 2).
3. **Save your work, which changes nothing:**
   - `git status --porcelain` lists every changed file. Pick the ones you edited or created.
   - Your edited files, staged or not, go in a binary patch: `git diff HEAD --binary -- <your edited files> > <scratchpad>/wip.patch`. Read it: if a file in it has changes you didn't make, leave that file out and tell the owner.
   - Note your new, untracked files: the patch doesn't carry them.
4. **Rebuild your branch in your own worktree,** still from the main folder:
   - `git worktree add .claude/worktrees/<issue-id> <your-branch>`, or `git worktree add --no-track -b <your-branch> .claude/worktrees/<issue-id> origin/<default>` if it doesn't exist yet. If git refuses because your branch is checked out in the shared folder, the other session is on your branch: stop, and the owner decides which session moves.
   - `git -C .claude/worktrees/<issue-id> cherry-pick <each stray commit of yours>`
   - `git -C .claude/worktrees/<issue-id> apply <scratchpad>/wip.patch`
   - Move each new file of yours: `mv <file> .claude/worktrees/<issue-id>/<file>` (create the folder first if needed).
5. **Take only your edits out of the shared folder:**
   - `git restore --staged -- <your edited files>`, so nothing of yours stays in the shared index for the other session's next commit
   - `git apply -R --check <scratchpad>/wip.patch`, then `git apply -R <scratchpad>/wip.patch`
   - `git status`: nothing of yours left, nothing else changed.

   **Never** `git reset --hard`, `git checkout -- .`, `git clean` or a stash there: they would wipe the other session's work.
6. **Enter your worktree:** `EnterWorktree` with its `path`.
7. **Foreign commits on another session's branch or PR:** tell the owner, and `SendMessage` that session: which commit is yours, where it landed, that you changed nothing of theirs, and the fix for it to run on its own branch: `git rebase --onto <your-commit>^ <your-commit> <their-branch>`, then `git push --force-with-lease origin <their-branch>`. **Never** rewrite or push another session's branch yourself.
8. **Versions:** when two PRs claim the same version, the PR that merges second takes the next number. If that's yours, keep it a draft: `gh pr create --draft`, or `gh pr ready <n> --undo` if it's already open. After the other merges: `git fetch origin <default>`, `git rebase origin/<default>`, resolve `RELEASES.md` and the version files (newest release on top), `git push --force-with-lease --force-if-includes origin <your-branch>`, then `gh pr ready <n>`.
9. **Give the owner the merge order** for every PR involved, with each rebase step between them (Law 35).

## C. Clean up after the merge (Law 9)

An isolated session can't remove the worktree it's in: switch first, with `EnterWorktree` into another worktree, or ask the owner to let you step out.

1. Confirm the merge: `gh pr view <n> --json state` shows `MERGED`. After a squash merge the branch isn't an ancestor of the default branch, so don't rely on `git merge-base --is-ancestor` alone.
2. Remove the worktree: `git worktree remove .claude/worktrees/<issue-id>`. **Never** add `--force`: without it, git refuses a worktree with changes, so this is your check. If it refuses, stop and ask the owner. Removing a clean worktree is Law 9 cleanup, not a Law 8 deletion.
3. Delete the branch: `git branch -D <branch>`, and `git push origin --delete <branch>` if GitHub didn't already.
4. Confirm the linked issue is closed (Law 9). In a shared folder, `git fetch origin <default>` replaces Law 9's pull.
