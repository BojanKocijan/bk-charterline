<p align="center">
  <img src="https://img.shields.io/badge/version-2.27.0-blue?style=flat-square" alt="Version" />
  <img src="https://img.shields.io/badge/license-GPL--3.0-blue?style=flat-square" alt="License: GPL-3.0" />
  <img src="https://img.shields.io/github/actions/workflow/status/BojanKocijan/design-forge/markdown-lint.yml?branch=main&style=flat-square&label=lint" alt="CI" />
  <img src="https://img.shields.io/badge/claude_code-plugin-blueviolet?style=flat-square" alt="Claude Code Plugin" />
  <img src="https://img.shields.io/badge/laws-38-orange?style=flat-square" alt="38 Laws" />
  <a href="https://ko-fi.com/bojaforjelena"><img src="https://img.shields.io/badge/buy_her_a_coffee-Ko--fi-6f4e37?style=flat-square&logo=kofi" alt="Buy her a coffee on Ko-fi" /></a>
</p>

# Design Forge

**The working knowledge of a UX manager, a full-stack designer and a senior developer, packaged as binding rules, skills and agents for Claude Code.**

Design Forge is a set of binding *laws*, reusable *skills*, and shared *knowledge files* that govern every Claude Code session. It controls how Claude scaffolds projects, names branches, opens PRs, writes components, runs UX research, and hands work off to developers. Library-agnostic. Framework-agnostic. No corporate toolchain required.

It's not only for developers. Design Forge carries the full product craft, from UX research, design critique, UX writing and Figma handoff to frontend, backend, testing and shipping, so Claude works like a senior teammate across the whole team, not just the codebase.

> Think of it as a constitution for your AI pair-programmer: announce before acting, branch + issue before code, never push to `main`, never merge for you, small atomic PRs, no inline styles, WCAG 2.2 AA, no bloated code, no hallucination.

---

## Table of contents

- [Why Design Forge](#why-design-forge)
- [Quick start](#quick-start)
- [Installation](#installation)
- [Architecture](#architecture)
- [Commands](#commands)
- [Working with the team](#working-with-the-team)
- [Wiring a project](#wiring-a-project)
- [Project registry](#project-registry)
- [Updating](#updating)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

---

## Why Design Forge

Out of the box, an AI coding assistant will happily push to `main`, invent APIs, ship 1000-line PRs, over-engineer, and forget your conventions between sessions. Design Forge fixes that with **38 binding laws** and knowledge files that travel with you to every project.

| Problem | Design Forge solution |
|---|---|
| Pushes directly to `main` | Branch + issue before code; PRs only; Claude never merges |
| Giant, unreviewable PRs | **Law 31** — every PR under 400 lines, one concern per PR, stacked sequences for large features |
| Over-engineered code | YAGNI enforcement, edge-case analysis upfront, verify-before-claiming |
| Forgets your conventions | 38 laws + 10 knowledge files that load on demand |
| Inconsistent components | 4-file component folders, no inline styles, TypeScript, accessibility baked in |
| No audit trail | Pre-execution announcements, Conventional Commits, living `PROJECT_KNOWLEDGE.md` |
| Stale repos | Auto branch cleanup, orphaned issue detection, README kept current with every PR |
| "Claude might forget and merge/push to `main` anyway" | **Law 32** — a `PreToolUse` hook mechanically blocks merge, push or force-push to `main`, skipped git hooks, malformed commits and secret commits, and asks you in the app before Claude changes its own guardrails, deletes tracked files or calls a tier 3 or 4 MCP tool |

---

## Quick start

```bash
curl -fsSL https://raw.githubusercontent.com/BojanKocijan/design-forge/main/install.sh | bash
```

Open any Claude Code session. You should see:

```
Rules loaded: DESIGN_FORGE v2.19.1
Project: <your-repo>
Persona: Frontend
GitHub: <your-username>
Ready.
```

That's it. Every session on your machine now follows the laws and has the Design Forge agents and skills. Check the agents with `claude agents`.

---

## Installation

### Path A — Claude Code / CLI (recommended)

The install script clones the repo to `~/.design-forge`, injects the rules into Claude's global memory (`~/.claude/CLAUDE.md`), registers the Law 32 hook, links the agents and skills into `~/.claude`, and installs the `dforge-update` shell function.

```bash
curl -fsSL https://raw.githubusercontent.com/BojanKocijan/design-forge/main/install.sh | bash
```

<details>
<summary>What the script does</summary>

1. Clones this repo to `~/.design-forge`
2. Adds `@~/.design-forge/CLAUDE.md` to `~/.claude/CLAUDE.md` (Claude's global memory)
3. Registers the Law 32 guardrail hook in `~/.claude/settings.json`
4. Links each agent into `~/.claude/agents/` and each skill into `~/.claude/skills/`. Your own agents and skills with the same name are never overwritten.
5. Installs the `dforge-update` shell function, which pulls the clone and re-runs the installer

Re-running the script is safe. Use one install method only: installing the plugin as well would list every agent and skill twice.

</details>

### Path B — Manual clone

```bash
git clone https://github.com/BojanKocijan/design-forge.git ~/.design-forge
```

Then add this line to `~/.claude/CLAUDE.md`:

```
@~/.design-forge/CLAUDE.md
```

### Path C — GitHub Copilot

Paste the contents of [`CLAUDE_LAWS.md`](./CLAUDE_LAWS.md) into your Copilot custom instructions (VS Code, JetBrains, or github.com Settings > Copilot > Custom instructions).

### Marketplace (coming soon)

The repo ships a valid plugin manifest (`.claude-plugin/plugin.json`), so a one-click install from the Claude / Cowork marketplace will be available once listed by Anthropic.

---

## Architecture

Design Forge has three layers:

```
┌─────────────────────────────────────────────────┐
│  CLAUDE_LAWS.md — 38 binding rules              │
│  (loaded every session)                         │
├─────────────────────────────────────────────────┤
│  agents/ — 8 specialized personas               │
│  Frontend · Backend · Lead · Tester             │
│  Fullstack · Design · Research · Analyst        │
├─────────────────────────────────────────────────┤
│  knowledge/ — 11 binding guides                  │
│  (loaded on demand per task scope)              │
├─────────────────────────────────────────────────┤
│  skills/ — 17 reusable skill definitions        │
│  (auto-discovered by Claude Code)               │
└─────────────────────────────────────────────────┘
```

### Laws — [`CLAUDE_LAWS.md`](./CLAUDE_LAWS.md)

38 binding rules. Key highlights:

- **Transparency** — pre-execution announcement before any change; Claude waits for explicit approval
- **Git discipline** — pull default branch, branch + issue before code, PRs only, never push to default branch, never merge
- **Small atomic PRs** — every PR under 400 lines, one concern per PR, stacked sequences for large features, squash-merge by default
- **Code quality** — 4-file component folders, no inline styles, Conventional Commits, secret scanning, PII-free mock data, WCAG 2.2 AA
- **Engineering rigor** — YAGNI, edge-case thinking, verify-before-claiming, reason-before-executing
- **Repo hygiene** — immediate branch cleanup, stale branch sweeps, orphaned issue detection, README always current
- **Human gates** — gate tier from severity, committed `intent.md` → `spec.md` → `plan.md` approvals, risk-scaled review, cap of 3 AI PRs awaiting review (Law 37)
- **AI tool risk tiers** — every MCP server, extension and plugin has a tier (1–4) and an owner; the Law 32 hook asks you in the app before a tier 3 tool's first call each session and before every tier 4 call (Law 38)
- **Safety controls** — `arm` / `disarm` toggle; `dry run` mode; three hard-safety rails always survive (never merge, no secrets, no PII)

### Personas

Eight specialized agents compose into a single pipeline. `install.sh` links each one into `~/.claude/agents/`, so `claude agents` lists them.

| Persona | Scope | Trigger | Model |
|---|---|---|---|
| **Frontend** | UI, React, a11y, mocked data | *default* / `frontend mode` | Sonnet |
| **Backend** | APIs, auth, DB, migrations, observability, CI | `backend mode` | Opus |
| **Lead** | Orchestrates the full team pipeline | `team` / `build feature` / `fullstack mode` | Opus |
| **Tester** | Tests, axe/coverage gate, can block the PR | `tester mode` | Sonnet |
| **Fullstack** | Production code; hands big features to the Lead, builds small changes solo | `fullstack mode` | Opus |
| **Design** | Figma, design critique, UX writing, handoff | *(implied by design tasks)* | Sonnet |
| **Research** | Transcripts, JTBD, RICE/MoSCoW, deck generation | `research mode` | Sonnet |
| **Analyst** | Product analytics (Pendo, Amplitude, Mixpanel, ...) | `analyst mode` | Sonnet |

### Knowledge — [`knowledge/`](./knowledge/)

| File | Scope |
|---|---|
| `FRONTEND_GUIDE.md` | React, components, styling, TypeScript, a11y |
| `COMPONENT_PATTERNS.md` | Shared component patterns and refactoring |
| `ANIMATION_GUIDE.md` | Animation, transitions, morphs, celebrations, reduced motion, measuring and testing motion |
| `PROJECT_SCAFFOLD.md` | New project scaffolding (Vite + React + TS) |
| `FULLSTACK_WORKFLOW.md` | Production PR flow (10 phases) |
| `TEAM_WORKFLOW.md` | Multi-agent team pipeline |
| `FEATURE_WORKFLOW.md` | Feature lifecycle (start/pause/resume/finish) |
| `SKILLS.md` | Layout, a11y, testing, handoff, git craft |
| `UX_RESEARCH_GUIDE.md` | Transcript analysis, research decks |
| `ANALYTICS_GUIDE.md` | Product analytics workflows |
| `HUMAN_IN_THE_LOOP.md` | Gate tiers, approval artifacts, PR intake, review cap (Law 37) |
| `PATTERNS.md` *(personal, gitignored — [example](./knowledge/PATTERNS.example.md))* | Cross-project bug/pattern catalogue |

---

## Commands

### Core workflow

| Command | Description |
|---|---|
| `new project` | Scaffold a new app — asks platform, UI library, architecture, deployment |
| `start feature` | 3-question triage, tracks active feature in `PROJECT_KNOWLEDGE.md` |
| `pause feature` | Park the current feature, free the slot |
| `resume feature` | Pick up a paused feature |
| `finish feature` | Close the feature, archive it, run handoff if ready |
| `handoff <id>` | Generate 13-section developer handoff + tracking issue |

### Team and personas

| Command | Description |
|---|---|
| `team` / `build feature` | Start the Lead-orchestrated pipeline (plan > build > test > document > review) |
| `frontend mode` | Switch to Frontend persona (default) |
| `backend mode` | Switch to Backend persona |
| `tester mode` | Switch to Tester persona |
| `fullstack mode` | Activate the Lead (team orchestrator) |
| `research mode` | UX research — produces 6-slide outcome deck |
| `research mode full` | Full 12-18 slide research deck |
| `analyst mode` | Product analytics persona |

### Safety and governance

| Command | Description |
|---|---|
| `disarm` | Suspend laws for this session (hard-safety rails survive) |
| `arm` | Restore full governance |
| `dry run` | Claude prints git/gh commands instead of running them |
| `auto git` | Exit dry-run mode |
| `update rules` | Pull latest rules and reload |
| `check rules` | Print loaded version and update status |
| `stop preview` / `start preview` | Control the background dev server |
| `approve intent` / `approve spec` / `approve plan` | Record your approval on a Law 37 artifact |
| `review queue` | Risk-sorted digest of open PRs awaiting your review |
| `review cap <N>` / `review cap off` | Change the cap on AI PRs awaiting review (default 3) |
| `skip gates` | Lower the gate tier for this change, with a reason |
| `hook log` | Law 32 blocks and permission prompts for the last 30 days, including false positives |
| `ai inventory` | Every MCP server, extension, plugin, skill, agent, hook and permission rule your sessions can use, with tiers, owners and what's new since last time |
| `ai classify` | Give each unclassified tool a Law 38 risk tier and owner; Claude proposes, you approve in chat, then confirm each write in the app's prompt |

---

## Working with the team

Every session starts as **Frontend**. The team pipeline is opt-in.

**Start the full pipeline:**

```
team
# or with context:
build feature: add CSV export to the invoices page
```

The **Lead** runs it end-to-end — scope, build, test, document, review, PR — pausing for your approval on multi-file edits (Law 2) and stopping at "PR open, CI green" for you to merge (Law 7).

**Or call a single role:**

| Goal | Trigger |
|---|---|
| Build / change UI | `frontend mode` *(default)* |
| Build an API, DB, auth | `backend mode` |
| Full feature with the team | `team` / `build feature` |
| Write and run tests | `tester mode` |
| Design critique, Figma work | *(design task)* |
| Transcript analysis | `research mode` |
| Product analytics | `analyst mode` |

Every agent obeys [`CLAUDE_LAWS.md`](./CLAUDE_LAWS.md). If an agent thinks it should break a rule, it stops and asks (Law 29).

---

## Wiring a project

Laws load globally — you never wire them per project. A project only needs its own context via a one-line `CLAUDE.md` at the project root:

```
@./PROJECT_KNOWLEDGE.md
```

`new project` creates this automatically. For existing projects, Claude creates it the first time you do code work.

> **Note:** Never add `@~/.design-forge/CLAUDE.md` to a project-level file — it's redundant (laws are global) and breaks the repo on machines without Design Forge installed.

---

## Project registry

Design Forge assigns each project a **locked localhost port** so running multiple `npm run dev` servers never clashes. The registry lives in `projects.yaml` (gitignored, local to your machine):

```bash
cp projects.example.yaml projects.yaml
```

Claude auto-registers new projects by adding an entry to this local file (no PR), and locks the port in `vite.config.ts` with `strictPort: true`.

### Reply language

On your first session, Claude asks once whether English should be the only language you communicate in, and saves the answer in the same file:

```yaml
settings:
  language: english-only   # or: any
```

For professional work we recommend one language, so code, commits, PRs and docs stay consistent. Edit the value any time to change it.

---

## Updating

| Method | Command |
|---|---|
| Shell (Path A) | `dforge-update` (pulls, then re-links agents and skills) |
| Manual (Path B) | `git -C ~/.design-forge pull` |
| In any session | `update rules` |

---

## Repository structure

```
design-forge/
├── CLAUDE.md                    # Entry point — imports laws, maps knowledge triggers
├── CLAUDE_LAWS.md               # 38 binding rules (loaded every session)
├── AGENTS.md                    # Agent architecture overview
├── RELEASES.md                  # Version history
├── install.sh                   # One-line installer
├── projects.example.yaml        # Project registry template
├── .claude-plugin/              # Claude Code plugin manifest
├── agents/                      # 8 persona definitions
│   ├── frontend.md
│   ├── backend.md
│   ├── lead.md
│   ├── tester.md
│   ├── design.md
│   ├── research.md
│   ├── analyst.md
│   └── fullstack.md
├── knowledge/                   # 11 binding guides (loaded on demand)
│   ├── FRONTEND_GUIDE.md
│   ├── COMPONENT_PATTERNS.md
│   ├── ANIMATION_GUIDE.md
│   ├── PROJECT_SCAFFOLD.md
│   ├── FULLSTACK_WORKFLOW.md
│   ├── TEAM_WORKFLOW.md
│   ├── FEATURE_WORKFLOW.md
│   ├── SKILLS.md
│   ├── UX_RESEARCH_GUIDE.md
│   ├── ANALYTICS_GUIDE.md
│   ├── HUMAN_IN_THE_LOOP.md
│   ├── PATTERNS.example.md
│   └── PATTERNS.md              # gitignored — your copy of the example above
├── skills/                      # 17 reusable skill definitions
├── docs/                        # Additional documentation
└── .github/
    └── workflows/
        └── markdown-lint.yml    # CI — lint on every push and PR
```

---

## Contributing

Issues and PRs are welcome. Read [`CONTRIBUTING.md`](./CONTRIBUTING.md) first. All contributions follow the project's own laws:

1. Branch + issue before code (Law 5)
2. Conventional Commits (Law 13)
3. PRs only — no direct pushes to `main` (Law 7)
4. Small, atomic PRs under 400 lines (Law 31)
5. CI (markdownlint and the hook tests) must pass. Run the hook tests locally with `python3 -m unittest discover -s tests -v`

See [`CLAUDE_LAWS.md`](./CLAUDE_LAWS.md) for the full governance framework.

---

## License

[GPL-3.0](./LICENSE) &copy; Bojan Kocijan. Free to use for personal and commercial projects. If you modify it and share your version, you must publish your changes under the same license. See [CONTRIBUTING.md](./CONTRIBUTING.md) to send your improvements back.

**Commercial license.** If your company wants to ship a changed version without publishing the changes, or can't use GPL software, a commercial license is available. See [Design Forge for companies](./FOR_COMPANIES.md), which also covers paid team setup.

Version 2.18.0 and earlier were published under the MIT License, and version 2.18.1 under an all-rights-reserved license. Copies obtained under those licenses keep their terms.

## Support

### If you like Design Forge, help a fellow husband and buy my wife a coffee

Design Forge is free and always will be. If you're married, you already know how this works: a happy wife means a happy life, and in my house a happy wife means a full cup of coffee. We've been happily married for years, mostly thanks to a reliable coffee supply.

<a href="https://ko-fi.com/bojaforjelena"><img src="https://img.shields.io/badge/%E2%98%95_Buy_her_a_coffee-Ko--fi-6f4e37?style=for-the-badge&logo=kofi&logoColor=white" alt="Buy her a coffee on Ko-fi" /></a>

Using Design Forge at a company? See [Design Forge for companies](./FOR_COMPANIES.md): team setup and workshops, or a commercial license if GPL doesn't fit.
