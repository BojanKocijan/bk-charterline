# Maintainer Guide — BK Charterline

## What this repo is

A Claude Code plugin for UX and frontend work — library-agnostic governance, scaffolding, and skills, with no corporate toolchain requirements.

## Maintainers & review

Maintainers and required reviewers are configured in **GitHub repository settings** (branch protection rules, required reviewers, optionally `CODEOWNERS`) — not hardcoded in these files. There is intentionally no law for this: GitHub settings are the source of truth, so anyone forking the repo configures their own review policy without editing the rules.

## Repository structure

```
bk-charterline/
├── .claude-plugin/plugin.json   ← plugin manifest
├── .github/                     ← workflows + PR/issue templates
├── agents/                      ← subagent definitions (Frontend, Fullstack, Design, Research, Analyst)
├── docs/                        ← maintainer and contributor guides
├── knowledge/                   ← binding knowledge files (loaded into Claude context)
│   ├── FRONTEND_GUIDE.md
│   ├── PROJECT_SCAFFOLD.md
│   ├── SKILLS.md
│   ├── FEATURE_WORKFLOW.md
│   ├── FULLSTACK_WORKFLOW.md
│   ├── UX_RESEARCH_GUIDE.md
│   ├── ANALYTICS_GUIDE.md
│   └── COMPONENT_PATTERNS.md
├── skills/                      ← skill definitions (plugin entry points)
│   ├── claude-laws/
│   ├── design-critique/
│   ├── design-resources/
│   ├── developer-handoff/
│   ├── feature-workflow/
│   ├── figma-craft/
│   ├── frontend-guide/
│   ├── fullstack-workflow/
│   ├── analyst/
│   ├── project-scaffold/
│   ├── scaffold-react-project/
│   ├── skills-matrix/
│   ├── ux-research-deck/
│   ├── ux-research-guide/
│   └── ux-writing/
├── CLAUDE.md                    ← session entry point (auto-imported by global memory)
├── CLAUDE_LAWS.md               ← the master laws (binding rules)
├── install.sh                   ← one-shot installer
└── README.md
```

## Versioning

This repo uses Conventional Commits. Version bumps in `CLAUDE_LAWS.md` header:

- `feat:` → minor bump (new law, new skill)
- `fix:` → patch bump (law clarification, bug fix)
- `chore:` → no bump (docs, tooling)
- `BREAKING CHANGE:` → major bump

## Making changes

1. Always branch from `main`: `git checkout -b feat/<description>`
2. Open a GitHub issue first.
3. Edit the relevant `CLAUDE_LAWS.md`, `knowledge/*.md`, or `skills/*/SKILL.md` file.
4. Bump the `**Version:**` header in the changed file.
5. Add a changelog entry to `CLAUDE_LAWS.md` if the law behavior changed.
6. Open a PR with `Closes #<issue>` in the body.
7. Merge via the GitHub UI after CI passes.

## Load the laws once in your development checkout

On a machine with BK Charterline installed, a session in a checkout of this repo loads the laws twice: once through the global import (`~/.claude/CLAUDE.md` → `~/.bk-charterline/CLAUDE.md`) and once through the checkout's own `CLAUDE.md`. That's about 27,000 extra tokens per session (#269). To load only the installed copy, add your checkout's paths to `claudeMdExcludes` in your personal `~/.claude/settings.json`:

```json
{
  "claudeMdExcludes": [
    "/path/to/bk-charterline/CLAUDE.md",
    "/path/to/bk-charterline/AGENTS.md",
    "/path/to/bk-charterline/.claude/worktrees/*/CLAUDE.md",
    "/path/to/bk-charterline/.claude/worktrees/*/AGENTS.md"
  ]
}
```

- Use absolute paths. Excluding a `CLAUDE.md` also skips what it imports, so the checkout's `CLAUDE_LAWS.md` drops out too.
- Sessions in the checkout then follow the **released** laws. A law you edit on a branch applies after it's released and installed (`update rules`).
- Don't put this in the repo's `.claude/settings.json`, and don't exclude `~/.bk-charterline` itself. `~/.bk-charterline` is a clone of this repo, so a session started there would load no laws at all.
- You add this yourself; Claude doesn't change which instructions it loads.

Measured on Haiku 4.5 (2026-10-09): 59,193 tokens per session in a worktree before, 31,872 after.

## Adding a new skill

1. Create `skills/<skill-name>/SKILL.md`.
2. Add the skill to `README.md`'s skills list.
3. If the skill has a corresponding knowledge file, add it to `knowledge/` and `@`-import it in `CLAUDE.md`.

## Updating `install.sh`

The installer does five things:

- clones the repo to `~/.bk-charterline`
- injects the import into `~/.claude/CLAUDE.md`
- registers the Law 32 hook in `~/.claude/settings.json`
- links `agents/*.md` and `skills/*/` into `~/.claude/agents` and `~/.claude/skills`
- writes the `charterline-update` function

`charterline-update` runs the installer on every update, so every step must stay safe to re-run. If the clone path or markers change, update both `install.sh` and `README.md`.

## Running `charterline-update`

End users run this shell function (installed by `install.sh`) to pull the latest rules and re-run the installer:

```bash
charterline-update
```

This pulls `~/.bk-charterline`, then re-runs `install.sh`, so new agents, skills and hook entries get registered. The rules themselves are picked up on the next Claude Code session.

## The page (`site/`)

The BK Charterline page is plain HTML, CSS and JavaScript in `site/`, published to <https://bojankocijan.github.io/bk-charterline/> by `.github/workflows/site.yml` when a change to `site/` reaches `main`.

- **See it locally:** open `site/index.html` in a browser. No server is needed.
- **Refresh the real numbers:** `python3 scripts/site_metrics.py`, then open a `chore(site)` PR with the changed `site/data.js`, `site/metrics-state.json` and `site/index.html`. It only asks GitHub for PRs merged since the last run, and a run with nothing new changes no file.
- **Run the checks:** `cd site && npm ci && npx playwright install chromium && npx playwright test` (WCAG 2.2 AA with axe at 390 and 1280 px in light and dark, the tabs by keyboard, the numbers against `data.js`, the page without JavaScript).
