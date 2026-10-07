# Report — what loading the rules costs every session (#188)

Measured 2026-10-07 at v2.35.0 with Claude Code 2.1.289, signed in through claude.ai. Plan: [plan.md](plan.md).

## The answer

| Where | Tokens per session | Opus 5.5, first load | Opus 5.5, each later request |
|---|---|---|---|
| Any project | **30,420** | $0.24 | $0.006 |
| This repo (rules load twice) | **60,623** | $0.49 | $0.012 |

That's about **10× the rest of a minimal Claude Code session** (2,926 tokens with no tools and no MCP servers). The issue's estimate of ~20k came from chars ÷ 4. The Claude 5 tokenizer packs only 2.4 to 2.8 bytes into a token, so the real count is half again as large.

## How it was measured

**Exact file counts (`scripts/laws_cost.py --measure`).** In an empty temp folder, the `claude` CLI runs headless (`-p`, no tools, no MCP servers, one turn): once as is, once with `.` appended to the system prompt, and once with each file appended. A file's count is its run's input tokens (fresh, cache write and cache read added up) minus the `.` run's, which cancels the 7 to 12 tokens the appended prompt adds around itself. Repeat runs agree to within about 10 tokens.

| Model | `CLAUDE.md` | `CLAUDE_LAWS.md` | Total | Bytes per token |
|---|---|---|---|---|
| `claude-opus-5-5` | 7,470 | 22,653 | 30,123 | 2.42 / 2.77 |
| `claude-sonnet-5-5` | 7,473 | 22,648 | 30,121 | same |
| `claude-haiku-4-5` (two runs) | 5,295 / 5,293 | 16,336 / 16,330 | 21,631 / 21,623 | 3.42 / 3.84 |

Opus 5.5 and Sonnet 5.5 share a tokenizer. Haiku 4.5 uses the older one, which needs about 28% fewer tokens for the same text. Fable 5.1 wasn't run, and the cost table below assumes the Claude 5 count for it.

**Whole sessions (`--setting-sources`).** The file counts leave out the line Claude Code puts before each loaded file and `~/.claude/CLAUDE.md` itself. So the same prompt ran with and without the memory sources, on Opus 5.5:

| Folder | All sources | Without user memory | Without user or project memory | Rules |
|---|---|---|---|---|
| Empty folder | 33,346 | 2,926 | — | 30,420 |
| This repo | 64,225 | 33,938 (user only) | 3,602 | 60,623 (30,336 global + 30,287 project) |

**Estimate for CI.** `python3 scripts/laws_cost.py` divides each file's bytes by its measured bytes per token: 30,128 at v2.35.0, 5 tokens off the exact count. It needs no account, so CI runs it on every PR.

## Cost per session

Prices from the [Claude API price list](https://platform.claude.com/docs/en/about-claude/pricing) on 2026-10-07. Claude Code writes the session prefix to the 1-hour cache: the bare Opus run reported `ephemeral_1h_input_tokens`, and its `total_cost_usd` ($0.26423) is exactly what the 1-hour write price gives. Each later request in the session re-reads the rules at the cache-read price, and a session idle for over an hour writes them again.

| Model | 1h write / read, $ per MTok | First load | Each later request | 50 requests | 200 requests |
|---|---|---|---|---|---|
| Opus 5.5 | 8 / 0.20 | $0.243 | $0.0061 | $0.54 | $1.45 |
| Sonnet 5.5 | 4 / 0.20 | $0.122 | $0.0061 | $0.42 | $1.33 |
| Fable 5.1 (not measured) | 20 / 0.25 | $0.608 | $0.0076 | $0.98 | $2.12 |
| Haiku 4.5 | 2 / 0.10 | $0.043 | $0.0022 | $0.15 | $0.47 |

These are for any project. **In this repo, double every figure.** On a claude.ai plan these are list-price equivalents counted against your usage limits rather than a bill (the CLI reports `costBasis: list`). The agents here run on Opus (lead, backend, fullstack, incident) and Sonnet (frontend, tester, design, research, analyst). The rules also take 3% of the 1M context window on Opus and Sonnet, and 11% of Haiku's 200k.

## Growth per release

Estimates from each tag's files with today's per-file ratios.

| Release | Date | `CLAUDE.md` | `CLAUDE_LAWS.md` | Total |
|---|---|---|---|---|
| v2.17.0 | 2026-10-02 | 5,740 | 16,161 | 21,901 |
| v2.20.0 | 2026-10-03 | 5,815 | 16,228 | 22,043 |
| v2.26.0 | 2026-10-05 | 6,666 | 19,990 | 26,656 |
| v2.28.0 | 2026-10-05 | 6,732 | 21,006 | 27,738 |
| v2.30.0 | 2026-10-06 | 7,295 | 21,250 | 28,545 |
| v2.33.0 | 2026-10-06 | 7,449 | 21,964 | 29,413 |
| v2.34.0 | 2026-10-07 | 7,470 | 22,336 | 29,806 |
| v2.35.0 | 2026-10-07 | 7,470 | 22,653 | 30,123 (exact) |

That's **+38% in 18 releases over five days**. The biggest additions are Law 32 (+2,300 tokens), the new Law 38 (+1,700) and `CLAUDE.md` (+1,700). From v2.36.0 on, each release note records the estimate.

## The budget

**33,000 tokens**, about 10% above today's count. The CI step `Rules token budget` prints a warning when a PR takes `CLAUDE.md` + `CLAUDE_LAWS.md` past it, and never fails the build. The plan suggested 22k, but that was 10% above the chars ÷ 4 estimate; against the exact count it would warn on every PR. The owner sets the final number in review.

## Where to cut, biggest first

Each option is its own PR later; nothing changes in this issue. Savings are Opus 5.5 tokens per session. Every 1,000 tokens cut saves $0.008 per first load and $0.0002 per later request.

| Option | Saves | Notes |
|---|---|---|
| Stop this repo loading the rules twice | 30,287 (this repo only) | Half of this repo's cost. Needs a way to skip either the global import or the project copy here without breaking the plugin install |
| Move most of the `CLAUDE.md` trigger table to on-demand knowledge | up to 3,504 | The largest single section. Most triggers (`ai classify`, `review cap`, `hook log`, …) are rare and repeat text from the laws |
| Move Law 32's detail to on-demand knowledge | 1,796 (the two tables) to ~3,400 (all but a summary) | Law 32 is 3,704 tokens, the largest law. The hook enforces the tables anyway |
| Move Law 31's README and repo-hygiene parts to knowledge | ~1,000 of 1,823 | |
| Trim `CLAUDE.md`'s session-start section | ~800 of 1,699 | Overlaps Laws 1, 16, 25 and 28 |
| "Sources" paragraphs | 163 | Too small for its own PR |

The four cuts outside the duplicate load add up to about 9,000 tokens at most, close to 30% of the rules.

## Not measured

- The output of the session-start steps (the release check, `gh auth status`, the PR list), which depends on the repo.
- Whether subagents load the rules again. If they do, each subagent pays the first-load cost too.
