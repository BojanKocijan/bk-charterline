---
name: design-critique
description: Run an 8-step design critique on a Figma file, screenshot, or UI mockup — visual hierarchy, typography, spacing, color, UI component consistency, accessibility (WCAG 2.2 AA), responsive behavior, and content quality. Each finding is numbered with severity (cosmetic / minor / major / catastrophe) and a concrete suggestion. Invoke when the user says "critique this", "review the design", "give feedback on", or shares a design for evaluation.
license: GPL-3.0-only
---

# Design Critique

## When to invoke

User shares a Figma link, screenshot, or design for evaluation. Trigger phrases: "critique this", "review the design", "give me feedback", "what's wrong with this UI".

## The 8-step critique

Work through all 8 steps in order. Don't skip any. Findings are numbered across all steps.

### Step 1 — Visual hierarchy

- Is there exactly **one primary action** per screen?
- Is the importance of elements communicated through size, weight, and color?
- Does the eye flow naturally from most important to least important?

### Step 2 — Typography

- Does the UI follow a consistent type scale?
- Are font sizes, weights, and line heights consistent across similar elements?
- Is body text ≥16px (14px minimum)?
- Is heading hierarchy clear (H1 → H2 → H3 → body)?

### Step 3 — Spacing

- Are margins, padding, and gaps consistent with a spacing scale?
- Is there enough whitespace between sections (minimum 24px section separation)?
- Are there any elements that feel cramped or overcrowded?

### Step 4 — Color

- Are semantic color tokens used consistently (primary action always the same color)?
- Are there any ad-hoc hex values or inconsistent color usage?
- Does body text meet **4.5:1 contrast** against its background (WCAG AA)?
- Does large text (≥18pt / bold ≥14pt) meet **3:1 contrast**?
- Do UI component borders and icons meet **3:1 contrast** against their backgrounds?

### Step 5 — UI component consistency

- Are like components treated alike across screens (buttons, inputs, cards)?
- Are buttons using consistent sizing, padding, and label conventions?
- Are there any one-off components that could be standardized?

### Step 6 — Accessibility

- Are touch targets ≥ 44×44px?
- Are focus states visible on interactive elements?
- Do icon-only buttons have visible labels or tooltips?
- Are form inputs labeled (not just placeholder)?
- Is color the only means of conveying information anywhere? (If so: flag it.)

### Step 7 — Responsive behavior

- Does the layout work at Desktop (1280px), Tablet (720px), and Mobile (390px)?
- Are there fixed-width elements that would break on smaller screens?
- Is the column structure appropriate for each breakpoint?

### Step 8 — Content quality

- Is all microcopy sentence case?
- Are buttons action-first (verb first: "Delete account" not "Account deletion")?
- Are empty states designed with a clear next action?
- Are error states designed (what does the user see when something fails)?
- Is any text truncating without a tooltip?

---

## Severity levels

| Severity | Meaning |
|---|---|
| **Cosmetic** | Doesn't affect usability or accessibility. Nice to fix. |
| **Minor** | Small usability or consistency issue. Fix before handoff. |
| **Major** | Significant usability, accessibility, or consistency problem. Fix before showing to users. |
| **Catastrophe** | Blocks users from completing a task, fails WCAG, or is a clear business-logic error. Must fix immediately. |

---

## Output format

```
## Design critique: <screen name>

### Finding 1 [Major] — Visual hierarchy: no clear primary action
The screen has three buttons of equal visual weight. Users can't tell which to click first.
Suggestion: Make "Create project" the primary button (filled), demote "Import" to outlined, and move "Cancel" to a text link.

### Finding 2 [Catastrophe] — Accessibility: insufficient contrast
The light grey label text (#aaa) on white background has a 2.3:1 contrast ratio. WCAG AA requires 4.5:1 for normal text.
Suggestion: Darken to #767676 (4.6:1) or #595959 (7:1 for AAA).

### Finding 3 [Cosmetic] — Typography: inconsistent label case
Most labels are sentence case but "Last Modified" uses title case.
Suggestion: Change to "Last modified" to match the pattern.

---
**Summary:** 1 catastrophe, 1 major, 1 cosmetic. Block on Finding 2 before testing with users.
```
