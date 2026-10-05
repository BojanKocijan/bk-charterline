---
name: developer-handoff
description: Package a completed UX design for developer implementation — generates docs/handoffs/<id>.md (13-section template) and opens a tracking issue in the GitHub Issues repo. Invoke when the user says "hand off", "ship to dev", "create the handoff for <id>", or runs the `handoff <id>` trigger. Never reply with chat-only links — always generate the file and the issue.
license: GPL-3.0-only
---

# Developer Handoff

## When to invoke

The user says: "hand off", "ship to dev", "prepare handoff", "create the handoff for <id>", or uses the `handoff <id>` trigger phrase.

## Prerequisites (check before generating)

1. Read `PROJECT_KNOWLEDGE.md §9` for the GitHub Issues repo. If it says "none yet", ask the user to provide the repo before proceeding.
2. Read `PROJECT_KNOWLEDGE.md §11 Active feature` for the story ID and title.

## What to generate (two surfaces — both required)

### Surface 1: `docs/handoffs/<id>.md`

Create the file in the project repo using the 13-section template below.

### Surface 2: Tracking issue in the GitHub Issues repo

```bash
gh issue create \
  -R <issues-repo> \
  --title "feat(<scope>): <title> [design handoff]" \
  --body "Design handoff ready for implementation.

## Links
- Handoff doc: <link to docs/handoffs/<id>.md>
- Figma: <link>
- Preview: <GitHub Pages URL>
- Issue: <original issue link>

## Summary
<2-3 lines from the handoff §1>

## Definition of done
- [ ] All acceptance criteria met
- [ ] WCAG 2.2 AA axe clean
- [ ] Unit tests written
- [ ] PR reviewed and CI green"
```

Cross-link both surfaces in the handoff doc body and the issue body.

---

## The 13-section HANDOFF.md template

```markdown
# Handoff — <id>: <title>

**Date:** <YYYY-MM-DD>
**Designer:** <GitHub username>
**Status:** ready-for-implementation

---

## 1. Summary

<One paragraph: what this feature does and why it matters to the user.>

## 2. Figma link(s)

| Screen | Figma URL | Status |
|---|---|---|
| <screen name> | <url> | ready |

## 3. User story / JTBD

As a <user type>, I want to <action> so that <outcome>.

## 4. Acceptance criteria

- [ ] <criterion 1>
- [ ] <criterion 2>
- [ ] <criterion 3>

## 5. UI components used

| Component | Library | Notes |
|---|---|---|
| <component> | <library or custom> | <any notes> |

## 6. Interaction spec

Describe every interaction:
- **Hover:** <description>
- **Click / tap:** <description>
- **Focus:** <description>
- **Loading:** <description>
- **Error:** <description>
- **Empty state:** <description>

## 7. Responsive behavior

| Breakpoint | Layout behavior |
|---|---|
| Desktop (≥1280px) | <description> |
| Tablet (720–1279px) | <description> |
| Mobile (<720px) | <description> |

## 8. Accessibility notes

- **Keyboard flow:** <describe Tab order through the feature>
- **ARIA roles/labels:** <list any non-obvious ARIA attributes>
- **Focus management:** <describe on modal open/close, route change, etc.>
- **Screen reader:** <any non-obvious text alternatives>

## 9. Analytics / telemetry (optional)

If the project uses Pendo or other analytics, list events to instrument here. Omit if not applicable.

## 10. Data layer

| Field | Source | Mock location |
|---|---|---|
| <field name> | <mock | API endpoint | localStorage> | <path in src/data/> |

## 11. Open questions / known gaps

- [ ] <question or gap that the dev team needs to resolve>

## 12. Implementation hints

Any architectural notes, edge cases, or gotchas the dev should know before starting.

## 13. Definition of done

- [ ] All acceptance criteria checked
- [ ] WCAG 2.2 AA — axe-core passes in both unit and E2E tests
- [ ] Unit tests written for every new component
- [ ] E2E smoke test updated if a new route or flow was added
- [ ] PR reviewed, CI green, merged to main
- [ ] GitHub Issues issue closed with a link to the merge commit
```

---

## Post-generation steps

After generating the two surfaces:

1. Append a row to `PROJECT_KNOWLEDGE.md §10 Handoffs shipped`.
2. Update the feature status in `PROJECT_KNOWLEDGE.md §11 Active feature` to `handed-off`.
3. Report both URLs to the user:
   - Handoff doc: `docs/handoffs/<id>.md`
   - Tracking issue: `https://github.com/<downstream-repo>/issues/<N>`
