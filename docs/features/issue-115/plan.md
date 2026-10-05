# Plan — risk tier and owner for every AI tool (Law 38)

Spec: [spec.md](./spec.md) (approved) · Gate tier: Significant · Branch: `feat/ai-tool-tiers` · Issue: #115 · Roadmap: #123
Work pile: judgment-heavy for the law text; delegable for the registry and inventory code
Approved-by: <pending>

## Files to change — four PRs, all targeting `main`, stacked by commits

All four PRs target `main`, never another feature branch, so they can be merged in a row without stranding anything.

**PR 0 — artifacts** (2 files): `docs/features/issue-115/spec.md` and this `plan.md`.

**PR A — registry module** (3 files, about 260 lines)

| File | Change |
|---|---|
| `scripts/ai_tools.py` (new) | Registry code and CLI. `load(path)` returns `(tools, problem)`. `lookup(kind, name, project)` returns the entry, project file first. `tier_for(entry, tool)` checks the override, then the server's tier. `set_entry(path, key, tier, owner, label, note, overrides)` validates (tier 1–4, key `<kind>:<name>` with kind `mcp`, `extension` or `plugin`, owner not empty) and writes atomically through a temp file plus `os.replace`, keeping other entries and unknown fields. CLI: `set` (`--personal` or `--project PATH`) and `show KEY`. Stdlib only. |
| `tests/test_ai_tools.py` (new) | See Proof. |
| `.gitignore` | `/ai-tools.json`, anchored to the root, so the personal file in the `~/.design-forge` clone is ignored but a project's `.claude/ai-tools.json` never is. |

**PR B — inventory shows tiers** (2 files, about 120 lines)

| File | Change |
|---|---|
| `scripts/ai_inventory.py` | For MCP, extension and plugin rows: look up `mcp:<name>` (and so on) through `ai_tools.lookup`. Add **Tier** and **Owner** columns after Detail. Overrides go into Detail (`send_message → 3`). Unclassified rows read `unclassified (tier 3)`. The summary line adds `N unclassified`. A broken registry goes under "Couldn't parse". Skills, agents, hooks and permissions keep today's columns. |
| `tests/test_ai_inventory.py` | New cases (see Proof). Existing assertions keep working because the new columns come after Detail. |

**PR C — Law 38, triggers, release** (6 files, about 80 lines)

| File | Change |
|---|---|
| `CLAUDE_LAWS.md` | **Law 38**: the tier table, the runtime rules (tier 3 once per session per tool, tier 4 every call with the exact action, unclassified means 3), owner, registry precedence, "a tier only adds friction", "only the user in chat approves". Version 2.24.0. |
| `CLAUDE.md` | An `ai classify` trigger row (propose from tool names, the user approves each one, write with `ai_tools.py set`). The `ai inventory` row mentions tiers. |
| `README.md` | Trigger table: `ai classify`; `ai inventory` mentions tiers and owners. |
| `RELEASES.md` | v2.24.0 entry |
| `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Version 2.24.0 |

Also part of the work: open the **follow-up issue for hook enforcement of tier 4** and link it from Law 38 and the roadmap (#123).

## Order of work

1. Commit this plan; owner approves.
2. PR A: `ai_tools.py` and its tests. Done when the tests pass.
3. PR B: the inventory integration and its tests. Done when the full suite passes.
4. PR C: Law 38, triggers, README, version, release; open the follow-up issue. Done when markdownlint, the manifests and `claude plugin validate` pass.
5. **Independent review:** a fresh-context Claude subagent that didn't write the code reviews the combined diff (A + B + C) against `spec.md`. Its findings are fixed or answered in the PRs. AI review is input, never a verdict; you merge.
6. Open the four PRs against `main` with Intake blocks and the review summary. Done when CI is green.

## Proof

- **`tests/test_ai_tools.py`**, each with a temp `HOME` and project:
  - `set` writes a new entry; a second `set` on another key keeps the first, and keeps unknown fields and a hand-added `note`.
  - Validation: tier 0 or 5, an unknown kind or a missing owner each exit non-zero and leave the file unchanged.
  - Precedence: a project entry beats a personal entry for the same key; a personal entry is used when the project has none.
  - `tier_for`: an override beats the server tier; an unknown tool falls back to the server tier; no entry means 3.
  - A broken JSON file: `load` reports a problem and returns no entries; `set` refuses to overwrite a broken file rather than losing it.
  - The write is atomic: no temp file is left behind, and the file is valid JSON after every `set`.
- **`tests/test_ai_inventory.py`**, new cases:
  - A classified MCP server shows its tier and owner; an override shows in Detail.
  - An unclassified server shows `unclassified (tier 3)`, and the summary counts it.
  - A project entry wins over a personal one in the output.
  - A broken `ai-tools.json` is listed under "Couldn't parse".
  - The existing secret tests still pass.
- **Existing tests:** none edited.
- **Commands that must pass:** `python3 -m unittest discover -s tests -v`, `python3 -m py_compile scripts/*.py`, markdownlint, `python3 -m json.tool` on the manifests, `claude plugin validate .claude-plugin/plugin.json`.
- **By hand after merge and `dforge-update`:** say `ai classify`, approve a few proposals, then `ai inventory` shows the tiers. A tier 3 call (for example creating a draft) triggers the one-time question.
- **Visual evidence:** none (no UI). PR bodies carry `Screenshots: not applicable`.

## Risks

- **Law 38 is instruction-only until the follow-up hook lands**, so a long session or a compacted context can miss a question. → Unclassified defaults to 3, so a miss tends toward caution. The follow-up issue makes tier 4 mechanical.
- **Connector names can change** (for example a UUID server id after reconnecting), leaving an entry orphaned. → `ai inventory` shows the new name as unclassified, and `ai classify` picks it up. Orphans are harmless.
- **A hand-edited registry with a mistake** (tier "high", a duplicate key). → `load` treats an invalid entry as unclassified and reports it, never as tier 1.
- **Size:** about 460 lines in total, so it's split into PRs A, B and C, each under 400 lines and 10 files.

## Ruled out

- **YAML for the registry:** not in Python's stdlib, and the scripts stay dependency-free.
- **The tier heuristics in code:** only the session sees connector tool names, so Claude proposes and the user approves. The script just stores what was approved.
- **Writing the registry from `ai_inventory.py`:** the inventory stays read-only, and writes go through one validated helper.
- **One PR:** 11 files and about 460 lines, over both Law 31 ceilings.
