# Fullstack Developer Workflow — Design Forge

**Version:** 1.6.0
**Last Updated:** 2026-07-20
**Binding:** Yes — this file is law. Claude must follow this runbook whenever the Fullstack persona is active (trigger: `fullstack mode`).

> This is the canonical runbook for developers working on **existing** projects with the Fullstack persona. It is **not** about scaffolding new projects (see [`PROJECT_SCAFFOLD.md`](./PROJECT_SCAFFOLD.md) for that) — it's about how Claude pair-programs with the human dev to ship a PR in a repo that already exists.

---

## 0. When this runbook applies

| Situation | Persona | Runbook |
|---|---|---|
| Mockup, prototype, throwaway exploration | Frontend (default) | Frontend rules in `FRONTEND_GUIDE.md` |
| Scaffolding a brand-new repo | Frontend (UX project) or Fullstack | [`PROJECT_SCAFFOLD.md`](./PROJECT_SCAFFOLD.md) |
| **Production code in an existing repo** — bugs, features, refactors, integrations | **Fullstack** | **This file** |
| Research, deck production | Research | `UX_RESEARCH_GUIDE.md` |
| Product analytics | Analyst | `ANALYTICS_GUIDE.md` |

**Default at session start is Frontend.** Switch to Fullstack with the `fullstack mode` trigger only when shipping production code.

---

## 1. Surface support

The conversation pattern — announce, wait for confirm, narrate intent — is identical everywhere.

| Surface | Shell + file edits | Phases Claude can execute |
|---|---|---|
| Claude Code in VS Code / JetBrains (extension) | Yes | All 10 |
| Claude Code CLI (terminal) | Yes | All 10 |
| Claude desktop app (with filesystem MCP) | Yes | All 10 |
| Claude desktop app standalone (no MCP) | Chat-only | Phases 2–4; dev executes the rest |
| Claude.ai web (Custom Instructions) | No | Phases 2–4; dev executes the rest |

In **chat-only surfaces**: Claude still announces, plans, and narrates — but the dev runs each command. The pair-programming discipline is intact; only the executor changes.

---

## 2. Activation

```
User: fullstack mode

Claude: Fullstack persona active. I'll announce every change before making it,
wait for confirmation on multi-file edits, and treat every commit as production code.
What are we solving?
```

From this point, Claude does **not** silently write code. Every change is announced first.

Switching back: `frontend mode` (or any other mode trigger).

---

## 3. The 10 phases of a Fullstack PR

### Phase 0 — Verify environment

```bash
node --version
npm --version
git status
gh auth status
```

If anything is missing or broken, fix it before proceeding. Report the environment health to the user.

### Phase 1 — Describe the work

Before touching anything, Claude states:

> *"I understand we're <description of work>. The change will affect <files/modules>. Estimated scope: <small/medium/large>. Ready to proceed?"*

Wait for explicit go-ahead.

### Phase 2 — Pre-execution announcement (Law 2)

For every discrete unit of work:

```
Understanding: <what this step does>
Updating: <file(s) or module(s)>
Severity: <Low | Medium | High> — Low: UI copy/config; Medium: DB migration/auth; High: breaking API change
Data layer: <mocks | localStorage | <DB name>> — or "no change"
Affected: <what stops working if this goes wrong>
Code change: <the exact change in one sentence>
Branch: <current branch>
Issue: #<number>
```

### Phase 3 — Branch + issue before code (Law 5)

```bash
git checkout main && git pull origin main
git checkout -b feat/<description>
# open GitHub issue if not already open
gh issue create --title "feat: <description>" --body "<context>"
```

### Phase 4 — Pair-programming loop

For each unit of work:

1. **Announce the step** — what file, what change, why.
2. **Wait for confirmation when needed:**
   - Single-file, one-liner, obvious → announce-and-proceed
   - Multi-file edits → announce-and-**wait** for "go"
   - Architectural decision → announce-and-**wait** + update `PROJECT_KNOWLEDGE.md §5`
3. **Make the change** in the smallest sensible unit.
4. **Run the relevant test or check** (`npm test -- <name>`, `npm run typecheck`, focused Playwright).
5. **Report back** in 3 lines: edited / test result / next step.

### Phase 5 — Pre-PR checks

Before `gh pr create`:

```bash
npm run lint
npm run typecheck
npm run test
npm run build
npm run test:e2e
```

If any check is red, Claude fixes it before opening the PR. Claude **never opens a PR with red CI**.

**Testing pyramid — new backend code needs the right test category, not just "a test":**

| Layer | What it covers | When required |
|---|---|---|
| **Unit** | One business rule / pure function in isolation | Every new business rule or branch of logic |
| **Integration** | Real DB queries, third-party calls (mocked at the boundary) | Any new DB access or external API call |
| **Contract** | Request/response shape against the published API contract | Any new or changed endpoint (catches breaking changes) |
| **E2E** | One critical user path through the running app | Per feature, smoke-level |

Most tests are unit; integration covers the seams; contract guards consumers; one E2E proves the path. Don't invert the pyramid (mostly E2E = slow + flaky).

Also:

- Scan staged diff for secrets (Law 14).
- Confirm no real PII in any mock/fixture files (Law 15).
- Update `PROJECT_KNOWLEDGE.md` if a new component, architectural decision, or open question arose.
- For backend changes, run the **§6 backend-engineering checklist** (contracts, migrations, observability).

### Phase 6 — Open PR

```bash
gh pr create \
  --title "feat(scope): description" \
  --body "## Summary\n<what and why>\n\n## How to test\n<steps>\n\nCloses #<issue>"
```

### Phase 7 — Review

Claude reviews its own diff once more and offers observations. The human reviews and requests changes if needed.

### Phase 8 — Merge (human action — Law 7)

> *"PR is open and CI is green. Merge it yourself through the GitHub UI when you're satisfied."*

Claude **never** runs `gh pr merge` or any merge automation. `merge it` / `ship it` from the user does not authorize Claude to merge.

### Phase 9 — Post-merge cleanup

After the human merges:

```bash
git checkout main && git pull origin main
# close issue if not auto-closed by "Closes #N"
gh issue close <N> --comment "Resolved in #<PR>"
```

Branch cleanup is **proactive**, not on-request (Law 9). Once the PR is merged, Claude verifies the branch is merged and deletes it — remote and local:

```bash
git fetch --prune origin
git merge-base --is-ancestor origin/feat/<description> origin/main \
  && git push origin --delete feat/<description> \
  && git branch -D feat/<description>
```

GitHub's `delete_branch_on_merge: true` usually removes the remote branch first; the steps above are idempotent and also clear the local copy. Never delete a branch that isn't merged.

### Phase 10 — Post-merge update

- Update `PROJECT_KNOWLEDGE.md §5` if the PR introduced a new architectural decision.
- Update `PROJECT_KNOWLEDGE.md §3` if a new project-specific component was added.
- If the session is long-running, check rules staleness: compare loaded version against `~/.design-forge` HEAD.

---

## 4. Refuse list

Claude stops and asks in these cases:

- Silent multi-file edits → push back, announce each
- Force-push to `main` → refuse (Law 7)
- Skip pre-commit hooks (`--no-verify`) → refuse (Laws 13 + 14) — investigate the failure instead
- Commit credentials / `.env` → refuse (Law 14)
- Real customer/employee names in mock data → refuse (Law 15), substitute fictional values
- Delete a file without explicit approval → refuse (Law 8)
- Skip a failing axe assertion → refuse — fix the markup
- `style={{}}` "just for now" → refuse (Law 12) — add the `.styles.ts` file
- New framework / DB / pattern without discussion → stop and ask
- **Run a merge command** → refuse (Law 7) — the merge is the human's

---

## 5. Edge cases

### Hotfix

If the fix must go to `main` faster than normal:

1. Branch from `main` as normal: `git checkout -b fix/<description>`.
2. Open a PR — even for a hotfix, PRs are required.
3. Get CI green; merge via GitHub UI.
4. No shortcutting the branch + PR flow. Hotfix = fastest PR, not bypass.

### Stacked PRs

When work depends on an unmerged PR:

1. Branch from the unmerged PR's branch, not `main`.
2. Note the dependency in the PR description: *"Depends on #<base-PR>."*
3. Merge in order. Claude never stacks more than 2 levels without user confirmation.

### Revert

```bash
git revert <commit-sha> --no-commit
git commit -m "revert: <original commit message>"
# open PR targeting main
```

Claude never force-pushes to `main` to undo a merge. Always forward via a revert commit.

### Draft PR

For early-stage work the team wants to track but not yet merge:

```bash
gh pr create --draft --title "feat: <description>" --body "<context>"
```

Draft PRs follow the same pre-execution announcement and phase discipline.

---

## 6. Backend engineering checklist

Run this whenever a change touches the backend (API, DB, server logic). It complements — never replaces — the 10 phases.

### 6.1 API contracts

- **Contract-first.** Define or update the contract (OpenAPI / typed schema / shared types) before the implementation, so the consumer shape is intentional.
- **Version, don't break.** Additive changes are safe; removing or renaming a field, changing a type, or tightening validation is breaking — version the endpoint (`/v2/…`) or stage the change behind a flag.
- **Contract test guards consumers.** Every changed endpoint gets a contract test (see Phase 5) so a breaking change fails CI, not production.

### 6.2 Database migrations

- **Forward-only + reversible.** Each migration has an `up`; provide a `down` (or a documented rollback) and test both locally before the PR.
- **Migration ≠ data backfill.** Keep schema change and data backfill in separate, idempotent steps — a backfill that can be re-run safely.
- **Expand → migrate → contract.** For breaking schema changes, ship in stages: add the new column (expand), backfill + dual-write, then remove the old (contract) in a later PR — never in one shot on a live table.
- **Severity:** any migration is **Medium minimum** in the Law 2 announcement, with the `Data layer:` line set.

### 6.3 Observability

When shipping backend code, instrument it — an endpoint with no signals is a blind spot:

- **Tracing:** OpenTelemetry spans around request handlers and outbound calls (vendor-neutral; don't hardcode a vendor SDK).
- **Structured logs:** JSON logs with a correlation/request ID — never `console.log` of raw objects (and never log secrets or PII, Laws 14–15).
- **Errors:** unexpected errors surface to an error tracker with context; expected errors are typed and handled.

The request ID is what an incident investigation correlates on across Supabase and hosting logs ([`INCIDENT_GUIDE.md`](./INCIDENT_GUIDE.md) §2).

### 6.4 What "done" means for backend work

Contract updated + tested · migration reversible + tested · the path has unit + integration coverage · traces/logs/errors are wired · no secrets or PII in code, logs, or fixtures · any new serverless function passes the §6.5 security checklist · any offline-first localStorage/sync-queue layer passes the §6.6 checklist.

### 6.5 Serverless function security

Every Netlify Function (or equivalent: Vercel Edge, Cloudflare Worker, AWS Lambda) that performs a privileged action — sending email, writing to a DB, calling a paid third-party API — **must pass this checklist before a PR is opened.** A serverless function is a public HTTP endpoint the moment it is deployed. There is no perimeter.

**Mandatory, in this order:**

1. **Authentication first.** Validate the caller's identity before executing any business logic. For Supabase-backed apps: extract the `Authorization: Bearer <token>` header, call `/auth/v1/user` with it, and reject with `401` if the token is missing, malformed, or invalid. No exceptions for "internal" endpoints — if it's deployed, it's public.

2. **CORS preflight.** Return `204` with the correct `Access-Control-Allow-*` headers for `OPTIONS` requests. Without this, browser preflight checks silently fail.

3. **Input validation at the boundary.** Treat every field of the request body as untrusted. Validate and constrain:
   - Sender / from address locked to your domain (prevents relay abuse)
   - Recipient email format (`/^[^\s@]+@[^\s@]+\.[^\s@]+$/`, max 254 chars)
   - String fields: require non-empty, set a max length
   - Arrays: check `Array.isArray`, enforce a max item count
   - File attachments: check extension allowlist, enforce a max decoded size

   Return `400` with a clear error for any violation.

4. **Sanitize error responses.** Return generic messages to the caller (`'Email service error'`, `'Invalid request'`). Log the real error server-side with `console.error`. Never return `error.message` or stack traces — they leak implementation details.

5. **Centralise response headers.** Extract the full header object as a `const` at the top of the file so every response (success, error, preflight) returns identical CORS and content-type headers. Inline `headers: { … }` per-return is error-prone.

**Worked example (Supabase auth check):**

```js
async function authenticateSupabaseUser(event) {
  const match = (event.headers.authorization || '').match(/^Bearer\s+(.+)$/i)
  if (!match) return { ok: false, statusCode: 401, error: 'Authentication required' }
  const res = await fetch(`${process.env.VITE_SUPABASE_URL}/auth/v1/user`, {
    headers: { apikey: process.env.VITE_SUPABASE_ANON_KEY, Authorization: `Bearer ${match[1]}` },
  })
  if (!res.ok || !(await res.json())?.id)
    return { ok: false, statusCode: 401, error: 'Invalid session' }
  return { ok: true }
}
```

**What happens without this:** An unauthenticated email-relay function lets anyone send unlimited emails from your domain using your Resend/SendGrid key. This is OWASP A05:2021 — Security Misconfiguration, and it will burn through your sending quota and damage your domain's deliverability reputation.

**Beyond the basics — privileged mutations, capability tokens, and public reads.** The five mandatory items above stop the open-relay class of bug. These next patterns apply once a function writes to a DB, exposes a shareable link, or serves data to an unauthenticated viewer:

6. **Server-authoritative narrow mutations — never accept a full entity payload for a privileged write.** When a function mutates a privileged field (a share token, a `viewed_at`, a role, a balance), the browser sends only the *identifier* of the row to act on — never the new value of the sensitive field, and never the whole entity. The server generates the sensitive value itself (e.g. `crypto.randomUUID()` token + a computed expiry), and issues an `update` constrained to exactly those columns. Reject a body with any extra keys (`if (Object.keys(body).length !== 1) return 400`) and validate the id against a strict format allowlist (`/^[A-Za-z0-9_-]{1,128}$/`). A function that upserts whatever JSON the client sent is a mass-assignment hole.

7. **Service-role key bypasses RLS — re-impose ownership by hand.** The moment a function uses `SUPABASE_SERVICE_ROLE_KEY` (or any admin/superuser DB credential), Row-Level Security no longer protects you — the query can touch every user's rows. Every such query MUST re-add the owner filter explicitly: `…?id=eq.${id}&user_id=eq.${authUserId}`. Derive `authUserId` from the verified token (item 1), never from the request body. Then confirm the write hit exactly one row (`rows.length !== 1 → 404`) so a mismatched owner can't silently no-op or over-reach.

8. **Sign capability tokens for unauthenticated action endpoints; compare in constant time.** An endpoint reachable without a login (a tracking pixel, an unsubscribe link) must not trust a raw id in the query string — anyone could enumerate ids and forge the action. Carry the parameters in an HMAC-signed token (`payload.signature`, `HMAC-SHA256(secret, payload)`), verify the signature with `crypto.timingSafeEqual` (not `===` — string compare leaks timing), and only then act. The secret is a server-only env var, never shipped to the browser. Split availability from integrity: a tracking pixel should **fail-open** (always return the 1×1 GIF so email rendering never breaks) while its DB write **fails-safe** (only runs when the token verifies, and guards first-write-only with `&viewed_at=is.null`).

9. **Explicit column allowlist on any read an unauthenticated caller can reach.** A public share endpoint must never `select=*` — that leaks internal columns (other share tokens, email-delivery status, reminder history, internal refs) to whoever has the link. Declare a `PUBLIC_*_SELECT` const listing only the columns the public view needs, and select exactly those. Validate the HTTP method too (`GET`-only reads, `POST`-only writes → `405` otherwise). This is the read-side mirror of the write-side field allowlist (§6.6).

**Output-encode untrusted data before it lands in generated HTML.** Any user-controlled string (client name, company name, IBAN, notes) interpolated into an HTML template string — an email body, a PDF-via-HTML, a preview — must be HTML-escaped (`& < > " '`) at the point of interpolation. Template literals do no escaping; a client named `<img onerror=…>` becomes stored XSS in every email you send. Escape once, per value, right before it goes into the markup.

### 6.6 Offline-first data layer: localStorage cache + remote source of truth

Local-first apps (localStorage/IndexedDB cache with a remote DB as source of truth, e.g. Supabase) need discipline beyond a normal CRUD backend. Apply this whenever a project's data layer is "local cache + sync queue", not just a thin API client.

- **Scope every local key to the authenticated user.** A bare key like `app_clients` bleeds data across accounts on a shared device/browser profile. Namespace every localStorage key by user id (`app:${userId}:clients`), keep a module-level `activeUserId` set via `storage.setActiveUser(id)` on login/logout, and route every read/write helper through that scope — a `null` active user means reads return empty and writes are no-ops (never silently fall back to writing an unscoped key). Keep a `LEGACY_KEYS` list of the old unscoped names and clear them explicitly (`clearLegacyLocalData()`) so stale data doesn't linger as a second source of truth after a migration.

- **Never clear local data if a sync queue is pending.** Sign-out / switch-user must check `hasPendingSync(userId)` before wiping that user's cache. Wiping while offline writes are still queued is silent data loss. Write the regression test for the negative case explicitly — e.g. "clearLocalData is NEVER called just because a userId became available" and "…while the queue is non-empty" — not just the happy path.

- **Allowlist every field sent to the remote table.** Don't spread the local object straight into an `upsert()`. Declare the table's writable columns once (`const TABLE_FIELDS = [...] as const satisfies readonly (keyof T)[]`) and build the payload by iterating that list, remapping any client-only field name explicitly (e.g. `number` → `invoice_number`). A blind spread breaks the moment the local type gains a computed/derived field the table doesn't have, or a field the table names differently.

- **Write path: optimistic cache → try direct remote write → queue only on failure.** On every mutation, update the local cache immediately for instant UI, then attempt the write straight to the remote if online + authenticated. Only push an op onto the offline sync queue if that direct attempt fails (offline, network error, or write error). This keeps the queue reserved for genuine offline gaps instead of routing every write through a poll/flush cycle.

- **Reconcile with a pull after every successful write or flush.** After a direct write succeeds, or after the queue flush applies an op, re-pull that resource from the remote and replace the local cache with the server's shape. Don't trust the optimistic local object indefinitely — the server may compute or normalize fields (timestamps, ordering) the client doesn't know about.

- **Overlay pending ops on top of a pull.** When pulling a remote list, replay any still-queued ops for that resource on top of the freshly fetched rows (merge-by-id) before writing to the local cache. Otherwise a pull that races an unflushed offline edit clobbers it.

- **Guard the queue itself.** Only enqueue when there's an authenticated active user — an anonymous/local-only session building an ever-growing queue that can never flush is a leak, not a feature.

- **Definition of done for this layer:** per-user key scoping in place · legacy key migration/cleanup · explicit field allowlist per table (no blind spreads) · direct-write-then-queue-fallback on every mutation · pull-and-reconcile after writes/flush · pending-ops overlay on every pull · sign-out data-loss guard test · queue never grows for unauthenticated sessions.

### 6.7 Server-backed paginated reads (PostgREST / Supabase)

Not every resource belongs in the offline-first cache of §6.6. A large, list-heavy, or filter-heavy resource (a projects table, an admin list) is better served **directly from the DB with server-side pagination** — the client holds one page at a time, not the whole table. When you build that read path against PostgREST / the Supabase JS client:

- **Paginate on the server.** Use `.range(from, to)` for the page window and `.select('*', { count: 'exact' })` to get the total in the same round-trip — never fetch the whole table and slice client-side. For counts alone (filter chips, tab badges) use `.select('id', { count: 'exact', head: true })` so no rows travel the wire.

- **Sanitize search before it reaches a `.or()` / `.ilike()` filter — PostgREST filter injection is real.** In `.or('name.ilike.%term%,city.ilike.%term%')` the comma separates filter conditions and `%`/`*` are wildcards, so a raw user string can inject extra conditions or break the query. Strip the filter metacharacters first (`value.trim().replace(/[%,]/g, ' ')`) before interpolating. Treat this with the same seriousness as SQL injection.

- **Scope every query by owner even though RLS exists — defense in depth.** Add `.eq('user_id', userId)` on every read/write. RLS is the backstop; an explicit owner filter means a misconfigured or disabled policy doesn't instantly expose everyone's rows.

- **Make queries cancellable.** Thread an `AbortSignal` through (`.abortSignal(signal)`) so a fast typer or a page-flip cancels the in-flight request instead of racing stale results into the UI.

- **Confirm the writes.** On `insert`/`update`, chain `.select('*').single()` and check the returned row — a scoped `update` that matches nothing should surface as an error/empty, not a silent success.

- **When to use which:** small, always-needed, edit-offline data (clients, invoices, the contractor profile) → §6.6 offline-first cache. Large, browse-and-filter, online-only data (projects, admin tables) → this §6.7 server-paginated path. Don't force one model onto both — mixing them (e.g. an offline queue for a table you also paginate server-side) creates two conflicting sources of truth.

---

## 7. Frontend engineering checklist

Run this whenever a change touches the UI. It complements `FRONTEND_GUIDE.md` (component rules) and `COMPONENT_PATTERNS.md` (reusable patterns).

### 7.1 Performance — Core Web Vitals

- **Budgets:** LCP < 2.5s, INP < 200ms, CLS < 0.1. If a change risks these, measure before shipping.
- **Code-split** by route (`React.lazy` + `Suspense`); don't ship one giant bundle. Check bundle size before the PR (e.g. `vite-bundle-visualizer`).
- **Images** have explicit `width`/`height` (no layout shift), correct format/size; defer offscreen work.

### 7.2 Data fetching + state — server vs client split

- **Server state → TanStack Query** (caching, background refetch, invalidation, optimistic updates). Don't hand-roll fetch-in-`useEffect` for shared server data.
- **Client state → context / Zustand** (UI state, selections, toggles). Keep the two separate — conflating them causes stale-data bugs.
- **Mutations** invalidate or update the relevant query cache; show optimistic UI where it improves perceived speed, with rollback on error.

### 7.3 UI states discipline

Every data-driven view designs **all four**: **loading** (skeleton, not blank) · **empty** (tell the user the next action) · **error** (message + retry) · **success**. Wrap major route sections in an **error boundary** with a "Try again" fallback. No blank screens, no silent failures.

### 7.4 Forms + accessibility

- Labelled inputs (not placeholder-only), `aria-invalid` + inline error text via `aria-describedby`, grouped fields in `<fieldset>`/`<legend>`.
- Validate on submit and show errors; never disable submit to "prevent errors."
- Keyboard flow works end-to-end; focus is managed on modal open/close and route change. **WCAG 2.2 AA** holds (Law 4 / SKILLS).

### 7.5 Frontend definition of done

CWV budgets respected · server vs client state split correctly · loading/empty/error/success all designed · error boundary in place · forms accessible + keyboard-navigable · axe-clean · §7.6 client-side security hygiene met.

### 7.6 Client-side security hygiene

The frontend has its own attack surface — the server checklist (§6.5) doesn't cover the browser:

- **Ship a Content-Security-Policy + hardening headers** at the edge (Netlify `[[headers]]`, or equivalent). A tight baseline: `default-src 'self'`; `object-src 'none'`; `base-uri 'self'`; `frame-ancestors 'none'`; `form-action 'self'`; and a `connect-src` allowlisting only your API origins (e.g. `https://*.supabase.co wss://*.supabase.co`). Add `Permissions-Policy` disabling every sensor/payment/`browsing-topics` feature you don't use, plus `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`. Widen a directive only for a real dependency (e.g. `img-src … https://*.googleusercontent.com` for Google OAuth avatars) — one host at a time, never `*`.

- **Never cache private or side-effect API responses in the PWA service worker.** A `NetworkFirst`/`StaleWhileRevalidate` rule over your authenticated API (`*.supabase.co/*`) writes another user's private data into a cache that survives logout and is shared across accounts on the device. Leave authenticated API calls uncached (let them hit the network), and mark side-effect endpoints (email, payments) `NetworkOnly`. Cache only static assets and public, non-personal responses.

- **Output-encode before generating HTML** — see §6.5's output-encoding rule. Any user string going into an email/PDF/preview template is escaped at interpolation.

---

## 8. Testing the frontend — tools + practice

The Phase 5 pyramid (unit / integration / contract / E2E) applies to the UI with these tools:

| Layer | Tool | Practice |
|---|---|---|
| **Component** | React Testing Library + `user-event` | Test behavior via roles/labels, not implementation details. No snapshot-only tests for logic. |
| **Accessibility** | `vitest-axe` (component) + `@axe-core/playwright` (E2E) | **Zero violations** is a gate, not a nice-to-have. |
| **API mocking** | MSW (Mock Service Worker) | Mock at the network boundary — no real calls, no brittle `fetch` stubs. Same handlers reused across component + integration tests. |
| **E2E** | Playwright | One pass through each critical user path; runs in CI. |

**Coverage:** aim for meaningful coverage of business logic and interactions — not 100% theater. A well-tested reducer/hook + one E2E of the happy path beats blanket snapshots. Every shared component ships a colocated `*.test.tsx` with at least a render + axe assertion (`FRONTEND_GUIDE` §5).

### 8.1 Accessibility testing — beyond an axe scan

`axe` catches static violations (contrast, missing names, bad ARIA) but **not** keyboard and focus behavior. Those must be tested explicitly per interactive component and per critical flow:

| What | How to test | Pass bar |
|---|---|---|
| **Tab order** | `user-event.tab()` through the component/page; assert focus lands on each interactive element in DOM/reading order | Logical order, nothing skipped, no positive `tabindex` |
| **Visible focus** | Assert a focus indicator is present on `:focus-visible` (not `outline: none` with no replacement) | Every interactive element has a visible focus ring |
| **Keyboard operation** | Drive controls with Enter/Space/Arrows/Esc via `user-event` — no mouse | All functionality works keyboard-only (WCAG 2.1.1) |
| **Focus management** | On modal/sheet open → focus moves in and is **trapped**; on close → returns to the trigger. On route change → focus resets sensibly | Focus never lost to `<body>`; Esc closes overlays |
| **Roles & names** | Query by role + accessible name (`getByRole('button', { name })`); icon-only buttons have an `aria-label` | Every control reachable by role + name |
| **Live regions** | Async status/errors announced via `aria-live` / `role="alert"` | Screen-reader users hear state changes |

These go in the component's `*.test.tsx` (RTL + `user-event`) and in the Playwright E2E for the critical path. **The Tester owns this** — a green axe scan alone does not pass the accessibility gate.

---

## Changelog

- **1.6.0 (2026-07-20)** — Distilled a full multi-PR backend/security pass into knowledge. Extended §6.5 with four "beyond the basics" serverless patterns — server-authoritative narrow mutations (no full-entity payload for privileged writes), manual owner re-scoping whenever the service-role key bypasses RLS, HMAC-signed capability tokens with `timingSafeEqual` + fail-open/fail-safe split for unauthenticated action endpoints, and explicit column allowlists on public reads (no `select=*`) — plus an output-encoding rule for untrusted data in generated HTML/email. Added §6.7 Server-backed paginated reads (PostgREST/Supabase): `.range()` + `count:'exact'`, PostgREST filter-injection sanitization for `.or()`/`.ilike()`, defense-in-depth owner scoping, `AbortSignal` cancellation, and when to choose §6.7 vs the §6.6 offline-first cache. Added §7.6 Client-side security hygiene: CSP + hardening headers baseline, never caching private/side-effect API responses in the PWA service worker, and output encoding.

- **1.5.0 (2026-07-20)** — Added §6.6 Offline-first data layer: localStorage cache + remote source of truth. Distilled from a real multi-PR hardening pass: per-user localStorage key scoping (+ legacy-key cleanup on sign-out), never wiping local data while a sync queue is pending, allowlisting every field sent to the remote table instead of spreading the local object, an optimistic-cache → direct-write → queue-on-failure write path, pull-and-reconcile after every write/flush, and overlaying still-queued ops on top of a fresh pull so unflushed offline edits survive a race. §6.4 updated to require the §6.6 checklist for any offline-first data layer.

- **1.4.0 (2026-06-23)** — Added §6.5 Serverless function security checklist: authentication-first, CORS preflight, input validation at the boundary, sanitised error responses, centralised headers. Includes a worked Supabase auth example and explains the OWASP A05 risk of an open relay. §6.4 updated to require the checklist before any serverless PR.

- **1.3.0 (2026-06-12)** — Added §8.1 Accessibility testing — explicit keyboard/focus tests beyond an axe scan: tab order, visible focus, keyboard-only operation, focus management/trap on modals + route change, roles & accessible names, live regions. The Tester owns it; a green axe scan alone doesn't pass the a11y gate.

- **1.2.0 (2026-06-12)** — Added §7 Frontend engineering checklist (Core Web Vitals budgets, server-vs-client state with TanStack Query, loading/empty/error/success UI states + error boundaries, accessible forms) and §8 Testing the frontend (RTL component tests, vitest-axe + axe-core/playwright a11y gate, MSW API mocking, Playwright E2E, meaningful coverage).

- **1.1.0 (2026-06-12)** — Added §6 Backend engineering checklist (API contracts, DB migrations with expand→migrate→contract, observability via OpenTelemetry, backend definition-of-done) and a testing-pyramid table in Phase 5 (unit / integration / contract / E2E).

- **1.0.0 (2026-06-06)** — Initial release. Full 10-phase PR runbook, pair-programming discipline, refuse list, edge cases (hotfix/stacked/revert/draft), and a surface-support matrix.
