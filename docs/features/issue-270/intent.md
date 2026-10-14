# Intent — A SessionStart hook runs the session-start checks (#270)

Part of epic [#267](https://github.com/BojanKocijan/bk-charterline/issues/267) · Issue: [#270](https://github.com/BojanKocijan/bk-charterline/issues/270) · Gate tier: Significant (High: a new hook, `install.sh` and the plugin manifest)
Approved-by: BojanKocijan, 2026-10-14, chat (with Claude's proposals for the three owner questions)

## Problem

Before the first reply, every session asks Claude to run the session-start checks itself. These are the steps in `CLAUDE.md` "Session-start behavior", plus Laws 18, 20 and 25:

- the newest release tag (`git ls-remote`)
- the language setting and the project's port (`projects.yaml`)
- the repo name, `PROJECT_KNOWLEDGE.md` and the active feature
- the dashboard refresh
- `gh auth status`
- pulling the default branch, open PRs, and sweeping merged branches

That costs twice:

1. **Instructions.** The session-start section of `CLAUDE.md` alone is 4,444 bytes, about 1,800 tokens (estimate, `BYTES_PER_TOKEN` 2.423). Law 25 and parts of Laws 18, 20 and 28 add to that. Every session pays this, including sessions that never write code.
2. **Tool calls.** About 5 to 10 calls before the user gets an answer. Each one adds time and its output to the context.

The checks also aren't reliable, because Claude has to remember to run them. On 2026-10-12, a cloud session answered the user's first question without running them or printing the confirmation.

## Outcome

- **Claude makes 0 tool calls at session start.** A `SessionStart` hook runs the checks and gives Claude one short block of context.
- **The confirmation still prints** with the same fields (rules version, project, persona, GitHub, knowledge, feature, dashboard), and so does the update notice when a newer release exists.
- **The session-start section of `CLAUDE.md` shrinks** to roughly "print what the hook gave you, and what to do when it gave you nothing". `laws_cost.py` shows the cut in the PR.
- **We'll know it worked when:**
  - a fresh local session and a fresh cloud session in this repo each print the confirmation with no tool call before it;
  - the hook's tests pass;
  - the measured token count drops.

## Who is affected

- **Everyone using BK Charterline**, through the global install (`install.sh` → `~/.claude/settings.json`). Every session, in every project.
- **Plugin installs.** The hook has to ship with the plugin (Law 27), not only with `install.sh`.
- **Cloud sessions.** There is no `~/.bk-charterline` and usually no `gh` login. The repo copy of the hook is used (as in #268).
- **claude.ai web.** There are no hooks and no shell there, so `CLAUDE.md` keeps a short fallback.
- **The Law 32 guardrail hook.** A new script under `.claude/hooks/` becomes part of what `charterline-update` shows and asks about (Law 28).

## Constraints

- **Fails open and runs fast.** A slow or missing network (`ls-remote`, `gh`) must never stall or block the session. A failed check leaves its line out, or shows `unknown`.
- **Law 28: never auto-pull the rules.** The hook only reports that an update exists.
- **Law 1: the language question still comes from Claude.** When the setting isn't set, the hook says so, and Claude asks as its whole first reply.
- **Law 32 / Law 28: approvals.** The new hook file goes through the same approval as any hook change. Nothing in it can approve anything.
- **Law 5, parallel sessions:** a hook that checks out or pulls in a folder another session uses breaks that session.
- **Law 27:** the plugin stays valid and submittable.
- **Tests:** the existing tests (`tests/test_enforce_laws.py`, `tests/test_laws_structure.py`) stay green.
- **Rules still bind without the hook.** Removing the hook must not remove any rule. Only who runs the check changes.

## Open questions

- [x] **Which steps move into the hook?** Decided 2026-10-14: read-only only; the hook reports, Claude acts. Only the read-only checks (version, project, language, port, knowledge, feature, GitHub login, open PRs)? Or also the steps that change things: pulling the default branch (Law 25), deleting merged branches, registering the project in `projects.yaml` (Law 20), creating the one-line local `CLAUDE.md` (Law 11), refreshing the dashboard? Proposal: read-only only, and the hook *reports* what Claude should do (for example "main is 3 commits behind", "not registered"). — owner: BojanKocijan
- [x] **Network time budget:** Decided 2026-10-14: 3 seconds each, in parallel; a timed-out check is left out. what's the longest the hook may wait for `ls-remote` and `gh pr list` before giving up on those lines? Proposal: 3 seconds each, run in parallel. — owner: BojanKocijan
- [ ] **Plugin delivery:** can a plugin's `hooks/hooks.json` register a `SessionStart` hook that adds context? And is there an always-on context slot a plugin can use instead of `CLAUDE.md` (the issue asks)? To be checked in the Claude Code docs before the spec. — owner: Claude
- [x] **GitHub line in cloud sessions,** Decided 2026-10-14: `GitHub: via connector`. where `gh` isn't logged in: print `GitHub: via connector` (or similar), not `unauthenticated`, so we don't block GitHub work that goes through the GitHub tools? — owner: BojanKocijan
