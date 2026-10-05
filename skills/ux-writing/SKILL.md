---
name: ux-writing
description: UX writing and microcopy for product UI surfaces — applies the 10 UX writing rules (sentence case, active voice, action-first buttons, specific over generic, no jargon, empty states with next action, error messages naming problem + fix, confirmation dialogs using action label, specific loading states, supplementary tooltips). Invoke when the user asks to write, review, or improve any product UI copy (labels, buttons, error messages, empty states, onboarding, tooltips).
license: GPL-3.0-only
---

# UX Writing

## When to invoke

User asks to write, review, or improve UI copy: button labels, form labels, error messages, empty states, tooltips, onboarding copy, confirmation dialogs.

## The 10 rules (binding)

| Rule | Right | Wrong |
|---|---|---|
| 1. Sentence case | "Add team member" | "Add Team Member" |
| 2. Active voice | "Save changes" | "Changes will be saved" |
| 3. Action-first buttons | "Delete account" | "Account deletion" |
| 4. Specific not generic | "Upload CSV file" | "Upload file" |
| 5. No jargon | "Choose a workspace" | "Select a tenant context" |
| 6. Empty states have next action | "No reports yet. Create your first report." | "No reports found." |
| 7. Errors name problem + fix | "Email already in use. Sign in or use a different email." | "Invalid email." |
| 8. Confirmation dialogs use action label | "Delete" / "Cancel" | "Yes" / "No" |
| 9. Loading states are specific | "Saving changes…" | "Loading…" |
| 10. Tooltips supplementary | Icon + visible label; tooltip adds detail | Icon only, tooltip required to understand the action |

## Review format

When reviewing copy, return a table:

| Location | Current copy | Issue | Suggested copy |
|---|---|---|---|
| Delete button | "Submit" | Not action-first; vague | "Delete account" |
| Empty state | "Nothing here." | No next action | "No projects yet. Create your first one." |

## Copy templates

### Empty state
```
[Illustration or icon]
<What's missing — noun phrase>
<Why it matters or what they can do here>
[Primary CTA button: action verb]
```

### Error message (inline)
```
<Problem in plain language.> <Fix: what to do next.>
```
Example: "This email is already registered. Sign in or use a different email address."

### Confirmation dialog
```
Title: <Action verb> <Object>? (e.g., "Delete project?")
Body: <Consequence — one sentence.> This cannot be undone.
Primary button: <Action verb> (e.g., "Delete")
Secondary: Cancel
```

### Loading state
```
<Verb + object>… (e.g., "Saving changes…", "Uploading file…", "Generating report…")
```

### Tooltip
```
<Sentence that supplements — never replaces — the visible label.>
```
