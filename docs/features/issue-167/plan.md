# Plan — incident mode: read-only production investigation with a health check (#167)

Spec: [spec.md](spec.md) · Gate tier: Significant · Branch: `feat/incident-mode` · Issue: #167
Work pile: judgment-heavy (a new persona's rules and wording; done interactively, not delegated)
Approved-by: <pending>

## PRs (Law 31)

1. **This branch, `docs/issue-167-spec`:** `spec.md` and `plan.md` only. About 230 lines. Base `main`.
2. **`feat/incident-mode`:** everything below. About 250 lines in 9 files, so one PR. Base `main`. It links the spec by its path on `main`, so it opens after PR 1 merges, or links the branch until then.

## Files to change (PR 2)

| File | Change |
|---|---|
| `knowledge/INCIDENT_GUIDE.md` (new) | Header (binding for incident mode, loaded on demand, version 1.0.0). §1 Sources table from the spec, with tiers and the never-list. §2 Investigation flow: symptom and window → announcement → hypotheses → evidence → confirm, linking `engineering:debug`. §3 The incident note: `.git/info/exclude` step with `git check-ignore`, the template, "kept live". §4 Redaction rules and placeholders. §5 Handoff to Backend or Lead, fix issue only after the owner's yes. §6 `health check`: the three steps, severity rules, output format, "Not checked". §7 Law 38 defaults for observability connectors. §8 Postmortem via `engineering:incident-response`. Changelog |
| `agents/incident.md` (new) | Frontmatter: `name: incident`, `description` (when to invoke, read-only, Opus, never for fixes), `model: opus`, `effort: high`, `disallowedTools: Edit, NotebookEdit`. Body in the house style of `agents/backend.md`: who you are, binding knowledge (INCIDENT_GUIDE, FULLSTACK_WORKFLOW §6.3, CLAUDE_LAWS), what you do, what you never do, handoff |
| `CLAUDE.md` | Knowledge table: INCIDENT_GUIDE row (`incident mode` / `health check`). Trigger table: `incident mode` and `health check` rows. Supporting-roles table: Incident row. Confirmation template: `Incident` in the `Persona:` list. `ai classify` row: the observability defaults |
| `CLAUDE_LAWS.md` | Law 4 file list gains INCIDENT_GUIDE. The Personas line and Law 29's role list gain Incident. Version 2.29.0 |
| `knowledge/FULLSTACK_WORKFLOW.md` | §6.3: one line, the request ID is what an incident investigation correlates on, with a link to INCIDENT_GUIDE |
| `README.md` | Persona table row (Incident, `incident mode`, Opus), trigger rows for `incident mode` and `health check`, the "which mode" row, the file tree (`agents/incident.md`, `knowledge/INCIDENT_GUIDE.md`), the persona list in the diagram, version badge |
| `RELEASES.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | v2.29.0, version sync (Law 27) |

`install.sh` needs no change: it already links every `agents/*.md`.

## Order of work (PR 2)

1. **Verify the hosting CLI reads** (see Open items). Done when the guide names commands taken from `--help` or the official CLI docs, not from memory.
2. **`knowledge/INCIDENT_GUIDE.md`.** Done when every spec Behavior section has a home in it and markdownlint is clean.
3. **`agents/incident.md`.** Done when it links the guide and contains no write step.
4. **Wiring:** `CLAUDE.md`, `CLAUDE_LAWS.md`, FULLSTACK §6.3, README. Done when `grep -rn INCIDENT_GUIDE` hits all four and every link resolves.
5. **Release:** RELEASES and the version files. Done when `release_version.py check` prints `2.29.0`.
6. **Dry run** on `sports-training-api` (Supabase + Netlify): `health check`, then one short investigation of a real or staged symptom. Done when the redacted output is in the PR and `git check-ignore docs/incidents/<note>.md` succeeds there, with `git status` clean.
7. **Independent review** by a fresh-context subagent given the spec, this plan and the diff. Findings go into the PR, ranked.

## Proof

- **Tests to add or change:** none. No script or hook changes; nothing in `tests/` reads agents or the tables. Existing tests must stay green.
- **Commands that must pass:** `python3 -m unittest discover -s tests`, `python3 scripts/release_version.py check` → `2.29.0`, `npx markdownlint-cli2` on every changed `.md`, and a link check: `grep -o '](\.[^)]*)'` on the changed files, each target exists.
- **Consistency checks:** the never-list in the agent and in the guide match the spec. `query_logs` always carries an explicit window. `execute_sql` appears only as a tier 4 `SELECT`. No step polls or schedules.
- **Dry run (step 6):** the health check output (redacted), the note's path, the `git check-ignore` result, and `git status` showing nothing to commit in that project.
- **Visual evidence:** none (no UI). `Screenshots: not applicable`.

## Risks

- **The persona edits code anyway** (spec conflict 2). → `disallowedTools: Edit, NotebookEdit` when spawned; the main-thread rule stated first in the agent file and the guide; tier 4 still asks for `execute_sql`.
- **A redaction slips into chat or the fix issue.** → The redaction section applies to chat and issues as well as the note, and the handoff step re-reads the issue text for the placeholders before asking to create it.
- **`query_logs` field names differ per project** (`log_attributes` keys, level field). → The guide starts with `select distinct source from logs` and a one-row sample per source, and says not to assume field names.
- **The Netlify CLI isn't installed here** (`which netlify` finds nothing). → `health check` lists it under "Not checked" with the reason; see Open items for the dry run.
- **`.git/info/exclude` on a worktree:** it lives in the common git dir, so it applies to all worktrees. → Use `git rev-parse --git-common-dir` to find it; `git check-ignore` confirms either way.
- **Size creeps past 400 lines.** → The guide is capped at about 150 lines; anything more moves to a follow-up.

## Ruled out

- **A `skills/incident/SKILL.md`.** Backend, Lead and Tester have no skill either; the trigger and the agent file are enough (Law 21). Revisit if plugin users can't reach the persona.
- **Putting the template in the agent file.** The spec chose a knowledge file; one source keeps the main-thread mode and the subagent in step.
- **A script for the health check.** It's three tool calls that need judgment on the results; a script adds code to maintain for no gain.
- **Committing the `.git/info/exclude` change somewhere.** It can't be committed, by design.

## Open items for the owner (before step 1)

- [ ] **Hosting CLI commands.** Neither `netlify` nor `vercel` is installed here, so I can't read `--help` locally. Options: (a) I check the official CLI docs with the built-in browser, or (b) you install `netlify-cli` (`npm i -g netlify-cli`) and I read `netlify logs --help`. (b) also lets the dry run cover the deploy status. **Recommendation: (b).**
- [ ] **Dry-run project:** `sports-training-api` (Supabase + Netlify) unless you'd rather use `remodo`.
