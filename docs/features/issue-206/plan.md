# Plan — always give the merge order when PRs are open (#206)

Spec: [#206](https://github.com/BojanKocijan/bk-charterline/issues/206) (the issue) · Gate tier: Standard · Branch: `feat/law-merge-order` · Issue: #206
Work pile: delegable (a law text change; checked by lint and the token budget)
Approved-by: <pending>

## The change

**Law 7**, after the PR summary format, a new paragraph:

> **Merge order.** Whenever one or more PRs are open for the owner, Claude's message ends with a numbered **Merge order**: each PR as a link, in the order to merge it, why that order (stacked, depends on another, would conflict), and what to do after (tell Claude, `update rules`, a manual step). One open PR still gets a one-item list. With nothing open, it says so in one line.

**Law 7's summary format** gains one line before "Merge it yourself…":

```
**Merge order:** <numbered list per the paragraph above>
```

**Law 37 §5:** "Ready PRs are reported together, not one message each" becomes "Ready PRs are reported together, with the merge order (Law 7), not one message each."

**Law 35:** one sentence after its example: "The PR steps in this checklist follow Law 7's merge order."

## Files to change

| File | Change |
|---|---|
| `CLAUDE_LAWS.md` | The four edits above; version 3.1.0 |
| `RELEASES.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | v3.1.0, with the rules' token count |
| `docs/features/issue-206/plan.md` | This plan |

About 5 files and 40 lines.

## Proof

- markdownlint clean; `release_version.py check` → `3.1.0`; `laws_cost.py --budget 33000` within budget (about +100 tokens); all tests OK.
- Visual evidence: none, no UI. `Screenshots: not applicable`.

## Ruled out

- **Only a memory note:** it already applies in this repo, but the laws reach every project and every user.
- **A hook check:** the hook sees tool calls, not Claude's replies.
