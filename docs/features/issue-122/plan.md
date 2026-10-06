# Plan — runbook for a leaked secret (#122)

Spec: [#122](https://github.com/BojanKocijan/design-forge/issues/122) (the issue) · Gate tier: Standard · Branch: `docs/secret-leak-runbook` · Issue: #122
Work pile: judgment-heavy (policy wording, done interactively; small)
Approved-by: <pending>

## Files to change

| File | Change |
|---|---|
| `knowledge/INCIDENT_GUIDE.md` | New `## 9. Leaked secret (Law 14)`, before the changelog (content below). Version 1.1.0, changelog line |
| `CLAUDE_LAWS.md` | Law 14 gets one sentence: when a secret gets through anyway, follow INCIDENT_GUIDE §9. Header 2.32.0, Last Updated 2026-10-06 |
| `CLAUDE.md` | The INCIDENT_GUIDE row in the on-demand table also loads it when "a secret got past Law 14" |
| `README.md` | The INCIDENT_GUIDE row mentions the leaked-secret runbook |
| `RELEASES.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | v2.32.0, version sync (Law 27) |

## §9 content

**When:** from any persona, as soon as Claude sees a secret that got past the Law 14 check: in a pushed commit, a PR or issue body or comment, CI or deploy logs, a build artifact, or a connector call. It doesn't switch the persona and writes no incident note.

1. **Stop and tell the owner.** Stop the current task. Say the secret's type (for example "a Supabase service-role key"), where it is (commit SHA and file, PR or issue URL, log location), and how exposed it is (pushed when, public or private repo). Never repeat the value, even partly (§4).
2. **Not pushed yet?** Then it hasn't left the machine. With the owner's yes, drop it from the unpushed commits (`git reset --soft <commit before it>`, then commit again without it). Rotation is needed only if it also went to a log or a connector. Then go to step 6.
3. **The owner revokes and rotates it first.** Claude can't, and removing it from git doesn't un-leak it: clones, forks, CI caches and GitHub's views may still hold it. Name the provider's dashboard when known. A public repo means rotate now: bots scan new pushes within minutes. Treat a possible test key as real until the owner says otherwise. Wait for the owner to confirm the rotation.
4. **Remove it from the current tree.** A normal fix commit on a feature branch (Law 2 announcement, Law 13 message): the value becomes an environment variable reference, and a committed `.env*` file is untracked and ignored. A PR or issue text that Claude wrote is edited only after the owner says yes (GitHub keeps the edit history, so rotation still comes first).
5. **History rewrite is the owner's call.** Claude never runs `git filter-repo`, `git rebase`, `git commit --amend` on pushed commits, or `git push --force` as part of this runbook. If the owner wants the history cleaned, Claude prints the commands for the owner to run and says what they don't fix (forks, caches; GitHub Support for cached views). A secret on the default branch stays there until the owner decides: the Law 32 hook blocks force-pushing it.
6. **Check where else it went** (read-only): other branches and tags (`git log --all -- <file>`), PR and issue text, CI run logs and artifacts after the leak, deploy logs (§1), GitHub secret-scanning alerts (`gh api repos/<owner>/<repo>/secret-scanning/alerts`, when the repo has it on), and any connector call that carried it. Search by file path, key prefix or type, **never by pasting the full value into a command**: commands show in the transcript.
7. **Learn from it.** Offer a `PATTERNS.md` entry (Law 36, ask first) on how it slipped past. If the hook's patterns missed the format, offer a hook issue that describes the shape (prefix, length), never the value.
8. **Report in chat:**

   ```text
   Leaked secret — <type> — <where>
   Rotated: <yes, confirmed by the owner | waiting>
   Removed from the tree: <commit | not needed>
   History: <the owner's decision>
   Also found in: <places, or "nowhere else">
   Not checked: <places and why>
   Follow-ups: <PATTERNS entry, hook issue>
   ```

**Never:** repeat or write the value anywhere (chat, file, commit, issue, note); rotate or revoke it through a connector or API for the owner; rewrite pushed history or force-push; call the leak closed before the owner confirms the rotation; act on another person's repo or fork beyond telling the owner.

## Order of work

1. §9, version and changelog in `INCIDENT_GUIDE.md`. Done when it covers both acceptance criteria and markdownlint passes.
2. The Law 14 pointer, the `CLAUDE.md` row, the `README.md` row. Done when every link resolves to §9.
3. Release v2.32.0. Done when `release_version.py check` prints `2.32.0`.

## Proof

- **Tests:** none added or changed (docs only).
- **Commands:** `npx markdownlint-cli2` with `.markdownlint.json` on the changed files, `python3 scripts/release_version.py check`, `python3 -m unittest discover -s tests` (unchanged, must stay green).
- **Checks by hand:** Law 14 links to INCIDENT_GUIDE §9; §9 says Claude never force-pushes or rewrites history on its own (the issue's second criterion); no example value in §9 looks like a real key.
- **Visual evidence:** none (no UI).

## Risks

- **A runbook Claude doesn't load when it matters.** The CLAUDE.md row adds the trigger, and Law 14, which is always loaded, points to §9.
- **Law 14 promises more than the hook checks.** The law lists "high-entropy strings", but the hook's `SECRET_PATTERNS` doesn't check entropy, so a bare JWT or an `sk_live_` key outside a `key = "…"` assignment gets through. That is a likely way in for this runbook. Out of scope here; step 7 feeds it back, and #119 reuses the same patterns.

## Ruled out

- **`knowledge/SKILLS.md` §6 (git hygiene):** loaded on git-craft questions, not when a leak is found, and the leak is often outside git.
- **A new knowledge file:** another row in the load table and the Law 4 list for one section. INCIDENT_GUIDE already holds the redaction rules and the log sources the check needs.
- **Claude running the history rewrite when asked:** destructive and hard to reverse. Printing the commands keeps the decision and the action with the owner.
