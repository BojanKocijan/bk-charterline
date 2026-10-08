# Plan: BK Charterline first, and Claude offers Anthropic's plugins (#247)

Gate tier: Standard (a knowledge-file rule and a page change; no law changes)

Approved-by: BojanKocijan, 2026-10-08, chat

## Goal

Make three things obvious, on the page and in how Claude behaves:

1. **BK Charterline is the core of the team:** its skills, rules and hand-offs lead every stage.
2. **Anthropic's plugins join when installed, and Claude asks first:** when a job needs one that isn't installed, Claude offers it with the exact commands; it never installs anything itself.
3. **They complement each other:** each pair does a different part of the same job, under our standards.

## Part 1: the rule (TEAM_WORKFLOW §8)

A new bullet under "When two skills fit":

> **Missing plugin: Claude asks.** When a job's "theirs goes first" skill isn't installed (it's missing from Claude's skill list), Claude says so once per session per plugin, gives the `/plugin` commands for the user to run (README › Installation), and does the job meanwhile with our own skill. Claude never installs a plugin itself and never asks again in that session after a "no".

- Why "the user runs it": `/plugin install` is the user's command and changes their setup; Law 38 treats new tools as the user's decision.
- Why once per session per plugin: it helps the first time and never nags.
- `agents/lead.md` gets nothing new; it already points to §8.

## Part 2: the page (#team section)

- **Heading stays**; the lede becomes: *BK Charterline is the core of the team: its rules, hand-offs and 18 skills lead every stage. Claude Code's own skills and Anthropic's plugins join in, and when a job needs a plugin you don't have, Claude asks before you install it.*
- **In each stage,** BK Charterline's skills come first under the brand name with the accent style (as now). Anthropic's group is labeled **"Anthropic plugin · joins when installed"**.
- **New row under the stages, "How they work together"**: three short cards.
  - **BK Charterline:** the rules, the gates and the hand-offs, and our standards that every skill's output meets (WCAG 2.2 AA, the design you're given, your chosen library, your merge).
  - **Claude Code:** built-in tools the rules call on: `/code-review`, plan mode, worktrees.
  - **Anthropic plugins:** specialist skills for one job each. When a job needs one you don't have, Claude asks, gives you the command, and carries on without it meanwhile.
- **Then four real pairs**, each one line in a small list:
  - Design critique (ours) + an accessibility-only audit (`design:accessibility-review`), held to our WCAG 2.2 AA.
  - Deploy steps with undo (Law 35, ours) + pre-deploy checks (`engineering:deploy-checklist`).
  - Research synthesis and the deck (ours) + planning the study (`design:user-research`).
  - The review gates (Law 37, ours) + `/code-review` (Claude Code) and `engineering:code-review` on Significant work.

## Tests

- `site/a11y.spec.js`: axe in light and dark at 390 and 1280 px covers the new row. The §8 check also covers every skill named in the pairs. A new check counts the three "work together" cards.
- No sideways scroll from 390 px up (existing check).

## PR

One PR, base `main`, under 10 files: TEAM_WORKFLOW, index.html, team.css, a11y.spec.js, RELEASES, this plan, plus 2 screenshots (desktop light, phone dark). `/code-review` before opening (Law 37, Standard).

## Edge cases

- **A user has the plugins through their claude.ai organization:** they're in the skill list, so Claude doesn't ask.
- **The user says no:** Claude doesn't ask again that session and keeps using our skill.
- **claude.ai web, where `/plugin` doesn't exist:** Claude names the plugin and says it can be added in Claude Code.
- **Page claims:** the page says "Claude asks" only once the rule is in §8, which this same PR adds.
