# Plan: one team, using Claude's own skills inside BK Charterline (#231)

Gate tier: Significant (law changes). The issue states the intent; this plan carries the spec.

Approved-by: BojanKocijan, 2026-10-08, chat (spec and plan)

**The idea (owner, 2026-10-08):** BK Charterline doesn't compete with Claude's own skills. It's the one place that runs the whole team, and each job goes to the right skill, whether it's ours, built into Claude Code, or in Anthropic's design and engineering plugins.

## Part 1: the review step in Law 37

### What we read

- **Built-in `/code-review`** ([docs](https://code.claude.com/docs/en/code-review)): reviews the branch's commits ahead of upstream plus uncommitted changes, or a target (a PR number, a branch, `main...my-feature`). It **runs as a background subagent with its own context window**, follows CLAUDE.md (so it sees the laws), and reports correctness bugs; at higher effort also reuse, simplification and efficiency. In the desktop app its findings arrive as a findings list. Flags: `--fix` applies findings, `--comment` posts them on the PR. `/code-review ultra` runs a fleet of reviewers in the cloud: 5–10 minutes, about $5–25 in usage credits, and only the user can start it.
- **`engineering:code-review`** (Anthropic's engineering plugin): a checklist review across security (OWASP, injection, auth, secrets), performance (N+1, unbounded queries, leaks), correctness and maintainability, with a table of findings and a **verdict** (Approve / Request changes).

### What changes

The Law 37 §4 sentence becomes (≈ 70 more words):

> **4. Review depth follows risk.** Trivial: CI green and a glance. Standard: the Lead, or the human, reviews the diff against `plan.md`, and Claude runs `/code-review` on the branch. Significant: the same, plus an independent review in a context that did not write the code: `/code-review` runs as its own subagent, and `engineering:code-review` adds a security and performance pass when that plugin is installed. The Lead runs them after the Tester gate. For the riskiest changes (auth, data, migrations, the hook), Claude offers `/code-review ultra`; only the owner starts it, since it's billed. Add a second named reviewer when there is a team. Findings go in the PR ranked by severity; a reviewer's "Approve" is dropped. Claude doesn't run `--fix` or `--comment` without the owner's yes. AI review is input, never a verdict. A change written, reviewed, and approved only by models is unreviewed (Law 7 stands).

Also:

- **HUMAN_IN_THE_LOOP §5:** the table's Standard and Significant rows name the reviewers; "Why a separate reviewer" says `/code-review` is that separate context. The PR's Decision log lists each finding as fixed, skipped (with why) or not applicable.
- **`agents/lead.md` step 5:** "Run `/code-review` (and `engineering:code-review` when installed) on the branch; fix or answer each finding; then open the PR."
- **`skills/human-in-the-loop` description:** names the reviewers so the skill is found by "review".

### Owner decisions (2026-10-08)

1. **Standard changes get `/code-review` too.**
2. **Claude offers `/code-review ultra`** for auth, data, migrations and changes to the hook, in the PR summary. It never starts it.

### Open question to check while building

In a terminal session the docs call the review a *forked* subagent. If a fork starts from the session's context, it isn't fully fresh. I'll test it in a session; if it inherits the authoring conversation, the law says "pass the PR number so it reviews the diff, not the conversation", and the plan gets a deviation note.

## Part 2: ux-writing gets what ux-copy has and we lack

We already cover tooltips, loading, confirmations, empty states and errors with templates (ux-copy has one line each for tooltips, loading and onboarding). Missing on our side, written in our own words:

- **Onboarding template:** one concept per step, the user's goal first, a skip, and where to find it later.
- **Errors:** what happened, **why**, and how to fix it (we have the first and last).
- **Tone by moment:** success, error, warning, neutral, one line each.
- **Review output:** 2–3 alternatives with their tone and when to use each.
- **Translator notes:** idioms, text that grows 30–40% in other languages, no strings built from fragments.

## Part 3: the skill map

A new section in `knowledge/TEAM_WORKFLOW.md`, **"Which skill for which job"**: the 7 stages (plan, research, design, build, test, review, ship and run), who leads each, and the skills used, tagged BK Charterline, Claude Code or Anthropic plugin. The page section (#230) shows the same map.

- **Each agent file** (`lead`, `design`, `research`, `frontend`, `backend`, `tester`, `incident`) gets one line pointing to its row.
- **Where two skills could answer the same request,** our skill's description says when to use the other, so the right one fires: `design-critique` hands an accessibility-only audit to `design:accessibility-review`; `ux-research-guide` hands study planning to `design:user-research`; `frontend-guide` hands visual direction to `frontend-design`. Every hand-off says "when installed", and our skill does the job when it isn't.
- **`argument-hint`** in the header of our skills that take an argument (a Figma link, a PR, a transcript folder).
- **`install.sh`** prints one line suggesting Anthropic's design and engineering plugins and how to add them. It never installs them.

## Part 4: ideas worth taking, in our own words

- **Law 35:** each step of the deploy checklist says how to undo it (rollback), and when to.
- **`design-critique`:** a first step, "first impression (2 seconds)", and a closing "What works" section, so feedback names strengths too.
- **`UX_RESEARCH_GUIDE.md`:** planning a study (an interview guide, a usability test script, a survey) goes to `design:user-research` when installed, with a short checklist of our own when it isn't.

## PRs

A series, each PR under 400 lines and 10 files, each base `main`:

1. `feat(laws)`: Law 37's review step, HUMAN_IN_THE_LOOP §5, the Lead, the skill description, RELEASES.
2. `feat(team)`: the skill map, the agents' pointers, the hand-offs in skill descriptions, `argument-hint`, the install suggestion, RELEASES.
3. `feat(skills)`: ux-writing additions, RELEASES.
4. `feat(laws)`: rollback in Law 35, RELEASES.
5. `feat(skills)`: design-critique and research planning, RELEASES.

They touch different files, except RELEASES (one line each, merged in order). The laws' token count is checked against the 33,000 budget in PRs 1 and 4. #230's page section waits for PR 2, so the page matches the rules.

## Edge cases

- **The engineering plugin isn't installed:** Law 37 says "when installed"; `/code-review` alone is enough.
- **`/code-review` finds nothing:** the PR says so; that's evidence too.
- **A finding is wrong:** the Decision log says why it was skipped; the human decides.
- **Cost:** `/code-review` uses the session's usage; ultra is never started by Claude.

## Deviations after approval

- **PR 1, the independent reviewer:** the docs call `/code-review` a *forked* subagent in a terminal, and a fork may start from the session's conversation. Rather than rely on it, Law 37 keeps the fresh subagent (only the plan, the spec and the diff) for Significant work, and that subagent uses `engineering:code-review`. `/code-review` runs on Standard and Significant work as the first pass. Nothing to test by hand any more.
