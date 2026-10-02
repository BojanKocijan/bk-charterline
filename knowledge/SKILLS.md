# Skills Matrix — Design Forge

**Version:** 1.0.0
**Last Updated:** 2026-06-06
**Binding:** Yes — this file lists the competencies Claude must apply to every Design Forge task. When a task touches one of these skills, Claude follows the rules in this file.

This file is the "how Claude thinks" companion to the other knowledge files. Where `FRONTEND_GUIDE.md` dictates what components to use, this file dictates how to reason about layout, design, state, a11y, and engineering craft.

---

## 1. Layout skills

**What Claude ships:** layouts that are responsive, consistently-spaced, and built on the correct primitive (Flexbox vs. Grid).

### Primitives

- **Flexbox** for 1-dimensional flow: toolbars, nav rows, form fields, button groups, card headers. Gaps set with `gap`, never margins between flex children.
- **CSS Grid** for 2-dimensional layouts: dashboards, table-like lists, card collections, form sections. Use `grid-template-columns: repeat(auto-fit, minmax(MIN, 1fr))` for responsive card grids.
- **Container queries** (`@container`) when a component's layout depends on its own width, not the viewport.

### Spacing

All gaps, padding, and margin come from the project's theme spacing scale. Never a raw `8px` or `0.5rem` literal unless there is no theme scale.

### Breakpoints

| Device | Width | Cols |
|---|---|---|
| Desktop | ≥ 1280px | 12 |
| Tablet | 720–1279px | 8 |
| Mobile | < 720px (390 baseline) | 4 |

Use the chosen UI library's breakpoint system when available (MUI's `theme.breakpoints.up('md')`, Chakra's responsive arrays, etc.).

### Layout rules

- **Mobile-first:** base styles target mobile; breakpoints add desktop.
- **No fixed widths** except for inherently fixed UI (fab buttons, sidebar rails). Everything else flexes.
- **No `margin-top` on the first child**, no `margin-bottom` on the last — use `gap` on the parent.
- **Overflow-aware:** long labels truncate via a tooltip or CSS `text-overflow: ellipsis`, never by cutting text.

---

## 2. Design skills

### Visual hierarchy

Every screen has exactly **one primary action**. Everything else is secondary, outlined, or text. Use size + color + position to express importance.

### Typography

Follow the project's type scale. If the chosen library has a type system (MUI's `Typography`, Ant Design's `Typography.Text`, Chakra's `Text`), use it. For library-agnostic projects, define the scale in `src/theme.ts`.

### Color

Use semantic color tokens from the theme. Never add ad-hoc colors or hardcoded hex values.

### Spacing

Consistent spacing via the theme scale. No arbitrary values.

---

## 2.a Design critique (8-step checklist)

When the user asks for a design critique on a Figma file, screenshot, or UI, Claude runs through:

1. **Visual hierarchy** — is there exactly one primary action per screen? Is the hierarchy clear?
2. **Typography** — does it follow the type scale? Font sizes, weights, line heights on-spec?
3. **Spacing** — are margins, padding, and gaps consistent with the scale?
4. **Color** — semantic tokens used? No ad-hoc hex? WCAG AA contrast on all text?
5. **UI component consistency** — are like components treated alike? Buttons, inputs, cards consistent across screens?
6. **Accessibility** — touch targets ≥44×44px, focus states visible, icon-only buttons labeled?
7. **Responsive** — does it work across the three breakpoints?
8. **Content quality** — microcopy clear and action-first? Empty states accounted for? Error states designed?

Findings are numbered, each with a severity (**cosmetic** / **minor** / **major** / **catastrophe**) and a concrete suggestion.

---

## 2.b UX writing rules (10 rules)

1. **Sentence case for all UI text.** Never title case except for product names.
2. **Active voice.** "Save changes" not "Changes will be saved."
3. **Action-first buttons.** Verb first: "Delete account" not "Account deletion".
4. **Specific over generic.** "Upload CSV file" not "Upload file".
5. **No jargon.** Write for the user's vocabulary, not the engineering vocabulary.
6. **Empty states tell users what to do next.** Not just "No items found" — "No items yet. Create your first one."
7. **Error messages name the problem and the fix.** "Email already in use. Sign in or use a different email."
8. **Confirmation dialogs use the action as the button label.** "Delete" not "Yes"; "Cancel" not "No".
9. **Loading states are specific.** "Saving changes…" not "Loading…"
10. **Tooltips are supplementary, never required.** Core labels must be visible without hover.

---

## 3. React skills

### State management

- **Local state** — `useState` / `useReducer` for component-scoped state.
- **Shared state** — React Context for medium-complexity sharing; Zustand or Jotai for larger apps (declare in `PROJECT_KNOWLEDGE.md §5`).
- **Server state** — TanStack Query (React Query) when the project graduates to a real backend.

### Performance

- Avoid unnecessary re-renders via `useMemo`, `useCallback`, and component splitting.
- Lazy-load routes with `React.lazy` + `Suspense`.
- Virtualize long lists (React Virtual or the chosen library's `VirtualList`).

### Testing

Every component must have a colocated `.test.tsx`:

```tsx
import { render } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { ExampleCard } from './ExampleCard';

describe('ExampleCard', () => {
  it('renders without a11y violations', async () => {
    const { container } = render(<ExampleCard title="Test" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

### Changed-pages screenshots (Law 34)

Capture only screens the PR touched, as fast as possible.

1. **Select screens.** `git diff --name-only <default-branch>...HEAD` → reverse-walk the import graph → the set of screen root components that reach a touched file. Docs, config, and logic files that reach no screen select nothing.
2. **Nothing selected = no run.** Skip Playwright entirely. No fallback or home-screen shot. PR body: `No screens affected` + the touched-file list.
3. **Cap at 6 screens.** Beyond that, capture the first 6 and say so in the PR body.
4. **Minimal spec.** A standalone screenshot spec, not the E2E/axe suite: `npx playwright test screenshots.spec.ts --project=chromium`.
5. **Speed settings:**
   - Reuse the running dev server (`reuseExistingServer: true`).
   - `fullyParallel: true`, one screen per worker.
   - `animations: 'disabled'` on every `page.screenshot()`.
   - Block fonts and analytics via `page.route`.
   - No fixed waits: `waitForLoadState('domcontentloaded')` + `expect(locator).toBeVisible()` on the element under change.
   - Screenshot the changed element or screen region, not `fullPage`.
6. **Report problems.** A screen that fails to render is an error in the PR body; a new screen without a screenshot key is a warning.

### PR-screenshot root scoping (Law 34)

When a PR-screenshot tool decides which screens to capture by following the import graph from each screen's root component file (the pattern used by `scripts/relevant-screens.mjs` in sports-training-ui, #286), **one screenshot key must map to one root file that renders exactly one screen.**

**Failure mode (found in sports-training-ui, issue #361):** a tabbed dashboard built as one file with internal tab state (`const [selected, setSelected] = useState(TAB_A)`) gets pointed at by several screenshot keys — one per tab — all sharing that same root file. Editing *any* tab, or a hook only one tab uses, trips every screenshot key that shares the file, because the walk is file-level and can't see which tab changed. A new tab added without ever giving it its own screenshot key is silently invisible to reviewers even when it's the only thing a PR actually changed.

**Rule:** split a multi-tab/multi-view container into one component per tab/view (a thin shell + `TabAPanel.tsx`, `TabBPanel.tsx`, …), and give each its own screenshot key rooted at its own panel component — never at the shared shell. This is the same instinct as Law 12's four-file component split, applied to screenshot tooling: a root file that renders more than one reviewable state is a signal the component itself should split, not just the test config.

---

## 4. WCAG 2.2 AA

Every component Claude ships must pass:

| Criterion | Requirement |
|---|---|
| 1.4.3 Contrast (Minimum) | 4.5:1 for normal text, 3:1 for large text |
| 1.4.11 Non-text Contrast | 3:1 for UI components and graphical objects |
| 2.1.1 Keyboard | All functionality via keyboard |
| 2.4.7 Focus Visible | Focus indicator is always visible |
| 2.5.3 Label in Name | Button labels match accessible name |
| 3.2.2 On Input | No unexpected context change on input |
| 4.1.2 Name, Role, Value | All UI has accessible name + role |

Tools: `vitest-axe` in unit tests, `@axe-core/playwright` in E2E.

---

## 5. Forms

- Label every input explicitly (not placeholder-only).
- Group related fields in `<fieldset>` + `<legend>`.
- Show validation errors inline below the field, not only via toast.
- Use `aria-required`, `aria-invalid`, and `aria-describedby` for error messages.
- Never disable the submit button to "prevent errors" — validate on submit and show errors.

---

## 6. Git hygiene

- **Conventional Commits** on every commit: `feat(scope): description` — lowercase, imperative, no period.
- **Branch naming:** `feat/<description>`, `fix/<description>`, `refactor/<description>`.
- **No direct push to `main`** — PRs only.
- **One logical change per commit.** Don't bundle unrelated changes.
- **PR description:** why the change was needed, what was changed, how to test it, screenshots for UI changes.

---

## 7. Motion

- All animations use `prefers-reduced-motion` media query. When reduced, skip or simplify.
- Duration: 150ms for micro-interactions, 250–300ms for transitions, 400ms max for complex sequences.
- Easing: ease-out for elements entering, ease-in for elements leaving.
- Never animate more than one large element at a time.

---

## 8. Error handling

- **Expected errors** (form validation, 404, empty state) — designed UI states, not console logs.
- **Unexpected errors** — React Error Boundary wrapping major sections; fallback UI with a "Try again" action.
- **Network errors** — surface with a retry mechanism. Never silently swallow.
- **Loading states** — skeleton screens for content, spinner for actions. Never blank.

---

## 9. Performance

- Bundle size: measure with `vite-bundle-visualizer` before shipping.
- Images: compressed, correct format (WebP preferred), explicit `width`/`height`.
- Fonts: self-hosted or Google Fonts with `font-display: swap`.
- No `console.log` in production builds.

---

## 10. Developer handoff

### 10.a The two-surface handoff (binding)

When the user says "hand off", "ship to dev", "create the handoff for <id>", or `handoff <id>`, Claude generates **two surfaces**:

1. **`docs/handoffs/<id>.md`** — the 13-section handoff document (see template below).
2. **Tracking issue in the downstream dev repo** (from `PROJECT_KNOWLEDGE.md §9`).

Both surfaces are required. A chat-only reply is never sufficient.

### 10.b The 13-section HANDOFF.md template

```markdown
# Handoff — <id>: <title>

## 1. Summary
One paragraph: what this feature does and why it matters to the user.

## 2. Figma link(s)
| Screen | Figma URL | Status |
|---|---|---|

## 3. User story / JTBD
As a <user type>, I want to <action> so that <outcome>.

## 4. Acceptance criteria
- [ ] criterion one
- [ ] criterion two

## 5. UI components used
| Component | Library | Notes |
|---|---|---|

## 6. Interaction spec
Describe every interaction: hover, click, focus, loading, error, empty state.

## 7. Responsive behavior
| Breakpoint | Layout behavior |
|---|---|
| Desktop (≥1280px) | |
| Tablet (720–1279px) | |
| Mobile (<720px) | |

## 8. Accessibility notes
- Keyboard flow: <describe Tab order>
- ARIA roles/labels: <list any non-obvious ARIA>
- Focus management: <describe on modal open/close, route change>

## 9. Analytics / telemetry (optional)
If the project uses Pendo or other analytics, list events to instrument.

## 10. Data layer
| Field | Source | Mock location |
|---|---|---|

## 11. Open questions / known gaps
- [ ] <question>

## 12. Implementation hints
Any architectural notes, edge cases, or gotchas the dev should know.

## 13. Definition of done
- [ ] All acceptance criteria checked
- [ ] WCAG 2.2 AA axe clean
- [ ] Unit tests written for new components
- [ ] E2E smoke test updated
- [ ] PR reviewed and CI green
```

---

## Changelog

- **1.0.0 (2026-06-06)** — Initial release. All layout/design/React/a11y/form/git/motion/error/performance skills, UX writing 10 rules, design critique 8-step checklist, and the 13-section developer-handoff template (analytics telemetry section optional).
