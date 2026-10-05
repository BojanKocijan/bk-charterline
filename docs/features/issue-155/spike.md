# Spike — an ops agent: which Agent0 capabilities Design Forge should add (#155)

Issue: [#155](https://github.com/BojanKocijan/design-forge/issues/155) · Type: spike (no code) · Date: 2026-10-05
Approved-by: <pending>

## What the owner's projects actually have (owner, 2026-10-05, chat)

- **Supabase logs:** API, Postgres, auth, storage and edge-function logs, plus the security and performance advisors, read through the Supabase connector. `query_logs` and `get_advisors` are already classified tier 2 (Law 38).
- **Netlify or Vercel logs:** deploy and function logs, through each CLI (`netlify logs`, `vercel logs`). These are plain Bash reads.
- **Not present:** an OpenTelemetry backend, distributed traces, a metrics store (Prometheus) or an error tracker.

Agent0 is built on an OTel stack that these projects don't have. Each recommendation below is judged against the data that exists today (Law 21). A "no-go" means "not until that data exists", not "never".

## Recommendation per gap

| # | Gap | Verdict | Why |
|---|---|---|---|
| 1 | Root cause from production telemetry | **Go, scoped** | Supabase and hosting logs are enough to correlate a failure by time window and request ID. Nothing reads them today. |
| 2 | Investigation hypothesis tree | **Go** | Cheap. It makes the reasoning visible while it happens, and it becomes the fix PR's Decision log (Law 37). |
| 3 | Plain-language questions over ops data | **Go, inside gap 1** | Writing the log query is how gap 1 works, so it isn't a separate feature. PromQL is moot without Prometheus. |
| 4 | Service dependency map | **No-go** | There are no traces. The architecture (frontend → Supabase, plus Netlify or Vercel functions) is static and belongs in `PROJECT_KNOWLEDGE.md`. Revisit when a project emits traces. |
| 5 | Dashboards, alerts and SLOs as code | **No-go** | There's nothing to receive them. Supabase's advisors are the closest thing, and gap 1 reads them. Revisit with Grafana, Dash0 or Datadog. |
| 6 | Proactive scanning every 60 s | **Ruled out as continuous; go as an on-demand health check** | A background loop conflicts with Law 2 (announce, then wait) and Law 37 (review capacity), and spends tokens on nothing. A read-only `health check` you start yourself gives the same signal. |

### Gap 1 and 3: how an investigation reads data

- **Supabase:** the connector's log tool, per service (API, Postgres, auth, storage, edge functions), over the incident's time window; `get_advisors` for security and performance findings. All tier 2.
- **Hosting:** `netlify logs` or `vercel logs` for function and deploy output around the same window.
- **The browser:** the built-in browser's console and network reads for a frontend symptom.
- **Correlation:** by timestamp and by request or correlation ID. FULLSTACK_WORKFLOW §6.3 already asks Backend to log one. Where a project doesn't, the investigation says so and adds "log a request ID" to the fix.
- **No writes.** The persona never changes data, config or code. The fix goes to Backend or Lead as a normal Law 37 change.

### Gap 2: the hypothesis tree

A file kept up during the investigation: `docs/incidents/<YYYY-MM-DD>-<slug>.md`.

```text
Symptom: <what the user sees, since when, how often>
├─ H1 <hypothesis> — evidence: <query + result summary> — status: open | ruled out | confirmed
├─ H2 …
└─ Root cause: <confirmed hypothesis>  →  Fix: <issue or PR>
```

- It reuses the installed `engineering:debug` flow (reproduce → isolate → diagnose → fix) and `engineering:incident-response` for a postmortem, by linking them instead of copying.
- **Logs contain personal data.** The note summarizes evidence and never pastes raw log lines with emails, IPs, tokens or user IDs (Laws 14 and 15). Where an exact line matters, it's redacted.

### Gap 6: the on-demand health check

`health check` (inside incident mode) runs once, read-only:
- `get_advisors`;
- the last hour of error-level logs per Supabase service;
- the latest Netlify or Vercel deploy status.

It reports findings ranked by severity and changes nothing. A recurring check would be a scheduled task **you** create, reporting only. Claude never sets one up on its own.

## Where the go items live: `incident mode`

- **New persona `agents/incident.md`**, activated by `incident mode`, plus a `health check` trigger. It's added to the persona tables in `CLAUDE.md`.
- **Read-only by design:** it can read logs, the advisors, the browser and the code. It writes only the incident note, and hands the fix to Backend (or Lead for a multi-part fix) with the confirmed root cause and the evidence.
- **Why not Analyst:** Analyst is product analytics (adoption, funnels) on Sonnet, and its tools and outputs differ.
- **Why not Backend:** Backend builds. Keeping diagnosis separate keeps "what's wrong" honest before "how to fix it", the same way Tester is independent of the author.
- **Model:** Opus, because diagnosis across logs is judgment-heavy (HUMAN_IN_THE_LOOP §6.3). Sonnet would be cheaper. **Owner decision.**

## Law 38 tiers for observability tools

The defaults `ai classify` proposes for any observability connector (Dash0, Sentry, Grafana, Datadog, and Supabase's log tools):

| Tier | Tools |
|---|---|
| 2 | Query, search, get or list logs, traces, metrics, errors, dashboards, alerts, advisors |
| 3 | Create or update a dashboard, alert rule, SLO, annotation or incident |
| 4 | Silence, mute, acknowledge or resolve an alert or incident; delete anything; change retention, sampling or ingestion; rotate keys |

Silencing sits at 4, not 3: a silenced alert hides the next incident, and can't be noticed after the fact.

## Follow-up work if this is approved

1. **One issue: "incident mode persona".** Covers `agents/incident.md`, the `incident mode` and `health check` triggers, the incident-note template (a short section in `knowledge/FULLSTACK_WORKFLOW.md` §6 or a new `knowledge/INCIDENT_GUIDE.md`), the Law 38 defaults above for `ai classify`, and README and RELEASES. Gate tier: Significant (a new persona and user flow), so intent is the issue, then spec, then plan.
2. **Nothing else for now.** Gaps 4 and 5 reopen when a project adds traces or an observability backend.

## Open questions for the owner

- [ ] Opus or Sonnet for the incident persona?
- [ ] Incident notes: commit them in the project repo (`docs/incidents/`), or keep them local and gitignored? Committed is reviewable; local is safer if a redaction is missed.
- [ ] Is `health check` worth having on day one, or should it wait until incident mode has been used a few times?
