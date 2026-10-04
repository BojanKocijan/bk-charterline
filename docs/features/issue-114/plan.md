# Plan — `ai inventory`

Spec: [#114](https://github.com/BojanKocijan/design-forge/issues/114) (the issue is the spec) · Gate tier: Standard · Branch: `feat/ai-inventory` · Issue: #114 · Roadmap: #123
Work pile: delegable (one stdlib script plus docs, verifiable with fixture tests)
Approved-by: <pending> (revision 2; revision 1 approved by BojanKocijan, 2026-10-05, chat)

## Revision 2 — why

Built and measured: the script is 302 lines and its tests 173, so the script and tests alone are 475 lines. Revision 1's fallback split (script and tests first, then docs) would still go over the 400-line ceiling. The work is split by source instead, into two PRs that each ship something whole. Both target `main` and are stacked by commits.

1. **PR A — core and MCP servers** (about 360 lines): the collector framework, Markdown output, first-seen state, **new** and **removed** marking, secret handling, and the MCP sources (user, local, project, desktop, extensions, `--session`). Tests: MCP and extension listing, no secrets in the output, empty home, broken file, idempotency, `--session` carry-over. No trigger yet.
2. **PR B — remaining sources, trigger and release** (about 170 lines): plugins, skills, agents, hooks and permission rules, plus their tests; the `ai inventory` trigger rows, `.gitignore`, `RELEASES.md` and the version bump to v2.23.0.

Nothing else in the plan changes.

## What was found on this machine

- **CLI MCP servers** live in `~/.claude.json` under `mcpServers` (user scope) and `projects.<path>.mcpServers` (local scope). Project-scope servers are in each repo's `.mcp.json`, with per-project `enabledMcpjsonServers` and `disabledMcpjsonServers` lists. None are configured here today.
- **Desktop app**: `~/Library/Application Support/Claude/claude_desktop_config.json` (`mcpServers`, none today), plus desktop extensions in `Claude Extensions/*/manifest.json`. On Linux the folder is `~/.config/Claude`. The same folder holds `config.json` with OAuth token caches, which **must never be read**.
- **claude.ai account connectors** (mail, cloud drive, a database with `execute_sql`, docs, …) are attached to the account on the server. **No local file lists them.** Only the session can see them, through its own `mcp__<server>__*` tools.
- **Plugins**: `enabledPlugins` in the settings files, `~/.claude/plugins/installed_plugins.json` when it exists, and the plugin ids in `~/.claude.json` → `pluginUsage` (desktop inline plugins such as `engineering@inline`).
- **Skills and agents**: `~/.claude/skills/*`, `~/.claude/agents/*.md` and the project's `.claude/skills` and `.claude/agents`. Design Forge's own entries are symlinks into `~/.design-forge`.
- **Hooks and permissions**: `hooks` and `permissions.allow` / `deny` in `~/.claude/settings.json`, `<project>/.claude/settings.json` and `settings.local.json`.

## Behavior

- **`scripts/ai_inventory.py [--project PATH] [--session NAME ...]`**, stdlib only. `--project` defaults to the current directory. `--session` takes the MCP server names Claude sees in its own tool list, which covers account connectors.
- **What it writes:** a local `~/.design-forge/ai-inventory.md`, also printed to stdout, with one table per type: MCP servers, desktop extensions, plugins, skills, agents, hooks and permission rules.
  - Every row has a name, scope (user / local / project / desktop / session), source file and first-seen date.
  - Rows new since the last run are marked **new**.
  - A last section lists the files it couldn't parse.
- **First-seen dates** are kept in `~/.design-forge/ai-inventory.json`, keyed by type, scope and name. Re-running is idempotent: dates are kept, and an item that disappears is listed once as **removed**, then dropped.
- **Secrets are never read into the output, only names:**
  - MCP servers record name, transport (`stdio` / `http` / `sse`), the executable's basename for `stdio`, and the URL **host** only for `http` / `sse`.
  - Never `args`, `env`, `headers`, URL paths or query strings.
  - Hooks record event, matcher and the command's script basename, never its arguments.
  - Permission rules are listed as written, except that any rule matching the Law 14 secret patterns is shown as `[masked]`.
  - The desktop `config.json`, cookies, token files and any `*token*` / `*cred*` file are never opened.
- **Fails soft:** a missing file is skipped; a broken file is listed under "Couldn't parse" and the run continues. Exit code 0 unless the inventory itself can't be written.
- **`ai inventory`**, a new trigger:
  1. Claude runs the script with `--project <cwd>`, passing `--session` the MCP server names from its own tool list.
  2. Claude reports the totals and the **new** rows.
  3. Classifying tools (risk tier and owner) is #115, not this PR.
- `ai-inventory*` is added to `.gitignore`, because the files sit at the root of the `~/.design-forge` clone.

## Files to change

| File | Change |
|---|---|
| `scripts/ai_inventory.py` (new) | The collector, the Markdown writer and the first-seen state |
| `tests/test_ai_inventory.py` (new) | Fixture tests with a temp `HOME` and a temp project (see Proof) |
| `.gitignore` | `ai-inventory*` |
| `CLAUDE.md` | `ai inventory` row in the trigger table |
| `README.md` | `ai inventory` row in the trigger table |
| `RELEASES.md` | v2.23.0 entry |
| `CLAUDE_LAWS.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Version 2.23.0 (new feature) |

That's 9 files, estimated at about 390 changed lines. **This plan ships as its own PR first.** Following the stacked-PR rule, every PR in the series targets `main`. If the implementation PR goes over 400 lines, I stop and split it: first the script and its tests, then the trigger, docs and version.

## Order of work

1. Open the plan PR (this file, base `main`) once approved.
2. Write the collector and secret-safe writer. Done when the fixture tests pass.
3. Add the first-seen state, **new** and **removed** marking. Done when the idempotency tests pass.
4. Trigger rows, `.gitignore`, version, `RELEASES.md`. Done when markdownlint passes and both manifests parse.
5. Measure the diff, split if needed, and open the PR(s) against `main`. Done when CI is green.

## Proof

- **Tests to add** in `tests/test_ai_inventory.py`, each with a temp `HOME` and a temp project:
  - **Every source is listed:** user, local and project MCP servers; a desktop extension; enabled plugins and `pluginUsage` ids; a symlinked skill (with its link target); an agent; hooks from user and project scope; permission rules.
  - **No secret value appears anywhere in the output** (Markdown and JSON). The fixtures carry `env` values, `headers`, a URL with a token in its path and query, `args` containing `--api-key sk-…`, and a permission rule containing a `ghp_…` token.
  - **Missing files:** an empty `HOME` with no project writes a valid inventory with empty sections.
  - **A broken file:** a broken `~/.claude.json` is listed under "Couldn't parse" and everything else is still collected.
  - **Idempotency:** two runs keep the first-seen dates and mark nothing **new**. Adding a server marks only it **new**. Removing it lists it once as **removed**, then drops it.
  - **`--session`:** names passed with `--session` appear with scope `session`.
  - **No forbidden files are opened:** the desktop `config.json` fixture holds a marker string that must never show up in the output.
- **Existing tests:** none edited.
- **Commands that must pass:** `python3 -m unittest discover -s tests -v`, `python3 -m py_compile scripts/ai_inventory.py`, markdownlint.
- **By hand after merge:** `ai inventory` in a real session. Check that the connectors show up through `--session` and that no secret appears.
- **Visual evidence:** none (no UI). The PR body carries `Screenshots: not applicable`.

## Risks

- **Claude Code's config layout can change between versions.** → Each source is a small reader that fails soft, and unknown shapes go to "Couldn't parse". The fixtures document the shapes this version reads.
- **Account connectors depend on Claude passing `--session`.** → The trigger text requires it. The Markdown says "session servers not provided" when the flag is missing, so a gap shows up instead of looking like "none".
- **Connector server names can be opaque ids** (for example a UUID). → They're recorded as seen. Giving them friendly names is #115's job (owner and tier).
- **Paths reveal local folder names.** → The files stay local and gitignored.

## Ruled out

- **Reading `args`, `env` or `headers` and masking secrets inside them.** Masking can miss a format. Not reading them at all can't leak them.
- **Querying claude.ai for the connector list.** It needs auth and network, and the session already knows its servers.
- **Putting the script under `.claude/hooks/`.** It isn't a hook. `scripts/` sits at the plugin root, which Law 27 allows.
- **A `dforge` CLI on the `PATH`.** It needs `install.sh` changes; same reasoning as #113.
