# Spec — incident mode: read-only production investigation with a health check (#167)

Intent: [#167](https://github.com/BojanKocijan/design-forge/issues/167) (the issue is the intent) · Spike: [#155](../issue-155/spike.md) · Roadmap: #123
Design: none (no UI; a persona, two triggers and a knowledge file)
Approved-by: <pending>

## Decisions already taken (owner, in #167)

- **Opus**, because diagnosis across logs is judgment-heavy (HUMAN_IN_THE_LOOP §6.3).
- **Incident notes stay local and gitignored**, so a missed redaction never reaches a repo.
- **`health check` ships on day one.**
- **Linked, not copied:** the installed `engineering:debug` and `engineering:incident-response` skills.

## Open question settled here: where the incident-note template lives

**A new `knowledge/INCIDENT_GUIDE.md`**, not a section in FULLSTACK_WORKFLOW §6.

- §6 is the Backend *building* checklist, and every production PR loads FULLSTACK_WORKFLOW (457 lines). Incident content there would load on every build and be needed on almost none (Law 4).
- It matches the other supporting personas: Analyst → ANALYTICS_GUIDE, Research → UX_RESEARCH_GUIDE.
- `agents/incident.md` stays short, like the other persona files, and links the guide as its binding knowledge.
- §6.3 gains one line pointing to the guide: the request ID it asks Backend to log is what an investigation correlates on.

## Behavior

### Activation

- **`incident mode`** switches the main thread to the Incident persona, like `backend mode`. It stays active until another persona trigger. The Lead may also spawn it as a subagent.
- **`health check`** runs the one-off check below. It works from any persona and doesn't switch the persona.
- On activation Claude asks for the symptom (what, since when, how often, who sees it) and the time window, unless the user already gave them. It then posts a short announcement before the first read: symptom, window, the sources it will read, and "read-only: nothing in data, config or code changes". No branch or issue: an investigation changes nothing tracked (see conflict 6).

### What it reads (all reads)

| Source | How | Law 38 tier |
|---|---|---|
| Supabase logs | The connector's `query_logs`: read-only ClickHouse SQL over the unified `logs` table, filtered by `source` (`edge_logs`, `postgres_logs`, `function_edge_logs`, …; discovered with `select distinct source from logs`). Window ≤ 24 h, always passed explicitly | 2 |
| Supabase advisors | `get_advisors`, both `security` and `performance` | 2 |
| Supabase project | `list_projects` / `get_project` to find the project, unless `PROJECT_KNOWLEDGE.md` names it | 2 |
| Hosting | The Netlify or Vercel CLI through Bash: function logs, deploy logs, latest deploy status. The plan names the exact commands after checking the installed CLIs' `--help`; this spec doesn't guess flags | n/a (Bash, see conflict 3) |
| Browser | The built-in browser's console and network reads, for a frontend symptom | unclassified until `ai classify` (asks once per session) |
| Code | Read, Grep, `git log` / `git blame` around the window | n/a |

- **Correlation:** by time window first, then by request or correlation ID. Where the project logs no request ID, the note says so and the fix includes "log a request ID" (FULLSTACK_WORKFLOW §6.3).
- **Never:** `execute_sql` writes, `apply_migration`, deploys, rollbacks, env or config changes, alert silencing, code edits. `execute_sql` for a read-only `SELECT` is allowed only as a tier 4 call: Claude states the exact query in chat and the hook's prompt asks every time (Laws 35 and 38).
- **No loops.** `query_logs` is never polled. No scheduled tasks, no background monitors.

### The incident note

- **Path:** `docs/incidents/<YYYY-MM-DD>-<slug>.md` in the project.
- **Ignored before written:** before the first write, Claude makes sure the path is ignored. If it isn't, Claude adds `docs/incidents/` to `.git/info/exclude` (local, untracked, no commit; see conflict 1), then confirms with `git check-ignore`. If the check still fails, it doesn't write the note and says why.
- **Template** (in INCIDENT_GUIDE.md):

  ```text
  # Incident — <slug>
  Opened: <ISO time> · Window: <start → end, UTC> · Project: <name> · Status: investigating | root cause confirmed | handed off

  Symptom: <what the user sees, since when, how often, who>

  ├─ H1 <hypothesis> — evidence: <query or command + summarized result> — status: open | ruled out | confirmed
  ├─ H2 …
  └─ Root cause: <confirmed hypothesis, or "not yet">  →  Fix: <issue or PR>

  ## Timeline
  - <UTC time> <event>  (deploy, first error, spike, user report)

  ## Gaps
  - <signal that was missing, e.g. no request ID on /api/x>
  ```

- **Kept live:** Claude updates the tree after each piece of evidence, not at the end.
- **Redaction (Laws 14 and 15):** evidence is summarized ("37 × 500 on `/rest/v1/orders`, 14:02–14:09 UTC, all from one function version"). Raw log lines are never pasted. Where an exact line matters it's quoted with emails, IPs, user and session IDs, tokens, keys and JWTs replaced by `<email>`, `<ip>`, `<user-id>`, `<token>`. The same rule applies to the chat replies and to the handoff issue, which may be public.
- **Linked flows:** reproduce → isolate → diagnose follows `engineering:debug`. A postmortem, when the owner asks for one, uses `engineering:incident-response`. Neither is copied.

### Handoff

When a hypothesis is confirmed, Claude:

1. Sets the note's status to `root cause confirmed`.
2. Proposes a fix issue: the root cause, the redacted evidence summary, the ruled-out hypotheses (which become the fix PR's Decision log, Law 37) and the gaps. It creates the issue only after the owner's yes (Law 2).
3. Names the receiver: **Backend** for a single-area fix, **Lead** for a multi-part one. The fix follows the normal Law 2 / Law 37 path. Incident mode never starts it itself.

If nothing is confirmed, Claude says so, lists the open hypotheses and the evidence it would need next, and stops.

### `health check`

Runs once, read-only, then stops:

1. `get_advisors` for `security` and `performance`.
2. One `query_logs` over the last hour: error-level rows per `source`, counted, with the top messages summarized and redacted.
3. The latest Netlify or Vercel deploy status (CLI).

Output, in chat only (no file):

```text
Health check — <project> — <UTC time> — read-only, nothing changed

1. [critical] <finding> — <source> — <evidence summary> — next: <suggestion>
2. [high] …
…
Not checked: <source and why, e.g. "Vercel CLI not logged in">
```

Severity: **critical** (security advisor at ERROR level, or the latest deploy failed), **high** (error rate in the last hour, performance advisor at WARN on a hot table), **medium**, **low**, **info**. Nothing found prints "No findings." A source that can't be read is listed under "Not checked", never silently skipped. It suggests `incident mode` for any critical or high finding and never schedules itself; a recurring check is a scheduled task the owner creates.

### Law 38 defaults for observability tools

The `ai classify` row in `CLAUDE.md` gains the spike's defaults for any observability connector (Sentry, Grafana, Datadog, Dash0, Supabase logs):

- **2:** query, search, get or list logs, traces, metrics, errors, dashboards, alerts, advisors.
- **3:** create or update a dashboard, alert rule, SLO, annotation or incident.
- **4:** silence, mute, acknowledge or resolve an alert or incident; delete anything; change retention, sampling or ingestion; rotate keys.

These are proposals. The owner still approves each one (Law 38).

## Files the plan will touch (for sizing; the plan decides the order)

`agents/incident.md` (new) · `knowledge/INCIDENT_GUIDE.md` (new) · `CLAUDE.md` (triggers, persona table, knowledge table, `ai classify` row) · `CLAUDE_LAWS.md` (Law 4's file list, the persona line, version) · `knowledge/FULLSTACK_WORKFLOW.md` (§6.3 pointer) · `README.md` · `RELEASES.md` · `.claude-plugin/plugin.json` · `.claude-plugin/marketplace.json`. 9 files and likely over 400 lines, so the plan will probably split it into two PRs (Law 31): the guide and persona first, then the triggers, docs and version.

## Acceptance criteria

- [ ] `agents/incident.md` exists with `name`, `description` and `model: opus` frontmatter, links INCIDENT_GUIDE.md as binding knowledge, and states the read-only rule, the never-list and the handoff.
- [ ] `knowledge/INCIDENT_GUIDE.md` holds the sources table, the note template, the redaction rules, the `health check` steps and output, and links `engineering:debug` and `engineering:incident-response`.
- [ ] `incident mode` and `health check` are in the `CLAUDE.md` trigger table. Incident is in the supporting-roles persona table. INCIDENT_GUIDE.md is in the on-demand knowledge table and in Law 4's file list.
- [ ] The note is written only to an ignored path. The ignore goes to `.git/info/exclude`, never to a tracked file, and is checked with `git check-ignore` first.
- [ ] No step in the guide or persona calls a write tool, polls, or schedules anything. `execute_sql` appears only as a tier 4 read with the query stated in chat.
- [ ] The `ai classify` row lists the observability defaults.
- [ ] FULLSTACK_WORKFLOW §6.3 points to the guide.
- [ ] README (persona table, triggers, file tree) and RELEASES are updated; minor bump to 2.29.0 with the version sync (Law 27); `python3 -m unittest discover -s tests` and markdownlint pass.
- [ ] A dry run on one real project is recorded in the PR: `health check` output (redacted) and one short investigation, with the note confirmed ignored.
- [ ] Independent review by a fresh-context Claude subagent before merge (Significant).

## Policy check

- Component library, accessibility, copy: not applicable (no UI). The health check output and prompts follow the house style: short, specific, the next action named.
- **Conflicts flagged for the owner:**
  1. **`.git/info/exclude` instead of `.gitignore`.** #167 says to add `docs/incidents/` to the project's `.gitignore`. That's a tracked file, so it needs a branch, an issue and a PR (Law 5) before the first note can be written, in the middle of an incident. `.git/info/exclude` is local, untracked and has the same effect. Trade-off: a teammate's clone doesn't ignore the folder, but their notes are theirs. **Recommendation: `.git/info/exclude`.**
  2. **Read-only is enforced by instruction, not mechanically.** The persona needs Write (the note) and Bash (the CLIs and `git check-ignore`), so it could still edit code. The hook backstops the worst cases: tier 4 MCP calls ask every time, and deleting tracked files asks. As a subagent, `disallowedTools` can drop `Edit` and `NotebookEdit`. The Supabase server's tool names are per-user ids, so the shipped agent file can't name `execute_sql` there; tier 4 covers it.
  3. **Hosting CLIs run through Bash, outside Law 38.** `netlify` and `vercel` use your logged-in token and can deploy, roll back or change env vars. The hook doesn't see them. The persona allows only their log and status reads by instruction. A hook ask for `netlify deploy|env:*` and `vercel deploy|rollback|env` would close this. **Recommendation: a follow-up issue, not this one.**
  4. **The browser tools ask once per session** until you classify `mcp:Claude_Browser`. Running `ai classify` first avoids the prompt.
  5. **`get_advisors` is tier 2 in your personal registry** (as an override on a tier 4 server). A project that commits its own `.claude/ai-tools.json` can change that (Law 38 known limit).
  6. **No branch or issue for an investigation.** Laws 2 and 5 cover changes. An investigation changes nothing tracked, so it gets the short announcement and no branch. The fix gets the full path.

## Out of scope

- Writing the fix (Backend or Lead does it).
- Dependency maps, alerts and SLOs as code (spike gaps 4 and 5), until a project has traces or an observability backend.
- Any continuous or scheduled scanning.
- Committed incident notes or postmortems. A postmortem the owner wants to keep goes through `engineering:incident-response` and a normal docs PR.
- Hook enforcement for the hosting CLIs (conflict 3).
- Observability connectors other than Supabase (Sentry, Datadog, …). The guide names the tier defaults; reading them waits until one is connected.
