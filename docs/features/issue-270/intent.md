# Intent — A SessionStart hook runs the session-start checks (#270)

Issue: [#270](https://github.com/BojanKocijan/bk-charterline/issues/270), part of epic [#267](https://github.com/BojanKocijan/bk-charterline/issues/267) (sub-issue 3) · Gate tier: Significant (a new hook)
Approved-by: <pending>

## Problem

Every session starts with Claude doing chores before it answers the first message. `CLAUDE.md`'s "Session-start behavior" asks for these steps:

1. List the remote's release tags and compare them with the loaded version (Law 28)
2. Detect the project
3. Read `PROJECT_KNOWLEDGE.md` and the active feature
4. Read the language setting in `projects.yaml` (Law 1)
5. Refresh the dashboard
6. Run `gh auth status` (Law 16)
7. Check registration and the port (Laws 18, 20)
8. List open PRs and sweep merged branches (Law 25)

That makes 5 to 8 tool calls before any work starts, and each one costs a round trip and output tokens. The instructions for these steps are also part of the ~27k tokens of rules every session loads. Claude can skip a step or get one wrong, because nothing checks it. And in a cloud session most of these steps don't apply, yet the text still loads.

## Outcome

- At session start, **Claude makes no tool calls.** A `SessionStart` hook runs the checks and hands Claude one short block: rules version and any update notice, the project, the GitHub login, the language setting, the knowledge line, the active feature, open PRs, and the dashboard path.
- Claude prints the confirmation from that block, so its format and content don't change for you.
- The "Session-start behavior" section of `CLAUDE.md` shrinks to a few lines ("print the confirmation from the hook's block; if there is no block, do the steps yourself"). The rules then cost fewer tokens.
- **How we'll know:** a session in any registered project shows the confirmation with 0 tool calls before the first answer (from the session log), and `scripts/laws_cost.py` shows the smaller `CLAUDE.md`.

## Who is affected

- **You**, at the start of every session, in every project. That covers the terminal, the desktop app and cloud sessions.
- **Installs:** `install.sh` registers the hook in `~/.claude/settings.json`, and `update rules` adds it. A plugin install gets it from the plugin's own `hooks/hooks.json`.
- **The Law 32 hook and its update gate (Law 28):** the new script is a hook file, so changes to it need your approval, like the others.
- **The dashboard:** its refresh moves into the hook.

## Constraints

- **Never block or slow a session.** The hook fails open: any error leaves its line out and the session starts. A slow network call (`git ls-remote`, `gh`) gets a short timeout.
- **Writes nothing remote.** Only reads (tags, auth, PR list). Its only local write is registering a new project in `projects.yaml` (Law 20). Deleting merged branches stays with Claude.
- **Stays under the 10,000-character cap** on hook output, or Claude only gets a preview.
- **Works without the hook.** Without it (claude.ai web, a plugin install from before this change), Claude still does the steps itself.
- **Stdlib Python only, no new dependencies**, like the other hooks.
- **Small PRs** (Law 31): probably 1) the hook and its tests, 2) `install.sh` and the plugin registration, 3) the `CLAUDE.md` cut, each with its measurement.

## Open questions

Answered by the owner, 2026-10-09, chat:

- [x] **Branch sweep (Law 25):** the hook lists the merged branches it finds, and Claude deletes them only when there are some. The hook never deletes anything.
- [x] **Language (Law 1):** the hook reports `language: not set`, and Claude's first reply is the Law 1 question, as today.
- [x] **Registration (Law 20):** the hook registers the project itself (a local `projects.yaml` edit, no network or git) and reports the port in its block.
- [x] **Triggers:** `startup`, `clear` and `compact`. Resumes and forks keep their context, so they don't trigger it.
- [ ] **An always-on slot for the laws** (a plugin hook's `additionalContext`, up to 10,000 characters) goes to #275, after the cut. Owner: BojanKocijan
