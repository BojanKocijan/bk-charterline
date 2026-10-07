# Plan — a marketing page for Design Forge, with an analytics demo (#177)

Spec: [spec.md](spec.md) · Gate tier: Significant · Branches: `feat/site-1-metrics` … `feat/site-4-publish` · Issue: #177
Work pile: judgment-heavy (a new public page and its look), built in one session, not split across agents
Approved-by: BojanKocijan, 2026-10-07, chat (all four decisions as recommended)

## Design decisions (owner, 2026-10-07, chat)

- **Look:** a calm product page: white space, one accent, clear type, a dashboard that looks like a real tool.
- **Accent:** violet. About `#6d28d9` on light and `#a78bfa` on dark; both checked for at least 4.5:1 contrast during the build.
- **Demo:** one dashboard frame with three tabs.
- **Motion:** animated charts, per the Animation Guide (below).
- **Type:** the system font stack. No web fonts, so the page makes no requests to other sites.

## Four PRs, merged in order

The page is about 1,200 lines, so Law 31 splits it. Each PR is opened against `main` and stacked by commits, says "merge in order", and leaves `main` green.

| PR | Branch | What | Size |
|---|---|---|---|
| 0 | `docs/issue-177-spec` | This plan and the spec | ~200 |
| 1 | `feat/site-1-metrics` | `scripts/site_metrics.py`, its tests, the first `site/data.js` | ~300 |
| 2 | `feat/site-2-page` | The page without the demo: hero, what it does, the numbers, install; the accessibility check in CI | ~400 |
| 3 | `feat/site-3-demo` | The analytics demo: tabs, example data, animated SVG charts | ~400 |
| 4 | `feat/site-4-publish` | The Pages workflow, the `site metrics` instructions, release v2.37.0 | ~150 |

## Files

| File | PR | Change |
|---|---|---|
| `scripts/site_metrics.py` (new) | 1 | Collects the real numbers and writes `site/data.js`. It also updates every `<span data-metric="…">` fallback in `site/index.html`, if the file exists |
| `tests/test_site_metrics.py` (new) | 1 | The counts against a fixture repo; a fake `gh` for the PR numbers; incremental runs; the fallback spans |
| `site/data.js` (generated) | 1 | `window.DF_METRICS = {…}`, totals and rates with their dates only |
| `site/metrics-state.json` (generated) | 1 | `collected_through` and one record per merged PR (number, lines changed, merge date). The page never loads it |
| `site/index.html` (new) | 2, 3 | The five sections; real numbers in `data-metric` spans as the no-JS fallback; the tabs and panels in PR 3 |
| `site/styles.css` (new) | 2, 3 | Tokens: colors (light and dark), type scale, spacing, and **motion tokens** (durations, stagger, distances) as custom properties. No `style=` attributes anywhere |
| `site/site.js` (new) | 2 | The one motion switch, the copy button, numbers filled from `data.js` with a count-up |
| `site/demo.js`, `site/charts.js` (new) | 3 | Example data (fictional names only, Law 15); bar, line and funnel charts drawn as SVG |
| `site/package.json`, `site/package-lock.json`, `site/a11y.spec.js` (new) | 2 | Playwright and axe, pinned; one spec checking the page at 390 and 1280 px, light and dark (decision 1) |
| `.github/workflows/site.yml` (new) | 2, 4 | PR 2: the accessibility job on every PR that touches `site/`. PR 4: deploy `site/` to Pages from `main` |
| `.github/dependabot.yml` | 2 | Adds npm updates for `/site` (decision 1) |
| `docs/MAINTAINER.md` | 4 | How to refresh the numbers (decision 3) |
| `RELEASES.md` | 1–4 | One line per PR under `## Unreleased`; PR 4 turns it into `## v2.37.0` (decision 2) |
| `CLAUDE_LAWS.md` (version only), `plugin.json`, `marketplace.json` | 4 | v2.37.0 |

## The real numbers (`site_metrics.py`)

Each value carries the date it was collected.

| Number | Source |
|---|---|
| Releases | `git tag -l 'v*'`, release tags `vX.Y.Z` only |
| Laws | numbered laws in `CLAUDE_LAWS.md` (`5a` isn't counted separately) |
| Skills / agents / knowledge guides | `skills/*/SKILL.md` / `agents/*.md` / `knowledge/*.md` without `*.example.md` |
| Tests | `def test_` in `tests/test_*.py` |
| Rules' tokens per session | `laws_cost.py`'s estimate function |
| PRs merged, median lines changed, share within 400 lines | `gh pr list --state merged --search "merged:>=<cursor>" --json number,additions,deletions,mergedAt`, de-duplicated by PR number |

**Incremental** (the owner's requirement on #177): the first run collects everything. Each later run reads only PRs merged since `collected_through`, and the cursor moves only after a run that finishes. A second run with nothing new writes nothing. It never reads `projects.yaml`, the hook log or the AI inventory.

## The page

- **Without JavaScript:** every section reads; the numbers come from the `data-metric` spans; **all three demo panels show, stacked, each with its data table**. This changes the spec, which showed only the first tab; showing all three hides nothing (decision 4).
- **With JavaScript:** `site.js` hides the inactive panels and builds the ARIA tabs (arrow keys, Home, End, roving `tabindex`).
- **Charts:** inline SVG with `role="img"` and a one-sentence `aria-label`, plus a "Show data" table under each chart, in the HTML from the first render. A bar or point shows its value on hover and on keyboard focus.
- **Demo content:**
  - **Governance:** hook blocks per law; AI tools per tier; a PR-size histogram against the 400-line ceiling, chipped **Planned (#120)**.
  - **Product analytics:** a checkout funnel, weekly retention, and an insight brief with a verified, partial or contradicted verdict per theme.
  - **Usage:** skills and personas used per week, chipped **Planned** with its new issue; tokens per session by model.
  - **The fictional team:** "Acme Corp", for all three tabs.

## Motion (Animation Guide)

- **Only `transform` and `opacity`.**
  - Bars fill with `scaleX` or `scaleY` from their baseline, about 0.6 s, 0.06 s apart.
  - Lines are revealed by a mask that scales in X, not by animating the stroke.
  - The funnel fills like bars.
- **Count-up:** the numbers count on from the value already shown (the fallback), never from 0, over about 0.7 s. The final number is in the HTML from the first render.
- **Entrances:** each section and chart grows in (scale from 0.92, fade) once, when it scrolls into view (`IntersectionObserver`). Nothing replays on scrolling back. At most 8 staggered items; anything past that appears at once.
- **Tab switch:** the new panel grows in and the old one disappears at once. There is no exit animation, so two panels are never on screen together.
- **One switch point:**
  - `site.js` is the only code that reads `prefers-reduced-motion`. It sets `data-motion="off"` on `<html>`, and every animation is keyed to that attribute.
  - A settings toggle can be added later without touching the charts.
  - Under reduced motion, everything starts in its final state.
- **Tokens:** every duration, stagger and distance is a custom property in `styles.css`, which the JavaScript reads too.

## Order of work

1. **PR 0:** this plan and the spec, for `approve plan`.
2. **PR 1:** tests, then the script. Done when the tests pass and two runs in a row leave `data.js` unchanged.
3. **PR 2:** the page and its accessibility job. Done when axe reports 0 violations at 390 and 1280 px, in light and dark, and the page opens from the file with no console errors.
4. **PR 3:** the demo. Done when the PR 2 checks still pass, the tabs work by keyboard, and the motion measures below hold.
5. **Preview:** after PR 3, I publish the page as a private claude.ai link for you to review before anything is public.
6. **PR 4:** Pages and the release. Done when the workflow deploys from `main` after you turn Pages on (manual step below).

## Proof

- **Tests:** `tests/test_site_metrics.py` as listed; `site/a11y.spec.js` (axe at two widths and two themes, the tabs by keyboard, no console errors, no requests to other origins).
- **Measures** (Animation Guide §10, a throwaway Playwright run with 4× CPU throttling; numbers in the PR): no task over 50 ms while the demo animates, and layout shift 0.
- **Commands:** `python3 -m unittest discover -s tests`, `npx playwright test` in `site/`, markdownlint, `release_version.py check`, `laws_cost.py --budget 33000`.
- **Visual evidence:** I'll ask before each UI PR whether you want screenshots (Law 34).

## Manual steps for you (Law 35)

1. Merge PRs 0 to 4 in order.
2. Before PR 4's first deploy: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. Check `https://bojankocijan.github.io/design-forge/` loads; I'll send you the link as soon as the deploy is green.

## Risks

- **The first npm dependency in the repo** (decision 1). → Dev-only and pinned, used only in CI for `site/`, with Dependabot.
- **CI changes** (Law 2: High). → One job runs only when `site/` changes; the deploy runs only on `main`.
- **A marketing claim the data can't back.** → Planned items are chipped and linked to their issue, and every real number has a date.
- **The README badge says 38 laws**, while the page counts from the file. → #178 aligns the README.

## Ruled out

- **Vite + React:** a build step and a dev server for one page; the owner wants it to open from the file.
- **A chart library** (Chart.js, D3): requests to a CDN or a vendored copy, for a few bars and lines that SVG draws in a few dozen lines.
- **`fetch('data.json')`:** browsers block it on a page opened from disk.
- **Stroke-dash line drawing:** animates a paint property, which the Animation Guide rules out.
- **Showing local hook-log or inventory aggregates:** out of scope at launch (spec).

## Decisions for the owner

1. **Accessibility testing with Playwright and axe**, through a `site/package.json` with a lockfile and Dependabot. It's the repo's first npm dependency, dev-only (Law 29). Recommended: yes. The alternative is installing pinned versions in CI with no lockfile, which needs no `package.json` but gets no Dependabot updates.
2. **Releases across the stack:** PRs 1 to 3 add their lines under `## Unreleased`, and PR 4 releases them as v2.37.0. Recommended: yes. The alternative is a version per PR (v2.37.0 to v2.40.0).
3. **Where `site metrics` lives:** in `docs/MAINTAINER.md`, not as a trigger in `CLAUDE.md`. A trigger there loads in every session of every project (about 70 tokens each time) for a command that only applies to this repo. Recommended: `MAINTAINER.md`. #177 asked for a trigger.
4. **Without JavaScript, all three demo panels show stacked,** instead of only the first one as the spec says. Recommended: yes.
