# Spec — Prepare Design Forge for the official plugin directory

Intent: [#102](https://github.com/BojanKocijan/design-forge/issues/102)
Design: none — no UI; this changes rules text, plugin packaging, and CI
Approved-by: BojanKocijan, 2026-10-04, chat
Revision 2026-10-04: Law 1 asks once when no language setting exists, instead of silently defaulting (owner request in chat). Previous approval: BojanKocijan, 2026-10-04, chat.

## Behavior

### 1. Reply language (Law 1)

- Law 1 stops being a fixed rule and reads a `language` setting from the
  `settings:` block of the user's local `projects.yaml`.
- `settings.language: english-only` → today's behavior, unchanged: Claude
  replies only in English and answers any other language with
  *"Please provide instructions in English only."*
- `settings.language: any` → Claude replies in the language the user
  writes in.
- Setting absent → at session start Claude asks once, in English:
  *"Do you want English to be the only language we communicate in?"*
  "Yes" saves `language: english-only`, "no" saves `language: any`, in the
  global `settings:` block of `~/.design-forge/projects.yaml`. The answer
  applies to every project and Claude never asks again.
- `projects.yaml` missing → Claude copies `projects.example.yaml` first, then
  saves the answer (same as Law 20).
- `projects.yaml` can't be parsed → Claude asks, applies the answer for this
  session only, doesn't write the file, and tells the user why.
- The "Prime Directives (Immutable)" heading is renamed so it no longer
  claims Law 1 cannot change. The other directives keep their wording.
- `projects.example.yaml` documents the `settings:` block with
  `language` commented out and both values explained.

### 2. GitHub Pages URL (Law 10)

- The preview URL is `https://<github-username>.github.io/<project-name>/`,
  where `<github-username>` comes from the active `gh` login
  (`gh api user -q .login`).
- `gh` not logged in → Law 16 already blocks GitHub work, so Claude asks the
  user to run `gh auth login --web` before setting up Pages. It never
  guesses a username.

### 3. Project registration (Law 20)

- On first session in an unregistered project, Claude adds the entry
  directly to the local `~/.design-forge/projects.yaml` with the next free
  port. No issue, branch, commit, or PR in the Design Forge repo.
- `projects.yaml` missing → Claude copies `projects.example.yaml` to
  `projects.yaml` first, then adds the entry.
- `projects.yaml` can't be parsed → Claude stops and tells the user. It does
  not overwrite the file.
- Claude tells the user in one line which port it assigned.

### 4. Hook ships with the plugin (Law 32)

- Installing Design Forge as a plugin registers the same `PreToolUse` Bash
  hook as `install.sh` does, without running `install.sh`.
- Installed both ways → the checks run **once** per tool call, not twice.
  Blocks and messages are identical either way.
- Install paths containing spaces work.
- `install.sh` users see no change.

### 5. Hook tested in CI

- CI runs automated tests of the hook script on every push and pull request,
  next to the existing Markdown lint.
- The tests cover at least one allow case and one block case for each check:
  merge, commit on default branch, push to default branch, commit message
  format, PR screenshots line, and secrets. They also cover the dedupe
  (installed twice → one run) and fail-open on bad input.

## Acceptance criteria

- [ ] With `settings.language: english-only`, a non-English prompt gets the
      English-only refusal; with `language: any`, Claude replies in the
      prompt's language.
- [ ] With no `language` setting, the first session asks the English-only
      question once, saves the answer to the global `settings:` block, and
      later sessions don't ask again.
- [ ] Every remaining `bojankocijan` hit in tracked files is a link to the
      Design Forge repo itself, author metadata in the plugin manifests, or
      history (`RELEASES.md`, `docs/features/`). None tells Claude to act on
      the owner's account.
- [ ] Law 10 contains no hardcoded username.
- [ ] Law 20 contains no `gh issue create`, branch, commit, or PR step.
- [ ] `hooks/hooks.json` exists at the plugin root and points at the hook
      script via `${CLAUDE_PLUGIN_ROOT}`.
- [ ] With both install methods active, a blocked `gh pr merge` prints the
      block message once.
- [ ] CI has a hook-test job, and it passes on `main`.
- [ ] Version is 2.21.0 in `plugin.json`, `marketplace.json`, the
      `CLAUDE_LAWS.md` header, and `RELEASES.md` after PR 1 (Law 27).
- [ ] README explains the `language` setting and states that installing
      twice is safe.
- [ ] The owner's own setup, with `settings.language: english-only` added,
      behaves exactly as it does today.

## Policy check

- Component library: n/a, no UI.
- Accessibility: n/a, no UI.
- Copy: the English-only refusal text stays word for word.
- Conflicts flagged for the owner:
  - Law 1 is listed under "Immutable". Making it a setting means
    deliberately editing a directive marked immutable.
  - Law 20 drops its issue + PR flow. That flow could never work, because
    `projects.yaml` is gitignored.

## Out of scope

- Submitting to `anthropics/claude-plugins-official`. That's a separate step
  you approve after the 3 PRs merge.
- Making other opinionated laws optional (Conventional Commits, issue
  before code, announce-and-wait).
- Changing or removing the global hook entry `install.sh` already wrote to
  existing users' `~/.claude/settings.json`.
- Tests for anything other than the hook script.
