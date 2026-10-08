# Spec — My BK Charterline: a private dashboard for every user (#120)

Intent: [#120](https://github.com/BojanKocijan/bk-charterline/issues/120), as the owner extended it on 2026-10-08 ([comment](https://github.com/BojanKocijan/bk-charterline/issues/120#issuecomment-6055156189))
Design: the owner-reviewed prototype from 2026-10-08 (overview plus a "Tools and calls" page, in the site's navy and lime design)
Approved-by: BojanKocijan, 2026-10-08, chat (all three decisions as recommended)

## Owner decisions (chat, 2026-10-07 and 2026-10-08)

- **Every user gets a private dashboard** once they use the rules: what the rules stopped, what they were asked, which tools Claude can reach and how risky each is, and how their pull requests go.
- **It lives in their own clone:** `~/.bk-charterline/dashboard/`, gitignored, opened straight from the file. Nothing is committed or sent anywhere.
- **It's rebuilt on every `update rules` and at session start,** at session start only when the data changed.
- **Design:** a short visual overview, with details on a second page. Severities have names (Critical, High, Low, Minimal), and every tool says what it can do in plain words.
- **A button can't run a command in Claude,** so commands get a **Copy command** button and say where to paste.
- **Which tool, on which call:** the hook records the tool's name (never its inputs) for every prompt, so Critical calls are named too.

## Behavior

### Page 1: Overview (`index.html`)

1. **Three headline numbers** for the last 30 days: hook blocks, permission prompts, and the share of pull requests within the 400-line ceiling.
2. **What Claude can reach, by severity:** four tiles (Critical, High, Low, Minimal), each with its count, its rule ("asks you every time", "asks you once per session", "reads only", "stays on your machine"), and up to four tool names as chips, riskiest areas first. Each tile links to its section on page 2.
3. **Not rated yet** (only when there are any): the count, a "See them" link, and `ai classify` with a **Copy command** button ("Paste it into Claude Code and press Enter").
4. **Latest tools you approved:** the five most recent, as time · severity dot · tool · what it can do. Then "See every call".
5. **What the hook did:** blocks per law and prompts by kind, as bars; pull request size against the 400-line ceiling, as columns.

### Page 2: Tools and calls (`tools.html`)

- **One section per severity,** with a card per tool: area (Database, Email, Files and docs, Your computer, Web, Claude app, Design and dev tools), name, and what it can do, listed.
- **Not rated yet:** the tools, as chips.
- **Every call:** time, severity, tool, what it can do, and the call's name, for every High and Critical prompt in the last 30 days.
- **Pull requests per project** (decision 1): merged, median size, share within 400 lines, time to merge, reverts, share co-authored by Claude.

### Data (all local; read, never written)

| Source | Gives |
|---|---|
| `~/.bk-charterline/hook-log.jsonl` | blocks, prompts, activity per day, and (after the hook change) the tool name of each prompt |
| `~/.bk-charterline/ai-approvals.jsonl` | the first High call per session, with its tool |
| `~/.bk-charterline/ai-tools.json` and `ai-inventory.json` | each tool's severity and what's not rated yet |
| `~/.bk-charterline/projects.yaml`, git and `gh` | pull request numbers per registered project, collected incrementally (the owner's requirement on #120) |
| `scripts/laws_cost.py` | the rules' tokens per session |

**Plain words for each tool's actions** come from a small table in the repo (for example `send_message` → "Send an email"); an action not in it shows its own name with underscores as spaces.

### The hook change

For every MCP prompt (High first use, Critical every call), the hook log gains one field: `tool`, the full tool name (`mcp__<server>__<tool>`). Never its inputs, never a command. Blocks and other prompts don't change.

### When it's built

- **`update rules`:** at the end of the install, a full build (local data and GitHub).
- **Session start:** a fast build from local data only, and only when a source changed since the last build. No network calls, so a session never waits on GitHub.
- **`my metrics`:** a new trigger that does a full build and gives the path to open.
- The session-start confirmation gains one line: `Dashboard: ~/.bk-charterline/dashboard/index.html` (decision 3).

### States

- **A new user** (no hook log, no approvals yet): each section says what will appear and when ("Your first blocked or approved call shows up here").
- **No `gh` login or no network:** the pull request parts say "Sign in with `gh auth login` to see pull request numbers", and the rest still builds.
- **A source that can't be read:** that section says so; the build never fails the update or the session.

## Acceptance criteria

- [ ] After `update rules`, `~/.bk-charterline/dashboard/index.html` and `tools.html` exist and open from the file with no console errors and no requests to other sites.
- [ ] `dashboard/` is gitignored, so `update rules` never sees it as a local change.
- [ ] At session start, a build with no changed sources does nothing; one with changed local sources finishes without network calls.
- [ ] Every tool in the registry and inventory appears exactly once, under its severity; unrated tools show as Not rated (treated as High).
- [ ] After the hook change, a Critical prompt appears on page 2 with its tool's name; no log line holds a tool's inputs or a command.
- [ ] The Copy command button copies `ai classify` and says where to paste it.
- [ ] WCAG 2.2 AA with axe at 390 and 1280 px in light and dark, on a dashboard built from fixture data.
- [ ] A missing or broken source shows a message in its section and never stops `update rules` or a session.

## Policy check

- **Component library:** none; plain HTML and CSS, reusing the site's styles and chart script (Laws 12 and 30 don't apply).
- **Accessibility:** WCAG 2.2 AA as above; severities are named in text, never by color alone.
- **Privacy:** Law 15 and Law 32's rule that the hook log never stores commands or inputs; the dashboard reads local data and the user's own `gh` login, and sends nothing.
- **Copy:** plain words for every action; severities named, not numbered.
- **Conflicts flagged for the owner:**
  1. **The rules grow a little:** the `my metrics` row and the session-start line add about 150 tokens per session (30,613 today, budget 33,000).
  2. **Session start does one more thing,** kept to local files and skipped when nothing changed.
  3. **The hook log gains a field.** The hook changes, so `update rules` asks you to approve its diff (Law 28).

## Out of scope

- Publishing any of it, or adding it up across users.
- Product analytics (that's `analyst mode` with the user's analytics tool).
- Changing a tool's severity from the page: rating stays `ai classify`, in chat, with the user's yes.

## Decisions for the owner

1. **Which projects' pull requests:** every project registered in `projects.yaml` (recommended), or only the current repo.
2. **The time window:** the last 30 days, fixed (recommended), or a 7 / 30 / 90-day switch.
3. **A `Dashboard:` line in the session-start confirmation** (recommended), or none.
