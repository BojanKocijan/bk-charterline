# Spec — what a tool call may carry, and wider secret patterns (#119)

Intent: [#119](https://github.com/BojanKocijan/design-forge/issues/119) (the issue and its two scope comments are the intent) · Roadmap: #123 · Builds on: #115 (Law 38), #138 (MCP hook), #122 (leak runbook)
Design: none (no UI; law text and hook behavior)
Approved-by: <pending>

## Decisions already taken (owner, 2026-10-06)

- **Law text plus a hook check.** The hook blocks an MCP call whose input matches a secret pattern. Personal data stays a rule in the law only.
- **Widen the patterns.** The commit check (Law 14) and the MCP check share one list.
- **Order:** code starts after #182 merges (#181 → #182 → #119). This spec and the plan can land before that.

## What's wrong today

A test of the hook's `SECRET_PATTERNS` (2026-10-06) against common key shapes:

| Shape | Caught today |
|---|---|
| `ghp_…` with 36 characters, `api_key = "…"` | yes |
| GitLab `glpat-…`, Slack `xoxb-…` | **no**: Law 14 names them, but the pattern expects `_` where these tokens use `-` |
| GitHub `ghs_` / `ghu_` / `ghr_`, Stripe `sk_live_`, Anthropic `sk-ant-`, a bare JWT, `-----BEGIN ENCRYPTED PRIVATE KEY-----` | **no** |
| `SECRET_KEY=…` or `client_secret: "…"` (the keyword is part of a longer name) | **no** |

Law 14 also promises a "high-entropy strings" check that the hook doesn't run. Nothing tests the commit secret check at all.

## Behavior

### 1. New Law 39: what a tool call may carry

Law 38 says how risky a tool is; Law 39 says what may go into it. It covers every MCP call (claude.ai connectors included), plugins and extensions.

| Data | Tier 1–2 (local, reads) | Tier 3–4 (writes, production) |
|---|---|---|
| **Secrets:** keys, tokens, passwords, private keys, `.env` content | **Never.** The hook blocks it | **Never.** The hook blocks it |
| **Personal or customer data:** real names, emails, phone numbers, addresses, IPs, account or user IDs, customer records | Only the values the read needs, such as one filter value | **Ask in chat first:** name the tool, the fields and why. A yes covers that call only |
| **Production database writes** | — | Law 35: Claude hands over the SQL and never runs it |
| **Everything else** (code, mock data, docs) | Allowed | Allowed when the task needs it; the Law 38 tier prompts still apply |

A blocked secret never left the machine. If the value is a placeholder, Claude replaces it with `<token>` and calls again. If it's real, Claude tells the owner and doesn't send it. INCIDENT_GUIDE §9 applies only when a secret did get out.

### 2. Hook: block secrets in MCP call inputs

- **Where:** at the start of `check_mcp`, before the tier lookup, so the block wins over any tier ask. It runs at **every** tier, unclassified included: a secret sent to a read tool as a search query leaks too.
- **What's scanned:** every string value in `tool_input`, walking nested objects and lists. Keys aren't scanned on their own (a `page_token` field is normal), but a string value is scanned whole, so code or a document holding `api_key = "…"` is caught.
- **Block reason:** `Blocked (Law 39): the input to <tool> contains what looks like <kind> in <field path>. Secrets never go to a connector. Replace a placeholder with <token>; if it's real, tell the owner.` It never contains the value.
- **Block log:** law 39, check `mcp-secret`. The log hashes only the tool name, as it does for every MCP call today.
- **Fails open** when the input can't be walked. An input of 1 MB is checked in well under a second.

### 3. One shared pattern list, widened

One function (for example `find_secret(text) -> kind | None`) serves both the commit check and the MCP check. The commit check's reason also names the kind.

**Add** (exact regexes and minimum lengths in the plan):

- Private key blocks of any type: RSA, EC, DSA, OpenSSH, PKCS#8, `ENCRYPTED`, `PGP PRIVATE KEY BLOCK`.
- AWS `AKIA…` and `ASIA…` access key IDs.
- GitHub `ghp_`, `gho_`, `ghu_`, `ghs_`, `ghr_`, `github_pat_`; GitLab `glpat-`; Slack `xox[abposr]-`, `xapp-`.
- Stripe live keys `sk_live_`, `rk_live_`; Anthropic `sk-ant-`; OpenAI `sk-proj-`, `sk-svcacct-`, `sk-admin-`; Google `AIza…`.
- Supabase `sbp_` access tokens and `sb_secret_` keys; Netlify `nfp_`; npm `npm_`; Figma `figd_`.
- JWTs (`eyJ….eyJ….…`), **except** a Supabase anon key: a JWT whose payload decodes to `"role": "anon"`. It's public by design and sits in frontend code.
- Credential-shaped assignments whose name **contains** a keyword (`STRIPE_SECRET_KEY=…`, `client_secret: "…"`, `DB_PASSWORD=…`), quoted or unquoted, with a value of 16+ characters.

**Never counts as a secret:**

- Placeholders: a body that is one repeated character (`ghp_xxxx…`, `0000…`) or contains `EXAMPLE` (AWS's documented convention).
- A private-key header with no key body after it, as in docs that name the format (this spec does).
- References to a secret rather than the secret itself: `${{ secrets.X }}`, `${X}`, `process.env.X`, `os.environ[…]`, `import.meta.env.X`.
- Stripe test keys (`sk_test_`, `pk_`), Supabase `sb_publishable_` keys, git SHAs, UUIDs, `sha512-…` integrity strings.

### 4. Law 14 says what is actually checked

Law 14's list matches the shared list, and "high-entropy strings" goes. There's no general entropy check: hashes, lockfile integrity strings and base64 images would block too often, and a hook that blocks too often gets routed around.

## Acceptance criteria

- [ ] Law 39 with the table above; Law 32's block table gets an `mcp-secret` row; Law 38 links to Law 39 in one line.
- [ ] Law 14's pattern list matches the hook's, without "high-entropy strings".
- [ ] An MCP call at any tier, unclassified included, whose input holds a secret at any depth is blocked before any tier prompt; the reason names the kind and the field path, never the value.
- [ ] The commit check and the MCP check use the same function.
- [ ] Tests, for both the commit check and the MCP check: every added shape is caught; every "never counts" item passes; `glpat-` and `xoxb-` are caught (today's bug). These are the first tests for the Law 14 commit check.
- [ ] Input that can't be walked fails open; a 1 MB input is checked in under a second.
- [ ] By hand in the app: an MCP call carrying a shaped fake token is blocked, and nothing reaches the server.
- [ ] README (Law 32 summary), `RELEASES.md` and the version files, minor bump.

## Policy check

- **Laws touched:** 14 (list), 32 (block table), 38 (one link), new 39. Laws 35 and 15 stay as they are; Law 39 points to Law 35 instead of repeating it.
- **Consistency with system safety rules:** Law 39 never permits more than they do (for example, entering credentials into fields stays prohibited). It only adds blocks and asks.
- **Conflicts flagged for the owner:** none beyond the decisions below.

## Decisions for the owner at spec approval

1. **New Law 39** rather than more text in Law 38 (already long) or Law 15 (about mock data). *Recommended: Law 39.*
2. **JWTs:** block all except a Supabase anon key. *Recommended.* Blocking every JWT would block normal Supabase frontend commits.
3. **Stripe test keys pass.** They only reach test mode. *Recommended.*
4. **Placeholders pass** (a repeated character, `EXAMPLE`, or a key header with no body). *Recommended*, so docs and tests can show key shapes.
5. **Law 14 drops "high-entropy strings"** instead of the hook adding an entropy check. *Recommended.*

## Out of scope

- Bash commands that send data out (`curl`, `gh issue|pr create|comment` bodies) and WebFetch / WebSearch URLs. A follow-up issue, since a PR body can leak a secret too (#122).
- Secrets in tool **outputs** (`PostToolUse`) and inside base64 or other encoded content.
- Detecting personal data in the hook: a pattern can't tell a customer's name from ordinary text.
- Tokens with no fixed shape (for example Vercel tokens); Law 39 still forbids sending them.
