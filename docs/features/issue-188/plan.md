# Plan — measure what loading the laws costs every session (#188)

Spec: [#188](https://github.com/BojanKocijan/design-forge/issues/188) (the issue) · Report: [report.md](report.md) · Gate tier: Standard · Branch: `feat/laws-cost` · Issue: #188
Work pile: delegable (a measurement script and a report; machine-verifiable)
Approved-by: BojanKocijan, 2026-10-07, chat

## What gets measured

- **Every session** loads `~/.claude/CLAUDE.md` (228 bytes), which imports `~/.design-forge/CLAUDE.md` (18,102 bytes), which imports `CLAUDE_LAWS.md` (62,805 bytes). About 81 KB at v2.35.0.
- **This repo** loads the project's own `CLAUDE.md` and `CLAUDE_LAWS.md` on top of that, so about 162 KB.

## Method

**Exact tokens, an A/B pair of headless runs** (owner-run, needs a logged-in `claude` CLI). In an empty folder:

- **A:** `claude -p "Reply with exactly: ok" --output-format json`
- **B:** the same plus `--append-system-prompt-file <file>`

B − A in `usage` (input, cache creation and cache read tokens added up) is the exact token count of `<file>`. It runs once for `CLAUDE_LAWS.md` and once for `CLAUDE.md`, with nothing switched off. `total_cost_usd` from run A gives the cost of a minimal session for comparison. Six requests in all, each a few hundred output tokens at most.

**An offline estimate for every release:** bytes ÷ a calibrated bytes-per-token ratio, taken from the exact run and stored in the script. It needs no API, so CI can run it.

## Files to change

| File | Change |
|---|---|
| `scripts/laws_cost.py` (new) | `--estimate` (default): bytes, words and estimated tokens per file and in total, for the repo's `CLAUDE.md` + `CLAUDE_LAWS.md`; `--budget N` prints a GitHub Actions `::warning::` when the total passes N and still exits 0. `--measure` (owner-run): the A/B runs above, printing exact tokens and the ratio; refuses to run when `CI` is set |
| `tests/test_laws_cost.py` (new) | Estimate maths, the budget warning and exit code, and that `--measure` refuses under `CI` and never runs in tests |
| `.github/workflows/markdown-lint.yml` | One step: `python3 scripts/laws_cost.py --budget <N>` (a warning, never a failure) |
| `docs/features/issue-188/report.md` (new) | The exact numbers for a normal project and for this repo; cost per session for each model you use, both a first load and a cached load, with prices from the current price list; the growth table per release; the biggest sections; the options to cut, each with its saving |
| `RELEASES.md`, `CLAUDE_LAWS.md` (version only), `README.md`, `plugin.json`, `marketplace.json` | v2.36.0, with the token estimate in the release note |
| `docs/features/issue-188/plan.md` | This plan |

That's 9 files, about 300 lines.

## Order of work

1. You log the CLI in once (`claude`, then `/login`, in your terminal). I can't sign in for you.
2. Run `--measure`, put the exact numbers and the ratio into the script and the report.
3. The estimate, the budget and the tests.
4. The report: costs, growth, options to cut.
5. The CI step and the release.

## Proof

- **Tests:** `test_laws_cost.py` as above. `--measure` is never called by tests or CI.
- **Evidence in the PR:** the six runs' `usage` numbers, redacted to counts only; the estimate against the exact count (within 5%).
- **Commands:** `python3 -m unittest discover -s tests`, `python3 scripts/laws_cost.py --budget <N>`, `release_version.py check`, markdownlint.

## Risks

- **CI change** (Law 2: High by the letter). → One read-only step that can only warn.
- **Token counts differ slightly by model.** → The report names the model each count came from.
- **The appended prompt carries a small wrapper.** → It's measured once with an empty appended file and subtracted.

## Ruled out

- **The token-counting API:** it needs an API key, and you shouldn't hand me one.
- **`claude --bare`:** it skips memory, but it needs `ANTHROPIC_API_KEY` too.
- **chars ÷ 4 alone:** it's fine for tracking growth, but it isn't an answer to "how much does it cost".
- **Cutting the laws in this issue:** measuring comes first, and each cut is its own PR afterwards.

## Open questions for the owner

- [x] **The budget N.** Suggested: warn about 10% above today's total. The plan was approved without a number, and the exact total turned out to be 30,123, not ~20k, so 22k would warn on every PR. The step uses **33,000** (the same ~10% headroom); the owner confirms or changes it in review.

## Deviations after approval

- **More measurement runs than the six planned:** the same four runs on Sonnet 5.5 and Haiku 4.5 (Haiku twice, to check repeatability), plus five whole-session runs with `--setting-sources`, to cover each model the agents use and the file headers the A/B pair leaves out. 22 runs in all, about $4 at list price, counted against the owner's plan.
- **The wrapper is measured with `.`, not an empty file,** because Claude Code may skip an empty appended prompt. The `.` adds about one token, within the run-to-run noise.
- **One bytes-per-token ratio per file,** not one for both: a single ratio put `CLAUDE.md` 10% off. Per-file ratios land within 5 tokens of the exact total.
- **Two PRs, not one:** the diff came to 508 lines, past Law 31's 400-line ceiling. PR 1 (docs) holds this plan and the report; PR 2 (feat) holds the script, its tests, the CI step and the v2.36.0 release, and links the report, so it merges second.
- **Recording the count with each release** starts in `RELEASES.md` with v2.36.0. Adding it to Law 27's release checklist is a law change, so it waits for its own PR.
