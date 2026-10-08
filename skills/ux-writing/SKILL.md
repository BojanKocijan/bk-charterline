---
name: ux-writing
description: UX writing and microcopy for product UI surfaces — applies the 10 UX writing rules (sentence case, active voice, action-first buttons, specific over generic, no jargon, empty states with next action, error messages naming problem + fix, confirmation dialogs using action label, specific loading states, supplementary tooltips), with tone by moment, onboarding steps, alternatives and notes for translators. Invoke when the user asks to write, review, or improve any product UI copy (labels, buttons, error messages, empty states, onboarding, tooltips).
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
| 7. Errors name problem + fix (+ why, when it helps) | "Email already in use. Sign in or use a different email." | "Invalid email." |
| 8. Confirmation dialogs use action label | "Delete" / "Cancel" | "Yes" / "No" |
| 9. Loading states are specific | "Saving changes…" | "Loading…" |
| 10. Tooltips supplementary | Icon + visible label; tooltip adds detail | Icon only, tooltip required to understand the action |

## Review format

When reviewing copy, return a table:

| Location | Current copy | Issue | Suggested copy |
|---|---|---|---|
| Delete button | "Submit" | Not action-first; vague | "Delete account" |
| Empty state | "Nothing here." | No next action | "No projects yet. Create your first one." |

When **writing new copy**, lead with your pick and list 2–3 other options under it, each with a few words on its tone and where it fits better:

- **Pick: "Save changes"**, plain; right for most forms.
- "Save and continue": moves people forward; for multi-step flows.
- "Save draft": low commitment; for work people come back to.

Add **notes for translators** when they matter (see below).

## Tone by moment

| Moment | Tone | Example |
|---|---|---|
| Success | Warm, brief; at most one exclamation mark, usually none | "Report sent to 12 people." |
| Error | Calm, specific, never blaming the user | "We couldn't reach the server. Check your connection and try again." |
| Warning | Plain about the consequence, before it happens | "Leaving now discards your draft." |
| Neutral | Short and informative | "Last saved 2 minutes ago." |

## Notes for translators

- Translated text grows, and short strings grow most: a one-word label can double or triple, longer sentences grow about 30%. Leave room; never size a button to the English word.
- No idioms, puns or culture-bound references in UI strings.
- Never build a sentence from fragments ("You have " + n + " items"); use one string with a placeholder and plural forms.
- Say what a placeholder holds (`{count}` = number of files) and where the string appears.

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
<Problem in plain language.> <Why, when knowing it helps the user act.> <Fix: what to do next.>
```
Example: "This email is already registered. Sign in or use a different email address."
With why: "Your file didn't upload. It's over the 25 MB limit. Compress it or split it into smaller files."

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

### Onboarding step
```
Title: <The user's goal, not the feature name> (e.g., "Invite your team")
Body: <One concept, one sentence: what they get by doing it.>
Primary button: <Action verb> (e.g., "Send invites")
Secondary: Skip for now
Later: <Where to find it again> (e.g., "You can invite people anytime from Settings → Team.")
```
One concept per step, five steps or fewer in a tour, and every step can be skipped.
