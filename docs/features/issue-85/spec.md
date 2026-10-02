# Spec — install registers Design Forge agents and skills

Intent: [#85](https://github.com/BojanKocijan/design-forge/issues/85)
Design: none (installer behavior, no UI)
Approved-by: BojanKocijan, 2026-10-02, chat

## Behavior

`install.sh` gets one new step, **Link agents and skills**, after the hook step:

1. For each `~/.design-forge/agents/*.md`, make `~/.claude/agents/<file>` a symlink to it.
2. For each `~/.design-forge/skills/<name>/` that contains a `SKILL.md`, make `~/.claude/skills/<name>` a symlink to that folder.
3. If the target already exists and is **not** a symlink into `~/.design-forge`, leave it untouched and print a warning that names it. The user's own agent or skill always wins.
4. If the target is already a symlink into `~/.design-forge`, refresh it, so re-running changes nothing.
5. Remove symlinks in those two folders that point into `~/.design-forge` but whose target no longer exists (an agent or skill removed upstream). Nothing else is ever removed.
6. Print what happened, e.g. `Linked 8 agents and 17 skills into ~/.claude`, plus any skipped names.

`dforge-update` now pulls the clone and then runs `~/.design-forge/install.sh`. Every update therefore also re-links agents and skills and refreshes the memory block, the hook and the function itself. The pull happens before `install.sh` starts, so the script never changes while it is running.

The closing banner lists all five things the installer sets up and prints the installed version, replacing the hard-coded `v1.0.0`.

Docs: the README install section describes all five, and Law 32's sentence about re-running `install.sh` is updated, since `dforge-update` now does that.

## Acceptance criteria

- [ ] In an empty scratch home folder, install creates 8 agent links and 17 skill links, and all of them resolve into `~/.design-forge`.
- [ ] `HOME=<scratch> claude agents` lists the 8 Design Forge agents as user agents.
- [ ] Claude Code's startup event (`claude -p --output-format stream-json --verbose`) lists the 17 skills.
- [ ] A second run changes nothing and prints no errors.
- [ ] A pre-existing real `~/.claude/agents/frontend.md` stays byte-for-byte unchanged and is named in a warning.
- [ ] A dangling link into `~/.design-forge` is removed; a dangling link pointing anywhere else is left alone.
- [ ] `bash -n install.sh` passes, and the script runs under macOS `/bin/bash` 3.2.
- [ ] After `dforge-update`, a skill added upstream is linked without running `install.sh` by hand.

## Policy check

- Component library: n/a (no UI)
- Accessibility: n/a
- Copy: installer messages use the existing `ok` / `warn` helpers
- Conflicts flagged for the owner: rule 5 removes dangling symlinks in `~/.claude`. Law 8 covers repository files, and these are links the installer itself created, but approving this spec approves that removal explicitly.

## Out of scope

- An uninstall command
- Plugin-mode installs, which already work through the manifest. Installing both ways would show every agent and skill twice.
- Rewriting the `../../knowledge/` links inside skill files (see the plan's Risks)
- Windows
