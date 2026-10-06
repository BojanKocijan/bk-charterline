# Plan — the hook asks before Netlify or Vercel CLI commands that change a live site (#173)

Spec: [#173](https://github.com/BojanKocijan/design-forge/issues/173) (the issue) · Gate tier: Standard · Branch: `feat/hook-ask-hosting-cli` · Issue: #173
Work pile: delegable (one hook check, specified, machine-verifiable), done in this session
Approved-by: BojanKocijan, 2026-10-06, chat

## Sources (verified, not from memory)

- **Netlify:** `netlify --help` and each group's `--help`, netlify-cli 27.11.2 (installed). `netlify api` methods from the bundled OpenAPI spec (`@netlify/open-api/dist/swagger.json`): of 181 operations, every one named `get…`, `list…`, `show…` or `search…` is a `GET`, and every other one writes.
- **Vercel:** not installed. Commands, aliases and global options from the official docs: `vercel.com/docs/cli`, `/docs/cli/global-options`, `/docs/cli/deploy`, `/docs/cli/env` (read 2026-10-06). Bare `vercel` deploys ("the only command that operates without a subcommand").

## The rule: a short free list, everything else asks

The issue lists write commands to catch. Vercel alone has over 60 commands with mixed reads and writes (`buy`, `tokens add`, `firewall publish`, `cache purge`, `domains buy`), Netlify has `database reset` and `database migrations apply`, and new ones arrive with each CLI release. So the hook inverts the list: **only commands verified as reads or local-only are free; anything else asks, including commands it doesn't know.** An unknown command costs one prompt; a missed write could change production.

**Free — Netlify** (`netlify`, `ntl`):

- bare `netlify` (prints help), `help`, any `--help` / `-h` / `--version` / `-v`
- reads: `logs` and `log`, `logs:*`; `status`, `status:hooks`; `watch`; `database status` / `db status`; any `<group>:list|get|show|search` except the `env` group; `api --list` and `api <method>` where the method starts with `get`, `list`, `show` or `search`
- local only: `dev`, `serve`, `build`, `functions:*` / `function:*` (all local per their help), `link`, `unlink`, `open`, `open:site`, `open:admin`, `completion`, `recipes`, `recipes:list`

**Free — Vercel** (`vercel`, `vc`):

- `help`, any `--help` / `-h` / `--version` / `-v`
- reads: `whoami`, `ls`, `list`, `inspect`, `logs`, `activity`, `alerts`, `metrics`, `usage`, `contract`, `security`, `bisect`; any `<group> ls|list|inspect|get|status` except the `env` group (for example `dns ls`, `promote status`, `rollback status`, `webhooks get`)
- local only: `dev`, `build`, `open`, `init`

**Asks, among others:** bare `vercel` and `vercel <path>` (both deploy), `deploy`, `promote`, `rollback`, `redeploy`, `remove`, `alias set`, `domains add|buy`, `dns add|rm`, `cache purge`, `firewall publish`, `tokens add`, `buy`, `api` (Vercel: any request), `curl`, `link`, `pull`; Netlify `deploy`, `init`, `create`, `claim`, `sites:create|delete`, `blobs:set|delete`, `agents:create|stop`, `database migrations apply`, `database reset`, `api deleteSite` and every other write method, `login`, `logout`, `switch`, `dev:exec`.

**The `env` group always asks** on both CLIs (`netlify env:list`, `env:get`, `vercel env ls|pull|run`), and so does `vercel pull`: they change env vars or copy their values out of the provider, which are the site's secrets (Law 14).

## Files to change

| File | Change |
|---|---|
| `.claude/hooks/enforce-laws.py` | New `hosting_cli_write(segment) -> str \| None`: the command as shown in the prompt (`vercel deploy`, `netlify api deleteSite`) when it isn't free, else None. Called in `check_bash`'s per-segment loop, held as `pending_ask` so blocks still win. Check id `hosting-write`, reason names Law 38 |
| `tests/test_enforce_laws.py` | New `HostingCliTests(HookRunner, unittest.TestCase)` (see Proof) |
| `CLAUDE_LAWS.md` | Law 38: a "Hosting CLIs" bullet (write commands count as tier 4; the hook asks on every call). Law 32 asks table: a row. Version 2.32.0 |
| `knowledge/INCIDENT_GUIDE.md` | §1.1: "the hook doesn't check this yet (#173)" becomes "the Law 32 hook asks before anything else (#173)" |
| `README.md` | The Law 32 summary row, version badge |
| `RELEASES.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | v2.32.0, version sync |
| `docs/features/issue-173/plan.md` | This plan |

## How the check reads a command

1. **Tokenise** (`shlex`); unbalanced quotes → None (fail open). A nested `bash|sh|zsh|$SHELL -c "<inner>"` is checked segment by segment.
2. **Strip** `VAR=value` prefixes and wrappers (`strip_command_prefix`), so `NETLIFY_AUTH_TOKEN=… netlify deploy` is seen.
3. **Unwrap runners:** `npx`, `bunx`, `bun x`, `pnpm dlx|exec`, `pnpm <bin>`, `yarn dlx|exec`, `yarn <bin>`, `npm exec|x [--]`, skipping their flags (`-y`, `--yes`, `-p|--package <pkg>`). The package or binary is matched after dropping `@version`: `netlify-cli`, `netlify`, `ntl` → Netlify; `vercel`, `vc` → Vercel. Full paths (`./node_modules/.bin/vercel`) match by basename.
4. **Skip global options**, taking their values: Vercel `--cwd`, `--scope|-S`, `--team|-T`, `--token|-t`, `--project`, `--local-config|-A`, `--global-config|-Q` (also the `--opt=value` form); Netlify `--auth`, `--filter`. So `vercel --scope ls deploy` is a deploy, not a read.
5. **Find the command:** Netlify `group:sub` or `group sub`; Vercel `command [sub]`. Help or version flags anywhere → free.
6. **Decide** with the lists above.

## Order of work

1. `hosting_cli_write` and the wiring. Done when the new tests pass.
2. Laws, INCIDENT_GUIDE, README, release. Done when `release_version.py check` prints `2.32.0` and markdownlint is clean.

## Proof

- **Tests to add:**
  - **Ask:** `netlify deploy --prod`, `ntl deploy`, `netlify env:set KEY v`, `netlify env:list`, `netlify api rollbackSiteDeploy --data '{}'`, `netlify database migrations apply`, `netlify db reset`, `netlify sites:delete`, `netlify login`; `vercel`, `vercel --prod`, `vc ./site`, `vercel deploy`, `vercel promote dpl_1`, `vercel rollback`, `vercel env pull`, `vercel env ls`, `vercel pull`, `vercel dns rm rec_1`, `vercel --scope ls deploy`, `vercel -S team`, `vercel api /v2/user`; runners `npx netlify-cli deploy`, `npx -y vercel@latest --prod`, `pnpm dlx vercel deploy`, `yarn netlify deploy`, `bunx vercel`, `npm exec -- netlify deploy`, `npx -p netlify-cli netlify deploy`; `NETLIFY_AUTH_TOKEN=x netlify deploy`, `bash -c "netlify deploy"`, `cd site && vercel --prod`, an unknown command (`netlify frobnicate`, `vercel frobnicate`).
  - **Free:** `netlify`, `netlify --help`, `netlify deploy --help`, `netlify -v`, `netlify logs --since 1h --json`, `netlify status --json`, `netlify watch`, `netlify sites:list`, `netlify blobs:get k`, `netlify api listSiteDeploys`, `netlify api getSite`, `netlify api --list`, `netlify db status`, `netlify dev`, `netlify build`, `netlify functions:invoke hello`, `netlify link`; `vercel --version`, `vercel whoami`, `vercel ls`, `vercel inspect x`, `vercel logs x`, `vercel dns ls`, `vercel promote status`, `vercel dev`, `vercel build`, `vercel --scope team ls`, `vercel --token=x whoami`; `npx vercel whoami`; text that only mentions them (`echo netlify deploy`, `git commit -m "docs: vercel deploy"`, `grep vercel package.json`).
  - The ask is logged as Law 38 `hosting-write`; a block still wins (`netlify deploy && git push` on the default branch blocks); unbalanced quotes fail open.
- **Tests touched:** none.
- **Commands:** `python3 -m unittest discover -s tests`, `python3 scripts/release_version.py check`, markdownlint.
- **Visual evidence:** none (no UI). `Screenshots: not applicable`.

## Risks

- **A new read command asks** after a CLI release. → One click; add it to the free list with a test.
- **A future CLI turns a free name into a write** (for example a `logs` subcommand that deletes). → Low; the free list is short and each entry is a documented read. Re-check the lists when a CLI's major version changes.
- **Scripts that wrap a CLI** (`npm run deploy`, a Makefile target) are invisible to string matching. → Out of scope (issue constraint); Law 2's announcement still covers them.
- **Prompt fatigue on `vercel env ls` / `vercel pull`** in a Vercel workflow. → Accepted for secrets; revisit if it bites.

## Ruled out

- **The issue's write-list only:** it misses every write the list doesn't name, on two CLIs that add commands often.
- **Asking once per session (tier 3 style):** a deploy or rollback approved at 10:00 shouldn't cover one at 16:00. Every call asks, nothing is stored, as for tier 4.
- **Parsing `vercel api` flags to allow GETs:** a beta command whose flags aren't settled; one prompt per call is cheap.
- **Sharing the nested-shell code with `moves_installed_clone`:** a refactor of #170's code belongs in its own PR (Law 31).
