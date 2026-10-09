# Plan — The dashboard shows every data point the marketing page shows (#256)

Spec: [#256](https://github.com/BojanKocijan/bk-charterline/issues/256), plus #198 for skills and personas · Gate tier: Significant · Branches: `docs/dashboard-parity-plan`, then `fix/dashboard-counts` … `fix/site-planned-chips` · Issue: #256 (and #198)
Work pile: judgment-heavy (a new data source and a hook change), built in this session
Skip gates: separate `intent.md` and `spec.md` skipped at the owner's request (2026-10-09, chat: "one plan, approve once"); #256 and #198 serve as the intent
Approved-by: <pending>

## Why

The marketing page's Analytics section (`site/index.html`, `#analytics`) shows example data points for Governance and Usage. The private dashboard (`~/.bk-charterline/dashboard/`, built by `scripts/my_metrics.py`) is missing half of them. The owner's decisions, 2026-10-09:

- **Token cost per session** shows both the rules' share (fixed per release) and the real total each session used.
- **Sessions per persona** comes from mode commands and persona subagents in the session logs, plus a new hook log of mode commands from now on, so counts survive log cleanup.
- Product analytics (funnel, retention, insight brief) stays with `analyst mode`. The dashboard doesn't get it.

## Data points, before and after

| Data point | Site | Dashboard today | After | PR |
|---|---|---|---|---|
| Hook blocks | ✓ | ✓ (counts false positives as blocks) | ✓ correct | 1 |
| Prompts by kind | – | ✓ ("Edit to a guardrail" twice) | ✓ one row per label | 1 |
| Blocks marked wrong (n, %) | ✓ | ✗ | ✓ stat | 2 |
| AI tools classified, X of Y | ✓ | ✗ | ✓ stat | 2 |
| AI tools per tier, with Unclassified | ✓ | tiles only, unclassified counted as High | ✓ bar chart, the site's tier names | 2 |
| Scope of PR numbers | – | unlabelled | "All registered projects" | 2 |
| Token cost per release | ✓ | ✗ | ✓ column chart | 3 |
| Rules' share per session | – | ✗ | ✓ stat | 3 |
| Real tokens per session | – | ✗ | ✓ weekly median, line chart | 4 |
| Skill runs | ✓ | ✗ | ✓ bar chart | 4 |
| Sessions per persona | ✓ | ✗ | ✓ bar chart | 4, 5 |

## Seven PRs, merged in order

Each is opened against `main`, stays under Law 31's 400 lines, and updates `RELEASES.md` under Unreleased. A plain number below means this repo's PR.

| PR | Branch | What | Size |
|---|---|---|---|
| 0 | `docs/dashboard-parity-plan` | This plan | ~150 |
| 1 | `fix/dashboard-counts` | False positives stop counting as blocks; prompts merge by label | ~60 |
| 2 | `feat/dashboard-governance` | Blocks marked wrong, tools classified, tools per tier, scope label | ~200 |
| 3 | `feat/dashboard-rules-cost` | Token cost per release, the rules' share per session | ~200 |
| 4 | `feat/dashboard-sessions` | Session logs: real tokens per session, skill runs, sessions per persona | ~380 |
| 5 | `feat/persona-log` | The hook logs mode commands; the dashboard reads them | ~250 |
| 6 | `fix/site-planned-chips` | The site drops "Planned" chips for what is now built | ~20 |

## PR 1: correct counts (fix)

- `scripts/my_metrics_data.py` `hook_activity`: count a row as a block only when `type == "block"`. Collect `type == "false_positive"` rows separately as `false_positives` (count only; the note is never read).
- `scripts/my_metrics.py` `overview`: sum `asks` rows that map to the same label in `WORDS["checks"]` before charting, so `guardrail-write` and `guardrail-edit` show as one "Edit to a guardrail" row.
- **Tests** (`tests/test_my_metrics_data.py`, `tests/test_my_metrics.py`): a `false_positive` row doesn't raise the block count; two checks with one label give one row with the summed count.

## PR 2: governance data points

- `my_metrics_data.py`: `hook_activity` returns `false_positives: <int>`. `tools` returns `classified: <int>` (registry entries) and `known: <int>` (classified + unrated).
- `my_metrics.py` `overview`:
  - "Your rules at work" stats gain **Blocks marked wrong**: `n (p%)` of blocks, or `0` with no blocks; and **AI tools classified**: `X of Y`.
  - A new figure, **AI tools per Law 38 tier**: bars `1 · Local`, `2 · Reads`, `3 · Writes`, `4 · Production`, `Unclassified`, the same labels as the site. Tier counts come from the registry tiers, not the overrides, so each tool counts once. The severity tiles stay as they are.
  - The "Pull requests within 400 lines" stat's caption becomes `<n> merged · all registered projects`.
- **Tests:** the counts on a fixture registry with two rated tools and one unrated; the empty states (no registry → the existing error; no blocks → `0`).

## PR 3: rules' cost

- `my_metrics_data.py`: a new section, `rules_cost(home)`. For every tag matching `^v\d+\.\d+\.\d+$` in the rules clone (`git -C <home> tag -l 'v*'`), read `CLAUDE.md` at that tag (`git show <tag>:CLAUDE.md`). Add the `@./` files it imports, read at that tag as well, and estimate tokens with `laws_cost.estimate` (the per-file ratio, falling back to 2.7 bytes per token for files outside `laws_cost.FILES`). This measures what each release actually loaded, including old releases that imported every knowledge file. The results are cached in `dashboard/state.json` under `rules_cost`, keyed by tag; a tag is never measured twice.
- `my_metrics.py`: a new **Usage** section with a figure, **Tokens the rules add to each session, per release** (columns, the last 12 releases), and a stat, **Rules' share per session**: the installed release's tokens.
- Missing git or no tags → that section says "The rules' history couldn't be read." and the rest of the page builds.
- **Tests:** a temp git repo with two tags and an `@./` import; a second run reads from the cache (no `git show`, checked with a fake `git` on `PATH`).

## PR 4: session logs (#198)

- A new module, `scripts/my_metrics_sessions.py`, imported by `my_metrics_data.py` as one more `section`. It reads `~/.claude/projects/*/*.jsonl` (the main sessions; `subagents/` files count toward their parent session's tokens) modified within the 30-day window.
- **Incremental:** `dashboard/sessions-state.json` keeps one summary per file keyed by path, with `size` and `mtime`. A file is parsed again only when either changes; files gone from disk drop out. A line is JSON-parsed only when it contains `"usage"`, `"tool_use"` or `"type":"user"`, so a 300 MB folder stays quick. Target: under 2 s cold, under 0.3 s warm, timed on the owner's machine and written in the PR.
- **What a summary keeps, counts only** (#198's rule: never prompts or file names):
  - `start`: the first timestamp
  - `tokens`: input + cache creation + cache read + output, summed over assistant messages
  - `skills`: `{name: runs}` from `Skill` tool calls
  - `subagents`: `{subagent_type: runs}` from `Agent`/`Task` calls
  - `personas`: the set of personas from user messages whose whole text, trimmed and case-folded, is one trigger phrase from the CLAUDE.md table (`frontend mode`, `fullstack mode`, `backend mode`, `tester mode`, `research mode`, `research mode full`, `analyst mode`, `incident mode`, `team`, `build feature`)
- **Persona per session:** every persona whose mode command appears, plus every persona whose subagent ran (`frontend`, `fullstack`, `lead`, `backend`, `tester`, `design`, `research`, `analyst`, `incident`). `fullstack mode`, `team` and `build feature` count as Lead. A session with none counts as Frontend, the default.
- `my_metrics.py` Usage section: **Sessions per persona** (bars), **Skill runs** (bars, the top 10), **Tokens per session** (line chart, weekly median, last 30 days) and a stat with this window's median. Each figure's caption names its source: "From Claude Code's session logs on this machine".
- The session-start build (`--if-changed`) keeps its current fingerprint and doesn't watch the session logs, so it doesn't rebuild every session. `my metrics` and the post-merge build (Law 9) read them.
- No logs folder → "Claude Code's session logs weren't found on this machine." A file that can't be parsed is skipped, never fatal.
- **Tests** (`tests/test_my_metrics_sessions.py`): a fixture folder with two sessions and one subagent file, which checks tokens, skills, the persona from a mode command, the persona from a subagent, and the Frontend default; the cache is reused when size and mtime are unchanged and dropped when the file is gone; a prompt's text and a file path in the fixture appear nowhere in `sessions-state.json` or the built HTML.

## PR 5: persona log (hook)

- A new hook script, `.claude/hooks/persona_log.py`, registered for `UserPromptSubmit`. When the whole prompt is one trigger phrase (the same list as PR 4), it appends `{"ts", "session_id", "persona"}` to `~/.bk-charterline/persona-log.jsonl`. The prompt's text is never written. It always exits 0 with no output, never blocks, takes no lock, and ignores every error.
- `.claude/settings.json` and `install.sh`'s `wanted` list gain the `UserPromptSubmit` entry (no matcher). `install.sh` adds it once, and a second run writes nothing.
- `my_metrics_sessions.py` merges the persona log into the session summaries by `session_id`, so the persona count stays right after Claude Code removes old session logs (`cleanupPeriodDays`).
- `persona-log.jsonl` joins `SOURCES` in `my_metrics.py` and is gitignored.
- `knowledge/GUARDRAILS.md` gets one line on what the new hook writes.
- **Tests:** a trigger prompt writes one line holding no prompt text; a normal prompt writes nothing; an unwritable home still exits 0; running the install twice adds one entry.
- This changes the hook, so the merge order offers `/code-review ultra` (Law 37).

## PR 6: the site

- `site/index.html`: drop the "Planned · #120" chip on Pull request size and the two "Planned · #198" chips; the Usage panel's source line names `my metrics`. `scripts/site_metrics.py` runs as before; no number changes.
- Screenshots per Law 34 only if the owner says yes when the PR is opened.

## Proof

- Commands that must pass: `python3 -m pytest tests/`, `cd site && npx playwright test` (the a11y and dashboard specs build a fixture dashboard), `python3 scripts/release_version.py check`.
- Each PR runs `/code-review main...HEAD` and fixes its findings before opening. After PR 5, a fresh subagent reviews the whole stack against this plan.
- Done by hand once, on the owner's machine: `python3 scripts/my_metrics.py`, then open `~/.bk-charterline/dashboard/index.html` and check every row of the "After" column above.
- Visual evidence: the owner's yes or no is asked before each UI PR (Law 34).

## Risks

- The session log format belongs to Claude Code and can change → every field is read with `.get`, an unknown shape is skipped, and the section says how many files were skipped.
- Parsing 300 MB of logs slows the dashboard down → the line pre-filter and the per-file cache, with the timing written in PR 4.
- Personal data in the cache → only counts and skill or subagent names are stored, checked by a test with a marker string.
- A hook on every prompt adds delay → `persona_log.py` imports only the standard library, does one string comparison, and returns at once for normal prompts.
- Old release tags imported different files → PR 3 reads each tag's own `@./` imports instead of today's file list.

## Ruled out

- **Real numbers on the marketing page.** The page shows example data on purpose, and the owner's numbers stay private (#120).
- **Product analytics on the dashboard.** It needs an analytics tool, which `analyst mode` already covers.
- **Watching the session logs at every session start.** They change every session, which would turn the cheap "nothing changed" check into a full rebuild.
- **Inferring personas from Claude's replies.** It would be guesswork; mode commands and subagents are facts.
