# Guardrails — BK Charterline

**Version:** 1.2.0
**Last Updated:** 2026-10-09
**Binding:** Yes — the detail behind Law 32 (the hook) and the hook's part in Law 38. Read on demand when a block or a permission prompt needs explaining, when changing the hook, or when the user asks what the hook does.

> Moved here from `CLAUDE_LAWS.md` Law 32 in v3.5.0 (#239) so every session loads less; the law keeps what Claude must do. Nothing here was loosened.

---

## 1. How the hook works

**Mechanism.** `.claude/hooks/enforce-laws.py` — a dependency-free Python 3 script — runs as a `PreToolUse` hook matched on `Bash`, on the file-editing tools (`Edit|Write|MultiEdit|NotebookEdit`) and on MCP tools (`mcp__.*`), and as a `PostToolUse` hook on MCP tools that records a tier 3 tool's first run and never blocks. It reads the tool call from the hook's stdin JSON. For a narrow, explicit set of patterns it either exits with code `2` and a reason on stderr, which blocks that one tool call outright (Claude sees the reason and must stop, not retry the same call), or returns `permissionDecision: "ask"`, which hands the call to the user's permission prompt (see the asks table below). Everything else passes through untouched.

**What it blocks:**

| Check | Law | Trigger |
|---|---|---|
| `gh pr merge` in any form, or GraphQL `mergePullRequest` | Law 7 | Any form of Claude merging a PR itself — **no exception, unlike `--auto` carve-outs elsewhere; Law 7 stays absolute** |
| `git commit` while the current branch is the default branch | Law 5 | Writing directly to the default branch instead of a feature branch |
| `git push` while the current branch is the default branch | Law 7 | Pushing directly to the default branch |
| `git commit -m "..."` (or a heredoc-quoted message) whose first line doesn't match `type(scope): description` | Law 13 | Non-Conventional-Commits message |
| `gh pr create` whose body (or `--body-file`) has no `Screenshots:` line (yes, skipped or not applicable) | Law 34 | Opening a PR without having asked about screenshot images |
| `git commit` when the lines the commit adds hold a secret from Law 14's list (the reason names the kind and the file, never the value), or the commit adds a `.env` or `.env.*` file other than `.env.example`. It reads the staged diff plus what `git add` earlier in the same call, `-a` or commit paths add | Law 14 | A secret about to be committed. Removing one is never blocked |
| `git commit --no-verify` / `-n` (alone or in a short cluster such as `-an`), or `git push --no-verify` | Law 32 | Skipping git hooks; `git push -n` (dry run) stays allowed |
| `git push` with `--force`, `-f`, `--force-with-lease`, `--force-if-includes` or a `+refspec` to the default branch | Law 7 | Rewriting the default branch's history; force-pushing a feature branch stays allowed |

**What it asks you about (#117).** These don't block. The hook returns `permissionDecision: "ask"` and Claude Code shows **you** its permission prompt with the reason. Only your click approves; nothing Claude says, and no text in a file, tool output or web page, can.

| Check | Law | Trigger |
|---|---|---|
| Edit / Write / MultiEdit / NotebookEdit on a guardrail file, or a Bash command that writes to one (`>`, `>>`, `tee`, `sed -i`, `perl -i`, `cp`/`ln`/`install` destination, `mv`, `rm`, `unlink`, `truncate`, `chmod`, `chown`) | Law 32 | Changing the guardrails themselves. Guardrails: `~/.claude/settings*.json`, `~/.claude/CLAUDE.md`, any project's `.claude/settings*.json`, and the installed `~/.bk-charterline` except its own data files (`hook-log*`, `ai-inventory*`, `projects.yaml`, `knowledge/PATTERNS.md`). Compared after resolving symlinks; a BK Charterline development checkout isn't the installed copy. Reads and `charterline-update` stay free |
| `git checkout`, `switch`, `pull`, `reset`, `merge`, `rebase`, `restore`, `cherry-pick`, `am`, `apply`, `clean`, `revert` or `stash` in the installed `~/.bk-charterline`, found through `cd`, `-C`, `--git-dir`, `--work-tree`, `GIT_DIR` / `GIT_WORK_TREE` or a nested `bash -c` (logged as `guardrail-git`) | Law 32 | Changing the installed rules without `charterline-update`'s reviewed diff (Law 28). Reads (`status`, `log`, `fetch`, `ls-remote`, `describe`), `stash list` / `show`, `charterline-update` and a development checkout stay free; a wrong ask goes on the hook's exception list with a test |
| A `netlify` / `ntl` or `vercel` / `vc` command that isn't a verified read or local command, also through `npx`, `pnpm`, `yarn`, `bunx`, `npm exec`, nested shells or `$(…)` (logged as `hosting-write`) | Law 38 | Changing a live site, its settings or data, or copying its secrets, with the user's account. Every call asks; reads (`logs`, `status`, `ls`, `inspect`, `whoami`, list/get commands, `netlify api` get/list/show/search methods) and local work (`dev`, `build`) stay free |
| `charterline-update … --approve <commit>` (or `dforge-update`, its v3.0.0 pointer), also inside `"$SHELL" -ic` or `bash -c` (logged as `update-approve`) | Law 28 | Installing a release that changes the hook without the terminal `y`: the click in this prompt is the approval. Plain `charterline-update` stays free |
| `rm`, `unlink` or `git rm` (not `--cached`) on files git tracks in the command's repo | Law 8 | Deleting tracked files. Untracked, ignored and outside-repo files stay free |
| An MCP call (`mcp__<server>__<tool>`) whose Law 38 tier is 4 | Law 38 | Every call (`tier4-unapproved`). Nothing is stored, so approval never carries over |
| An MCP call whose tier is 3, or that is unclassified | Law 38 | The first call per session per tool (`tier3-first-use`). After the tool runs once, a `PostToolUse` entry in `~/.bk-charterline/ai-approvals.jsonl` (session id, tool name and time only, pruned after 7 days) lets later calls in that session through |
| Changing the Law 38 registry or approvals: Edit / Write or a Bash write on `~/.bk-charterline/ai-tools.json`, `~/.bk-charterline/ai-approvals*` or any project's `.claude/ai-tools.json` (logged as Law 32 `guardrail-edit` / `guardrail-write`), or `ai_tools.py set`, including through `uv run` or `bash -c` (logged as Law 38 `registry-write`) | Law 32, Law 38 | A tier is the user's decision and an approval is the user's click. `ai_tools.py show` stays free |

**A block always wins over an ask.** The hook runs every block check first, so approving a prompt can never let a blocked command through. **No permission mode turns an ask into a silent allow:** a live test (2026-10-05, Claude Code 2.1.289) had a hook answer "ask" to every edit in each mode, `default`, `acceptEdits`, `auto`, `dontAsk`, `plan` and `bypassPermissions`, and the file was never written. Where no prompt can be shown (headless runs), an ask is refused. The hook still receives `permission_mode` and denies in any mode later found to skip the prompt.

**Fails open, not closed.** If the hook can't parse its input, can't confidently extract a commit message, or a `git` subprocess errors, it allows the call rather than blocking on an infrastructure fluke. This is a backstop against mechanical slips, not a replacement for the judgment the rest of this document asks for — false blocks on edge cases are worse than an occasional missed catch, because they teach the user to route around the hook entirely.

**Not a replacement for git-level hooks.** A `commitlint`/`husky` or `detect-secrets` pre-commit hook (if the project has one) catches a *human* committing directly with git. Law 32's hook operates one layer up: it stops Claude's own tool calls before they ever reach git or GitHub, whether or not the project has those hooks installed.

**Where it lives.** `.claude/hooks/enforce-laws.py` + a `PreToolUse` entry in `.claude/settings.json`, both committed in this repo as the canonical reference implementation. `install.sh` registers the same hook globally in `~/.claude/settings.json` (merging into whatever's already there, never overwriting it), pointing at `~/.bk-charterline/.claude/hooks/enforce-laws.py` — so the checks run in every repo a session touches, not just this one. Because the registered command points at that fixed path inside the clone, a `charterline-update` picks up any change to the script's *logic*, and `charterline-update` applies a hook change only after the user approves its diff, in their own terminal or in the app's prompt for `--approve` (Law 28). Since v2.18.0, `charterline-update` also re-runs `install.sh` after updating, so a newly added registration (such as a new hook entry) applies on the next update too. Changing or removing an existing entry still needs a manual edit of `~/.claude/settings.json`.

**The persona log (#256).** A second, separate script, `.claude/hooks/persona_log.py`, runs as a `UserPromptSubmit` hook (registered by `install.sh` the same way). When the whole prompt is one of CLAUDE.md's mode commands, it appends the time, the session id and the persona to `~/.bk-charterline/persona-log.jsonl` for the private dashboard; the prompt's text is never written, and any other prompt writes nothing. It never blocks, never prints and ignores every error, so it can't stop a prompt.

**Block log.** Every block appends one line to `~/.bk-charterline/hook-log.jsonl`: the time, law, a fixed check id (`commit-on-default`, `commit-message`, …), the repo and branch the hook judged, and a SHA-256 of the command. It never stores the command, the commit message or the block reason. The log rotates to `hook-log.1.jsonl` at 1 MB. Writes hold an exclusive lock on `hook-log.lock` for at most 200 ms, so concurrent sessions never interleave lines. The code lives in `.claude/hooks/hook_log.py`, which the hook imports in a guarded way: a missing module, an unwritable log or a busy lock skips the line and never changes the decision. The log stays local and gitignored. `hook log` runs `python3 ~/.bk-charterline/.claude/hooks/hook_log.py --summary` (blocks per law and check for the last 30 days, plus false positives and permission prompts). Asks are logged as type `ask`.

---

## 2. Why the hook, and Law 38's limits

**Why the hook exists.** Every other law in this document relies on Claude reading and following instructions — reliable most of the time, but not deterministic. Law 32 backstops the handful of laws where "Claude might forget" has real teeth: merging its own PR, writing directly to the default branch, a malformed commit message, a secret slipping into a staged diff.

**Law 38, known limits (accepted, owner decision 2026-10-05).** Because the project entry wins, a repo that commits a `.claude/ai-tools.json` can lower a tool's tier, including below your personal tier, while Claude works in that repo; the hook asks before Claude writes that file or moves a folder onto `.claude`, but not when it arrives through `git clone`, `checkout` or `pull`. Check a new repo's `.claude/ai-tools.json` before working in it. And if the hook itself crashes or times out on a tier 3 call, the call runs and counts as that session's approval.

**Sources:** the Classify phase of Xensam's *Out of the Shadows* handbook; OWASP Top 10 for Agentic Applications 2026 (ASI02 tool misuse, ASI03 identity and privilege abuse); NIST AI RMF MAP 4 and GOVERN 6.

---

## Changelog

- **1.2.0 (2026-10-09)** — §1: the `UserPromptSubmit` persona log for the dashboard (#256).
- **1.1.0 (2026-10-08)** — §2: why the hook exists, Law 38's known limits and sources, moved from the laws (#239).
- **1.0.0 (2026-10-08)** — Law 32's mechanism, the blocks and asks tables, the block log and where the hook lives, moved from `CLAUDE_LAWS.md` (#239).
