# Plan — commercial license alongside GPL-3.0

Spec: [#134](https://github.com/BojanKocijan/design-forge/issues/134) (the issue is the spec, decisions included) · Gate tier: Standard (changes skills and the project's license terms) · Branch: `docs/commercial-license` · Issue: #134
Work pile: judgment-heavy for the wording (licensing), mechanical for the skill frontmatter
Approved-by: BojanKocijan, 2026-10-05, chat

## Behavior

- **Two ways to use Design Forge:**
  - **GPL-3.0, unchanged and free:** anyone may use, modify and share it under GPL terms.
  - **A commercial license on request:** for companies that want to modify or embed Design Forge and ship it without publishing their changes, or whose policy bans GPL.
- **How companies ask:** a "Commercial license inquiry" issue form (company, use case, team size, timeline). It warns not to put confidential details in the public issue, and offers to continue privately once the owner replies. No email is published.
- **Price:** no public price. Terms are quoted per company.
- **Contributions:** `CONTRIBUTING.md` changes from "licensed under GPL-3.0, you keep the copyright" to "licensed under GPL-3.0, **and** you grant the owner a non-exclusive right to license it under other terms, including commercially. You keep the copyright." Without this, a merged outside contribution couldn't go into a commercial license. Today every commit is the owner's, so nothing has to be re-licensed retroactively.
- **Every skill names its license:** `license: GPL-3.0-only` in each `SKILL.md` frontmatter. A skill copied on its own (linked into `~/.claude/skills`, pasted into a project) then still says what license it's under.
- **Unchanged:**
  - The Ko-fi coffee section.
  - `plugin.json` and `marketplace.json` keep `"license": "GPL-3.0-only"`: the SPDX id for what the public gets. The commercial option is a separate agreement, not a second public license.
  - GitHub Sponsors comes in a follow-up once the owner's Sponsors profile is approved.

## Files to change — three PRs, all targeting `main`

**PR 1 — commercial license terms** (8 files, about 120 lines)

| File | Change |
|---|---|
| `COMMERCIAL.md` (new) | What the commercial license is, who needs one (and who doesn't: GPL users), what it allows, how to ask, and that the agreement itself is a separate signed document |
| `.github/ISSUE_TEMPLATE/commercial-license.yml` (new) | The inquiry form |
| `README.md` | License section: GPL-3.0 **or** a commercial license, linking `COMMERCIAL.md`. Support section: one line under the coffee pointing companies to `COMMERCIAL.md` |
| `CONTRIBUTING.md` | The contribution-terms change above |
| `RELEASES.md` | v2.23.1 entry |
| `CLAUDE_LAWS.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Version 2.23.1 (version sync only; the license field doesn't change) |

**PR 2 — skill license lines, A–F** (9 files, 9 lines): `analyst`, `arm-disarm`, `claude-laws`, `design-critique`, `design-resources`, `developer-handoff`, `feature-workflow`, `figma-craft`, `frontend-guide`.

**PR 3 — skill license lines, F–U** (8 files, 8 lines): `fullstack-workflow`, `human-in-the-loop`, `project-scaffold`, `scaffold-react-project`, `skills-matrix`, `ux-research-deck`, `ux-research-guide`, `ux-writing`.

The skill PRs are split only because of Law 31's 10-file ceiling. They have no version bump, because the license itself doesn't change; the v2.23.1 release entry mentions them.

## Order of work

1. Commit this plan; owner approves.
2. PR 1: draft `COMMERCIAL.md`, the issue form, the README and `CONTRIBUTING.md` wording, the release entry and version. Done when markdownlint passes, the form YAML parses and both manifests parse.
3. PRs 2 and 3: add `license: GPL-3.0-only` after `description:` in each skill. Done when every `SKILL.md` frontmatter still parses (`name`, `description`, `license`) and `claude plugin validate` passes if available.
4. Open all three against `main`, cross-linked, merge in order. This plan travels in PR 1.

## Proof

- **Tests:** none (documentation and frontmatter only).
- **Commands that must pass:**
  - markdownlint;
  - `python3 -c` YAML-free frontmatter check: each `SKILL.md` starts with `---`, has `name:`, `description:` and `license: GPL-3.0-only`, and closes with `---`;
  - `python3 -m json.tool` on both manifests;
  - parsing the issue form with Ruby's stdlib YAML (`ruby -ryaml`), since Python has no YAML in its stdlib.
- **By hand:** open the issue form preview on the branch on GitHub.
- **Visual evidence:** none (no UI). PR bodies carry `Screenshots: not applicable`.

## Risks

- **This is legal wording, and I'm not a lawyer.** → `COMMERCIAL.md` and the `CONTRIBUTING.md` grant are plain-language drafts. The PR asks you to have them reviewed before you sign a commercial deal. The actual commercial agreement is out of scope.
- **Copyright in AI-assisted text is unsettled.** That can weaken how much a commercial license is worth for the parts Claude co-wrote. → Stated once in the PR's decision log for your lawyer, not in public docs.
- **The contribution grant may put off some contributors.** → It's non-exclusive, they keep their copyright, and their contribution stays GPL for everyone. Common for dual-licensed projects.
- **Inquiries are public issues.** → The form says to leave out confidential details and offers to move to a private channel after first contact.

## Ruled out

- **Publishing your email.** You chose the issue form.
- **A price in the docs.** You chose "contact for terms".
- **Changing the SPDX license in `plugin.json`** to `GPL-3.0-only OR LicenseRef-Commercial`. Validators and the plugin directory expect a standard id, and the commercial option isn't a public license.
- **One PR with all 20+ files.** Over the ceiling; you chose to split.
- **Adding the Sponsors button now.** You chose to add it after the profile is approved.
