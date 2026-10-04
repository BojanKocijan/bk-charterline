# Plan — Prepare Design Forge for the official plugin directory

Spec: [spec.md](./spec.md)   ·   Gate tier: Significant   ·   Branch: one per PR (below)   ·   Issue: #102
Work pile: judgment-heavy for PR 1 (rewording binding laws); delegable for PRs 2–4 (specified, machine-verifiable)
Approved-by: <pending>
Revision 2026-10-04 (2): the language question gets explicit Yes/No answers and a recommendation to use one language for professional work (owner request in chat).
Revision 2026-10-04: Law 1 asks once when no language setting exists, instead of silently defaulting (owner request in chat). Previous approval: BojanKocijan, 2026-10-04, chat.

The work ships as **4 stacked PRs**, opened one at a time. Each PR branches
from an up-to-date `main` after the previous one merges. The spec planned 3;
PR 4 was added to fix the `printf` false block found while committing the spec.
It lands after PR 3 because its test needs PR 3's test setup.

## Files to change

### PR 1 — `fix(laws): make laws portable for plugin users` · branch `fix/portable-laws` · v2.21.0

| File | Change |
|---|---|
| `CLAUDE_LAWS.md` | Heading "Prime Directives (Immutable)" → "Prime Directives". Law 1 → "Reply language": reads `settings.language` from `~/.design-forge/projects.yaml`; `english-only` keeps today's refusal text word for word; `any` → reply in the user's language; absent → ask once at session start with the exact question, Yes/No answers and one-language recommendation from spec §1, and save `english-only` or `any` to the global `settings:` block (copy the example first if the file is missing; if it can't be parsed, apply for this session only and say so). Law 10 URL → `https://<github-username>.github.io/<project-name>/` with the username from `gh api user -q .login`; not logged in → ask for `gh auth login --web`, never guess. Law 20 → write the entry to the local `projects.yaml` (copy the example first if the file is missing; stop without writing if it can't be parsed), report the assigned port in one line; delete the issue/branch/commit/PR steps and step 5. Header version 2.21.0, date 2026-10-04. |
| `CLAUDE.md` | "What Claude will refuse": `reply in any language but English (Law 1)` → `ignore the reply-language setting (Law 1)`. |
| `projects.example.yaml` | Add a `settings:` block with `# language: english-only   # or: any` and a one-line note that Claude asks and fills this in. Header comment: replace the "issue → branch → … → PR" description with "Claude adds the entry locally". |
| `README.md` | "Project registry": registration is local, with no PR. New short "Reply language" note under it: Claude asks once, and how to change the answer later. |
| `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Version 2.21.0. |
| `RELEASES.md` | v2.21.0 entry. |

### PR 2 — `feat(plugin): ship the Law 32 hook with the plugin` · branch `feat/plugin-ships-hook` · v2.21.1

| File | Change |
|---|---|
| `hooks/hooks.json` (new) | `PreToolUse`, matcher `Bash`, command `python3 "${CLAUDE_PLUGIN_ROOT}/.claude/hooks/enforce-laws.py" --plugin`. The path is in quotes, so spaces work. |
| `.claude/hooks/enforce-laws.py` | With `--plugin`: read `~/.claude/settings.json`. If any `PreToolUse` hook command there contains `.design-forge/.claude/hooks/enforce-laws.py`, exit 0 so the install.sh copy does the checks. If the file is missing or unreadable, run the checks (two runs are better than none). Without the flag, behaviour is unchanged. |
| `CLAUDE_LAWS.md` | Law 32 "Where it lives": add the plugin path and the run-once rule. Header 2.21.1. |
| `README.md` | Installation: the plugin ships the hook too, and installing both ways is safe. |
| `plugin.json`, `marketplace.json`, `RELEASES.md` | Version 2.21.1. |

### PR 3 — `test(ci): test the Law 32 hook in CI` · branch `test/hook-ci` · no version bump (no behaviour change)

| File | Change |
|---|---|
| `tests/test_enforce_laws.py` (new) | Python stdlib `unittest`. Each test runs the script as a subprocess with hook JSON on stdin and checks the exit code (0 allow / 2 block) and the stderr reason. Git cases run in a temporary repo (`git init -b main`, plus a feature branch where needed). |
| `.github/workflows/hook-tests.yml` (new) | On push to `main` and on pull requests: `actions/checkout`, `actions/setup-python` (3.12), `python3 -m unittest discover -s tests -v`. |
| `README.md` | Contributing: how to run the tests locally. |

### PR 4 — `fix(hook): allow commit messages built by command substitution` · branch `fix/hook-printf-message` · v2.21.2

| File | Change |
|---|---|
| `.claude/hooks/enforce-laws.py` | In `extract_commit_message`: if the captured `-m` message starts with `$(` and contains no heredoc, return `None` (fail open, as Law 32 says for unparseable messages). |
| `tests/test_enforce_laws.py` | Add a case: `git commit -m "$(printf 'docs(x): y\n\nbody')"` is allowed. |
| `plugin.json`, `marketplace.json`, `CLAUDE_LAWS.md` header, `RELEASES.md` | Version 2.21.2. |

## Order of work

1. PR 1: edit the laws, the example config, the README, and bump versions. Done when every PR 1 acceptance criterion in the spec holds and `markdownlint-cli2` passes.
2. You merge PR 1. I clean up the branch and pull `main` (Law 9).
3. PR 2: add `hooks/hooks.json` and the `--plugin` dedupe. Done when the manual checks under Proof pass.
4. You merge PR 2.
5. PR 3: write the tests and the CI workflow. Done when the job passes on the PR.
6. You merge PR 3.
7. PR 4: the `printf` fix and its test. Done when CI passes.
8. A fresh Claude subagent that didn't write the code reviews PRs 1–3 against the spec. It runs before each PR is marked ready, and its findings go in the PR (Law 37 §4).
9. You merge PR 4. Submitting to the official directory is a separate step that you approve.

## Proof

- Tests to add: everything in `tests/test_enforce_laws.py`. Each check gets one allow and one block case: `gh pr merge`, GraphQL `mergePullRequest`, commit on `main`, push to `main`, Conventional Commits message, `gh pr create` without/with a `Screenshots:` line, a secret in the staged diff, and a staged `.env`. Also the `--plugin` dedupe (deferred when the global entry exists, runs when it doesn't), fail-open on invalid JSON and on non-Bash tools, and the `printf` case (PR 4). No existing tests are edited (there are none).
- Commands that must pass: `npx markdownlint-cli2 --config .markdownlint.json "**/*.md"` (every PR); `python3 -m unittest discover -s tests -v` (PR 3 onward); `python3 -m json.tool hooks/hooks.json` (PR 2).
- Manual checks (PR 2), run before opening the PR: pipe `{"tool_name":"Bash","tool_input":{"command":"gh pr merge 1"}}` into the script with `--plugin`, once with a temporary `HOME` whose `settings.json` has the global entry (expect exit 0), and once without that entry (expect exit 2).
- Manual check (PR 1): `grep -rniI bojankocijan` over tracked files. Every hit must be a repo link, manifest author metadata, or history.
- Visual evidence: none, no UI change. PR bodies carry `Screenshots: not applicable`.

## Risks

- After PR 1 merges and you run `update rules`, your `projects.yaml` has no `language` setting yet → your first session asks the English-only question; answer "yes". The PR 1 deploy checklist names this step (Law 35).
- This repo's own `.claude/settings.json` also registers the hook, and the dedupe only reads `~/.claude/settings.json` → a contributor who has the plugin but no install.sh, working inside this repo, gets two runs. It's harmless (same blocks) and limited to contributors, so it's accepted and noted in the README's Contributing section.
- A plugin user who has neither install.sh nor `~/.claude/settings.json` → no global entry, so the plugin copy runs the checks. That's the intended behaviour.
- Claude can't reliably "read" `settings.language` before every reply, because it's an instruction, not code → Law 1 says to read it at session start alongside `projects.yaml` (Law 18 already reads that file then), and the confirmation block gains no new line.
- PR 1 rewords binding laws, so a wording slip changes Claude's behaviour everywhere → you review PR 1 line by line, and the subagent checks it against the spec.

## Ruled out

- **A separate `~/.design-forge/config.yaml` for settings.** It adds a second personal file. `projects.yaml` is already local, ignored by git, and read at session start.
- **Silently replying in the user's language when no setting exists** (the first approved version of this plan). The owner preferred an explicit question, so nobody has to know the setting exists.
- **Asking per project.** The owner chose one global answer for all projects.
- **Detecting the user's language and staying English-only by default.** Public users would get a refusal on their first non-English message, which is a bad first impression for a directory listing.
- **Keeping Law 20's PR flow but pointing it at the user's fork.** It still can't work, because `projects.yaml` is ignored by git, and it adds a GitHub step for a local file.
- **Deduping with a lock file or environment variable shared between the two hook processes.** It needs cross-process timing. Checking for the global entry is stateless and easy to test.
- **Moving the hook script to `hooks/` at the plugin root.** It would break the path that existing install.sh users already have written into `~/.claude/settings.json`, which the spec rules out.
- **Putting the `printf` fix into PR 2 or PR 3.** That mixes a fix with a feature or with test-only work (Law 31).
