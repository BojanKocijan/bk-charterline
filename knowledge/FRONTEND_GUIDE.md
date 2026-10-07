# Frontend Writing Guide

**Version:** 1.0.0
**Last Updated:** 2026-06-06
**Applies to:** All React projects under BK Charterline governance
**Binding:** Yes — this file is a law (see [`CLAUDE_LAWS.md`](../CLAUDE_LAWS.md) Laws 4, 12, 15). Claude must follow it on every frontend task.

---

## 1. Stack

| Layer | Technology |
|---|---|
| Framework | React (functional components + hooks only) |
| UI library | Chosen at scaffold time — shadcn/ui, MUI v6, Ant Design, Chakra UI, or local components |
| Routing | React Router (`react-router-dom`) for any multi-screen app — navigation via `useNavigate`, never screen-state callbacks. Single-screen apps may skip it. |
| Base styling | `styled-components` (default) or Tailwind (when the chosen library requires it) |
| State (local) | React `useState` / `useReducer` |
| State (shared) | Root context (`useAppContext` pattern) by default; Zustand/Jotai when it outgrows context |
| Persistence | `localStorage` (no backend DB) |
| Data | Mocked — no live API calls unless explicitly approved |

**UI library:** chosen at scaffold time (shadcn/ui | MUI | Ant Design | Chakra UI | local). Every project uses whatever was chosen during `new project`. Claude never switches the library mid-project without explicit approval.

**Resolve every UI to the chosen library (Law 30).** Whatever the input — a paper sketch, a Figma frame, or a **screenshot of another app** — it's a description of *intent*, not a component source. Map each element to the nearest primitive in the project's library (another app's dropdown → the library's `Select`, its card → `Card`, its tab bar → `Tabs`). Never hallucinate components, never pull in a second UI library, never hand-roll a primitive the library already provides. If the library genuinely lacks something, say so and ask before adding a dependency or building custom — don't improvise.

**Routing:** any app with more than one screen uses React Router. Navigation is always `useNavigate()` (or `<Link>`), never an `onNav`/`onBack`/`setScreen` callback threaded through props. Pages stay route-agnostic; a thin route-wrapper component injects data and navigation. Shared app state is provided once at the root via context and read with a `useAppContext()` hook — not prop-drilled across route boundaries. Transient route-to-route payloads travel in `location.state` with a `returnTo`. See [`COMPONENT_PATTERNS.md`](./COMPONENT_PATTERNS.md) Patterns 15–17.

---

## 2. Project Setup

Every app must be wrapped with the appropriate root provider for the chosen library:

```tsx
// shadcn/ui — no global provider required; use cn() utility
// MUI
import { ThemeProvider } from '@mui/material/styles';
<ThemeProvider theme={theme}>{children}</ThemeProvider>

// Ant Design
import { ConfigProvider } from 'antd';
<ConfigProvider>{children}</ConfigProvider>

// Chakra UI
import { ChakraProvider } from '@chakra-ui/react';
<ChakraProvider>{children}</ChakraProvider>

// No library — custom theme via styled-components ThemeProvider
import { ThemeProvider } from 'styled-components';
import { theme } from './theme';
<ThemeProvider theme={theme}>{children}</ThemeProvider>
```

---

## 3. Component Rules

### 3.1 Use the chosen library's components — never roll your own primitives

**The chosen UI library is the implementation.** If a UI primitive exists in the library (button, input, select, dialog, card, etc.), **import it and use it** — never rebuild it from scratch.

If genuinely missing: build the custom primitive in a 4-file folder under `src/components/<Name>/` (per §5 + Law 12) **and** add it to `PROJECT_KNOWLEDGE.md §3` (project-specific components).

### 3.2 Design fidelity — only add elements present in the design

When implementing from a Figma link or any design:

1. **Only add visual elements explicitly present in the design.** Icons, color accents, borders, badges — if it isn't in the design, it doesn't go in the code.
2. **When an icon is needed, source the exact identifier from Figma** before writing any icon reference. Never intent-match a component label to a likely icon name.
3. **When in doubt, implement less.** A text-only button that matches the design is correct; an icon button with a guessed icon is a deviation.

### 3.3 Triage-first — ask before building non-trivial UI (Law 17)

Before implementing any UI with a non-trivial signal (multi-step flow, drawer/panel layout, component state with multiple plausible implementations, behaviour the design doesn't specify), Claude must run **one `AskUserQuestion` call with up to 4 focused questions** on:

1. Layout/sizing
2. Interaction
3. Visual treatment
4. Flow pacing

Trivial UI (one-line CSS, copy edit, token swap) skips the triage.

---

## 4. Styling Rules

### 4.1 Never use hard-coded values

All colors, spacing, font sizes, and shadows must come from the theme or the library's design tokens. Never write raw hex codes, pixel values, or font names.

```tsx
// ✅ correct — using theme tokens (styled-components + custom theme)
const StyledCard = styled.div`
  ${({ theme }) => css`
    background-color: ${theme.colors.background};
    padding: ${theme.spacing[3]};
  `}
`;

// ❌ wrong
const StyledCard = styled.div`
  background-color: #ffffff;
  padding: 24px;
`;
```

### 4.2 styled-components is the base styling layer — and it lives in a separate file

**Binding under [`CLAUDE_LAWS.md`](../CLAUDE_LAWS.md) Law 12.** Every component is a four-file folder, and CSS only lives in the `.styles.ts` file.

```
src/components/OrderCard/
├── OrderCard.tsx          # logic + JSX only — no css, no styled.* declarations
├── OrderCard.styles.ts    # every styled-components declaration goes here
├── OrderCard.types.ts     # prop interfaces + related types
└── index.ts               # barrel re-export
```

**Exception for Tailwind projects (shadcn/ui):** Tailwind utility classes are allowed directly in `.tsx`. However, custom CSS overrides and complex style compositions still go in `.styles.ts` as styled-components or `cn()` variants.

**Banned in `*.tsx` files (every one of these fails CI):**

```tsx
// ❌ inline style prop — even for "just one quick value"
<div style={{ marginTop: 8 }} />

// ❌ template-literal CSS string in the component file
const wrapperCss = css`padding: 16px;`;

// ❌ styled.* declaration in the component file
const Wrapper = styled.div`padding: 16px;`;
```

**Required pattern:**

```ts
// OrderCard.styles.ts
import styled, { css } from 'styled-components';

export const StyledOrderCard = styled.div`
  ${({ theme }) => css`
    background-color: ${theme.colors.surface};
    border: 1px solid ${theme.colors.border};
    padding: ${theme.spacing[2]};
  `}
`;
```

```tsx
// OrderCard.tsx
import { OrderCardProps } from './OrderCard.types';
import { StyledOrderCard } from './OrderCard.styles';

export const OrderCard = ({ title, total }: OrderCardProps) => (
  <StyledOrderCard>
    <div>{title}</div>
    <div>{total}</div>
  </StyledOrderCard>
);
```

Dynamic values flow as **props** into the styled-component, never via the inline `style` attribute:

```tsx
// ❌ wrong
<div style={{ background: 'red' }}>Error</div>

// ✅ correct
// in .styles.ts
export const ErrorBox = styled.div<{ $severity: 'low' | 'high' }>`
  ${({ $severity }) => css`
    background: ${$severity === 'high' ? '#d32f2f' : '#f57c00'};
  `}
`;
// in .tsx
<ErrorBox $severity="high">Error</ErrorBox>
```

---

## 5. File & Folder Structure

```
src/
├── components/
│   ├── ComponentName/
│   │   ├── ComponentName.tsx        # logic + JSX only — NO css, NO styled.* here (Law 12)
│   │   ├── ComponentName.styles.ts  # every styled-component declaration lives here
│   │   ├── ComponentName.types.ts   # prop interfaces + related types
│   │   ├── ComponentName.test.tsx   # colocated Vitest spec (with vitest-axe assertion)
│   │   └── index.ts                 # barrel re-export
├── pages/
│   └── PageName/
│       ├── PageName.tsx
│       ├── PageName.styles.ts
│       ├── PageName.types.ts
│       └── index.ts
├── hooks/
│   └── useHookName.ts
├── utils/
│   └── utilName.ts
├── assets/
│   └── (images, fonts, etc.)
├── data/
│   └── mockDataName.ts              # default data layer — fictional values only (Law 15)
├── services/
│   └── storage.ts                   # localStorage adapter
└── App.tsx
```

**Every component folder has at least three files** (`.tsx` + `.styles.ts` + `index.ts`) and ideally a fourth (`.types.ts`) once props go beyond a couple of fields.

---

## 6. Naming Conventions

| Thing | Convention | Example |
|---|---|---|
| Component files | PascalCase | `UserCard.tsx` |
| Style files | PascalCase + `.styles` | `UserCard.styles.ts` |
| Hook files | camelCase + `use` prefix | `useUserData.ts` |
| Util files | camelCase | `formatDate.ts` |
| Mock data files | camelCase | `mockUsers.ts` |
| Styled components | `Styled` prefix | `StyledWrapper`, `StyledHeader` |
| Props interfaces | `ComponentNameProps` | `UserCardProps` |

---

## 7. TypeScript

- **Always use TypeScript.** No `.js` or `.jsx` files.
- Define props interfaces in a separate `.types.ts` file.
- No `any`. Use `unknown` if the type is truly unknown and narrow it.
- Prefer explicit return types: `(): JSX.Element` or `React.FC<Props>`.

---

## 8. Data layer

The default data layer is **mocks + `localStorage`**. All mock data lives in `src/data/`. Persistent reads/writes go through a thin adapter in `src/services/storage.ts` — never `window.localStorage` directly inside a component.

### PII-free mock data (Law 15 — binding)

All mock data generated by Claude must use **purely fictional** values.

| Category | Never | Always |
|---|---|---|
| Names | Real person names | `Alice Chen`, `Bob Müller` |
| Emails | Any real domain | `alice@example.com` (RFC 2606) |
| Phones | Real numbers | `+1 555-0100` (reserved fictionals) |
| Companies | Real names | `Acme Corp`, `Globex Systems` |
| IDs | Copy-pasted real UUIDs | `crypto.randomUUID()` |
| Addresses | Real addresses | `1 Fictional Lane, Nowhere, NS 00001` |
| IPs | Real IPs | `192.0.2.x` (RFC 5737) |

### Graduating to a real database

Any database is allowed. To graduate, Claude must pre-execution announce with the `Data layer:` line (severity **Medium** at minimum), and note the choice in `PROJECT_KNOWLEDGE.md §5`.

---

## 9. Accessibility

- Use semantic HTML: `<header>`, `<main>`, `<nav>`, `<section>`, `<article>`.
- All interactive elements must be keyboard-accessible.
- All images need `alt` text or `aria-label`.
- Use `aria-label` on icon-only buttons.
- Target: **WCAG 2.2 AA** on every component.

---

## 10. Do / Don't Quick Reference

| Do | Don't |
|---|---|
| Use the chosen UI library's components | Build custom primitives if the library has one |
| Keep CSS in `.styles.ts` | Use `style={{}}` in `.tsx` |
| Use theme tokens for colors/spacing | Hard-code hex or px values |
| Use TypeScript, define prop types | Use `any` or skip typing |
| One component per folder with styles + types | Dump all code in one file |
| Functional components + hooks | Class components |
| Semantic HTML for layout | Divs for everything |
| Mock data in `src/data/` with fictional values | Real PII in mock files |

---

## Changelog

- **1.0.0 (2026-06-06)** — Initial release. Library-agnostic stack (shadcn/ui, MUI, Ant Design, Chakra UI, or local). 4-file folder pattern (Law 12), no-inline-styles rule, TypeScript, WCAG 2.2 AA, mock-data PII rules, triage-first discipline, design-fidelity rule.
