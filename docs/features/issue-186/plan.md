# Plan — one secret pattern list for the hook, the registry and the inventory (#186)

Spec: [#186](https://github.com/BojanKocijan/design-forge/issues/186) (the issue) · Gate tier: Standard · Branch: `fix/issue-186-shared-secret-patterns` · Issue: #186
Work pile: delegable (a move plus one import; machine-verifiable)
Approved-by: <pending>

## The gap

`scripts/ai_tools.py` keeps its own `SECRET_PATTERNS`, from before #119. `looks_secret` uses them to refuse secrets in the Law 38 registry, and `ai_inventory.py` uses them to mask secrets in its output. They miss GitLab `glpat-` and Slack `xoxb-` / `xoxp-` tokens and most kinds the hook knows. They also have none of the hook's pass rules.

## The change

1. **New `.claude/hooks/secret_patterns.py`:** the secret code moves out of `enforce-laws.py` unchanged: `SECRET_KINDS`, the private-key, JWT and assignment patterns, the pass-rule constants and helpers, and `find_secret`. It imports only `base64`, `json` and `re`, never the hook or `ai_tools.py`, so there's no import cycle. It sits under `.claude/hooks/` because `dforge-update` already shows you that folder's diff before installing (Law 28).
2. **The hook** imports `find_secret` and `PRIVATE_KEY_RE` from it. The import is guarded, like `hook_log`: if the module can't load, only the secret check fails open, and every other check (never merge, never push to `main`) still runs.
3. **`ai_tools.py`:** `SECRET_PATTERNS` goes, and `looks_secret(text)` becomes `find_secret(text) is not None`. It imports the module from `../.claude/hooks/`, without writing bytecode into the clone. `ai_inventory.py` doesn't change: it already calls `ai_tools.looks_secret`.

## What changes for the registry and the inventory

- **Newly caught:** every kind the hook knows, including `glpat-`, `xoxb-` and `xoxp-`, AWS `ASIA`, all GitHub token types, Stripe live, Anthropic, Google, Supabase, Netlify, npm, Figma and JWTs.
- **Newly passed, by the #119 pass rules:** placeholders such as `ghp_abcdefghijklmnopqrstuvwxyz` (no digit and no capital), references such as `${{ secrets.X }}`, Stripe test keys, public keys, and short credential assignments with no digits (`token=abcdefghijklmnop`). A trial run with the shared function fails 3 of the 33 script tests, all because their fake tokens are lowercase placeholders (decision 1).
- **Lost:** the old catch-all `\bsk-[A-Za-z0-9_-]{16,}`. The hook only knows `sk-ant-` and `sk-proj-` / `sk-svcacct-` / `sk-admin-`, so a legacy OpenAI key (`sk-` + 48 characters) on its own would stop being masked (decision 2).

## Files to change

| File | Change |
|---|---|
| `.claude/hooks/secret_patterns.py` (new) | The moved code, plus the legacy OpenAI pattern if decision 2 is yes |
| `.claude/hooks/enforce-laws.py` | The moved code goes; a guarded import of `find_secret` and `PRIVATE_KEY_RE` |
| `scripts/ai_tools.py` | `SECRET_PATTERNS` goes; `looks_secret` calls `find_secret` |
| `tests/test_ai_tools.py`, `tests/test_ai_inventory.py` | The three fixtures switch to realistic fakes built at run time (decision 1); new tests: a `glpat-` and an `xoxb-` value refused in a registry label and masked in inventory output |
| `tests/test_enforce_laws.py` | A legacy OpenAI key is found (decision 2); the hook still blocks a secret when `secret_patterns.py` loads, and its other checks still run when it doesn't |
| `CLAUDE_LAWS.md` (version only), `RELEASES.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | v2.36.2 |
| `docs/features/issue-186/plan.md` | This plan |

About 9 files and 350 lines: the move counts twice, about 100 lines out and 100 in.

## Order of work

1. The new tests and fixtures, done when they fail for the right reason.
2. Move the code, done when `test_enforce_laws.py` passes unchanged except for the new tests.
3. Switch `looks_secret`, done when all 33 script tests and the new ones pass.
4. The release, done when `release_version.py check` passes.
5. **#192 (v2.36.1) merges first.** This PR stays a draft until it does, then rebases onto `main`, since both change the version lines and `RELEASES.md`.

## Edge cases

- **The module can't load** (a broken clone): the hook's secret check fails open and every other check runs. `ai_tools.py` fails to import, so the hook's tier lookup counts every MCP tool as tier 3 (never lower), and `ai inventory` stops with an error rather than printing unmasked output.
- **Bytecode:** both imports set `sys.dont_write_bytecode`, so no `__pycache__` appears in `~/.design-forge` and `dforge-update` never sees local edits.
- **The plugin install:** the hook always runs from `~/.design-forge/.claude/hooks/`, so the module sits next to it.
- **A name already shown as `[masked]`** stays masked: `[masked]` itself isn't a secret, and the code that never looks up a masked name doesn't change.

## Proof

- **Tests to add:** listed in the table above.
- **Tests edited:** `test_secrets_are_refused` (`test_ai_tools.py`), and `test_hand_edited_secrets_in_the_registry_are_masked` and `test_masked_names_are_never_looked_up` (`test_ai_inventory.py`). Only their fake tokens change, to realistic fakes. What they check doesn't change.
- **Mutation checks:** the old `SECRET_PATTERNS` put back fails the new `glpat-` / `xoxb-` tests, and an unguarded import fails the "other checks still run" test.
- **Commands that must pass:** `python3 -m unittest discover -s tests`, `release_version.py check`, markdownlint, `laws_cost.py --budget 33000`.
- **Visual evidence:** none, no UI change. `Screenshots: not applicable`.

## Risks

- **The hook changes,** so `update rules` asks you to approve its diff (Law 28).
- **The inventory masks less** for placeholder-looking values. → Real tokens are random, with digits and capitals, which the pass rule never lets through.
- **Two PRs touch `enforce-laws.py`** (#192 and this). → They change different parts. This one rebases after #192 merges.

## Ruled out

- **Copying the new patterns into `ai_tools.py`:** two lists drift apart again; that's how this bug happened.
- **The module in `scripts/`:** `dforge-update`'s hook-change check would need it added to its list (Law 28).
- **A stricter mode for the registry and inventory** that masks placeholders too: it means two sets of pass rules on one list. Over-masking costs little in output, so this is decision 1's alternative, not the recommendation.

## Decisions for the owner

1. **The registry and inventory follow the hook's pass rules,** as the issue says, and the three fixtures switch to realistic fakes. Recommended: yes. Alternative: a strict mode that also masks placeholders and short assignments in the registry and inventory.
2. **Add the legacy OpenAI key pattern** (`sk-` + 20 characters + `T3BlbkFJ` + 20 characters, the shape secret scanners use) to the shared list. It keeps what the old `sk-` catch-all masked, and the Law 14 commit check gets it too. Recommended: yes. Law 14 already names OpenAI, so its text doesn't change.
3. **A guarded import in the hook,** so a missing module disables only the secret check, not the never-merge and never-push-to-`main` checks. Recommended: yes.
