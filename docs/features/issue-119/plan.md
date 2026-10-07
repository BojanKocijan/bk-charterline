# Plan — what a tool call may carry, and wider secret patterns (#119)

Spec: [spec.md](spec.md) · Gate tier: Significant · Issue: #119
Work pile: judgment-heavy (patterns that must not block too often; done interactively)
Approved-by: BojanKocijan, 2026-10-07, chat

## Three PRs (Law 31: a fix and a feature never share a PR)

1. **`docs/issue-119-spec`:** this spec and plan only. Base `main`.
2. **`fix/secret-patterns`** (fix, v2.35.0): one shared `find_secret`, the widened patterns, the commit check scanning added lines only, its first tests, and Law 14's list. Fixes the `glpat-` / `xoxb-` bug on its own.
3. **`feat/law-39-tool-inputs`** (feat, v2.36.0): Law 39, the MCP input block, its tests, and the Law 32 / 38 rows. Built on PR 2's `find_secret`, so it opens after PR 2 merges.

Each runs in its own worktree if another session may share the folder (Law 5).

## The shared function (PR 2)

`find_secret(text: str) -> tuple[str, int] | None` returns the kind and the character offset of the first secret, or None. Every regex below is bounded (no nested `*`), so a 1 MB input can't backtrack for long.

| Kind | Regex (Python, `re.ASCII`) |
|---|---|
| private key | `-----BEGIN ((RSA\|EC\|DSA\|OPENSSH\|ENCRYPTED\|PGP) )?PRIVATE KEY( BLOCK)?-----` then, within 300 characters, a run of 40+ of `[A-Za-z0-9+/=]` after a line break (`\n`, `\r\n` or a literal `\n`), so a header with no body passes |
| AWS key ID | `\b(AKIA\|ASIA)[0-9A-Z]{16}\b` |
| GitHub token | `\bgh[pousr]_[A-Za-z0-9]{36,255}\b` and `\bgithub_pat_[A-Za-z0-9_]{60,255}\b` |
| GitLab token | `\bglpat-[A-Za-z0-9_-]{20,}` |
| Slack token | `\bxox[abposr]-[A-Za-z0-9-]{10,}` and `\bxapp-[A-Za-z0-9-]{10,}` |
| Stripe live key | `\b[rs]k_live_[A-Za-z0-9]{20,}` |
| Anthropic key | `\bsk-ant-[A-Za-z0-9_-]{20,}` |
| OpenAI key | `\bsk-(proj\|svcacct\|admin)-[A-Za-z0-9_-]{20,}` |
| Google API key | `\bAIza[0-9A-Za-z_-]{35}\b` |
| Supabase key | `\bsbp_[a-f0-9]{40}\b` and `\bsb_secret_[A-Za-z0-9_-]{20,}` |
| Netlify token | `\bnfp_[A-Za-z0-9]{36,}` |
| npm token | `\bnpm_[A-Za-z0-9]{36}\b` |
| Figma token | `\bfigd_[A-Za-z0-9_-]{30,}` |
| JWT | `\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}` |
| credential assignment | a name containing `api_key`, `apikey`, `secret`, `token`, `password`, `passwd`, `private_key` or `access_key` (any case, `-` or `_`), then `=` or `:`, then a value of 16+ of `[A-Za-z0-9+/=_.~-]`, quoted or not |

**Checked after a match, so these pass:**

- **Placeholders:** the part after the prefix is one repeated character, or the match contains `EXAMPLE`, or the value is `<…>`.
- **References:** the value starts with `${{`, `${`, `$`, `process.env`, `os.environ`, `import.meta.env`.
- **Public or test values:** `sk_test_`, `pk_` (any), `sb_publishable_`.
- **Not keys:** a 40-character hex value (a git SHA), a UUID, `sha1-` / `sha256-` / `sha384-` / `sha512-` integrity strings.
- **A credential assignment needs a mixed value:** at least one letter and one digit, or 32+ characters. That way `token_type: "refresh-token-name"` passes.
- **A JWT whose payload decodes to `"role": "anon"`:** a Supabase anon key, public by design. A payload that doesn't decode still counts as a secret.

**Commit check:** it scans only the **added** lines of `git diff --cached` (lines starting with `+`, not `+++`). Today it scans removed and context lines too, so a commit that *deletes* a leaked secret (the #122 runbook's fix) is blocked. The reason names the kind and the file, never the value: `Blocked (Law 14): the staged diff adds what looks like <kind> in <file>. Remove it before committing.` The `.env` file check stays as it is.

## The MCP input block (PR 3)

- `scan_tool_input(tool_input) -> tuple[str, str] | None` walks every string value in nested dicts and lists (depth ≤ 50) and returns the kind and a field path such as `query.filters[0]`. Keys aren't scanned on their own.
- `main()` calls it for every `mcp__…` tool **before** `check_mcp`, so it blocks at every tier, unclassified included, ahead of any tier prompt. Block reason as in the spec; log: law 39, check `mcp-secret`, the hash of the tool name only (as today).
- Anything that isn't a dict, deeper than 50 levels or that raises, passes (fails open).

## Files

| PR | File | Change |
|---|---|---|
| 2 | `.claude/hooks/enforce-laws.py` | `find_secret` with the table above, replacing `SECRET_PATTERNS`; the commit check scans added lines and names kind and file |
| 2 | `tests/test_enforce_laws.py` | `SecretPatternTests` (unit, per kind and per pass rule) and `CommitSecretTests` (a real repo: staged adds block, a removal passes, `.env` still blocks) |
| 2 | `CLAUDE_LAWS.md` | Law 14: the list matches the hook; "high-entropy strings" goes; version 2.35.0 |
| 2 | `README.md`, `RELEASES.md`, `plugin.json`, `marketplace.json` | Version, release note |
| 3 | `.claude/hooks/enforce-laws.py` | `scan_tool_input` and the call in `main()` |
| 3 | `tests/test_enforce_laws.py` | `McpSecretTests` |
| 3 | `CLAUDE_LAWS.md` | New Law 39 (the spec's table), Law 32's heading and block table (`mcp-secret`), Law 38 links to Law 39; version 2.36.0 |
| 3 | `README.md`, `RELEASES.md`, `plugin.json`, `marketplace.json` | Law 32 summary row, version, release note |

## Order of work

1. PR 1: push, open, merge.
2. PR 2: tests first (all fail today for the new kinds, `glpat-`, `xoxb-` and the removal case), then `find_secret` until they pass, then Law 14 and the release.
3. PR 3 after PR 2 merges: tests first, then `scan_tool_input`, then Law 39 and the release.
4. Each: an independent fresh-context review before it's opened (Significant).

## Proof

- **Fake tokens are built at runtime** in the tests (for example `"gh" + "p_" + "a1B2" * 9`), never written whole in a source file or in these docs. Otherwise the hook's own commit check, and GitHub's push protection, would block the PR that adds them.
- **PR 2 tests:**
  - every kind in the table is caught once
  - each pass rule passes once (placeholder, `EXAMPLE`, a header with no body, each reference form, `sk_test_`, `pk_`, `sb_publishable_`, a git SHA, a UUID, a `sha512-` string, an anon JWT, `token_type: "refresh-token-name"`)
  - a `service_role` JWT is caught
  - the commit check blocks a staged add of `glpat-` and of `xoxb-`, passes a staged *removal* of a secret, and still blocks a staged `.env`
  - a 1 MB input is checked in under a second
- **PR 3 tests:**
  - a secret three levels deep is blocked, and the reason has the field path and not the value
  - it's blocked at tiers 1, 2, 3, 4 and unclassified, before any ask
  - a placeholder passes
  - a non-dict input passes
  - the block log entry reads law 39, `mcp-secret`
- **Mutation checks:** with `find_secret` returning None, and with the scan call removed from `main()`, the new tests fail.
- **By hand** (spec): after PR 3 is installed, an MCP call with a runtime-built fake token is blocked in the app.
- **Commands:** `python3 -m unittest discover -s tests`, `python3 scripts/release_version.py check`, markdownlint.

## Risks

- **False positives teach people to route around the hook.** → Bounded patterns, the pass rules, and the mixed-value rule for assignments; every pass rule has a test. A wrong block is reported with `hook_log.py --false-positive` and fixed with a test.
- **GitHub push protection** may still flag a test file. → Runtime-built tokens, and no full token anywhere in the repo.
- **Scanning only added lines changes today's behavior.** → It only allows removals and context; every added secret is still caught. Named in PR 2's Decision log.
- **JWT decoding** on malformed padding or JSON. → Treated as a secret, never as an error.

## Amendment 1 (2026-10-07) — after the independent review of PR 2

Approved-by: BojanKocijan, 2026-10-07, chat

The fresh-context review of PR 2 (#185) found gaps. Fixes that restore what this plan promised:

- **A key body added under an already-committed header is caught.** Key headers in context lines count, so "every added secret is still caught" holds.
- **The staged diff is read with `--no-color --no-ext-diff`** (and `errors="replace"`). `color.ui=always` or `diff.external` hid every `+` line.
- **The diff reader** takes headers only before a file's first hunk, and splits on `\n` only.
- **Crafted inputs stay fast.** A bare value allows `=` only as base64 padding, and the JWT pattern starts with a lookbehind instead of `\b`. Crafted 1 MB inputs take about 0.15 s.
- **A token inside an assignment reports its own kind.**

Changes to this plan's rules, approved by the owner:

1. **Quoted values may hold symbols** (`"S3cure!Pass#2024xyz"`). Bare values keep the narrow character set.
2. **Dotted lowercase names pass** under a token or secret name: `color.primary.500`, `tls-secret-prod-2024`, `credentials/token_v2.json`. That's lowercase words or digits joined by 2 or more of `.`, `/`, `-`, `_`, no part longer than 15 characters. Never under a password name, since a passphrase looks just like this.
3. **Placeholders** also cover separators and short leading parts (`xoxb-xxxx-xxxx`, `api03-xxxx`), and a body with no digit and no capital letter (`your-api-key-goes-here`).
4. **`rk_test_` passes,** as a Stripe test key.
5. **Removing a committed `.env` isn't blocked:** the `.env` check ignores staged deletions (`--diff-filter=d`).

Follow-ups, outside #119:

- `scripts/ai_tools.py` keeps its own older pattern copy.
- A single `git add X && git commit` call checks the staging area as it was before the add.

## Ruled out

- An entropy check (decision 5).
- Scanning tool outputs, encoded content and Bash network commands (out of scope in the spec; a follow-up issue).
- One PR for everything: it mixes a fix with a feature and would pass 400 lines.
