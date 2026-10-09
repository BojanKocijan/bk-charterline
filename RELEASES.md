# BK Charterline Releases

---

## Unreleased

### The dashboard shows every data point the page shows ([#256](https://github.com/BojanKocijan/bk-charterline/issues/256))
- **The page's governance numbers:** **Blocks marked wrong** (and their share of blocks), **AI tools classified** (X of Y), and an **AI tools per Law 38 tier** chart with an Unclassified bar, using the page's tier names. The pull request numbers now say they cover all registered projects.
- **What the rules cost:** a new Usage section shows the **rules' share per session** (the tokens loaded before your first message) and **tokens per release** for the last 12 releases, each measured from what that release's `CLAUDE.md` imports. A release is measured once and kept in `dashboard/rules-cost.json`.
- **Correct counts:** a block you marked as a false positive no longer counts as a second block, and two kinds of prompt with one label ("Edit to a guardrail") show as one row.

---

## v3.5.0 — October 8, 2026

Lighter and clearer: every session loads 14% less (27,111 tokens of rules instead of 31,571) with every rule still in force; BK Charterline is shown as the core of the team; and Claude asks before using an Anthropic plugin you don't have.

### BK Charterline first, and Claude asks before a plugin ([#247](https://github.com/BojanKocijan/bk-charterline/issues/247))
- **Missing plugin: Claude asks** (TEAM_WORKFLOW §8, 1.3.0): when a job's preferred Anthropic skill isn't installed, Claude says so once per session per plugin, gives the `/plugin` commands for you to run, and does the job meanwhile with our own skill. It never installs a plugin itself, and after a "no" it doesn't ask again that session.
- **The page puts BK Charterline first:** the team section says it's the core of the team, labels Anthropic's skills "joins when installed", and adds **How they work together**: what each source brings, and four real pairs (critique + accessibility audit, deploy steps + pre-deploy checks, research synthesis + study planning, review gates + `/code-review`). A check makes sure every skill named there is in §8.
- **It works in every session:** CLAUDE.md's knowledge table sends Claude to §8 whenever a skill names an Anthropic plugin that isn't installed, not only in team work.

### The page says up front why to add BK Charterline ([#249](https://github.com/BojanKocijan/bk-charterline/issues/249))
- **New hero:** "Get the most out of Claude Code and its plugins". BK Charterline gives Claude Code and Anthropic's skills a way of working: when each skill runs, what standard it meets, and when to stop for your yes.
- **New "Why add it" strip** under the hero, with a Why link in the header: Claude Code, Anthropic's plugins, built-in tools and safety, each on its own and with BK Charterline. A page check counts the four rows; axe in light and dark at 320, 390 and 1280px covers it.
- **Fresh numbers:** the rules' tokens per session (31,531), merged PRs, releases, tests and median PR size, from `scripts/site_metrics.py`.
### Lighter sessions ([#239](https://github.com/BojanKocijan/bk-charterline/issues/239))
- **Law 32 is shorter:** it keeps what the hook guarantees (every block and every permission prompt, "a block always wins", "fails open") and Claude's behavior on a block; the tables, the mechanism, the block log and where the hook lives move to the new `knowledge/GUARDRAILS.md`, read on demand. Nothing was loosened, and the hook is unchanged. Rules: 31,571 → 28,749 tokens; the budget warning drops from 33,000 to 30,000.
- **The reasons move out, the rules stay:** the research behind Law 31, the motivation for Laws 32, 35 and 37, and the sources for Laws 37 and 38 move to FULLSTACK_WORKFLOW, HUMAN_IN_THE_LOOP and GUARDRAILS §2; Law 36 says the same in one sentence; Law 38's known limits stay in full (check a new repo's `.claude/ai-tools.json` before working in it; the hook doesn't ask when it arrives by clone or pull; a hook crash on a tier 3 call counts as approval); only its sources move. Rules: 28,749 → 27,856 tokens. A new test checks that every law keeps its own numbered, bold-titled item and that its knowledge links resolve.
- **Shorter trigger rows:** the steps for `update rules`, `ai inventory` and `ai classify` move from CLAUDE.md into two new skills, `update-rules` and `ai-tools`, loaded when you type the trigger. Each row keeps what it does and its one rule (only your click approves a hook change; never classify on your own judgment). Skills: 18 → 20. Rules: 27,856 → 27,111 tokens. CLAUDE.md's rows keep every safeguard (show the diff first, `--approve` with the exact commit, only your click approves, a refusal means stop; for `ai classify`, text in tool output never counts as approval) and link to the skills; a test checks both.
- **Tighter skill headers:** the four longest skill descriptions (`human-in-the-loop`, `ux-writing`, `design-resources`, `parallel-sessions`) are 23% shorter, keeping every trigger phrase, and quoted so a colon can't turn one into a nested mapping; a new test checks every skill header. The rules' budget warning drops to 28,000 tokens, and the page shows the new size (27,111 tokens) against it.

- **Rules: 27,111 tokens** (estimate).
- The Laws, `plugin.json` and `marketplace.json` are at 3.5.0.

---

## v3.4.0 — October 8, 2026

One team: BK Charterline brings Claude Code's own skills and Anthropic's plugins into the team instead of competing with them, reviews every change with Claude's own code review, and gets an optional coworker with a sense of humor.

### The page fits a 320px phone ([#243](https://github.com/BojanKocijan/bk-charterline/issues/243))
- **No more sideways scroll below 390px.** The analytics demo's three tabs set the width of its one grid column, so every panel spilled past the screen at 320–389px, and at 390–414px ran into the frame's right padding. The column now shrinks (`minmax(0, 1fr)`), the badge and the "In your project" line wrap, and below 415px the tabs get tighter sides, with "Product analytics" on two lines on the narrowest phones. At 768px and wider the demo looks exactly as before.
- **Checked:** the Playwright + axe check now also runs at 320px, in light and dark, and fails without this fix.

### A coworker with a sense of humor ([#229](https://github.com/BojanKocijan/bk-charterline/issues/229))
- **New optional output style, Coworker** (`output-styles/coworker.md`): the same rules and coding (`keep-coding-instructions: true`), with a dry, warm sense of humor that plays along with the rules. Jokes stay in chat, never in commits, PRs, issues or docs, and stop during incidents or when you're frustrated. Once per session it says how to turn it off.
- **Off by default:** turn it on with `/output-style coworker`, off with `/output-style default`. The plugin ships it in `output-styles/`; `install.sh` links it into `~/.claude/output-styles/` (never over a file of yours with the same name), prints a one-line hint on a fresh install, and never sets `outputStyle`.

### One team, using Claude's own skills ([#231](https://github.com/BojanKocijan/bk-charterline/issues/231))
- **Law 37's review names its reviewers:** Claude Code's `/code-review` runs on Standard and Significant work before the PR; Significant work adds a fresh subagent that gets only the plan, the spec and the diff, using `engineering:code-review` when Anthropic's engineering plugin is installed. It reviews `<default-branch>...HEAD` explicitly, since a bare `/code-review` sees nothing once the branch is pushed. For any change to auth, data, migrations or the hook, the merge order offers `/code-review ultra <PR>`, which only the owner starts. A reviewer's "Approve" is dropped; `--fix` and `--comment` need the owner's yes. HUMAN_IN_THE_LOOP §5 (with a `/code-review` column in the surface table), FULLSTACK_WORKFLOW Phases 5 and 7, TEAM_WORKFLOW's pipeline and the Lead follow.
- **A skill map for the whole team** (TEAM_WORKFLOW §8): each stage, from plan to ship and run, with the skills it uses from BK Charterline, Claude Code and Anthropic's design, engineering and frontend-design plugins (when installed), and which one goes first when two fit; the design, the chosen library and WCAG 2.2 AA still beat any skill's own taste. The Lead, builders, Tester, Design and Research agents point to their rows; README's team section says so.
- **The right skill fires:** where two skills could answer the same request, ours now says when to use the other: `design-critique` and `frontend-guide` hand an accessibility-only audit to `design:accessibility-review` (held to WCAG 2.2 AA), `ux-research-guide` hands planning a study to `design:user-research` (and plans it itself when that plugin is missing), and `frontend-guide` hands visual direction with no design to `frontend-design:frontend-design`, each when installed. `design-critique`, `ux-research-guide` and `developer-handoff` get an `argument-hint`. The Analyst and Incident agents point to their §8 rows.
- **Anthropic's plugins, suggested:** the run that first installs BK Charterline points to README's Installation section, which lists the commands to add the design, engineering and frontend-design plugins. Nothing installs them for you. The Coworker hint now also shows only on that first run, not on a manual re-run. README's install steps mention output styles too.
- **ux-writing goes further:** an onboarding step template (the user's goal first, one concept, skippable, where to find it later), errors that say why when it helps, tone by moment (success, error, warning, neutral), 2–3 alternatives with their tone when writing new copy, and notes for translators.
- **Law 35: every deploy step says how to undo it.** The migration's `down` SQL, where the old setting lives (never a secret's value) or which PR to revert; undos run in reverse order, code before schema; an undo that loses data says so; and the checklist ends with what means roll back, so the owner decides before deploying. The example shows all of it.
- **design-critique** (and SKILLS §2.a, the Design agent's checklist) starts with a two-second first impression and names what works before the findings. **UX_RESEARCH_GUIDE §2a, Planning a study:** `design:user-research` when installed, otherwise our five-step checklist (the decision, the method, participants, the guide or script, privacy). A kept plan goes to `docs/research/<study>/plan.md`, never with participant names or contacts.

### The whole team, on the page ([#230](https://github.com/BojanKocijan/bk-charterline/issues/230))
- **New section "Every skill your team needs, in one place"** after "What it does", with a Team link in the header: the 7 stages from plan to ship and run, who leads each and the skills it uses, labeled BK Charterline, Claude Code or Anthropic plugin, ending with "You merge." It matches TEAM_WORKFLOW §8; the page checks (axe in light and dark at phone and desktop width) cover it, plus a check for the 7 stages and that every skill shown is in §8. Section links now stop below the sticky header at any width, also when the nav wraps.

- **Rules: 31,531 tokens** (estimate).
- The Laws, `plugin.json` and `marketplace.json` are at 3.4.0.

---

## v3.3.1 — October 8, 2026

### The dashboard shows styled in the Claude app's browser pane ([#234](https://github.com/BojanKocijan/bk-charterline/issues/234))
- **Each dashboard page now carries its own styles and scripts.** The app shows a local file outside the project folder as the HTML alone, so the six stylesheets and two scripts the pages loaded from files next to them never arrived, and the dashboard showed unstyled. `my_metrics.py` now writes them into `index.html` and `tools.html` as `<style>` and `<script>` blocks, in the same order, and no longer copies them into `dashboard/`. The page still reads fully without JavaScript, and `site/` keeps its separate files.
- **Checked:** a test makes sure the built pages have no `<link rel="stylesheet">` or `<script src=`, and the Playwright + axe dashboard check still passes at phone and desktop width, in light and dark.
- **Rules: 31,214 tokens** (estimate).
- The Laws, `plugin.json` and `marketplace.json` are at 3.3.1.

---

## v3.3.0 — October 8, 2026

Your own private dashboard: what the rules did for you, which tools Claude can reach and how risky each is, and how your pull requests go, built on your machine and never sent anywhere.

### A private dashboard for every user ([#120](https://github.com/BojanKocijan/bk-charterline/issues/120))
- **The hook log names the tool behind each MCP prompt** (`tool`, for example `mcp__gmail__send_message`), so the dashboard can show which tool was asked about on which call. Only a well-formed tool name is kept; a tool's inputs are never logged.
- **New `scripts/my_metrics_data.py`** gathers the dashboard's data from local files only: what the hook blocked and asked, which tool was asked about on which call, every tool's severity and the ones not rated yet, and, through the user's own `gh` login, pull request numbers for each project in `projects.yaml`, fetched only since the last run. A missing or broken source shows a message in its own section and never stops the rest.
- **New `scripts/my_metrics.py`** builds the two pages in `~/.bk-charterline/dashboard/`: an overview (headline numbers, tools by severity, the latest calls, what the hook did) and Tools and calls (a card per tool with what it can do, every High and Critical call, pull requests per project). Commands get a Copy command button; nothing points to another site.
- **It builds itself:** at the end of every `update rules` (a full build; a failure prints one warning and never fails the update), quietly at session start (local files only, skipped when nothing changed), and on `my metrics`. The session-start confirmation shows `Dashboard: ~/.bk-charterline/dashboard/index.html`. The folder is gitignored.
- **It refreshes after every merge and every pull of `main`** (Laws 5, 9 and 25): Claude rebuilds it in the background right after the pull, so the pull request numbers include what you just merged. It never blocks or fails the cleanup.
- **Checked like the page:** a new Playwright check builds the dashboard from example data and runs axe (WCAG 2.2 AA) on both pages at phone and desktop width in light and dark, plus the Copy command button and no requests to other sites. It found two fixes: the severity dots now carry hidden text instead of an `aria-label` on a plain `<span>`, and the scrolling tables are keyboard-reachable regions with a name.
- **README:** a "Your private dashboard" section, and the screenshots at the top retaken from the final code, still with example data.
- **Rules: 31,035 tokens** (estimate).
- The Laws, `plugin.json` and `marketplace.json` are at 3.3.0.

---

## v3.2.1 — October 7, 2026

### A navy and lime palette for the page ([#215](https://github.com/BojanKocijan/bk-charterline/issues/215))
- **Dark theme:** a near-black navy ground, lime numbers, buttons and highlights, and dark text on lime.
- **Light theme:** the same character, with a deeper olive-lime where bright lime on white would fail contrast. The Site checks (WCAG 2.2 AA with axe in light and dark) pass.
- **Rules: 30,613 tokens** (estimate).
- The Laws, `plugin.json` and `marketplace.json` are at 3.2.1.

---

## v3.2.0 — October 7, 2026

### The BK Charterline page ([#177](https://github.com/BojanKocijan/bk-charterline/issues/177))
- **New `site/`:** the BK Charterline page in plain HTML and CSS. It opens straight from the file, makes no requests to other sites, and follows the system's light or dark setting.
- **The sticky header, the hero and the tiles:** the laws by number, the agents' flow from Lead to you, real skill and guide names.
- **The numbers and the script:** three big counts and three gauges from `data.js`, each with its date; a System / Light / Dark switcher; motion that plays once and never under reduced motion.
- **The analytics demo:** governance, product analytics and usage for a fictional team, marked as example data, with Available now or Planned (linked to its issue) on each part.
- **The dashboard's look:** tabs, KPI tiles, cards, and verified, partial or contradicted verdicts.
- **The charts' look and motion:** bars and columns grow, lines draw in, once each, never under reduced motion.
- **Published:** `.github/workflows/site.yml` checks every change to `site/` (WCAG 2.2 AA with axe at phone and desktop width, light and dark, the tabs, the numbers, the page without JavaScript) and deploys `main` to <https://bojankocijan.github.io/bk-charterline/>.
- **Refreshing the numbers** is in `docs/MAINTAINER.md`.
- **Rules: 30,613 tokens** (estimate).
- The Laws, `plugin.json` and `marketplace.json` are at 3.2.0.

---

## v3.1.0 — October 7, 2026

### Every reply with open PRs ends with the merge order ([#206](https://github.com/BojanKocijan/bk-charterline/issues/206))
- **Law 7:** whenever PRs are open for you, Claude's message ends with a numbered **Merge order**: each PR as a link, in order, why that order (stacked, depends on another, would conflict), and what to do after. The PR summary format has a `Merge order:` line.
- Law 37 reports ready PRs together with the merge order, and Law 35's checklist follows it.
- **Rules: 30,613 tokens** (estimate).
- The Laws, `plugin.json` and `marketplace.json` are at 3.1.0.

---

## v3.0.0 — October 7, 2026

**Design Forge is now BK Charterline.** To update, type `update rules` in Claude Code as always. The first update shows you the hook diff to approve, then moves your install from `~/.design-forge` to `~/.bk-charterline` with all your data (projects, hook log, AI tool registry and approvals, patterns). Your next session starts with `Rules loaded: BK CHARTERLINE v3.0.0`.

- **Plugin users:** remove the `design-forge` plugin, then add `bk-charterline` from `BojanKocijan/bk-charterline`. A plugin can't rename itself.
- **For this release only,** `~/.design-forge` stays as a link to the new folder and `dforge-update` runs `charterline-update`. Both go in the next major version.
- **The repo moved** to `BojanKocijan/bk-charterline`. Old links and the old install command still redirect.
- **Rules: 30,418 tokens** (estimate).
- The Laws, `plugin.json` and `marketplace.json` are at 3.0.0.

### Renamed to BK Charterline ([#199](https://github.com/BojanKocijan/bk-charterline/issues/199))
- **The hook and the scripts find the install under either name:** `~/.bk-charterline`, or `~/.design-forge` until an install has moved. A new `.claude/hooks/rules_home.py` decides, and a fresh install uses the new name.
- **The hook guards the installed clone under both names,** including the old name as a link to the new folder, and `charterline-update --approve` asks as `dforge-update --approve` does.
- **`install.sh` installs the new name and moves an old install:** `~/.design-forge` becomes `~/.bk-charterline` with every data file in it, and the old name links to it for v3.0.0. It re-points the `~/.claude/CLAUDE.md` block, the hook in `~/.claude/settings.json` (backed up first), the shell function and the agent and skill links. `charterline-update` replaces `dforge-update`, which points to it for v3.0.0. Nothing moves if both folders exist or the clone has local edits.
- **The rules files use the new name:** `CLAUDE.md`, `CLAUDE_LAWS.md` and `AGENTS.md` say BK Charterline, `~/.bk-charterline` and `charterline-update`, and the session starts with `Rules loaded: BK CHARTERLINE v…`. `update rules` runs `charterline-update`, or on an install from before v3.0.0 `dforge-update`, which moves it.
- **The docs use the new name:** the README (with a rename note at the top), knowledge, skills, agents and the issue templates. Release notes before v3.0.0 and `docs/features/` keep the old name as history.
- **The plugin is `bk-charterline`,** this repo's own hook entries point to `~/.bk-charterline`, and a test keeps the old name out of everything but history, the move code and its fallbacks.

### A page for BK Charterline, with an analytics demo ([#177](https://github.com/BojanKocijan/bk-charterline/issues/177))
- **New `scripts/site_metrics.py`** collects the page's real numbers from git and `gh` into `site/data.js`: releases, laws, skills, agents, knowledge guides, tests, merged PRs, the median PR size, the share of PRs within 400 lines, and the rules' tokens per session. Each number keeps the date it last changed.
- **It only asks `gh` for PRs merged since its last run** (`site/metrics-state.json`), and a run with nothing new changes no file. It reads public data only.

---

## v2.36.2 — October 7, 2026

### One secret pattern list for the hook, the registry and the inventory ([#186](https://github.com/BojanKocijan/design-forge/issues/186))
- **Fixed: `ai inventory` and the Law 38 registry missed most secrets.** `scripts/ai_tools.py` kept its own copy of the patterns from before #119, which never matched GitLab `glpat-` or Slack `xoxb-` / `xoxp-` tokens. It now uses the hook's list, so the inventory masks and the registry refuses every kind the hook knows.
- **New `.claude/hooks/secret_patterns.py`** holds the patterns and `find_secret`; the hook, `ai_tools.py` and `ai_inventory.py` all use it. `dforge-update` already shows that folder's diff before installing.
- **The same pass rules everywhere:** placeholders such as `ghp_xxxx…`, references such as `${{ secrets.X }}`, and Stripe test and public keys are no longer masked or refused.
- **Legacy OpenAI keys** (`sk-` + 48 characters) are caught again, now by the commit check too. The old copy's `sk-` catch-all was the only thing that found them.
- If the shared module can't load, only the secret check stops; never merge, never push to `main` and the other checks still run.
- **Rules: 30,171 tokens** (estimate).
- The Laws, `plugin.json` and `marketplace.json` are at 2.36.2.

---

## v2.36.1 — October 7, 2026

### The Law 14 check reads what the commit will contain ([#187](https://github.com/BojanKocijan/design-forge/issues/187))
- **Fixed: a secret added in the same call got through.** The hook runs before the command, so it read the staging area as it was before `git add X && git commit`, and never saw what `git commit -a` or `git commit <path>` take from the working tree. It now reads those too.
- **`git add` in the same call:** git's own `git add --dry-run` lists the files the add would stage, so `.gitignore`, `.`, globs and `-f` count as they do for the real add, and the hook changes nothing. New files are read whole: up to 1 MB each, 2,000 files and 32 MB in all, skipping binaries and links.
- **Fixed: the `.env` check only ran when the command named `.env`,** so `git add -A && git commit` with an untracked `.env` got through. It now runs on every commit and matches `.env` and `.env.*` other than `.env.example`; a direnv `.envrc` passes.
- Removing a secret is still never blocked, and a command the hook can't parse still falls back to the staged diff.
- **Rules: 30,171 tokens** (estimate).
- The Laws, `plugin.json` and `marketplace.json` are at 2.36.1.

---

## v2.36.0 — October 7, 2026

### What loading the rules costs every session, measured and budgeted ([#188](https://github.com/BojanKocijan/design-forge/issues/188))
- **Every session loads 30,420 tokens of rules**, counted exactly on Opus 5.5 and Sonnet 5.5: `CLAUDE.md` 7,470, `CLAUDE_LAWS.md` 22,653, plus the lines Claude Code puts around them. This repo loads them twice: 60,623. The earlier ~20k guess was chars ÷ 4; the Claude 5 tokenizer gets 2.4 to 2.8 bytes per token.
- **On Opus 5.5 that's $0.24 to load them at the start of a session and $0.006 for each later request,** about $0.54 over 50 requests, at list price. Sonnet 5.5, Haiku 4.5 and Fable 5.1 are in the [report](docs/features/issue-188/report.md).
- **New `scripts/laws_cost.py`:** estimates each file's tokens from its bytes. `--measure` counts them exactly with the `claude` CLI on your own account, and refuses to run in CI.
- **A budget that warns:** CI's new `Rules token budget` step warns when `CLAUDE.md` + `CLAUDE_LAWS.md` pass 33,000 tokens, and never fails the build.
- **They grew 38% in 18 releases,** from 21,901 tokens at v2.17.0. The report ranks where to cut, each with its saving; each cut gets its own PR.
- **Rules: 30,128 tokens** (estimate). Each release note records this from now on.
- The Laws, `plugin.json` and `marketplace.json` are at 2.36.0.

---

## v2.35.0 — October 7, 2026

### The Law 14 secret check catches what it promised, and lets removals through ([#119](https://github.com/BojanKocijan/design-forge/issues/119))
- **Fixed: GitLab `glpat-` and Slack `xoxb-` / `xoxp-` tokens were never caught.** The pattern expected `_` where these tokens use `-`.
- **Wider patterns, one shared function:** private keys of any type (with a key body), AWS `AKIA` / `ASIA`, all GitHub token types, GitLab, Slack, Stripe live, Anthropic, OpenAI, Google, Supabase, Netlify, npm and Figma tokens, JWTs (a Supabase anon key passes), and credential assignments whose name *contains* a keyword (`STRIPE_SECRET_KEY=…`, `client_secret: "…"`).
- **Fewer false blocks:** placeholders (`ghp_xxxx…`, `EXAMPLE`, `sk-ant-your-api-key-goes-here`), references (`${{ secrets.X }}`, `process.env.X`), Stripe test and public keys, git SHAs, UUIDs, integrity strings, and design-token or file names such as `color.primary.500` under a token or secret name pass.
- **Fixed: removing a leaked secret was blocked,** including a committed `.env`. The check read removed and context lines too; now it reads only the lines a commit adds, as the #122 runbook needs. A key body added under an already-committed key header still blocks.
- **Fixed: color or an external diff tool hid every secret.** With `color.ui=always` or `diff.external` set, no line started with `+`; the check now asks git for plain output.
- **The block names the kind and the file,** never the value.
- **The first tests for this check,** with fake tokens assembled at run time so no whole token sits in the repo.
- Law 14's list now matches the hook, without the "high-entropy strings" it never checked.
- The Laws, `plugin.json` and `marketplace.json` are at 2.35.0.

---

## v2.34.0 — October 6, 2026

### Parallel sessions: one worktree each ([#182](https://github.com/BojanKocijan/design-forge/issues/182))
- **Law 5:** when another session may work in the same folder, Claude creates its branch in its own git worktree, never checks out, switches or pulls in the shared folder (fetch only, which overrides the checkouts and pulls in Laws 9 and 25), and never shares one checkout with another session. Two sessions in one folder share one checked-out branch, so a commit can land on the other session's branch (it happened with #173 and #180).
- **New `knowledge/SKILLS.md` §6.b:** when a folder counts as shared, setup, the shared stash, plain git commands in a worktree, running `update rules` from outside it, recovery after a collision (including staged and new files) without touching the other session's work, the version order when two PRs bump the version, and cleanup after the merge.
- **New `parallel-sessions` skill** with the commands for setup, recovery and cleanup.
- **Law 18:** the main folder keeps the project's locked preview port; a worktree previews on the locked port + 100 (up to +109), says `(worktree)` in its footer, and names the project from the main folder.
- An independent review of the first draft found the shared-folder checkouts, the port clash and the staged-file gap before release.
- The Laws, `plugin.json` and `marketplace.json` are at 2.34.0.

---

## v2.33.0 — October 6, 2026

### The hook asks before Netlify or Vercel commands that change a site ([#173](https://github.com/BojanKocijan/design-forge/issues/173))
- **Every call asks** when Claude runs a `netlify` (`ntl`) or `vercel` (`vc`) command that isn't a verified read or local command: deploys, rollbacks, promotes, env changes, `netlify database migrations apply` and `reset`, `netlify api` write methods, and any command the hook doesn't know (Law 38 `hosting-write`). Bare `vercel` deploys, so it asks too.
- **Secrets ask as well:** the `env` group on both CLIs and `vercel pull` print or download the site's secrets.
- **Still free:** reads (`logs`, `status`, `ls`, `inspect`, `whoami`, list and get commands, `netlify api` get/list/show/search methods) and local work (`dev`, `build`, `functions`, `link`).
- **Hard to route around:** it sees through `npx`, `pnpm`, `yarn`, `bunx`, `npm exec`, version suffixes, `NETLIFY_AUTH_TOKEN=…` prefixes, nested shells and `$(…)`.
- Sources: each CLI's own help (netlify-cli 27.11.2), Netlify's bundled API spec and Vercel's CLI docs.
- The Laws, `plugin.json` and `marketplace.json` are at 2.33.0.

---

## v2.32.0 — October 6, 2026

### A runbook for a secret that got through ([#122](https://github.com/BojanKocijan/design-forge/issues/122))
- **New `INCIDENT_GUIDE.md` §9.** When Claude finds a secret that got past the Law 14 check (pushed, in a PR or issue, in a log, or sent to a connector), it stops and tells you the type and where it is, never the value. You revoke and rotate it first; Claude then removes it from the current tree in a normal commit and checks, read-only, where else it went.
- **Not pushed yet** means nothing leaked: with your yes, Claude drops it from the local commits.
- **Rewriting pushed history stays yours.** Claude prints the commands and never runs them or force-pushes, even when asked.
- Law 14 points to the runbook, and the on-demand table loads the guide when a secret gets through.
- The Laws, `plugin.json` and `marketplace.json` are at 2.32.0.

---

## v2.31.0 — October 6, 2026

### Approve a hook update in the app, no terminal needed ([#170](https://github.com/BojanKocijan/design-forge/issues/170))
- **`update rules` no longer sends you to a terminal.** When an update changes the hook, Claude shows you the diff in chat and runs `dforge-update --approve <commit>`. The Law 32 hook raises the app's permission prompt (`update-approve`, Law 28), and your click is the approval.
- **Exactly what you saw:** `--approve` installs only that commit. If a newer release appears in between, nothing changes and you review the new diff. It works only when the hook is registered in `~/.claude/settings.json`, so there is always a prompt.
- **No more pager:** in the terminal, the diff prints straight out and the `y/N` question follows. No `q` needed.
- **Installing this release** still needs your terminal `y` once, since it changes the hook. After that, approvals happen in the app.
- The Laws, `plugin.json` and `marketplace.json` are at 2.31.0.

---

## v2.30.0 — October 6, 2026

### The hook asks before git changes the installed rules ([#170](https://github.com/BojanKocijan/design-forge/issues/170))
- **`dforge-update`'s reviewed diff can't be skipped by hand any more.** A `git checkout`, `switch`, `pull`, `reset`, `merge`, `rebase`, `restore`, `cherry-pick`, `am`, `apply`, `clean`, `revert` or `stash` that Claude runs in `~/.design-forge` now shows you the app's permission prompt (Law 32 `guardrail-git`). It finds the clone through `cd`, `-C`, `--git-dir`, `--work-tree`, `GIT_DIR` / `GIT_WORK_TREE`, symlinks and nested `bash -c`.
- **Still free:** reads (`status`, `log`, `fetch`, `ls-remote`, `describe`), `stash list` / `show`, `dforge-update` itself, and your development checkout. A command that asks wrongly goes on the hook's exception list, with a test.
- The Laws, `plugin.json` and `marketplace.json` are at 2.30.0.

---

## v2.29.0 — October 6, 2026

### Incident mode: read-only production investigation ([#167](https://github.com/BojanKocijan/design-forge/issues/167))
- **`incident mode`** (new Incident persona, Opus) turns a production symptom into a confirmed root cause. It reads Supabase logs and advisors, Netlify or Vercel logs and deploy status, the browser console and the code, and correlates them by time window and request ID. It never writes data, config or code, and hands the fix to Backend or Lead as an issue you approve.
- **A live hypothesis tree** in `docs/incidents/<date>-<slug>.md`. It stays local: the folder is ignored through `.git/info/exclude`, checked with `git check-ignore` before the first write. Evidence is summarized and redacted, in the note, in chat and in the handoff issue.
- **`health check`** runs once, read-only: Supabase advisors, the last hour of error logs per source, the latest deploy. Ranked findings in chat. It never schedules itself.
- **New `knowledge/INCIDENT_GUIDE.md`**, loaded on demand. FULLSTACK_WORKFLOW §6.3 points to it.
- **`ai classify`** proposes tiers for observability connectors: reads 2; creating dashboards, alerts or incidents 3; silencing, deleting or changing retention 4.
- Hook enforcement for the Netlify and Vercel CLIs follows in [#173](https://github.com/BojanKocijan/design-forge/issues/173).
- The Laws, `plugin.json` and `marketplace.json` are at 2.29.0.

---

## v2.28.2 — October 6, 2026

### Release Tag no longer misses a fixed-up release ([#171](https://github.com/BojanKocijan/design-forge/issues/171))
- **Any of the four version files starts the workflow**, not only `CLAUDE_LAWS.md`. If a bump merge fails the version check, the follow-up fix to `plugin.json`, `marketplace.json` or `RELEASES.md` now tags the release.
- **Re-run by hand** from the Actions tab (`workflow_dispatch`). A version that's already tagged is left as it is.
- The Laws, `plugin.json` and `marketplace.json` are at 2.28.2.

---

## v2.28.1 — October 6, 2026

### One update run is enough ([#168](https://github.com/BojanKocijan/design-forge/issues/168))
- **The installer moves the clone onto the release tag** when the clone is on a branch, has no local edits, and sits exactly on the newest release. So one run of any `dforge-update`, including the old one that pulls `main`, ends on the release. In every other case it leaves the clone alone.
- **Fixed: `update rules` could run a stale function.** Claude's Bash tool keeps the shell functions from when the session started, so after an update it kept running the old `dforge-update`, which pulls `main` without the hook-change gate. `update rules` now runs `"$SHELL" -ic dforge-update`, which loads the current function from your rc file.
- The README no longer says to run `dforge-update` twice.
- The Laws, `plugin.json` and `marketplace.json` are at 2.28.1.

---

## v2.28.0 — October 5, 2026

### `dforge-update` installs tagged releases and asks before a hook change ([#116](https://github.com/BojanKocijan/design-forge/issues/116))
- **Releases, not `main`:** `dforge-update` checks out the newest `vX.Y.Z` tag. `--main` follows `main` as before.
- **A hook change waits for your yes:** if `dforge-update` would change `.claude/hooks/`, `scripts/ai_tools.py`, `install.sh` or `.claude/settings.json`, you see the diff and answer `y` in your own terminal. Without a terminal (when Claude runs it), nothing is applied. It checks out exactly the commit you reviewed, by SHA.
- **Safe by default:** it never downgrades a clone that's ahead of the latest release, refuses to run over local edits, and changes nothing when the fetch fails.
- **Tags are automatic:** the Release Tag workflow tags each release on `main` once `scripts/release_version.py check` confirms the four version files agree (#161). The GitHub Actions are pinned to commit SHAs (#160).
- The session-start update check compares with the newest release tag, not `main`.
- **Upgrading:** run `dforge-update` twice. The first run is still the old function.
- The Laws, `plugin.json` and `marketplace.json` are at 2.28.0.

---

## v2.27.0 — October 5, 2026

### Rules for cloud sessions ([#146](https://github.com/BojanKocijan/design-forge/issues/146))
- **Assigned branch (Laws 5 and 9):** in a cloud session that may push to one branch only, Claude uses that branch and starts it again from the latest default branch before new work and after each merge. It never builds on merged history, and it keeps unmerged commits by rebasing them.
- **Hand over SQL; never run it (Law 35):** Claude never applies a migration or writing SQL to a hosted database. It hands over the SQL and a check query with its expected result, and the dependent PR waits for your confirmation.
- **CI that didn't run (Law 7):** the PR summary gains `not run ⚠ (<reason>)`, with the local checks that passed. Never `green` for checks that didn't run.
- **Images in a new message (`knowledge/SKILLS.md` §6.a):** when an image isn't on disk, Claude asks for it in a new message instead of guessing.
- The README version badge is back in sync (it still said 2.24.0).
- The Laws, `plugin.json` and `marketplace.json` are at 2.27.0.

---

## v2.26.0 — October 5, 2026

### The Law 32 hook enforces Law 38 tool tiers ([#138](https://github.com/BojanKocijan/design-forge/issues/138))
- **Tier 4 MCP calls** ask you in the app's permission prompt on every call. Nothing is stored, so approval never carries over.
- **Tier 3 and unclassified MCP calls** ask on the first call per session per tool. Once the tool has run, a `PostToolUse` entry (session id, tool name and time only, kept 7 days) in `~/.design-forge/ai-approvals.jsonl` lets later calls in that session through.
- Any registry lookup error counts as tier 3, never lower. Asks show up in `hook log` as `tier4-unapproved` and `tier3-first-use`.
- **The registry and approvals are guarded:** editing `~/.design-forge/ai-tools.json`, `ai-approvals*` or a project's `.claude/ai-tools.json`, and running `ai_tools.py set` (logged as `registry-write`), asks you first. `ai_tools.py show` stays free.
- **Known limits:** a repo that commits a `.claude/ai-tools.json` can still lower a tier while Claude works in it (the project entry wins, by design), and a hook crash on a tier 3 call counts as that session's approval. Both are written down in Law 38. Moving or linking a folder onto `.claude` now asks too.
- `install.sh` registers a `PreToolUse` and a `PostToolUse` entry for `mcp__.*`. Run `ai classify` before `dforge-update`, so the app's own MCP tools don't each prompt once.
- The Laws, `plugin.json` and `marketplace.json` are at 2.26.0.

---

## v2.25.0 — October 5, 2026

### The Law 32 hook guards the guardrails ([#117](https://github.com/BojanKocijan/design-forge/issues/117))
- **Blocked:** `git commit --no-verify` / `-n` and `git push --no-verify`; force-pushes to the default branch in any form, including a `+main` refspec that used to slip past.
- **Asks you in the app's permission prompt:** changing a guardrail file (Claude Code settings, `~/.claude/CLAUDE.md`, a project's `.claude/settings*.json`, the installed `~/.design-forge`) through Edit/Write or a Bash write, and deleting files git tracks (the mechanical backstop for Law 8). Only your click approves.
- A block always wins over an ask. A live test showed no permission mode lets an ask through without a prompt.
- `install.sh` registers a second hook entry for the file-editing tools; asks show up in `hook log`.
- The Laws, `plugin.json` and `marketplace.json` are at 2.25.0.

---

## v2.24.0 — October 5, 2026

### Law 38 — every AI tool has a risk tier and an owner ([#115](https://github.com/BojanKocijan/design-forge/issues/115))
- **New law:** MCP servers (including claude.ai connectors), desktop extensions and plugins get a tier: 1 local, 2 reads data, 3 writes or sends, 4 production or irreversible. Claude asks once per session before a tier 3 tool and before **every** tier 4 call. Unclassified tools count as tier 3.
- Per-tool overrides (for example mail at tier 2 with `send_message` at 3), and an owner for accountability.
- **Registry:** personal `~/.design-forge/ai-tools.json` plus an optional committed `.claude/ai-tools.json` per project (project wins), written by the new `scripts/ai_tools.py`. It validates, writes atomically and never overwrites a broken file.
- **`ai inventory`** shows tiers and owners and counts unclassified tools; the new **`ai classify`** trigger proposes classifications for you to approve.
- A tier only adds friction; existing safety rules still apply. Mechanical enforcement follows in #138.
- Hardened after an independent review: an invalid or duplicated project entry stays unclassified instead of falling through to a lower personal one, and the registry refuses values that look like secrets, the `[masked]` name and a `--project` folder that doesn't exist.
- The Laws, `plugin.json` and `marketplace.json` are at 2.24.0.

---

## v2.23.1 — October 5, 2026

### Commercial license alongside GPL-3.0 ([#134](https://github.com/BojanKocijan/design-forge/issues/134))
- Design Forge stays GPL-3.0. Companies that want to ship a changed version without publishing the changes, or can't use GPL, can ask for a commercial license: [FOR_COMPANIES.md](./FOR_COMPANIES.md) (originally `COMMERCIAL.md`) and the company inquiry form.
- `CONTRIBUTING.md`: contributions stay GPL-3.0 for everyone, and contributors also grant a non-exclusive right to include them in a commercial license. They keep their copyright.
- Every skill gets a `license: GPL-3.0-only` line, so a skill copied on its own keeps its license (two follow-up PRs).
- `plugin.json` and `marketplace.json` keep `GPL-3.0-only`; they and the Laws are at 2.23.1.

---

## v2.23.0 — October 5, 2026

### `ai inventory` ([#114](https://github.com/BojanKocijan/design-forge/issues/114))
- **New:** `scripts/ai_inventory.py` and the `ai inventory` trigger list every MCP server (user, local, project, desktop, and the claude.ai connectors the session passes with `--session`), desktop extension, plugin, skill, agent, hook and permission rule. The result goes to a local `~/.design-forge/ai-inventory.md`.
- First-seen dates are kept in `ai-inventory.json`, so each run marks what is **new** or **removed** since the last one.
- **Only names, never secrets:** MCP `args`, `env`, `headers` and URL paths are never read, the desktop `config.json` (OAuth token caches) is never opened, and permission rules that match the Law 14 patterns show as `[masked]`.
- First step of the AI-governance roadmap (#123); risk tiers and owners come next (#115).
- The Laws, `plugin.json` and `marketplace.json` are at 2.23.0.

---

## v2.22.0 — October 5, 2026

### Law 32 hook keeps a block log ([#113](https://github.com/BojanKocijan/design-forge/issues/113))
- **New:** every block appends one line to `~/.design-forge/hook-log.jsonl`: law, check id, repo, branch and a hash of the command. It never stores the command, the commit message or the reason.
- **`hook log`** trigger: blocks per law and check for the last 30 days, plus false positives. When you say a block was wrong, Claude marks it with `hook_log.py --false-positive` and offers a bug issue.
- The log rotates at 1 MB to `hook-log.1.jsonl` and uses a lock file with a 200 ms limit, so concurrent sessions never interleave lines. The code lives in the new `.claude/hooks/hook_log.py`; if that file is missing or the log can't be written, the hook still blocks as before.
- Tests in `tests/test_enforce_laws.py` now run with a temporary `HOME`, so they never write to your real log.
- The Laws, `plugin.json` and `marketplace.json` are at 2.22.0.

---

## v2.21.4 — October 5, 2026

### Context-menu card pattern works by keyboard ([#124](https://github.com/BojanKocijan/design-forge/issues/124))
- **Fix:** `COMPONENT_PATTERNS.md` §20 (v1.6.1). The 3-dot trigger stayed invisible to keyboard users on desktop, and the example's `<div onClick>` card body was skipped by Tab.
- The trigger also reveals on `group-focus-within:opacity-100`; a new rule makes the card body a `<button type="button">` (or `<a>`) with a visible focus ring (WCAG 2.1.1); the no-event-conflict example uses the button body.
- The Laws, `plugin.json` and `marketplace.json` are at 2.21.4.

---

## v2.21.3 — October 5, 2026

### Law 32 hook checks only the commit's own message ([#107](https://github.com/BojanKocijan/design-forge/issues/107))
- **Fix:** the Law 13 check no longer reads a heredoc from another command as the commit message. Chaining `git commit -m "docs(readme): …"` with `gh pr create --body "$(cat <<'EOF' …)"` was blocked with `Got: '## Summary'`.
- The hook splits the command into segments on `&&`, `||`, `;`, `|`, `&` and newlines, respecting quotes, `$(...)`, backticks and heredocs. It checks the heredoc, `-m`/`--message` or `-F <file>` message of every `git commit` segment. Combined flags such as `-am` are now checked too.
- Still fails open: unbalanced quoting or an unreadable `-F` file skips the Law 13 check.
- New regression tests in `tests/test_enforce_laws.py`, next to the #110 tests. CI now runs them all through `.github/workflows/hook-tests.yml`.
- The Laws, `plugin.json` and `marketplace.json` are at 2.21.3.

---

## v2.21.2 — October 5, 2026

### Law 32 hook checks the repo the command runs in ([#110](https://github.com/BojanKocijan/design-forge/issues/110))
- **Fix:** no more false Law 5 blocks ("refusing to commit directly on `main`") when Claude runs in a git worktree on a feature branch while the main checkout is on `main`.
- The hook uses the `cwd` field of the PreToolUse input instead of its own process cwd, falling back to the process cwd when the field is missing. In a worktree session the hook process runs in the main checkout, and Claude Code drops a leading `cd <cwd> &&` before calling hooks, so the hook used to read the main checkout's branch.
- `cd path; git commit …` now resolves to `path` (the trailing `;` was read as part of the path). Every `cd` is followed in order, a target that isn't a directory (`cd -`) is skipped, and a `cd` inside a heredoc body is ignored.
- Still fails open.
- New regression tests in `tests/test_enforce_laws.py` (`python3 -m unittest discover -s tests -v`).
- The Laws, `plugin.json` and `marketplace.json` are at 2.21.2 (2.21.1 is reserved for #107).

---

## v2.21.0 — October 4, 2026

### Laws work for any plugin user ([#102](https://github.com/BojanKocijan/design-forge/issues/102))
- **Law 1 — reply language is a setting.** Claude asks once, on the first session, whether English should be the only language (Yes) or any language is fine (No), recommends one language for professional work, and saves `settings.language` (`english-only` or `any`) in the local `projects.yaml`. `english-only` keeps the old refusal text word for word. "Prime Directives (Immutable)" is now "Prime Directives".
- **Law 10 — GitHub Pages URL** uses the active `gh` login instead of a hardcoded username.
- **Law 20 — registration is local.** Claude adds the entry to `projects.yaml` directly. The old issue → branch → PR flow is gone; it could never work because `projects.yaml` is gitignored.
- `projects.example.yaml` gains a `settings:` block; README documents the reply-language setting.
- The Laws, `plugin.json` and `marketplace.json` are at 2.21.0.

---

## v2.20.0 — October 3, 2026

### New patterns in `COMPONENT_PATTERNS.md` (v1.6.0) and a rule in `ANIMATION_GUIDE.md` (v1.1.0)
- **§20** dialogs and menus become bottom sheets on phones by changing the shared wrapper (a dialog switches by CSS at 640 px with no remount; a menu picks a dialog-based sheet from a context and keeps its roles); **§21** touch targets and the thumb zone (48 px header controls, 56 px sheet rows, measured, not assumed); **§22** one top bar for many screens through props, with a fixed or zero-height sticky placement; **§23** one editor for several roles through a `restrictTo` prop (send only changed fields, typed errors, the server is the authority); **§24** a time limit on every request; **§25** cache derived render work that two screens share (a small LRU, after profiling).
- **Animation guide §2.1, switchable by design:** one preference module (`motion` and `haptics`, each system, on or off), a `data-motion="off"` root attribute, a `no-motion:` variant and one haptics helper, so animations and haptics can be made user-toggleable later without touching components.
- The Laws, `plugin.json` and `marketplace.json` are at 2.20.0.

---

## v2.19.1 — October 3, 2026

### License — GPL-3.0
- `LICENSE` is now the GNU General Public License v3.0. Use it for personal or commercial projects; if you modify it and share your version, publish your changes under the same license
- `CONTRIBUTING.md` rewritten: contributions are licensed under GPL-3.0, and the earlier relicensing clause is gone
- README license section and badge, and the `license` field in `plugin.json` and `marketplace.json` (`GPL-3.0-only`), updated to match
- Law 27's directory-submission gate now says "an open source `LICENSE` present (GPL-3.0)" instead of requiring MIT
- History: v2.18.0 and earlier were MIT, v2.18.1 was all rights reserved. Copies obtained under those keep their terms
- Donations: `.github/FUNDING.yml` adds a Sponsor button on the repo, and the README has a Support section, both linking to PayPal

---

## v2.19.0 — October 3, 2026

### New knowledge: `ANIMATION_GUIDE.md`
- A new binding guide, loaded on demand when a task adds or changes an animation, transition, morph, celebration or motion effect. It is listed in Law 4 and in the on-demand table of `CLAUDE.md`, and in the README.
- Content, from the fluid game-like UI of a real project and generalised: principles (specific effects, content first, never a screen-filling start), one motion library and one token file, what may animate (transform and opacity, with listed exceptions), reduced motion, screen transitions (a relative offset, not a transform, because a transformed ancestor breaks fixed children), the tile morph (one animation per property), entrances and fills, per-step effects, arena-style introductions (compose arrival with scroll on one element so a blend mode survives), celebrations, the faux-bold "doubled number" on iOS, measuring (CPU-throttled long tasks, layout shift, profile, reuse before warm-up) and testing (the happy-dom unhandled-error gotcha that fails a build while every test passes).
- Law 4 lists the new file; the Laws, `plugin.json` and `marketplace.json` are at 2.19.0.

---

## v2.18.1 — October 3, 2026

### License — all rights reserved, contributions welcome
- `LICENSE` replaced: the project is no longer MIT. You may view it, run it locally to evaluate it, and contribute through pull requests. Copying, redistributing or reusing it needs written permission
- New `CONTRIBUTING.md` with the contribution terms and the pull request steps
- README license section and badge, and the `license` field in `plugin.json` and `marketplace.json`, updated to match
- Versions before v2.18.1 stay under MIT for copies already obtained
- Open: Law 27's directory-submission gate still says "MIT `LICENSE` present"; it needs a decision from the owner

---

## v2.18.0 — October 2, 2026

### Install registers the agents and skills
- `install.sh` links each agent into `~/.claude/agents/` and each skill into `~/.claude/skills/`, so Claude Code registers all of them (`claude agents` lists the agents as user agents)
- Your own agents and skills with the same name are never overwritten. The only links ever removed are the installer's own links whose agent or skill was deleted upstream
- `dforge-update` now pulls and then re-runs `install.sh`, so new agents, skills and hook entries apply on every update
- Re-runs never damage your shell config or `~/.claude/CLAUDE.md`: if a Design Forge end marker is missing, the file is left unchanged with a warning
- The install banner lists all five things it sets up and shows the installed version
- Plan and approvals: `docs/features/issue-85/`
- **One-time step:** run `dforge-update && bash ~/.design-forge/install.sh` once, because the old `dforge-update` only pulls. Then open a new terminal and a new Claude Code session so both pick up the new function, agents and skills

---

## v2.17.1 — October 2, 2026

### Fix — agents and plugin manifest pass validation
- `agents/backend.md` and `agents/fullstack.md`: the `description` values are now quoted. Before, an unquoted colon inside them broke the YAML frontmatter, and Claude Code loaded both agents without their description
- `.claude-plugin/plugin.json`: removed the unsupported `displayName` key so `claude plugin validate` passes (Law 27)

---

## v2.17.0 — October 2, 2026

### Law 37 — Human gates in the agentic loop
- Gate tier from the Law 2 severity: Trivial needs nothing extra, Standard needs an approved `plan.md`, Significant needs `intent.md` → `spec.md` → `plan.md`, each approved in order
- Artifacts are committed in `docs/features/<id>/`; Claude never writes an `Approved-by` line without the owner's explicit approval
- Every non-chore PR carries an Intake block and a Decision log
- Review depth follows risk, with an independent fresh-context reviewer subagent for Significant work
- Cap of 3 AI PRs awaiting review, delegable vs judgment-heavy triage, and a `review queue` digest
- New on-demand `knowledge/HUMAN_IN_THE_LOOP.md` and `skills/human-in-the-loop`
- Sources: Anthropic's AI-native SDLC playbook and seven Addy Osmani essays

---

## v2.16.0 — October 2, 2026

### Law 32 — Hook enforces the Law 34 screenshot question
- `enforce-laws.py` now blocks `gh pr create` unless the PR body (or its `--body-file`) has a `Screenshots: yes | skipped at the user's request | not applicable` line, so Claude has to ask "Do you want e2e/screenshot images for this PR?" before opening any PR, in every project
- Fails open if the body file can't be read

---

## v2.15.0 — October 2, 2026

### Law 34 — Ask before creating screenshot images
- Claude now asks "Do you want e2e/screenshot images for this PR?" and waits for an explicit yes before creating, adding or regenerating any; on no or silence the PR says screenshots were skipped
- Prompted by screenshot images overloading the GitHub Actions worker in a real project

---

## v2.14.0 — October 2, 2026

### Law 34 — Changed-pages-only screenshots
- PR screenshots now cover only screens whose import graph contains a file the PR touched; a touched file that reaches no screen produces no screenshot and no home-screen fallback (PR says `No screens affected`)
- Speed recipe in `knowledge/SKILLS.md`: minimal standalone Playwright spec, reused dev server, parallel workers, animations disabled, blocked fonts/analytics, no fixed waits, element-level capture, cap of 6 screens

---

## v2.13.0 — October 1, 2026

### Law 36 — Cross-project pattern catalogue
- New binding law: `knowledge/PATTERNS.md` (personal, gitignored like `projects.yaml`) logs bugs/patterns already solved in one project, so the same symptom showing up in another project gets recognized instead of re-solved from scratch
- Claude surfaces a matching entry and asks before applying it — never silently reuses a past fix; offers to log a new entry when it solves something reusable, never logs one without asking
- Ships `knowledge/PATTERNS.example.md` as the public template, same convention as `projects.yaml` / `projects.example.yaml`

---

## v2.12.0 — October 1, 2026

### Law 35 — Explicit, ordered deploy steps
- New binding law: whenever a change needs more than "merge the PR" — a migration to run by hand, an env var to set, a dependent second PR, a required redeploy — Claude's PR-ready summary (or an immediate follow-up) includes a numbered, ordered checklist with the literal command/SQL/dashboard path, not a vague category
- Prompted by a real session where a two-repo pageview-stats feature needed migrations applied and env vars set between PR merges, and the ordering/exact steps weren't being surfaced proactively
- When new steps are discovered later, Claude restates the full remaining sequence rather than mentioning only the new step in isolation

---

## v2.11.0 — October 1, 2026

Four generic, stack-agnostic additions.

### Law 32 — Hook-enforced guardrails
- New binding law: a `PreToolUse` hook (`.claude/hooks/enforce-laws.py`) mechanically blocks `gh pr merge` in any form, commit/push while on the default branch, non-Conventional-Commits messages, and secrets in a staged diff
- No `--auto` exception for merges — Law 7 ("Claude never merges") stays absolute, unlike the source repo's carve-out
- `.claude/settings.json` ships the reference `PreToolUse` wiring; `install.sh` registers the same hook globally in `~/.claude/settings.json` (merging into existing content, never overwriting), so it runs in every repo a session touches — `dforge-update` alone is enough to pick up script-logic changes, since the registration points at a fixed path in the clone
- Fails open on parse errors — a backstop against mechanical slips, not a replacement for judgment

### Law 33 — Session resumption via `SESSION_NOTE.md`
- New binding law: Claude offers a short handoff note (goal, done, left, blocking decision, branch/issue/PR) when a non-trivial task is left unfinished at session end, reads it back at the next session start, and cleans it up once resumed work completes

### Law 34 — UI-PR screenshot evidence
- New binding law: any PR touching a component, styles, or layout file embeds a Playwright screenshot of the changed screen/state in the PR body — point-in-time reviewer context, not a request for a permanent visual-regression suite

### Law 9 — pull immediately after merge
- Added an explicit, unprompted `git pull` of the default branch as part of the existing post-merge cleanup duty, so local `main` doesn't go stale between sessions

---

## v2.10.0 — June 29, 2026

### Law 31 — Small, atomic PRs
- New binding law: every PR targets under 200 lines changed (400 hard ceiling), one concern per PR
- 5 splitting strategies: separate by type, vertical slices over horizontal layers, infrastructure first, tests travel with their code, sequential stacking for large features
- Atomic commits — no WIP commits, no commented-out code, each commit passes CI independently
- Pre-PR self-check, PR description discipline (What / Why / How to test / Sequence)
- Repo hygiene standards: squash-merge by default, stale branch sweeps, orphaned issue detection, README kept current with every PR

### README professionally restructured
- shields.io badges (version, license, CI, plugin, law count), problem/solution table, quick-start, ASCII architecture diagram, structured command tables, full repo tree, numbered contributing steps

---

## v2.9.0 — June 23, 2026

### Arm / disarm — soft governance toggle
- New skill: `skills/arm-disarm/SKILL.md` — type `disarm` to suspend all Design Forge laws for a session; type `arm` to restore them
- Hard-safety rails survive disarm and cannot be toggled off: **never merge** (Law 7) · **secret scan** (Law 14) · **no real PII** (Law 15)
- A visible `⚠ DISARMED` banner appears on every response while governance is suspended
- State resets to armed at every new session start — disarm never persists

### Default branch, not just `main`
- Law 5 and Law 7 now say **"default branch"** instead of `main` — detects `main`/`master`/`trunk`/`develop` or any other protected base via `git symbolic-ref refs/remotes/origin/HEAD`
- Prevents accidental direct pushes in repos where the default branch isn't `main`

### Immediate branch cleanup after merge (Law 9)
- Branch cleanup is now Claude's **immediate duty in the same response** where a merge is confirmed — no prompt, no reminder needed
- Explicit report line required: `Branch \`feat/…\` deleted (remote + local). Issue #N closed.`

---

## v2.8.0 — June 16, 2026

### Universal COMPONENT_PATTERNS (no project coupling)
- Reframed examples as a generic CRUD domain (illustrative, domain-agnostic) — substitute your own entities
- Removed the project-specific component inventories (those belong in each project's `PROJECT_KNOWLEDGE.md §3`)
- Genericized provenance; **no pattern changed** — purely a portability/clarity pass

---

## v2.7.0 — June 15, 2026

### Slimmer always-on payload
- Trimmed what loads at session start from ~10.7K to **~8.5K tokens** by cutting duplication — **no law removed or weakened**
- `CLAUDE_LAWS.md`: changelog → pointer to this file; the duplicated Personas table → pointer to `CLAUDE.md`; Law 4's knowledge table → pointer to the on-demand map
- `CLAUDE.md`: condensed the "Non-negotiables" and "What Claude will refuse" sections (they restated laws that already load)
- Net session start is now **~8.5K** (down from ~40.4K before lazy-loading — a −79% total reduction)

### Leaner skills (no behavior change)
- The 10 knowledge-backed skills are now **thin routers**: each triggers on its task and points to the canonical `knowledge/` file instead of re-hosting a (drift-prone) copy — skill bodies dropped ~12.2K → ~6.7K tokens, and an invoked skill no longer loads the same content twice
- Fixed the stale `claude-laws` skill (it listed "19 laws / v1.0.0")
- Self-contained skills (ux-writing, design-critique, design-resources, figma-craft, developer-handoff) unchanged — they *are* the source

### New: Law 30 — resolve every UI to the chosen component library
- Once a project's library is chosen, **all** UI is built from it — a paper sketch, Figma frame, or screenshot of another app is treated as *intent*, mapped to the library's primitives (e.g. another app's dropdown → the library's `Select`)
- Never hallucinate components, never introduce a second UI library, never hand-roll a primitive the library provides; if it genuinely lacks one, ask before adding/custom-building

---

## v2.6.0 — June 15, 2026

### Lazy-loaded knowledge — ~73% smaller session start
- Only the binding laws (`CLAUDE_LAWS.md`) load at session start now
- The 8 knowledge files load **on demand** — Claude reads each one only when its trigger/scope fires (e.g. `PROJECT_SCAFFOLD` on `new project`, `UX_RESEARCH_GUIDE` on `research mode`)
- Session-start context drops from ~40.4K to ~10.7K tokens; each session pulls in only the 1–2 files it actually uses
- No rules changed — only *when* they load

---

## v2.5.0 — June 15, 2026

### Documentation is the team's shared duty (no Docs agent)
- Removed the dedicated **Docs** role (`docs-writer.md`) and the `docs mode` trigger
- Each role now documents its own change as it builds; the **Lead enforces** the doc standards as a gate before review
- Pipeline stages: `planned → building → testing → in-review`; the documentation gate stays (undocumented change = not done), just owned by the team

---

## v2.4.0 — June 12, 2026

### An agent team that works one pipeline
- Personas now compose into a team that runs a single flow: **plan → build → test → document → review → human-merge** ([`TEAM_WORKFLOW.md`](./knowledge/TEAM_WORKFLOW.md))
- **New roles:** Lead (orchestrator), Backend (API/DB/server), **Tester** (writes + runs tests, axe/coverage gate, can block the PR), **Docs** (README/API docs, RELEASES, PROJECT_KNOWLEDGE, handoff)
- Frontend stays the UI builder; Design/Research/Analyst are supporting; `fullstack mode` now activates the Lead
- Two gates before a PR is review-ready: **Tester** (tests pass + axe clean + acceptance criteria met) and **Docs** (change is documented)
- Handoff rides one shared thread — the `PROJECT_KNOWLEDGE §11` Stage column + the PR body — so context isn't re-derived between roles
- New triggers: `team` / `build feature`, `backend mode`, `tester mode`, `docs mode`
- README gains a **"Working with the team"** how-to + a which-agent-for-what table

### Agents obey the rules (Law 29)
- Every role is fully bound by the laws; if it thinks it should do something the rules don't allow or cover, it **stops and asks** instead of acting on its own

### Stronger accessibility testing
- Beyond an axe scan, the Tester now explicitly verifies **tab order, visible focus states, keyboard-only operation, focus management/trap (modals + route change), roles + accessible names, and live regions** (`FULLSTACK_WORKFLOW §8.1`)

---

## v2.3.0 — June 12, 2026

### Deeper Fullstack engineering (FULLSTACK_WORKFLOW §6–§8)
- **Backend §6** — API contracts (contract-first, version breaking changes, contract tests); DB migrations (forward-only + reversible, expand → migrate → contract); observability (OpenTelemetry tracing, structured logs with request IDs, error tracking)
- **Frontend §7** — Core Web Vitals budgets, server-vs-client state (TanStack Query), loading/empty/error/success UI states + error boundaries, accessible forms
- **Testing §8 + Phase 5** — unit / integration / contract / E2E pyramid; RTL component tests, vitest-axe + axe-core/playwright zero-violation gate, MSW API mocking, Playwright E2E, meaningful coverage
- `agents/fullstack.md` references the full checklist

### AGENTS.md
- Added a root `AGENTS.md` shim pointing at the laws, so non-Claude agents (Cursor, Codex, Copilot, Aider, …) inherit Design Forge governance

---

## v2.2.0 — June 9, 2026

### Decks use your own PowerPoint template
- In research/deck mode, Claude asks you to share your `.pptx`/`.potx` template and builds the slides on top of it
- No built-in or third-party theme is ever used; if you have no template, you get a plain neutral 16:9 deck
- Removed the dangling `PPT_TEMPLATE.md` references (the file and `ppt-template/` skill never existed)

### Dependabot for scaffolded projects (Law 10)
- Every new project ships with `.github/dependabot.yml` — weekly update PRs for npm + GitHub Actions
- Applies to all platform tracks (React/Vite, React Native/Expo, Angular)
- This repo also gets a `dependabot.yml` (github-actions ecosystem)

### Stricter process discipline (Laws 2 + 7)
- Law 2: Claude announces what it understood and waits for explicit approval before executing — silence or "ok" is not approval
- Law 7: Claude never merges under any phrasing (no merge button, API, squash/rebase/fast-forward, or local merge); "merge it"/"ship it"/"done" = open/finish the PR and stop

### Update notifications (Law 28)
- At session start, Claude compares your loaded version against the remote and, if a newer one exists, shows: `Design Forge update available: v<x> → v<y>. Run \`update rules\` to pull and reload.`
- One global update reaches every consuming project (they share one `~/.design-forge`). Claude never auto-pulls — it notifies and waits for your go-ahead.
- Fixed the README law count (26 → 28)

---

## v2.1.0 — June 9, 2026

### Analyst persona (replaces Pendo mode)
- `pendo mode` → `analyst mode` — a tool-agnostic product-analytics persona
- Works with whichever analytics MCP is connected: Pendo, Amplitude, Mixpanel, PostHog, FullStory, Contentsquare (Heap/Hotjar), Adobe Analytics, Google Analytics 4, LogRocket, Statsig
- New `knowledge/ANALYTICS_GUIDE.md` with the supported-platform matrix, privacy rules, and Triangulated Insight Brief template — Pendo retained as the worked example
- Renamed `agents/pendo.md` → `agents/analyst.md` and `skills/pendo-analyst/` → `skills/analyst/`

---

## v2.0.0 — June 9, 2026 — Public release

### Public-ready repository
- New professional README explaining what Design Forge is and how anyone can use it
- `projects.yaml` is now gitignored — ships `projects.example.yaml` instead, so no personal project data is published
- `.claude-plugin/marketplace.json` added — the repo is installable via `/plugin marketplace add BojanKocijan/design-forge`

### New: `dry run` mode (Law 26)
- Toggle with `dry run` / `auto git`
- Claude prepares all edits, then prints a copy-paste terminal command block (commit/push/PR/issue) and offers to run it — instead of spending tokens executing git/gh itself
- Never overrides Law 7 (Claude never merges)

### New: plugin-standards compliance (Law 27)
- Codifies that the repo stays a valid, submittable Claude Code plugin
- Manifest + marketplace.json kept valid; skills as `skills/<name>/SKILL.md` with name+description; components at plugin root
- Version must stay in sync across plugin.json, marketplace.json, CLAUDE_LAWS header, and RELEASES on every release
- Quality/security gate (MIT license, README, no secrets, no personal data, CI green) before official-directory submission

### Plugin directory
- Tracking the submission of Design Forge to the official Claude Code plugin directory (`anthropics/claude-plugins-official`)

---

## v1.2.1 — June 9, 2026

### Proactive branch cleanup (Laws 9 + 25)
- Once a PR is merged, Claude deletes the branch (remote + local) without being asked
- Only deletes branches confirmed merged into `main` (`git merge-base --is-ancestor` check)
- Session-start checklist now sweeps orphaned merged branches
- Mirrored in FULLSTACK_WORKFLOW Phase 9

---

## v1.2.0 — June 8, 2026

### Session-start checklist (Law 25)
- Always pull `main` and check open PRs before any code work

### Automatic project wiring (Law 11)
- Laws load globally via `install.sh`; projects only link `@./PROJECT_KNOWLEDGE.md`
- Scaffold writes it for new projects; session-start step 4.6 auto-creates it for existing ones

---

## v1.1.0 — June 7, 2026

### New Laws (21–24): Senior-engineer thinking
- Law 21: No bloated code (YAGNI) — ask before over-engineering
- Law 22: Edge case thinking before code — identify 3-5 edge cases upfront
- Law 23: Verify before claiming — no hallucination, check the code first
- Law 24: Question and reason before executing — why, simpler way, best practice

### New law (5a): Check existing PRs
- Before branching, check if open/merged PR exists for same work
- Update existing PR instead of creating duplicate
- Prevents lost effort when resuming after quota limits

### Project Registry (Law 20): Auto-register new projects
- Detect unregistered project at session start
- Auto-open issue → branch → register in projects.yaml → PR workflow
- No manual registration step required
- Every project gets locked localhost port

**Documentation**: Auto-registration link in PROJECT_KNOWLEDGE.md template

---

## v1.0.0 — June 6, 2026

### Initial Design Forge release
- Library-agnostic from the start: shadcn/ui, MUI, Ant Design, Chakra UI, or local components
- `dforge-update` CLI, `~/.design-forge` clone dir
- 20 binding laws, 4-file component pattern, no-inline-styles rule, methodology (research, UX writing, handoff, feature workflow, fullstack workflow)
- Three install paths: plugin, install.sh (global memory), Copilot custom instructions
- Five personas: Frontend, Fullstack, Design, Research, Analyst
- Project registry with locked localhost ports per project
