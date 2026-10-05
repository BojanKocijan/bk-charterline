# Plan — the hook enforces Law 38 tier 3 and 4 approvals for MCP calls (#138)

Spec: [spec.md](./spec.md) (approved) · Gate tier: Significant · Issue: #138 · Roadmap: #123
Branches: `feat/mcp-approvals-1-store`, `feat/mcp-approvals-2-hook`, `feat/mcp-approvals-3-registry`, each targeting `main` and stacked by commits
Work pile: judgment-heavy for the lookup and approval boundaries; delegable for the tests
Approved-by: BojanKocijan, 2026-10-05, chat

## Design

- **One script, two events.** `enforce-laws.py` stays the single hook command. `main()` dispatches on the payload's `hook_event_name`:
  - `PreToolUse` with a `tool_name` starting `mcp__` → new `check_mcp()`.
  - `PostToolUse` with an `mcp__` tool → new `record_mcp()`. It never prints, never exits non-zero, and swallows every exception: a `PostToolUse` hook can't block anything, and must not try.
  - Everything else is unchanged, including fail-open on an unparseable payload.
- **Tier lookup:** new `mcp_tier(tool_name, base) -> (tier, entry)`.
  - Split `mcp__<server>__<tool>` at the first `__` after the `mcp__` prefix. A name that doesn't split counts as tier 3.
  - Import `ai_tools` from `<hook dir>/../../scripts` (guarded, as `hook_log` is). Project = `git -C <base> rev-parse --show-toplevel`; outside a repo, the project is `None` (personal registry only).
  - `ai_tools.lookup("mcp", server, project)` then `ai_tools.tier_for(entry, tool)`. Overrides use the bare tool name, as the registry already does.
  - Any exception → `(3, None)`.
- **`check_mcp()`:**
  - Tier 1 or 2: return.
  - Tier 4: `ask(reason, "tier4-unapproved")`.
  - Tier 3: `ask(reason, "tier3-first-use")` unless `session_id` is a non-empty string and `ai_approvals.approved(session_id, tool_name)` is true.
  - The existing `Asked` handling in `main()` prints the decision, applies `ASK_DENIED_MODES` and logs it. The log's hashed "command" is the tool name.
- **Prompt reasons** (Law 32 style: name the law and the tool, say what to do):
  - Tier 4: `Law 38: <tool> is tier 4 (<label>, owner <owner>). Approve only this call. Check the arguments below. Nothing carries over to the next call.`
  - Tier 3, classified: `Law 38: first use of <tool> this session (tier 3, owner <owner>). Approving lets this tool run for the rest of the session.`
  - Tier 3, unclassified: `Law 38: <tool> is unclassified, so it counts as tier 3. Approving lets it run for the rest of the session. Run ai classify to give it a tier.`
- **`record_mcp()`:** recompute the tier. Only if it's 3 and `session_id` is present, call `ai_approvals.record(session_id, tool_name)`.
- **New module `.claude/hooks/ai_approvals.py`** (stdlib only, imported in the same guarded way):
  - `approved(session_id, tool) -> bool`: scans `~/.design-forge/ai-approvals.jsonl`. A missing or unreadable file, or a bad line, counts as not approved.
  - `record(session_id, tool) -> bool`: under `hook_log.locked()`, rewrites the file without lines older than 7 days or with a bad timestamp, appends `{"ts", "session", "tool"}` and swaps it in with `os.replace`. Returns `False` if the lock isn't free (the next call simply asks again).
  - No arguments or output are ever stored.
- **Registry and approvals protection** (in `protected_target()` and `check_bash()`):
  - Drop `ai-tools.json` from `DF_DATA_FILES`. Label it "your Law 38 tool registry".
  - `ai-approvals*` stays protected (it was never exempt). Label it "your Law 38 approvals".
  - Any `.claude/ai-tools.json` → "a project's Law 38 tool registry".
  - In `check_bash()`: a segment whose command token ends in `ai_tools.py` (directly, or after `python3`/`python`) with first argument `set` → pending ask `registry-write`. `show` stays free.
- **Registration:**
  - `.claude/settings.json` and `install.sh` add a `PreToolUse` entry with matcher `mcp__.*`, and a `PostToolUse` entry with the same matcher. All point at the same command, merged once each, as today.
  - The probe confirmed the `mcp__.*` regex matcher fires.

## Files to change

| File | Change | PR |
|---|---|---|
| `.claude/hooks/ai_approvals.py` | New: `approved()`, `record()`, prune | 1 |
| `tests/test_ai_approvals.py` | New: record/approved, other session, other tool, prune, corrupt file, missing file, busy lock | 1 |
| `.gitignore` | `ai-approvals*` | 1 |
| `.claude/hooks/enforce-laws.py` | `hook_event_name` dispatch, `mcp_tier()`, `check_mcp()`, `record_mcp()`, docstring | 2 |
| `tests/test_enforce_laws.py` | New `McpTierTests` class (cases under Proof) | 2 |
| `.claude/settings.json`, `install.sh` | `mcp__.*` PreToolUse matcher and PostToolUse entry | 2 |
| `.claude/hooks/enforce-laws.py` | Registry and approvals labels, `DF_DATA_FILES`, `registry-write` ask | 3 |
| `tests/test_enforce_laws.py` | Registry protection cases; **edits** `test_data_files_dev_checkouts_and_normal_files_are_free` to drop `ai-tools.json` from its allowed list (it's now protected by design) | 3 |
| `CLAUDE_LAWS.md` | Law 32 asks table: MCP tier rows and `registry-write`; Law 38: replace "Instruction-only for now" with the hook behavior, and with the hook installed the prompt is the tier 3 approval (no chat question first); tier 4 still states the action in chat | 3 |
| `README.md`, `CLAUDE.md` | Law 38 one-liner and the `ai classify` row: classification writes now prompt | 3 |
| `RELEASES.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | v2.26.0, version sync per Law 27 | 3 |

Expected sizes: PR 1 ~150 lines, PR 2 ~300, PR 3 ~200. All under Law 31's 400-line ceiling.

## Order of work

1. **PR 1, store:** write `ai_approvals.py` and its tests. Done when `python3 -m unittest discover -s tests -v` passes.
2. **PR 2, hook:** dispatch, lookup, `check_mcp()`, `record_mcp()`, registration, tests. Done when the unit tests pass and the live probe (below) matches the expected table.
3. **PR 3, registry and laws:** protection checks, the edited test, laws and docs, release and version sync. Done when the tests pass, `bash -n install.sh` passes and `claude plugin validate .` reports no new errors.
4. **Independent review:** a fresh-context Claude subagent reviews the combined diff of all three PRs against this plan and the spec, before PR 3 opens. Findings are fixed in the stack and summarized in PR 3.
5. **Manual check by you** (the one thing a run without a prompt can't show), listed in the deploy steps.

## Proof

- **Tests to add** (`McpTierTests`, payloads run through the hook as a subprocess with `HOME` pointed at a temp dir, as the existing tests do):
  - tier 1 and 2 → no output
  - tier 4 → `ask`, and still `ask` after a `PostToolUse` for the same session
  - unclassified → `ask` `tier3-first-use`
  - tier 3 → `ask`, then `PostToolUse` → allow in the same session, `ask` in another session, `ask` for another tool on the same server, `ask` with no `session_id`
  - a per-tool override lowers or raises one tool
  - an invalid entry or a broken project file counts as tier 3
  - `ai_tools` import failure counts as tier 3
  - a tool name that doesn't split counts as tier 3
  - `PostToolUse` for a tier 2 or tier 4 tool records nothing
  - `PostToolUse` never prints and exits 0, even with a broken payload
  - asks are logged with the three check ids
  - an `ASK_DENIED_MODES` entry turns the MCP ask into a deny
  - registry: Write to `~/.design-forge/ai-tools.json`, a project `.claude/ai-tools.json` or `ai-approvals.jsonl` → `ask`; `python3 …/ai_tools.py set …` → `ask`; `… show …` → allow
- **Existing test edited:** `test_data_files_dev_checkouts_and_normal_files_are_free` (drops `ai-tools.json`; reason above). No test is deleted or loosened.
- **Commands that must pass:** `python3 -m unittest discover -s tests -v` (the Hook Tests CI job), `bash -n install.sh`, `python3 -m json.tool .claude/settings.json`, `claude plugin validate .`.
- **Live probe against the real hook** (PR 2): the stub MCP server from the spec probe, with the worktree's `enforce-laws.py` registered on `mcp__.*`, and the stub classified in the probe folder's `.claude/ai-tools.json`. Expected in a run without a prompt:

  | Stub tier | Tool runs |
  |---|---|
  | 2 | yes |
  | unclassified | no (ask refused) |
  | 4 | no (ask refused) |

  Results go in the PR 2 body.
- **Visual evidence:** none (no UI change). Screenshots: not applicable.

## Risks

- **Prompt burst from the app's own MCP tools** (`ccd_*`, `Claude_Browser`, `visualize`, connectors) right after the update → deploy steps put `ai classify` before `dforge-update`.
- **Latency on every MCP call** (python start, `git rev-parse`, two small JSON reads, ~50–100 ms) → measured once in the probe and noted in PR 2. If it's over 200 ms, cache nothing yet and raise it with you.
- **The lock shared with the block log is busy** → `record()` skips, and the next call asks again. Safe.
- **Subagents share the parent's `session_id`** → an approval covers the session's subagents too. That's the spec's "per session" meaning.
- **Server names containing `__`** → split at the first `__`. A wrong split can only miss a registry entry, which means tier 3: safe.
- **The hook runs from the installed clone, not this checkout** → nothing changes for you until `dforge-update` after merge, and the stack is only active once all three PRs are in.

## Ruled out

- **A Claude-written approval record:** Claude would create approvals (spec decision).
- **Blocking (exit 2) instead of `ask`:** you couldn't approve the call in place.
- **One approvals file per session:** more files to prune, and no simpler to read.
- **Keying approvals on `tool_use_id`:** it isn't known before the call, so it can't carry a session-wide approval.
- **A separate script for `PostToolUse`:** a second command to register and keep in sync. One script dispatching on `hook_event_name` is enough.
- **Caching the registry lookup between calls:** not needed at this size (Law 21). Revisit only if latency is a problem.

## Review outcome (2026-10-05)

The fresh-context review of the combined diff found:

- **Fixed in PR 3:** `ai_tools.py set` behind `bash -c` / `uv run`; a Bash write onto a `.claude` folder; the deny text for MCP calls; which law each registry ask is logged under.
- **Owner decisions, in chat:**
  - Keep "the project entry wins". A committed `.claude/ai-tools.json` can lower a tier; documented in Law 38 as a known limit.
  - A PreToolUse crash on a tier 3 call that is then recorded by PostToolUse is accepted and documented, not engineered around.
- **Noted:** about 140 ms per hook run (python start and `git rev-parse`), so about 280 ms per MCP call for both events; under the 200 ms per-run threshold above. `approved()` ignores age until the next prune.
