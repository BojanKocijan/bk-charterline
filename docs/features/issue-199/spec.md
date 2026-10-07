# Spec — rename Design Forge to BK Charterline (#199)

Intent: [#199](https://github.com/BojanKocijan/design-forge/issues/199), approved by the owner in chat on 2026-10-07
Design: none — a rename, no new UI
Approved-by: BojanKocijan, 2026-10-07, chat

## Owner decisions (chat, 2026-10-07)

- **Name:** **BK Charterline** for people; `bk-charterline` as the slug (repo, folder, plugin).
- **Scope:** rename everything, staged, with an automatic move for existing installs.
- **History:** release notes before v3.0.0 and `docs/features/` keep the old name; they record what was true then.
- **Old command:** `dforge-update` keeps working for v3.0.0 only.
- **The #177 page** launches only under the new name.
- **`update rules` stays the only thing a user types.** Behind it, Claude runs whichever update command the machine has.

## Behavior

### What changes name

| Today | After | Where |
|---|---|---|
| Design Forge | BK Charterline | README, laws, `CLAUDE.md`, knowledge, skills, agents, scripts, the hook's messages, the page |
| `BojanKocijan/design-forge` | `BojanKocijan/bk-charterline` | The GitHub repo (renamed by the owner on 2026-10-07); every URL in the repo |
| `~/.design-forge` | `~/.bk-charterline` | The installed clone and its data files |
| `dforge-update` | `charterline-update` | The shell function; `dforge-update` remains for v3.0.0 as a pointer |
| `Rules loaded: DESIGN_FORGE v…` | `Rules loaded: BK CHARTERLINE v…` | The session-start confirmation |
| `<!-- design-forge:begin -->` … | `<!-- bk-charterline:begin -->` … | The block in `~/.claude/CLAUDE.md` and the function block in the shell rc file |
| `design-forge` plugin | `bk-charterline` plugin | `.claude-plugin/plugin.json` and `marketplace.json` |
| `bojankocijan.github.io/design-forge/` | `bojankocijan.github.io/bk-charterline/` | GitHub Pages (never launched under the old name) |

Internal names that no user sees (such as the `DFORGE_UPDATE` variable) follow the same pattern. Hook check ids and log formats don't change, so `hook log` reads old and new lines alike.

### `update rules` across the rename

- **On a machine with only the old name:** `update rules` runs `dforge-update` as today. It installs v3.0.0, whose `install.sh` moves the install (below) and installs `charterline-update`. The final line says `ready (BK CHARTERLINE v3.0.0)`, and the next `update rules` runs `charterline-update`.
- **On a machine with the new name:** `update rules` runs `charterline-update`.
- **The hook diff:** v3.0.0 changes what the hook runs, so the first update stops for your approval of its diff, in the terminal or in the app's prompt (Law 28), as every hook change does.
- **`dforge-update` in v3.0.0** prints one line ("Design Forge is now BK Charterline: running charterline-update"), then runs it. In the release after, it's gone.

### The automatic move (v3.0.0 `install.sh`)

On the first run where `~/.design-forge` exists and `~/.bk-charterline` doesn't:

1. Move the folder: `~/.design-forge` → `~/.bk-charterline`, in one rename on the same disk. The personal data files inside (`projects.yaml`, the hook log, `ai-tools.json`, `ai-approvals.jsonl`, `ai-inventory.*`, `knowledge/PATTERNS.md`) move with it, untouched.
2. Leave a link `~/.design-forge` → `~/.bk-charterline` for v3.0.0, so anything still pointing at the old path (an old import line in a project's `CLAUDE.md`, an open terminal) keeps working. The next major release removes it.
3. Point the clone's `origin` at the new repo URL.
4. Replace the `design-forge` block in `~/.claude/CLAUDE.md` with the `bk-charterline` block.
5. Re-point the hook entries in `~/.claude/settings.json` from the old path to the new one, changing only entries whose command is the Design Forge hook, and leaving every other setting as it was.
6. Replace the function block in the shell rc file with the new one: `charterline-update`, plus the `dforge-update` pointer.
7. Re-link the agents and skills from the new folder; remove only links that point into the old folder.

Each step checks before it acts and can run twice safely. If a step fails, the install stops, says which step and how to finish it by hand, and leaves the old name working.

**When not to move:** if both folders exist, or the old folder has local changes, nothing moves, and the install says what to do. Law 28's rule stays: it never touches a clone with local edits.

### The hook

The Law 32 guardrails treat `~/.bk-charterline` as the installed clone, and the `~/.design-forge` link too, after resolving it. `charterline-update --approve <commit>` asks exactly as `dforge-update --approve` does today. `dforge-update --approve` still asks in v3.0.0.

## Acceptance criteria

- [ ] A fresh install from the new URL ends with `Rules loaded: BK CHARTERLINE v3.0.0`, the hook registered at `~/.bk-charterline/.claude/hooks/enforce-laws.py`, and `charterline-update` defined.
- [ ] An install on v2.36.x that runs `update rules` ends on v3.0.0 under the new name, with every personal data file intact (tested against a fake home with each file present).
- [ ] Running the v3.0.0 install twice changes nothing the second time.
- [ ] Both folders present, or local changes in the clone: nothing moves, and the message names the fix.
- [ ] `~/.claude/settings.json` keeps every non–Design Forge entry byte for byte.
- [ ] The hook guards `~/.bk-charterline`, follows the old-path link, and asks for `charterline-update --approve`.
- [ ] Nothing current says "Design Forge" outside the history (release notes before v3.0.0 and `docs/features/`) and the v3.0.0 migration code; a test lists the allowed places.
- [ ] Release v3.0.0: the four version files agree, and the release note says what changed for users and that `update rules` handles it.

## Policy check

- **Component library:** none; no UI.
- **Accessibility:** not affected.
- **Copy:** every message says what happened and what to do next, in the house style.
- **Conflicts flagged for the owner:**
  1. **The repo is renamed** (owner, 2026-10-07): `BojanKocijan/bk-charterline`. Checked the same day: the old git URL still fetches, the old web URL redirects (301), the old `raw.githubusercontent.com/…/design-forge/main/install.sh` still serves the installer (200), and Pages moved to `bojankocijan.github.io/bk-charterline/`. So existing installs keep updating before v3.0.0 ships, and the old install command keeps working.
  2. **Plugin users** must remove the `design-forge` plugin and add `bk-charterline`. A plugin can't rename itself, and the release note will say so.
  3. **Claude's per-project memory** is keyed by your local folder name (`~/Documents/GitHub/design-forge`). Renaming that folder is optional and yours to do; if you do, the memory files need moving too.
  4. **The name isn't cleared yet.** A trademark search (USPTO, EUIPO, BOIP) should confirm "BK Charterline" before the page goes public; a tool called Charter already exists in this niche.

## Out of scope

- Renaming history: old release notes, `docs/features/`, issues and PRs.
- Rewriting other projects' files. The old-path link covers them for v3.0.0.
- Renaming your local checkout folder.
- The trademark search itself.
