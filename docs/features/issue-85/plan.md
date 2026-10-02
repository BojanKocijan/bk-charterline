# Plan — install registers Design Forge agents and skills

Spec: [spec.md](./spec.md) · Gate tier: Significant · Branch: `feat/install-links-agents-skills` · Issue: #85
Work pile: delegable (fully specified, limited to the installer, verifiable in a scratch home folder)
Approved-by: BojanKocijan, 2026-10-02, chat

## Files to change

| File | Change |
|---|---|
| `install.sh` | A `link_into` helper and the "Link agents and skills" step; `dforge-update` pulls, then runs `install.sh`; the banner lists five items and the real version |
| `README.md` | Install section: what `install.sh` sets up (five items) and that `dforge-update` re-links |
| `CLAUDE_LAWS.md` | Version 2.18.0; update Law 32's sentence about re-running `install.sh` |
| `RELEASES.md` | v2.18.0 entry |
| `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Version 2.18.0 |

## Order of work

1. Rebase on `main` once #84 has merged, because it fixes the agent metadata this install registers. Done when the branch contains v2.17.1.
2. Add the link step to `install.sh`. Done when the scratch-home checks below pass.
3. Change `dforge-update` and the banner. Done when a scratch `dforge-update` links a newly added skill.
4. Update the README, the Law 32 sentence, the versions and `RELEASES.md`. Done when markdownlint and `claude plugin validate` pass.
5. Open the PR with the Intake block. Done when CI is green.

## Proof

- Tests to add or change: none in CI. The repo has no shell test suite, and adding one is out of scope. I run the scratch-home checks by hand and paste the results into the PR.
- Commands that must pass:
  - `bash -n install.sh`
  - `/bin/bash install.sh` with `HOME=<scratch>`, using a clone of this branch placed at `<scratch>/.design-forge`
  - `HOME=<scratch> claude agents`
  - the startup event from `HOME=<scratch> claude -p … --output-format stream-json --verbose`
  - `markdownlint-cli2`
  - `claude plugin validate .claude-plugin/plugin.json`
- Edge-case runs: a second run (no changes), a pre-existing user file, a symlink pointing somewhere else, and a dangling link into the clone.
- Visual evidence: none (no UI).

## Risks

- Skill files link to `../../knowledge/<FILE>.md`. If Claude Code reports a linked skill's folder as `~/.claude/skills/<name>`, that path doesn't lead to the knowledge files. → Check in a real session after install. If it fails, a follow-up PR points those links at `~/.design-forge/knowledge/`.
- Every session now lists 17 skill and 8 agent descriptions, which adds a little context at startup. → Accepted by the owner on 2026-10-02.
- Anyone who also installs the plugin sees every agent and skill twice (`frontend` and `design-forge:frontend`). → The README says to choose one install method.
- A machine with neither `~/.zshrc` nor `~/.bashrc`: unchanged behavior. The installer warns and skips the function.

## Ruled out

- Linking the whole `~/.claude/agents` and `~/.claude/skills` folders: that would hide or clash with the user's own agents and skills.
- Copying files instead of linking: copies go stale between updates, while links follow `git pull` automatically. Symlinks were verified to load on 2026-10-02: in a scratch project, `claude agents` and the startup event listed the linked agents and skill.
- Having `install.sh` install Design Forge as a plugin: that adds a second update path and namespaced names. The owner chose linking.
- Repeating the link logic inside `dforge-update`: `install.sh` stays the single source of truth.
