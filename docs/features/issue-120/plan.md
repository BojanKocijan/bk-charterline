# Plan — My BK Charterline: a private dashboard for every user (#120)

Spec: [spec.md](spec.md) · Gate tier: Significant · Branches: `docs/issue-120-spec`, then `feat/my-metrics-1-hook` … `feat/my-metrics-5-checks` · Issue: #120
Work pile: judgment-heavy (a new feature that runs on every install), built in this session
Approved-by: BojanKocijan, 2026-10-08, chat

## Six PRs, merged in order

Each is opened against `main`, stacked by commits, says "merge in order", and stays under Law 31's 400 lines. Nothing reaches users until PR 5 releases v3.3.0.

| PR | Branch | What | Size |
|---|---|---|---|
| 0 | `docs/issue-120-spec` | The spec and this plan | ~250 |
| 1 | `feat/my-metrics-1-hook` | The hook log records the tool's name for every MCP prompt | ~120 |
| 2 | `feat/my-metrics-2-data` | `scripts/my_metrics_data.py`: read every local source and the pull request numbers | ~380 |
| 3 | `feat/my-metrics-3-pages` | `scripts/my_metrics.py`: build the two pages | ~390 |
| 4 | `feat/my-metrics-4-wiring` | Build on `update rules` and at session start; the `my metrics` trigger | ~150 |
| 5 | `feat/my-metrics-5-checks` | Accessibility check on a fixture dashboard; release v3.3.0 | ~150 |

## PR 1: the tool's name in the hook log

- `.claude/hooks/hook_log.py`: `append_block` takes an optional `tool`, written only when given; a tool name longer than 200 characters, or one that isn't `mcp__…`, is dropped.
- `.claude/hooks/enforce-laws.py`: the two MCP asks (`tier3-first-use`, `tier4-unapproved`) pass the tool's name. Nothing else changes: blocks and other asks log as today, and inputs are never logged.
- **Tests:** a High and a Critical prompt each log `tool`; a Bash block logs no `tool`; no line holds the tool's input (checked with a marker string in the input).

## PR 2: the data (`scripts/my_metrics_data.py`)

One function, `collect(home, *, network)`, returns a plain dict. Each source is read in its own `try`, and a failure becomes `{"error": "<what to do>"}` for that section only.

| Section | From |
|---|---|
| `blocks`, `asks`, `calls`, `days` | `hook-log.jsonl` (last 30 days); `calls` merges in `ai-approvals.jsonl` |
| `tools`, `unrated` | `ai-tools.json`, `ai-inventory.json` (unrated when not in the registry) |
| `projects` | `projects.yaml` repos; for each, merged pull requests from `gh` (with `network=True`) |
| `rules_tokens` | `scripts/laws_cost.py`'s estimate |

- **Incremental pull requests** (the owner's requirement on #120): `dashboard/state.json` keeps one record per pull request per repo and a cursor per repo; each run asks `gh` only for pull requests merged since that repo's newest one. It reuses `site_metrics.py`'s approach.
- **Per project:** merged, median lines changed, share within 400, median hours to merge, reverts (`Revert "` titles), and the share with a Claude co-author trailer.
- **Limits:** a 20-second timeout per `gh` call and 60 seconds per build in total; past that, the remaining projects show "Couldn't reach GitHub this time".
- **Tests:** fixture homes for a new user, a busy user, and broken files; a fake `gh`; incremental runs; `network=False` makes no `gh` call.

## PR 3: the pages (`scripts/my_metrics.py`)

- Builds `index.html` and `tools.html` in a temporary folder, then swaps it into `~/.bk-charterline/dashboard/` in one rename, so two sessions building at once never leave a half-written page.
- Reuses the site's CSS and `charts.js` (copied in), plus `scripts/dashboard_assets/dashboard.css` (the prototype's tiles, chips, feed and tool cards).
- `scripts/dashboard_assets/actions.json`: the plain words for each tool's actions (`send_message` → "Send an email"). Unknown actions show their name with spaces.
- The empty and error states from the spec; the **Copy command** button with `data-copied`.
- `--if-changed`: skips the build when no source's size or modification time changed since `state.json` last recorded them. `--local-only`: no `gh` calls.
- **Tests:** a fixture build has every tool exactly once under its severity, a Not rated section only when needed, the Copy command button, every empty state, and no `http` URL except links.

## PR 4: wiring

- `install.sh`: at the end, `python3 "$LOCAL_DIR/scripts/my_metrics.py"` (full build). Its failure prints one warning line and never fails the install.
- `.gitignore`: `/dashboard/`.
- `CLAUDE.md`: a session-start step that runs `my_metrics.py --local-only --if-changed`, quietly; the confirmation's `Dashboard:` line; a `my metrics` trigger row (full build, then the path).
- **Tests:** in `tests/test_update.py`, an install builds the dashboard; a broken build still ends the install with exit 0.

## PR 5: checks and release

- `site/dashboard.spec.js`: builds a fixture dashboard through `my_metrics.py`, then axe (WCAG 2.2 AA) at 390 and 1280 px in light and dark on both pages, the Copy command button, and no requests to other sites.
- `.github/workflows/site.yml`: also runs on changes to `scripts/my_metrics*.py` and `scripts/dashboard_assets/`.
- Release v3.3.0, with the rules' token count.

## Order of work

1. PR 0: this plan, for `approve plan`.
2. PRs 1 to 5, each with its tests first. After PR 3, I rebuild your dashboard from the real code, so you can compare it with the prototype before the wiring lands.

## Edge cases

- **A new user** with no log or approvals: every section shows its empty state, and the build succeeds.
- **No `gh` login, or no network:** pull request sections say how to sign in; the rest builds.
- **Session start on a slow machine:** local files only, and skipped when nothing changed.
- **Two sessions build at once:** each builds in its own temporary folder; the last rename wins, and both results are whole.
- **A huge hook log:** only the last 30 days are read, line by line.

## Proof

- **Tests:** as listed per PR, all with a temporary `HOME`; the full suite and the Site checks.
- **A real build** on your machine after PR 3, compared with the prototype.
- **Commands:** `python3 -m unittest discover -s tests`, `cd site && npx playwright test`, `release_version.py check`, `laws_cost.py --budget 33000`.

## Manual steps for you (Law 35)

1. Merge PRs 0 to 5 in order.
2. Type `update rules` and approve the hook diff (PR 1 changes the hook).
3. Open `~/.bk-charterline/dashboard/index.html`, or type `my metrics`.

## Risks

- **Every install runs new code at the end.** → Its failure is one warning line, never a failed update.
- **The rules grow about 150 tokens.** → Within the 33,000 budget; the PR states the new count.
- **`gh` slow or rate-limited.** → Timeouts, incremental collection, and nothing from GitHub at session start.

## Ruled out

- **A local server:** the page works from the file, so there's nothing to start or stop.
- **Calling GitHub at session start:** a session must never wait on the network.
- **Storing tool inputs** to say more about each call: privacy (Law 32's log rule).
- **A JavaScript framework:** the site's plain HTML and chart script already do it.

## Amendment 1: refresh after every merge and every pull of main

Approved-by: BojanKocijan, 2026-10-08, chat

The owner asked for the dashboard to be rebuilt **after every PR they merge and every pull of the default branch**, the moments its pull request numbers change. It's a rules change.

- **Law 9** (cleanup after a merge): a fifth step after pulling the default branch: rebuild the dashboard in the background (`python3 ~/.bk-charterline/scripts/my_metrics.py`, a full build with the projects' pull requests). It never blocks or fails the cleanup.
- **Law 5** (pull before new work) and **Law 25** (session start): the same background rebuild right after each pull of the default branch.
- **Limit:** a merge you make in GitHub is seen when Claude next pulls (the cleanup after you say it's merged, or the next new work), not the second it happens; nothing polls GitHub.
- **Cost:** about 15 seconds of background work per pull; the session never waits for it.
- **Ships with v3.3.0**, with a test that the rules name the rebuild in Laws 5, 9 and 25.

## Deviations after approval

- **Two accessibility fixes found by the new dashboard check (PR 5):** the severity dots in the latest-calls list had an `aria-label` on a plain `<span>` (now hidden text), and the scrolling tables weren't reachable by keyboard (now focusable regions with a name).
- **The README images came early:** the owner asked for them at the top of the README before the release (#225, captioned "new in v3.3.0"); PR 5 retakes them from the final code, still with example data.
- **A renamed repo:** GitHub's search ignores a repo's old name, so a project registered under it showed 0 pull requests; the owner's `projects.yaml` now has the new name.
- **PR 5 became two PRs:** the checks and fixes (PR 5) and the release with Amendment 1 (PR 6), so neither touches more than 10 files (Law 31).
