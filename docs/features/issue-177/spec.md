# Spec — a marketing page for Design Forge, with an analytics demo (#177)

Intent: [#177](https://github.com/BojanKocijan/design-forge/issues/177), as the owner changed it in chat on 2026-10-07 (below)
Design: none — translated from #177 and the owner's answers in chat (Laws 19 and 30)
Approved-by: BojanKocijan, 2026-10-07, chat ("approve plan", read as the spec; both flagged items as recommended)

## What changed from #177

The owner's answers in chat on 2026-10-07:

1. **The page sells what users get:** analytics running alongside the skills, in three kinds: the **governance report**, **product analytics** and **usage of Design Forge**.
2. **The analytics appear as an interactive demo with example data,** clearly labeled. Numbers about Design Forge itself stay real.
3. **Plain HTML and CSS, with a little JavaScript.** The page opens straight from the file, with no server to start, and GitHub Pages publishes the same files.
4. **No aggregates from the local hook log or AI inventory at launch.** That drops #177's dependency on #120 for the launch.

## Behavior

One page, `site/index.html`, in five sections:

1. **Hero:** what Design Forge is, in one sentence; the one-line install command with a copy button; links to the README and the releases.
2. **What it does:** the laws, the hook that enforces them, the personas and the skills, one short block each, with real counts.
3. **Analytics demo**, three tabs, one per kind. Each tab shows an **Example data** badge, a short line on where the real numbers come from in your own project, and a status chip: **Available now** or **Planned**, linked to its issue.
   - **Governance report:** hook blocks per law and AI tools per Law 38 tier (available now: `hook log`, `ai inventory`); PR size against the 400-line ceiling, time to merge and reverts (planned: #120).
   - **Product analytics:** what `analyst mode` produces from a connected analytics tool: a funnel, retention, and a Triangulated Insight Brief with a verified / partial / contradicted verdict per theme (available now).
   - **Usage of Design Forge:** what the rules cost per session in tokens and per model, and how that grew per release (available now: `laws_cost.py`); which skills and personas a team uses (planned, new issue).
4. **Design Forge in numbers:** real counts with the date they were collected: releases, laws, skills, agents, knowledge guides, tests, PRs merged, median PR size, share of PRs within 400 lines, the rules' tokens per session.
5. **Install and footer:** the install command again, the license, the repo link.

### States

- **No JavaScript:** every text section reads normally. The demo shows its first tab as a static table with the same example data, and the numbers come from the page's HTML.
- **No `data.js`, or a broken one:** "Design Forge in numbers" shows the counts written into the HTML at build time, with their date, so the page never shows empty boxes.
- **Narrow screens (390 px):** the sections stack and the tabs scroll sideways. No horizontal page scroll.
- **Light and dark:** follows the system setting.

### Data

- `scripts/site_metrics.py` collects the real numbers from git and `gh` (public data only) and writes `site/data.js` (`window.DF_METRICS = {…}`). It's a script file, not JSON, because a browser won't read a local JSON file from a page opened from disk.
- **Incremental collection** (owner's requirement on #177): the file stores a `collected_through` time, each run pulls only what changed since then, and records are de-duplicated by PR number or commit.
- **Refresh:** a `site metrics` trigger rebuilds `data.js` and opens a PR. Nothing runs on a schedule.
- **Example data** for the demo lives in `site/demo.js`, with fictional names only (Acme Corp, Alice Chen).

## Acceptance criteria

- [ ] Double-clicking `site/index.html` opens the full page, with no server and no console errors.
- [ ] Every real number comes from `data.js` (or the HTML fallback) and shows its date.
- [ ] Every demo panel shows **Example data** and a status chip, and every **Planned** chip links to an open issue.
- [ ] The page makes no requests to other sites: no web fonts, no CDN, no tracking or analytics.
- [ ] WCAG 2.2 AA: axe reports no violations in CI; the tabs work with the keyboard (arrow keys, Home, End); charts have a text alternative; motion respects `prefers-reduced-motion`.
- [ ] Works at 390 px and at 1280 px, in light and dark.
- [ ] A GitHub Actions workflow publishes `site/` to GitHub Pages from `main`: `https://bojankocijan.github.io/design-forge/`.
- [ ] `site_metrics.py` has tests, never reads `projects.yaml`, the hook log or the AI inventory, and a second run with nothing new changes nothing.

## Policy check

- **Component library:** none. The page is plain HTML, so Laws 12 and 30 (React components, a UI library) don't apply. Styles live in `site/styles.css`, with no `style=` attributes, so the spirit of Law 12 holds.
- **Accessibility:** contrast, focus order and visible focus, the ARIA tabs pattern, text alternatives for charts, reduced motion, reflow at 320 CSS px.
- **Copy:** sentence case, active voice, and every number with its date. No claim the data can't back: planned features say **Planned**.
- **Privacy:** no tracking on the page (#177); example data is fictional (Law 15); real data is public repo data only (Law 14).
- **Conflicts flagged for the owner:**
  1. **Planned features on a marketing page.** Two of the eight demo items don't exist yet: the PR metrics (#120) and skill usage. The spec shows them labeled **Planned** with a link. The alternative is to leave them off until they ship.
  2. **CI change.** Publishing to Pages adds a workflow (Law 2: High) and needs Pages turned on in the repo settings, a manual step for you (Law 35).

## Out of scope

- Building the governance report (#120) or skill-usage tracking.
- Publishing aggregates from the local hook log or AI inventory.
- The README update (#178), which links the page once it's live.
- A custom domain, and analytics or tracking on the page itself.
