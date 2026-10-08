# Team Workflow — BK Charterline

**Version:** 1.1.0
**Last Updated:** 2026-06-12
**Binding:** Yes — this file governs the agent **team pipeline** (triggers: `team` / `build feature`). It composes the existing personas into one collaborating team rather than mutually-exclusive modes.

> Most work still uses a single persona. The **team pipeline** is for a complete feature you want carried end-to-end — planned, built, tested, documented, and reviewed — with one shared thread of context and a human merge at the end.

---

## 1. The team

| Role | Agent | Owns | Knowledge lens (shared files) |
|---|---|---|---|
| **Lead** | `lead.md` | Orchestration: scope, acceptance criteria, delegation, diff review, the PR | `FULLSTACK_WORKFLOW.md` (all 10 phases) |
| **Frontend** | `frontend.md` | UI implementation | `FRONTEND_GUIDE`, `COMPONENT_PATTERNS`, `FULLSTACK_WORKFLOW §7` |
| **Backend** | `backend.md` | API / DB / server / observability / migrations | `FULLSTACK_WORKFLOW §6` |
| **Tester** | `tester.md` | Tests + axe/coverage gate + acceptance-criteria check | `FULLSTACK_WORKFLOW §8`, `SKILLS` |
| Design / Research / Analyst / Incident | `design.md` / `research.md` / `analyst.md` / `incident.md` | Supporting — Lead calls them when the work needs them | their guides |

**Documentation is a shared team duty — there is no separate Docs role.** Each role documents its own change as part of doing it (Frontend/Backend write the README/API/PROJECT_KNOWLEDGE updates for what they built; the Tester records what was tested). The **Lead enforces** the doc standards in §6 as a gate before review — undocumented change = not done.

**Knowledge is shared, not split.** No per-role knowledge files — each agent reads the same binding knowledge through its lens (the column above). This avoids drift between roles.

**Every role obeys the laws (Law 29).** The laws override any role-specific instinct. If a role thinks the right move is something the rules don't allow or don't cover — skip a gate, merge, delete a file, deviate from the announced plan — it **stops and asks the human**, with its reasoning, instead of acting on its own. A better idea is a question, not a unilateral action.

---

## 2. The single pipeline

```
Lead: scope + acceptance criteria → pull main → branch + issue (Law 5)
  └─► Frontend / Backend build (each announces per Law 2)
        │   (builders document their own change inline — README / API / PROJECT_KNOWLEDGE)
        └─► Tester: write + run tests, axe gate, verify acceptance criteria
              ├─[fail]──► back to the Builder with the failing case
              └─[pass]──► Lead: verify docs (§6) + /code-review (+ independent reviewer on Significant), run pre-PR checks → open PR → STOP
                            └─► Human merges (Law 7). Lead does post-merge cleanup (Law 9).
```

Definition of done for a feature: **built · tested · documented · reviewed** — then the human merges. The Lead never merges (Law 7).

---

## 3. Orchestration — how the Lead delegates

The **Lead** runs the pipeline by invoking each specialist as a subagent in sequence, passing the shared context (issue, acceptance criteria, branch, prior stage's output). The Lead:

1. **Scopes** the work and writes acceptance criteria into the `PROJECT_KNOWLEDGE.md §11` feature row.
2. **Delegates the build** to Frontend and/or Backend — announcing each unit (Law 2). Multi-file edits wait for human "go". Builders **document their own change** as they go (README / API / `PROJECT_KNOWLEDGE`).
3. **Hands the result to the Tester** — who is *independent of the builder* so tests aren't rubber-stamped.
4. **Verifies documentation** against the §6 standards (the Lead's gate — no separate Docs role).
5. **Reviews** the combined diff, runs Phase 5 pre-PR checks, opens the PR, and **stops**.

The Lead is the only role that talks to the human about overall progress; specialists report up to the Lead.

---

## 4. Handoff — one shared thread

Context is never re-derived from scratch between stages. Two durable surfaces carry it:

- **`PROJECT_KNOWLEDGE.md §11` feature row** gains a **Stage** column: `planned → building → testing → in-review`. Each role updates it on entry/exit. (Documentation happens within `building`, by the builders.)
- **The PR body** is the running record — what was built, what was tested (and results), what was documented, and the review notes.

A role picking up the work reads the feature row + the PR body, not the whole chat history.

---

## 5. Gates

The pipeline has two gates the Lead must honor before marking a PR review-ready:

- **Tester gate** — all required tests pass, accessibility holds (axe clean **and** keyboard/focus behavior verified per `FULLSTACK_WORKFLOW §8.1`), and every acceptance criterion is verified. A failing gate sends work back to the Builder, not forward.
- **Documentation gate (Lead-enforced)** — the change is documented to the standard in §6 by the team. Undocumented change = not done. (No separate Docs role — the Lead verifies before review.)

Neither gate is a merge (Law 7 still holds — the human merges).

---

## 6. Doc standards — what each change type must document

| Change | Docs required (by the role that made the change; Lead-enforced) |
|---|---|
| New shared component | Row in `PROJECT_KNOWLEDGE §3` + usage note |
| New/changed API endpoint | API doc / contract update (OpenAPI or typed schema) |
| New architectural decision | `PROJECT_KNOWLEDGE §5` decision row (date + why) |
| User-facing change | `README` and/or `RELEASES.md` entry |
| New env var / setup step | `README` setup section + `.env.example` |
| Feature handed off to devs | `docs/handoffs/<id>.md` (SKILLS §10) + tracking issue |

---

## 7. When NOT to use the team

- A one-line fix, copy edit, or token swap — just use the relevant single persona.
- Pure exploration / mockups — `frontend mode`.
- Research or analytics-only work — `research` / `analyst`.

The team pipeline is for features substantial enough that the plan→build→test→document→review chain earns its overhead.

---

## Changelog

- **1.1.0 (2026-06-12)** — Removed the dedicated Docs role: documentation is a shared team duty (builders document their own change; the Lead enforces the §6 doc standards as a gate before review). Pipeline Stage column is now `planned → building → testing → in-review`.

- **1.0.0 (2026-06-12)** — Initial release. Defines the team (Lead, Frontend, Backend, Tester) plus supporting personas, the single plan→build→test→review pipeline, Lead-orchestrated subagent delegation, shared-knowledge role lenses, handoff via the `§11` feature-row Stage column + PR body, the Tester gate + Lead-enforced documentation gate, and the doc-standards matrix.
