# Design Forge Releases

---

## v2.17.1 — October 2, 2026

### Fix — agents and plugin manifest pass validation
- `agents/backend.md` and `agents/fullstack.md`: the `description` values are now quoted. Before, an unquoted colon inside them broke the YAML frontmatter, and Claude Code loaded both agents without their description
- `.claude-plugin/plugin.json`: removed the unsupported `displayName` key so `claude plugin validate` passes (Law 27)

---

## v2.17.0 — October 2, 2026

### Law 37 — Human gates in the agentic loop
- Gate tier from the Law 2 severity: Trivial needs nothing extra, Standard needs an approved `plan.md`, Significant needs `intent.md` → `spec.md` → `plan.md`, each approved in order
- Artifacts are committed in `docs/features/<id>/`; Claude never writes an `Approved-by` line without the owner's explicit approval
- Every non-chore PR carries an Intake block and a Decision log
- Review depth follows risk, with an independent fresh-context reviewer subagent for Significant work
- Cap of 3 AI PRs awaiting review, delegable vs judgment-heavy triage, and a `review queue` digest
- New on-demand `knowledge/HUMAN_IN_THE_LOOP.md` and `skills/human-in-the-loop`
- Sources: Anthropic's AI-native SDLC playbook and seven Addy Osmani essays

---

## v2.16.0 — October 2, 2026

### Law 32 — Hook enforces the Law 34 screenshot question
- `enforce-laws.py` now blocks `gh pr create` unless the PR body (or its `--body-file`) has a `Screenshots: yes | skipped at the user's request | not applicable` line, so Claude has to ask "Do you want e2e/screenshot images for this PR?" before opening any PR, in every project
- Fails open if the body file can't be read

---

## v2.15.0 — October 2, 2026

### Law 34 — Ask before creating screenshot images
- Claude now asks "Do you want e2e/screenshot images for this PR?" and waits for an explicit yes before creating, adding or regenerating any; on no or silence the PR says screenshots were skipped
- Prompted by screenshot images overloading the GitHub Actions worker in a real project

---

## v2.14.0 — October 2, 2026

### Law 34 — Changed-pages-only screenshots
- PR screenshots now cover only screens whose import graph contains a file the PR touched; a touched file that reaches no screen produces no screenshot and no home-screen fallback (PR says `No screens affected`)
- Speed recipe in `knowledge/SKILLS.md`: minimal standalone Playwright spec, reused dev server, parallel workers, animations disabled, blocked fonts/analytics, no fixed waits, element-level capture, cap of 6 screens

---

## v2.13.0 — October 1, 2026

### Law 36 — Cross-project pattern catalogue
- New binding law: `knowledge/PATTERNS.md` (personal, gitignored like `projects.yaml`) logs bugs/patterns already solved in one project, so the same symptom showing up in another project gets recognized instead of re-solved from scratch
- Claude surfaces a matching entry and asks before applying it — never silently reuses a past fix; offers to log a new entry when it solves something reusable, never logs one without asking
- Ships `knowledge/PATTERNS.example.md` as the public template, same convention as `projects.yaml` / `projects.example.yaml`

---

## v2.12.0 — October 1, 2026

### Law 35 — Explicit, ordered deploy steps
- New binding law: whenever a change needs more than "merge the PR" — a migration to run by hand, an env var to set, a dependent second PR, a required redeploy — Claude's PR-ready summary (or an immediate follow-up) includes a numbered, ordered checklist with the literal command/SQL/dashboard path, not a vague category
- Prompted by a real session where a two-repo pageview-stats feature needed migrations applied and env vars set between PR merges, and the ordering/exact steps weren't being surfaced proactively
- When new steps are discovered later, Claude restates the full remaining sequence rather than mentioning only the new step in isolation

---

## v2.11.0 — October 1, 2026

Four generic, stack-agnostic additions.

### Law 32 — Hook-enforced guardrails
- New binding law: a `PreToolUse` hook (`.claude/hooks/enforce-laws.py`) mechanically blocks `gh pr merge` in any form, commit/push while on the default branch, non-Conventional-Commits messages, and secrets in a staged diff
- No `--auto` exception for merges — Law 7 ("Claude never merges") stays absolute, unlike the source repo's carve-out
- `.claude/settings.json` ships the reference `PreToolUse` wiring; `install.sh` registers the same hook globally in `~/.claude/settings.json` (merging into existing content, never overwriting), so it runs in every repo a session touches — `dforge-update` alone is enough to pick up script-logic changes, since the registration points at a fixed path in the clone
- Fails open on parse errors — a backstop against mechanical slips, not a replacement for judgment

### Law 33 — Session resumption via `SESSION_NOTE.md`
- New binding law: Claude offers a short handoff note (goal, done, left, blocking decision, branch/issue/PR) when a non-trivial task is left unfinished at session end, reads it back at the next session start, and cleans it up once resumed work completes

### Law 34 — UI-PR screenshot evidence
- New binding law: any PR touching a component, styles, or layout file embeds a Playwright screenshot of the changed screen/state in the PR body — point-in-time reviewer context, not a request for a permanent visual-regression suite

### Law 9 — pull immediately after merge
- Added an explicit, unprompted `git pull` of the default branch as part of the existing post-merge cleanup duty, so local `main` doesn't go stale between sessions

---

## v2.10.0 — June 29, 2026

### Law 31 — Small, atomic PRs
- New binding law: every PR targets under 200 lines changed (400 hard ceiling), one concern per PR
- 5 splitting strategies: separate by type, vertical slices over horizontal layers, infrastructure first, tests travel with their code, sequential stacking for large features
- Atomic commits — no WIP commits, no commented-out code, each commit passes CI independently
- Pre-PR self-check, PR description discipline (What / Why / How to test / Sequence)
- Repo hygiene standards: squash-merge by default, stale branch sweeps, orphaned issue detection, README kept current with every PR

### README professionally restructured
- shields.io badges (version, license, CI, plugin, law count), problem/solution table, quick-start, ASCII architecture diagram, structured command tables, full repo tree, numbered contributing steps

---

## v2.9.0 — June 23, 2026

### Arm / disarm — soft governance toggle
- New skill: `skills/arm-disarm/SKILL.md` — type `disarm` to suspend all Design Forge laws for a session; type `arm` to restore them
- Hard-safety rails survive disarm and cannot be toggled off: **never merge** (Law 7) · **secret scan** (Law 14) · **no real PII** (Law 15)
- A visible `⚠ DISARMED` banner appears on every response while governance is suspended
- State resets to armed at every new session start — disarm never persists

### Default branch, not just `main`
- Law 5 and Law 7 now say **"default branch"** instead of `main` — detects `main`/`master`/`trunk`/`develop` or any other protected base via `git symbolic-ref refs/remotes/origin/HEAD`
- Prevents accidental direct pushes in repos where the default branch isn't `main`

### Immediate branch cleanup after merge (Law 9)
- Branch cleanup is now Claude's **immediate duty in the same response** where a merge is confirmed — no prompt, no reminder needed
- Explicit report line required: `Branch \`feat/…\` deleted (remote + local). Issue #N closed.`

---

## v2.8.0 — June 16, 2026

### Universal COMPONENT_PATTERNS (no project coupling)
- Reframed examples as a generic CRUD domain (illustrative, domain-agnostic) — substitute your own entities
- Removed the project-specific component inventories (those belong in each project's `PROJECT_KNOWLEDGE.md §3`)
- Genericized provenance; **no pattern changed** — purely a portability/clarity pass

---

## v2.7.0 — June 15, 2026

### Slimmer always-on payload
- Trimmed what loads at session start from ~10.7K to **~8.5K tokens** by cutting duplication — **no law removed or weakened**
- `CLAUDE_LAWS.md`: changelog → pointer to this file; the duplicated Personas table → pointer to `CLAUDE.md`; Law 4's knowledge table → pointer to the on-demand map
- `CLAUDE.md`: condensed the "Non-negotiables" and "What Claude will refuse" sections (they restated laws that already load)
- Net session start is now **~8.5K** (down from ~40.4K before lazy-loading — a −79% total reduction)

### Leaner skills (no behavior change)
- The 10 knowledge-backed skills are now **thin routers**: each triggers on its task and points to the canonical `knowledge/` file instead of re-hosting a (drift-prone) copy — skill bodies dropped ~12.2K → ~6.7K tokens, and an invoked skill no longer loads the same content twice
- Fixed the stale `claude-laws` skill (it listed "19 laws / v1.0.0")
- Self-contained skills (ux-writing, design-critique, design-resources, figma-craft, developer-handoff) unchanged — they *are* the source

### New: Law 30 — resolve every UI to the chosen component library
- Once a project's library is chosen, **all** UI is built from it — a paper sketch, Figma frame, or screenshot of another app is treated as *intent*, mapped to the library's primitives (e.g. another app's dropdown → the library's `Select`)
- Never hallucinate components, never introduce a second UI library, never hand-roll a primitive the library provides; if it genuinely lacks one, ask before adding/custom-building

---

## v2.6.0 — June 15, 2026

### Lazy-loaded knowledge — ~73% smaller session start
- Only the binding laws (`CLAUDE_LAWS.md`) load at session start now
- The 8 knowledge files load **on demand** — Claude reads each one only when its trigger/scope fires (e.g. `PROJECT_SCAFFOLD` on `new project`, `UX_RESEARCH_GUIDE` on `research mode`)
- Session-start context drops from ~40.4K to ~10.7K tokens; each session pulls in only the 1–2 files it actually uses
- No rules changed — only *when* they load

---

## v2.5.0 — June 15, 2026

### Documentation is the team's shared duty (no Docs agent)
- Removed the dedicated **Docs** role (`docs-writer.md`) and the `docs mode` trigger
- Each role now documents its own change as it builds; the **Lead enforces** the doc standards as a gate before review
- Pipeline stages: `planned → building → testing → in-review`; the documentation gate stays (undocumented change = not done), just owned by the team

---

## v2.4.0 — June 12, 2026

### An agent team that works one pipeline
- Personas now compose into a team that runs a single flow: **plan → build → test → document → review → human-merge** ([`TEAM_WORKFLOW.md`](./knowledge/TEAM_WORKFLOW.md))
- **New roles:** Lead (orchestrator), Backend (API/DB/server), **Tester** (writes + runs tests, axe/coverage gate, can block the PR), **Docs** (README/API docs, RELEASES, PROJECT_KNOWLEDGE, handoff)
- Frontend stays the UI builder; Design/Research/Analyst are supporting; `fullstack mode` now activates the Lead
- Two gates before a PR is review-ready: **Tester** (tests pass + axe clean + acceptance criteria met) and **Docs** (change is documented)
- Handoff rides one shared thread — the `PROJECT_KNOWLEDGE §11` Stage column + the PR body — so context isn't re-derived between roles
- New triggers: `team` / `build feature`, `backend mode`, `tester mode`, `docs mode`
- README gains a **"Working with the team"** how-to + a which-agent-for-what table

### Agents obey the rules (Law 29)
- Every role is fully bound by the laws; if it thinks it should do something the rules don't allow or cover, it **stops and asks** instead of acting on its own

### Stronger accessibility testing
- Beyond an axe scan, the Tester now explicitly verifies **tab order, visible focus states, keyboard-only operation, focus management/trap (modals + route change), roles + accessible names, and live regions** (`FULLSTACK_WORKFLOW §8.1`)

---

## v2.3.0 — June 12, 2026

### Deeper Fullstack engineering (FULLSTACK_WORKFLOW §6–§8)
- **Backend §6** — API contracts (contract-first, version breaking changes, contract tests); DB migrations (forward-only + reversible, expand → migrate → contract); observability (OpenTelemetry tracing, structured logs with request IDs, error tracking)
- **Frontend §7** — Core Web Vitals budgets, server-vs-client state (TanStack Query), loading/empty/error/success UI states + error boundaries, accessible forms
- **Testing §8 + Phase 5** — unit / integration / contract / E2E pyramid; RTL component tests, vitest-axe + axe-core/playwright zero-violation gate, MSW API mocking, Playwright E2E, meaningful coverage
- `agents/fullstack.md` references the full checklist

### AGENTS.md
- Added a root `AGENTS.md` shim pointing at the laws, so non-Claude agents (Cursor, Codex, Copilot, Aider, …) inherit Design Forge governance

---

## v2.2.0 — June 9, 2026

### Decks use your own PowerPoint template
- In research/deck mode, Claude asks you to share your `.pptx`/`.potx` template and builds the slides on top of it
- No built-in or third-party theme is ever used; if you have no template, you get a plain neutral 16:9 deck
- Removed the dangling `PPT_TEMPLATE.md` references (the file and `ppt-template/` skill never existed)

### Dependabot for scaffolded projects (Law 10)
- Every new project ships with `.github/dependabot.yml` — weekly update PRs for npm + GitHub Actions
- Applies to all platform tracks (React/Vite, React Native/Expo, Angular)
- This repo also gets a `dependabot.yml` (github-actions ecosystem)

### Stricter process discipline (Laws 2 + 7)
- Law 2: Claude announces what it understood and waits for explicit approval before executing — silence or "ok" is not approval
- Law 7: Claude never merges under any phrasing (no merge button, API, squash/rebase/fast-forward, or local merge); "merge it"/"ship it"/"done" = open/finish the PR and stop

### Update notifications (Law 28)
- At session start, Claude compares your loaded version against the remote and, if a newer one exists, shows: `Design Forge update available: v<x> → v<y>. Run \`update rules\` to pull and reload.`
- One global update reaches every consuming project (they share one `~/.design-forge`). Claude never auto-pulls — it notifies and waits for your go-ahead.
- Fixed the README law count (26 → 28)

---

## v2.1.0 — June 9, 2026

### Analyst persona (replaces Pendo mode)
- `pendo mode` → `analyst mode` — a tool-agnostic product-analytics persona
- Works with whichever analytics MCP is connected: Pendo, Amplitude, Mixpanel, PostHog, FullStory, Contentsquare (Heap/Hotjar), Adobe Analytics, Google Analytics 4, LogRocket, Statsig
- New `knowledge/ANALYTICS_GUIDE.md` with the supported-platform matrix, privacy rules, and Triangulated Insight Brief template — Pendo retained as the worked example
- Renamed `agents/pendo.md` → `agents/analyst.md` and `skills/pendo-analyst/` → `skills/analyst/`

---

## v2.0.0 — June 9, 2026 — Public release

### Public-ready repository
- New professional README explaining what Design Forge is and how anyone can use it
- `projects.yaml` is now gitignored — ships `projects.example.yaml` instead, so no personal project data is published
- `.claude-plugin/marketplace.json` added — the repo is installable via `/plugin marketplace add BojanKocijan/design-forge`

### New: `dry run` mode (Law 26)
- Toggle with `dry run` / `auto git`
- Claude prepares all edits, then prints a copy-paste terminal command block (commit/push/PR/issue) and offers to run it — instead of spending tokens executing git/gh itself
- Never overrides Law 7 (Claude never merges)

### New: plugin-standards compliance (Law 27)
- Codifies that the repo stays a valid, submittable Claude Code plugin
- Manifest + marketplace.json kept valid; skills as `skills/<name>/SKILL.md` with name+description; components at plugin root
- Version must stay in sync across plugin.json, marketplace.json, CLAUDE_LAWS header, and RELEASES on every release
- Quality/security gate (MIT license, README, no secrets, no personal data, CI green) before official-directory submission

### Plugin directory
- Tracking the submission of Design Forge to the official Claude Code plugin directory (`anthropics/claude-plugins-official`)

---

## v1.2.1 — June 9, 2026

### Proactive branch cleanup (Laws 9 + 25)
- Once a PR is merged, Claude deletes the branch (remote + local) without being asked
- Only deletes branches confirmed merged into `main` (`git merge-base --is-ancestor` check)
- Session-start checklist now sweeps orphaned merged branches
- Mirrored in FULLSTACK_WORKFLOW Phase 9

---

## v1.2.0 — June 8, 2026

### Session-start checklist (Law 25)
- Always pull `main` and check open PRs before any code work

### Automatic project wiring (Law 11)
- Laws load globally via `install.sh`; projects only link `@./PROJECT_KNOWLEDGE.md`
- Scaffold writes it for new projects; session-start step 4.6 auto-creates it for existing ones

---

## v1.1.0 — June 7, 2026

### New Laws (21–24): Senior-engineer thinking
- Law 21: No bloated code (YAGNI) — ask before over-engineering
- Law 22: Edge case thinking before code — identify 3-5 edge cases upfront
- Law 23: Verify before claiming — no hallucination, check the code first
- Law 24: Question and reason before executing — why, simpler way, best practice

### New law (5a): Check existing PRs
- Before branching, check if open/merged PR exists for same work
- Update existing PR instead of creating duplicate
- Prevents lost effort when resuming after quota limits

### Project Registry (Law 20): Auto-register new projects
- Detect unregistered project at session start
- Auto-open issue → branch → register in projects.yaml → PR workflow
- No manual registration step required
- Every project gets locked localhost port

**Documentation**: Auto-registration link in PROJECT_KNOWLEDGE.md template

---

## v1.0.0 — June 6, 2026

### Initial Design Forge release
- Library-agnostic from the start: shadcn/ui, MUI, Ant Design, Chakra UI, or local components
- `dforge-update` CLI, `~/.design-forge` clone dir
- 20 binding laws, 4-file component pattern, no-inline-styles rule, methodology (research, UX writing, handoff, feature workflow, fullstack workflow)
- Three install paths: plugin, install.sh (global memory), Copilot custom instructions
- Five personas: Frontend, Fullstack, Design, Research, Analyst
- Project registry with locked localhost ports per project
