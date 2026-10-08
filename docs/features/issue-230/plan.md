# Plan: the whole team in one place, on the page (#230)

Gate tier: Standard (a new section on the page; no rules change)

Approved-by: BojanKocijan, 2026-10-08, chat

## Goal

Show that BK Charterline isn't one more set of skills competing with Claude's own. It's the one place that runs the whole team: the laws, the hand-offs, and the right skill for each job, whether it's ours or one Anthropic ships.

Owner decisions (2026-10-08): a new section right after "What it does"; Anthropic's plugins named; a layout that works on phones. Revised the same day: **no comparison, no verdicts**. One team, all in one place.

## The section

- Eyebrow "One team", heading **"Every skill your team needs, in one place"**, then one line: *BK Charterline brings Claude Code's own skills and Anthropic's design and engineering plugins into one team, with one set of rules and a hand-off at every step.*
- **A pipeline of 7 stages,** left to right on desktop and top to bottom on phones. Each stage names who leads it and the skills it uses. A small tag says where a skill comes from: **BK Charterline**, **Claude Code** or **Anthropic plugin**, in text, not only color.

| Stage | Who | Skills |
|---|---|---|
| Plan | Lead | `intent → spec → plan` (BK Charterline) · plan mode (Claude Code) · `architecture` (Anthropic plugin) |
| Research | Research | `user-research` to plan a study (Anthropic plugin) · `ux-research-guide`, `ux-research-deck` (BK Charterline) |
| Design | Design | `design-critique`, `figma-craft`, `ux-writing` (BK Charterline) · `accessibility-review`, `design-system` (Anthropic plugin) |
| Build | Frontend, Backend | `frontend-guide`, `scaffold-react-project` (BK Charterline) · `frontend-design` (Anthropic plugin) · worktrees (Claude Code) |
| Test | Tester | axe and Playwright gate (BK Charterline) · `testing-strategy` (Anthropic plugin) |
| Review | A fresh agent, then you | `/code-review` (Claude Code) · `code-review` (Anthropic plugin) · the hook (BK Charterline) |
| Ship and run | Lead, Incident | `developer-handoff`, the deploy checklist and merge order (BK Charterline) · `deploy-checklist`, `incident-response` (Anthropic plugin) |

- Under it, one line: **"You merge."** That's the only step no agent takes.
- A small note: *Uses Anthropic's design and engineering plugins when they're installed; every stage works without them.* With a date, as the other tiles have.

The table above must match the team's own skill map (#231 or its follow-up). The page shows what the rules really do, never more.

## Build

- `site/index.html`: the section as an ordered list of stages (`<ol>`), each with a heading, the role and a list of skills with their source tag. No table: it's a sequence, and a list reads in order with a screen reader.
- `site/layout.css` (or a small `site/team.css`): a horizontal row with connecting lines on desktop, one column under 720 px. Source tags use the palette tokens in light and dark.
- The nav gets a "Team" link if the header has room at 390 px; otherwise not.
- No `data.js` change.

## Tests

- `site/a11y.spec.js` already runs axe on the page at phone and desktop width in light and dark. Add one check: 7 stages, each with at least one skill, and "You merge" last.
- By hand: no sideways scroll at 390 px; the stages read in order with a screen reader.

## PR and wording

One PR, about 150 lines in 3–4 files, base `main`. Screenshots in light and dark at desktop and phone width. The wording never compares or ranks; it says which skill does which job.

## Edge cases

- **The Anthropic plugins aren't installed:** the note says every stage still works; the page doesn't promise them.
- **A skill changes name upstream:** the note carries the date; a docs PR fixes the name.
- **Long skill lists on phones:** they wrap inside their stage; nothing scrolls sideways.
- **No JavaScript:** plain HTML, fully shown.
