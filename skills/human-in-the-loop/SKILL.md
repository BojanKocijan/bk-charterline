---
name: human-in-the-loop
description: Load the Law 37 human-gates playbook — gate tiers from the Law 2 severity (Trivial / Standard / Significant), the committed intent.md → spec.md → plan.md artifact chain in docs/features/<id>/ with owner approval rules, the PR Intake block and Decision log, risk-tiered review with an independent fresh-context reviewer subagent for high-risk work, the review cap on AI-authored PRs awaiting review, the review queue digest, and the delegable vs judgment-heavy triage. Auto-load before any Medium-or-High change, before drafting any non-chore PR, and when the user says "review queue", "approve intent", "approve spec", "approve plan", "review cap", or "skip gates".
---

# Human in the loop — Law 37

Full reference: `Read knowledge/HUMAN_IN_THE_LOOP.md`. Load it before acting; this skill is the trigger and the summary.

## When to invoke

- The Law 2 announcement is Medium or High severity, or the change is a new feature or user flow
- Drafting any non-`chore:` PR (Intake block + Decision log)
- `review queue`, `approve intent` / `approve spec` / `approve plan`, `review cap <N>` / `review cap off`, `skip gates`

## The five rules in one screen

| Rule | What Claude does |
|---|---|
| Gate tier | States `**Gate tier:**` in the announcement. Trivial: nothing extra. Standard: approved `plan.md`. Significant: `intent.md` → `spec.md` → `plan.md`, approved in order. |
| Committed artifacts | Writes them in `docs/features/<id>/`, links existing stories or design files instead of duplicating, stops after each one, records `Approved-by` only after explicit approval. |
| PR explains itself | Intake block + Decision log under `## Summary`; size per Law 31; names every touched test. |
| Review follows risk | Standard: diff checked against the plan. Significant: independent subagent review, plus a second named reviewer on a team. AI review is never the merge decision. |
| Review capacity | Cap of 3 AI PRs awaiting the user's review; sorts work into delegable vs judgment-heavy; batches ready PRs into one `review queue` digest. |

## Never

- Code before an approved `plan.md` on Standard or Significant work
- An `Approved-by` line without the owner's explicit approval in this session
- Lowering a gate tier without the user's `skip gates`
- Treating any AI review, including Claude's own, as approval to merge
