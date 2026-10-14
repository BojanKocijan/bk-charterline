# Plan — Every plan gets an HTML page that walks through how it will work (#285)

Spec: [#285](https://github.com/BojanKocijan/bk-charterline/issues/285) (the issue answers every intent and spec field) · Gate tier: Standard (changes a knowledge file) · Branch: `feat/plan-html-page` · Issue: #285
Work pile: judgment-heavy (rule wording), built in this session
Approved-by: BojanKocijan, 2026-10-14, chat

## The rule (new §2.6 in `knowledge/HUMAN_IN_THE_LOOP.md`)

> ### 2.6 The plan page
>
> Each time Claude writes or changes a `plan.md`, it also publishes a **plan page**: a private HTML Artifact that walks the owner through how the plan will work, before they approve it.
>
> - **What's on it, in this order:**
>   1. a one-paragraph summary;
>   2. the user flow, or for work with no UI, how it works, as a diagram;
>   3. each step of **Order of work** in plain language, with what changes for whom;
>   4. how it's proven (**Proof**);
>   5. **Risks** and **Ruled out**.
> - **Only what's in `plan.md`.** The page explains the plan and never adds to it. Anything the page needs that the plan doesn't say goes into `plan.md` first.
> - **`plan.md` is the record.** Approval is still `approve plan` on `plan.md` (§2.5). The page is how the owner reads it.
> - **Linked both ways.** `plan.md` carries a `Plan page:` line with the Artifact link, and Claude's approval message gives the same link.
> - **Kept current.** When the plan changes (drift, re-approval), Claude republishes the page to the same link.
> - **Private by default.** The owner decides whether to share it. It holds no secrets and no real personal data (Laws 14 and 15).
> - **Where there's no Artifact tool** (for example, a global-memory install without it), Claude skips the page and writes one line in its approval message: `Plan page: not available on this surface`.

## Files to change

| File | Change |
|---|---|
| `knowledge/HUMAN_IN_THE_LOOP.md` | New §2.6 (the text above). `Plan page:` line added to the §2.4 template header. §2.5 first bullet: "commits it, publishes the plan page (§2.6), and stops". §8 table: a "Plan page" column. Version 1.1.0 → 1.2.0, and a changelog line. |
| `RELEASES.md` | An `Unreleased` entry for #285 |
| `docs/features/issue-285/plan.md` | This file |

`CLAUDE_LAWS.md` and `CLAUDE.md` don't change, so the session-load cost stays the same. `CLAUDE.md` already has Claude read HUMAN_IN_THE_LOOP for every Medium or High change, which is when plans are written.

## Order of work

1. Add §2.6 and the three small edits — done when the file reads cleanly from §2.4 to §2.6.
2. Bump the version, add the changelog line and the RELEASES entry — done when `python3 -m pytest tests/test_laws_structure.py` passes.
3. Run `/code-review main...HEAD`, fix what it finds, then open the PR — done when CI is green.

## Proof

- **Tests to add:** none. This is a rule in a knowledge file. No existing test is edited.
- **Commands that must pass:** `python3 -m pytest tests/` (laws structure, skill headers, trigger skills) and `python3 scripts/laws_cost.py`, which must show no change in rules tokens.
- **Visual evidence:** none. No UI change (Law 34).
- **Live proof:** the #270 plan is the first plan published with a plan page, and its link goes in this PR.

## Risks

- **The page drifts from `plan.md`** → it says only what's in the plan and is republished whenever the plan changes, and approval stays on `plan.md`.
- **It slows down small plans** → it applies only where a `plan.md` already exists (Standard and Significant), and Trivial work never gets one.
- **It gets shared too widely** → the page starts private, and the Artifact tool shares it only when the owner chooses.

## Ruled out

- **A committed `plan.html`:** it adds to the PR size, and GitHub shows it as source code, not as a page (owner decision).
- **Pages for intent and spec too:** the plan is where the "how it works" view helps the most (owner decision).
- **Putting the rule in Law 37:** that would add about 70 tokens to every session, against #267 (owner decision).
