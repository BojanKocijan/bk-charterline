# Spec — the hook enforces Law 38 tier 3 and 4 approvals for MCP calls (#138)

Intent: [#138](https://github.com/BojanKocijan/design-forge/issues/138) (the issue is the intent) · Roadmap: #123 · Builds on: #115 (Law 38), #117 (`ask`)
Design: none (no UI; hook behavior and the app's permission prompt)
Approved-by: BojanKocijan, 2026-10-05, chat

## Decisions already taken (owner, 2026-10-05)

- **Use the app's permission prompt (`ask`), not a Claude-written approval record.** Your click in the prompt is the approval. Claude, tool output and file content can't create one.

## Live probe (2026-10-05, Claude Code 2.1.289)

A stub MCP server with one harmless tool (`mcp__stub__ping`) ran headless (`claude -p`) with logging `PreToolUse` and `PostToolUse` hooks on `mcp__.*`. Headless has no prompt, so an `ask` shows up as a refusal.

| Hook answer | Allow rule for the tool | Mode | Tool ran |
|---|---|---|---|
| none | `permissions.allow` | default | yes |
| `ask` | `permissions.allow` | default | **no** |
| `ask` | `--allowedTools` | default | **no** |
| `ask` | `permissions.allow` | bypassPermissions | **no** |
| `ask` | `permissions.allow` | auto | **no** |
| `ask` | none | default | no |
| none | none | auto | **yes, with no prompt** |
| none | none | default | no (the app's own prompt) |

What this settles:

1. **A hook `ask` wins over allow rules and every mode tested.** An "always allow" rule or bypass mode can't skip it.
2. **In auto mode an MCP call runs today with no prompt at all.** That's the gap this hook closes.
3. **`PostToolUse` carries `session_id` and `tool_use_id`** (the same id as the matching `PreToolUse`), and it fires **only when the tool actually ran**. A refused call produces no `PostToolUse`.

Still to verify by hand before release: in an interactive session, the `ask` shows a prompt and approving it runs the call. Headless can't show a prompt.

## Behavior

The Law 32 hook gets a third matcher, `mcp__.*`, and a new `PostToolUse` entry on the same matcher.

### Tier lookup

- `mcp__<server>__<tool>` maps to the registry key `mcp:<server>`, split at the first `__` after `mcp__`. The tier comes from `scripts/ai_tools.py` (`lookup()` then `tier_for()`), with the project being the git top level of the payload's `cwd`. Per-tool override, else server tier, else **3**.
- Unclassified, invalid, a broken project file, or **any lookup error counts as tier 3**. A mistake never lowers a tier (Law 38). This deliberately replaces #138's "fail open on any lookup error".

### Tier 1 and 2: no change

The hook returns nothing and the app's normal permission flow applies.

### Tier 3: ask once per session per tool

- **First call of that tool in the session:** `ask`, check id `tier3-first-use`. The reason names the tool, its tier and owner, or says it's unclassified and suggests `ai classify`.
- **After a tier 3 call runs**, the `PostToolUse` hook records `session_id` + full tool name in a local approvals file. Later calls of that tool in the same session pass.
- **Declined:** nothing is recorded, so the next call asks again.
- **Approved but the call failed:** `PostToolUse` doesn't fire, so the next call asks again. Safe, slightly noisy.
- **Per tool, not per server:** approving `mcp__x__search` doesn't approve `mcp__x__create`.
- The record is keyed on the session, so it survives context compaction (an improvement over approvals held in Claude's context). `/clear` starts a new session and asks again. A resumed session that keeps its id keeps its approvals: it's the same session.
- `PostToolUse` records only calls whose tier is 3 at that moment, so a tool reclassified upward mid-session still asks.

### Tier 4: ask on every call

- Every call: `ask`, check id `tier4-unapproved`. Nothing is recorded, so an approval never carries over. The prompt shows the call's arguments (the SQL, the target).
- Choosing "don't ask again" in the prompt can't weaken this: the probe shows the hook's `ask` wins over allow rules.

### The approvals file

- `~/.design-forge/ai-approvals.jsonl`, gitignored, one line per approved tool per session: time, `session_id`, tool name. No arguments, no output.
- Written only by the `PostToolUse` hook, under the same short lock as the block log. Lines older than 7 days are pruned on write.
- **It stays a guardrail file.** It's not added to the data-file exemptions from #117, so an Edit, Write or Bash write to it by Claude asks you first.

### Tiers can't be lowered without your click either

Lowering a tier is the same as approving in advance, so the registry gets the same protection:

- The personal registry `~/.design-forge/ai-tools.json` leaves the #117 data-file exemptions, and any project's `.claude/ai-tools.json` joins the protected set. Edits to either ask.
- A Bash command that runs `ai_tools.py set` asks, check id `registry-write`. `ai classify` still proposes in chat. Each approved write now also shows the prompt.

### Unchanged

- **Logging:** each `ask` goes to the block log as type `ask` with its check id (#113). `hook log` counts them.
- **Fail open only on a hook crash:** an unparseable payload passes, as Law 32 does today. A missing or unreadable approvals file means "not approved yet", so it asks. A missing `session_id` means no session memory, so tier 3 asks every call.
- **Permission modes:** `ASK_DENIED_MODES` applies as today. The probe found no mode that skips the prompt.
- **A block still wins over an ask.** The hook's Bash and file-edit checks are untouched.
- **`disarm` doesn't lift it:** the hook doesn't know about `disarm`.

## Acceptance criteria

- [ ] Tier 4 MCP calls return `ask` on every call, and nothing is recorded for them.
- [ ] Tier 3 MCP calls return `ask` until one has run in that session. After a `PostToolUse` record for that session and tool, they pass. A different session, a different tool on the same server, or a missing `session_id` asks again.
- [ ] Tier 1 and 2 calls get no hook output.
- [ ] Unclassified tools, invalid entries, a broken project registry and a lookup exception all behave as tier 3. Per-tool overrides apply.
- [ ] `PostToolUse` records only tier 3 calls and never stores arguments or output. Lines older than 7 days are pruned.
- [ ] Edits and Bash writes to `ai-approvals.jsonl`, `~/.design-forge/ai-tools.json` and a project's `.claude/ai-tools.json` ask, and so does `ai_tools.py set`. `ai_tools.py show` and `ai inventory` don't.
- [ ] Asks are logged with check ids `tier3-first-use`, `tier4-unapproved` and `registry-write`.
- [ ] `install.sh` registers the `mcp__.*` `PreToolUse` matcher and the `PostToolUse` entry, merging as today; the repo's `.claude/settings.json` matches. `.gitignore` covers `ai-approvals*`.
- [ ] Unit tests for each row above, plus the probe re-run against the real hook, recorded in the PR. Interactive prompt checked by hand once.
- [ ] Law 32 and Law 38 text updated (Law 38 is no longer "instruction-only" for MCP tools), `RELEASES.md` entry, minor version bump (2.26.0), version sync per Law 27.
- [ ] Independent review by a fresh-context Claude subagent before merge (Significant).

## Policy check

- Component library, accessibility, copy: not applicable (no UI). Prompt reasons follow the hook's style: name the law and the tool, say what to do (approve, or `ai classify`).
- **Conflicts flagged for the owner:**
  1. **Claude's own app tools count as MCP tools.** `mcp__ccd_session__*`, `mcp__Claude_Browser__*`, `mcp__visualize__*` and the like are unclassified today, so each asks once per session until you classify them with `ai classify` (tier 1 or 2 makes them silent). Running `ai classify` before release avoids a burst of prompts.
  2. **Double asking for tier 3.** Law 38 has Claude ask in chat, and now the app prompts too. Proposal: with the hook installed, the prompt is the tier 3 approval and Claude doesn't ask in chat first. For tier 4, Claude still states the exact action in chat before the call, and the prompt approves it. On claude.ai web (no hook), the chat question stays.
  3. **`ai classify` writes now need a click each.** That's intended: lowering a tier is an approval in advance.
  4. **Bash write detection stays string-based.** A script can evade it, for example `python3 -c "open(...).write(...)"` on the approvals file. This is a backstop, not a sandbox; Law 32 already says so.

## Out of scope

- Desktop extensions and plugins that aren't MCP tools. Law 38 covers them by instruction only.
- Enforcing anything on claude.ai web (no hooks there).
- Per-argument approval for tier 4 (for example, approving one SQL statement but not another). The prompt already shows the arguments for each call.
- A command to list or revoke a session's tier 3 approvals. `/clear` or a new session resets them.
