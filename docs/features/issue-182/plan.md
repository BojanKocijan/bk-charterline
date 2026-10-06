# Plan — one session, one worktree: parallel sessions never share a checkout (#182)

Spec: [spec.md](spec.md) · Gate tier: Significant · Branch: `docs/parallel-sessions-worktrees` · Issue: #182
Work pile: judgment-heavy (the wording of a law and a workflow; done interactively in this session's own worktree)
Approved-by: BojanKocijan, 2026-10-06, chat

## One PR

Spec, plan and implementation in one PR: 10 files and about 330 lines, inside Law 31's ceilings. Release v2.34.0 (main is at v2.33.0; #119 queues behind this one).

## Files to change

| File | Change |
|---|---|
| `CLAUDE_LAWS.md` | **Law 5:** after "No code is written on a stale branch …", one sentence: "**Parallel sessions.** When another session may work in the same folder, create the branch in your own worktree (`knowledge/SKILLS.md` §6.b, skill `parallel-sessions`); never share one checkout with another session." **Law 18:** one bullet: the main folder keeps the locked port; a worktree session runs `npm run dev -- --port <locked + 1>` (up to +9 if taken) and marks its footer `(worktree)`. Version 2.34.0 |
| `knowledge/SKILLS.md` | New **§6.b "Parallel sessions: one worktree each"** after §6.a: when it applies (three checks, and who is already isolated), setup (five steps), working rules (one branch per worktree, the shared stash, plain git commands, `update rules` outside the worktree, previews), recovery after a collision (eight steps, condensed), cleanup. Links the skill. Changelog entry 1.1.0 |
| `skills/parallel-sessions/SKILL.md` (new) | Frontmatter: `name: parallel-sessions`, `description` (triggers: parallel sessions, another session in the same repo, worktrees, a branch that changed by itself, commits or edits you didn't make), `license: GPL-3.0-only`. Body: read §6.b, then three procedures with the exact commands: **A. Set up your worktree**, **B. Recover from a collision**, **C. Clean up after the merge** |
| `CLAUDE.md` | Knowledge table: the SKILLS.md row also loads for "parallel sessions / worktrees" |
| `README.md` | Skills count 17 → 18 (the overview box and the file tree), version badge |
| `RELEASES.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | v2.34.0, version sync (Law 27) |
| `docs/features/issue-182/plan.md` | This plan |

`install.sh` needs no change: it links every `skills/*` folder (line 244), so the next update reports 18 skills.

## Order of work

1. **`knowledge/SKILLS.md` §6.b.** Done when every heading under the spec's Behavior has a home there and markdownlint is clean.
2. **The skill.** Done when its frontmatter has `name`, `description` and `license`, and each procedure's commands match §6.b.
3. **Laws, `CLAUDE.md`, README.** Done when the Law 5 and Law 18 sentences are in, and every relative link in the changed files resolves.
4. **Release.** Done when `release_version.py check` prints `2.34.0`.
5. **Independent review** by a fresh-context subagent given the spec, this plan and the diff (Significant). Findings go into the PR, ranked.

## Proof

- **Tests:** none change (docs and a skill only). `python3 -m unittest discover -s tests` must still pass.
- **No step discards another session's work:** grep §6.b and the skill for `reset --hard`, `checkout -- .`, `git clean`, `stash pop`, `--force`; each hit must sit in a "never" sentence.
- **Dry run, recorded in the PR:** this branch was set up with the spec's steps (`git fetch`, `git check-ignore`, `git worktree add … -b … origin/main`, `git branch --unset-upstream`, `EnterWorktree`), and the recovery steps were used on 2026-10-06 for #173 / #180 (patch, own worktree, cherry-pick, `git apply -R`, message to the other session, version order). `update rules` was run by stepping out of the worktree.
- **Commands:** `python3 -m unittest discover -s tests`, `python3 scripts/release_version.py check`, markdownlint, the link check.
- **Visual evidence:** none (no UI). `Screenshots: not applicable`.

## Risks

- **The laws load every session**, so they must stay short. → One sentence in Law 5, one bullet in Law 18; the detail lives in §6.b and the skill.
- **Claude Code's worktree guard may change** what it refuses. → The text says "may refuse" and names the pattern, not exact error messages.
- **`--port` and `strictPort`:** the CLI's `--port` overrides `server.port` in `vite.config.ts`, and `strictPort` still stops it from drifting to a random port. → Stated in §6.b.
- **Detection misses a peer** that `ListAgents` doesn't show (a session on another tool). → The collision signs in step 3 of "when it applies" catch it after the fact, and recovery is documented.

## Ruled out

- **A hook:** it can't see which sessions share a folder.
- **A new law number:** the rule belongs where branching happens, in Law 5.
- **The full procedure in both places:** §6.b holds the rules, the skill holds the commands, and each links the other.
- **Always using a worktree, even alone:** it costs an install and disk space on every task, for a risk that only exists with a second session.
