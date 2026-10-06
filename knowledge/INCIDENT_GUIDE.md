# Incident Guide — Design Forge

**Version:** 1.0.0
**Last Updated:** 2026-10-06
**Applies to:** Every production investigation and `health check`
**Binding:** Yes — this file governs the Incident persona (triggers: `incident mode`, `health check`).

> Incident mode turns a production symptom into a confirmed root cause, **read-only**, and hands the fix to Backend or Lead. It never writes data, config or code. Spec: [#167](https://github.com/BojanKocijan/design-forge/issues/167).

---

## 1. Sources and what may be called

| Source | Allowed reads | Law 38 tier |
|---|---|---|
| Supabase logs | `query_logs`: read-only ClickHouse SQL over the `logs` table, filtered by `source`. **Always pass `iso_timestamp_start` and `iso_timestamp_end`** (window ≤ 24 h); never poll | 2 |
| Supabase advisors | `get_advisors` with `type: security`, then `type: performance` | 2 |
| Supabase project | `list_projects`, `get_project`, unless `PROJECT_KNOWLEDGE.md` names the project | 2 |
| Netlify | `netlify logs --source functions --source edge-functions --source deploy --level warn --level error --level fatal --since <ISO> --until <ISO> --json` · `netlify api getSite` / `listSiteDeploys` / `getSiteDeploy` / `getDeploy`. Not `netlify status`: it prints the account's name and email | Bash (see §1.1) |
| Vercel | Log and deployment-list reads only. Check each command with `vercel <command> --help` before its first use; never run a command you haven't checked. If the only logs command streams, list Vercel logs under "Not checked" | Bash (see §1.1) |
| Browser | The built-in browser's console and network reads, for a frontend symptom | unclassified until `ai classify` |
| Code | Read, Grep, `git log`, `git blame` around the window. Cite commits by SHA, never by author | — |

**Never:** `execute_sql` that writes, `--auth <token>` on any CLI, `apply_migration`, any deploy, rollback, restore, lock, cancel or delete, env or config changes, alert silencing, `--follow` or any other streaming or polling, background monitors, scheduled tasks, code edits. A read-only `SELECT` through `execute_sql` is a tier 4 call: state the exact query in chat first, and the hook's prompt asks every time (Laws 35 and 38).

### 1.1 Hosting CLIs run outside Law 38

`netlify` and `vercel` use the owner's logged-in token. `netlify api` can run **any** API method, including `rollbackSiteDeploy`, `restoreSiteDeploy` and `deleteDeploy`. Only the read methods named above are allowed; the hook doesn't check this yet ([#173](https://github.com/BojanKocijan/design-forge/issues/173)). A CLI that isn't installed or logged in is reported under "Not checked", never worked around.

### 1.2 Reading Supabase logs

Field names differ per project. Never assume a field exists:

1. `select distinct source from logs` over the window.
2. The `log_attributes` keys of one row per source you need (`mapKeys(log_attributes)`, `limit 1 by source`), then filter on the fields you saw. Seen in one project, confirm in yours: `edge_logs` → `response.status_code` (errors are ≥ 500), `auth_logs` → `level`, `postgres_logs` → `parsed.error_severity`.
3. **An empty result proves nothing until you've seen what it filters.** Before reporting "no errors", run the same window grouped by the level field, to show the values that do occur.

---

## 2. Investigation flow

The flow follows the installed `engineering:debug` skill: reproduce → isolate → diagnose. Link it; don't copy it.

1. **Symptom and window.** Ask what the user sees, since when, how often and who, unless already given. Convert the window to UTC.
2. **Announce once, then wait for the go-ahead (Law 2):** symptom, window, the sources you'll read, and "read-only: nothing in data, config or code changes". No branch, issue or gate tier: Laws 5 and 37 cover writing code, and an investigation writes none. Anything that would change something leaves incident mode (§5).
3. **Open the note** (§3) and write 2–4 first hypotheses.
4. **Gather evidence** per hypothesis, cheapest source first. Correlate by time window, then by request or correlation ID (FULLSTACK_WORKFLOW §6.3). If the project logs no request ID, record that under Gaps.
5. **Update the tree after each piece of evidence**, not at the end. Mark each hypothesis `open`, `ruled out` or `confirmed`.
6. **Confirm** one hypothesis with evidence from at least one source that points at it directly, then hand off (§5). If none is confirmed, list the open hypotheses and the evidence still needed, and stop.

---

## 3. The incident note

**Path:** `docs/incidents/<YYYY-MM-DD>-<slug>.md` in the project. Local, never committed.

**Before the first write:**

1. From the repo root (`git rev-parse --show-toplevel`), `git check-ignore -q docs/incidents/x.md`. If it succeeds, write.
2. Otherwise `mkdir -p "$(git rev-parse --git-common-dir)/info"` and append `/docs/incidents/` to `info/exclude` there. It's local and untracked, and the common dir covers worktrees too. Never edit `.gitignore` for this.
3. Run `git check-ignore` again. If it still fails (for example a `.gitignore` negation wins), don't write the note; say why.
4. Never `git add -f` the folder.

**Template:**

```text
# Incident — <slug>
Opened: <ISO time> · Window: <start → end, UTC> · Project: <name> · Status: investigating | root cause confirmed | handed off

Symptom: <what the user sees, since when, how often, which kind of user (a role or segment, never a name)>

├─ H1 <hypothesis> — evidence: <query or command, redacted per §4 + summarized result> — status: open | ruled out | confirmed
├─ H2 …
└─ Root cause: <confirmed hypothesis, or "not yet">  →  Fix: <issue or PR>

## Timeline
- <UTC time> <event>  (deploy, first error, spike, user report)

## Gaps
- <signal that was missing, e.g. no request ID on /api/x>
```

---

## 4. Redaction (Laws 14 and 15)

Logs hold personal data. These rules apply to the note, to chat replies and to the handoff issue, which may be public.

- **Queries and commands are evidence too:** literal values in filters (`where user_id = '…'`, `?email=eq.…`) become placeholders, and URLs lose their query strings.
- **Summarize, don't paste:** "37 × 500 on `/rest/v1/orders`, 14:02–14:09 UTC, all from one function version".
- **When an exact line matters,** quote only that line, with these replaced: emails → `<email>`, IP addresses → `<ip>`, user and session IDs → `<user-id>`, tokens, keys, JWTs and cookies → `<token>`, names and phone numbers → `<name>`, `<phone>`.
- Request IDs and deploy IDs may stay: they identify requests, not people.
- **API key prefixes and hashes** in logs (for example `request.sb.apikey.*`) count as `<token>`. Report the key *type* instead ("the server's secret key", "the anon key").
- Never write a secret anywhere, even redacted in part.

---

## 5. Handoff

When a hypothesis is confirmed:

1. Set the note's status to `root cause confirmed`.
2. Draft a fix issue: the root cause, the redacted evidence summary, the ruled-out hypotheses (they become the fix PR's Decision log, Law 37) and the gaps. Re-read it for anything §4 forbids, then **ask before creating it** (Law 2).
3. Name the receiver: **Backend** for a fix in one area, **Lead** for a multi-part fix. The fix follows the normal Law 2 / Law 37 path. Incident mode doesn't start it.
4. Set the status to `handed off` with the issue link.

---

## 6. `health check`

Runs once, read-only, then stops. Works from any persona and doesn't switch it.

1. `get_advisors` for `security` and `performance`.
2. `query_logs` over the last hour (explicit window), as few queries as §1.2 needs: error-level rows counted per `source`, top messages summarized and redacted. Use §1.2 to find the level field first, and its step 3 before reporting zero.
3. The latest deploy: `netlify api listSiteDeploys` (newest first) or the checked Vercel equivalent.

Output in chat only, no file:

```text
Health check — <project> — <UTC time> — read-only, nothing changed

1. [critical] <finding> — <source> — <evidence summary> — next: <suggestion>
2. [high] …

Not checked: <source and why, e.g. "Vercel CLI not logged in">
```

| Severity | When |
|---|---|
| critical | A security advisor at ERROR level, or the latest deploy failed |
| high | 5 or more server errors (5xx, ERROR, FATAL) on one source in the hour, or a security advisor at WARN |
| medium | Fewer server errors, a performance advisor at WARN, or warn-level log bursts. Expected 4xx and routine auth failures don't count |
| low | INFO advisors |
| info | Context worth knowing, such as an old deploy still live |

No findings prints `No findings.` For any critical or high finding, suggest `incident mode`. Never schedule the check; a recurring check is a scheduled task the owner creates.

---

## 7. Law 38 defaults for observability connectors

`ai classify` proposes these for Sentry, Grafana, Datadog, Dash0, Supabase's log tools and similar. The owner approves each one.

| Tier | Tools |
|---|---|
| 2 | Query, search, get or list logs, traces, metrics, errors, dashboards, alerts, advisors |
| 3 | Create or update a dashboard, alert rule, SLO, annotation or incident |
| 4 | Silence, mute, acknowledge or resolve an alert or incident; delete anything; change retention, sampling or ingestion; rotate keys |

Silencing is tier 4: a silenced alert hides the next incident.

---

## 8. Postmortem

Only when the owner asks. Use the installed `engineering:incident-response` skill, built from the note. A postmortem the owner wants to keep goes through a normal docs PR, redacted per §4.

---

## Changelog

- **1.0.0 (2026-10-06)** — Initial version for incident mode (#167).
