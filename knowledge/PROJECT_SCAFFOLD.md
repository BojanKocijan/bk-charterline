# Project Scaffold — BK Charterline

**Version:** 1.1.0
**Last Updated:** 2026-06-06
**Applies to:** Every new project under BK Charterline governance
**Binding:** Yes — this file is a law (see [`CLAUDE_LAWS.md`](../CLAUDE_LAWS.md) Laws 7, 10, 11, 12, 13, 14, 15, 18). Claude must follow it whenever the user says **"new project"** (or equivalent).

---

## 0. GitHub authentication gate (always first)

Before a single file is created, Claude verifies the user is authenticated to GitHub.

```bash
gh auth status
```

If not authenticated:

```bash
gh auth login
```

Required scopes: `repo` (create repo, push, open issues + PRs), `workflow` (push `.github/workflows/`).

After authentication, confirm identity:

```bash
gh api user --jq '"Authenticated as: " + .login'
```

---

## 1. When the user says "new project"

**Step 0 — Ask which kind of project (UX vs Fullstack).**

> *"Two project types are supported:*
>
> 1. **UX project** (default) — mockups, prototypes, UI exploration. Frontend persona stays default.
> 2. **Fullstack project** — production code, real backend, real DB. Activates the Fullstack persona.
>
> *Which one?"*

Wait for the answer.

**Step 0.5 — Ask which platform target.** Run an `AskUserQuestion` call:

```ts
AskUserQuestion({
  questions: [
    {
      header: "Platform",
      question: "What kind of app are you building? This determines the entire scaffold — framework, styling approach, CI, and component rules.",
      options: [
        {
          label: "Web app — React (Recommended)",
          description: "Vite + React + TypeScript. Targets browsers only. styled-components, shadcn/ui, MUI, Chakra, or Ant Design. Full BK Charterline 4-file component pattern."
        },
        {
          label: "Hybrid app — React Native / Expo",
          description: "Expo Router + React Native. Runs on iOS, Android, and web from one codebase. StyleSheet-based styling, Expo CI. Adapted BK Charterline rules."
        },
        {
          label: "Web app — Angular",
          description: "Angular CLI + TypeScript. Component-per-folder pattern, Angular Material or custom. Adapted BK Charterline rules."
        },
        {
          label: "Other — I'll describe it",
          description: "Claude will ask for your stack, research the setup, and adapt the scaffold rules accordingly."
        }
      ],
      multiSelect: false
    }
  ]
});
```

Store the answer as **Platform** in `PROJECT_KNOWLEDGE.md §5`. This choice gates which scaffold branch runs — jump to the matching section:

| Answer | Go to |
| --- | --- |
| Web app — React | §1-React onwards (existing flow) |
| Hybrid app — React Native / Expo | §1-RN onwards |
| Web app — Angular | §1-Angular onwards |
| Other | Ask for stack details, then adapt |

**Step 0.6 — Ask the app-architecture questions (drive a correct app).** Before scaffolding, run one `AskUserQuestion` call so the app is built on the right structure from line one — not refactored into it later. Skip only for a deliberately single-screen throwaway.

```ts
AskUserQuestion({
  questions: [
    {
      header: "Routing",
      question: "How many screens, and should they have real URLs?",
      options: [
        { label: "Multi-route — React Router (Recommended)", description: "More than one screen. Real URLs, browser back/forward, deep links. Navigation via useNavigate, never screen-state callbacks. (Expo Router for RN, Angular Router for Angular.)" },
        { label: "Single screen — no router", description: "One screen, no navigation. Add a router later if it grows." }
      ],
      multiSelect: false
    },
    {
      header: "App shell",
      question: "Is there a persistent navigation chrome around the pages?",
      options: [
        { label: "Persistent shell (sidebar + bottom nav)", description: "A layout route wraps all main pages via <Outlet/> so the shell isn't re-mounted on navigation. Public pages (landing, login) sit outside it." },
        { label: "No shell — standalone pages", description: "Each page is full-bleed with its own layout. No shared chrome." }
      ],
      multiSelect: false
    },
    {
      header: "Data flow",
      question: "How does app state reach the screens?",
      options: [
        { label: "Root context — useAppContext (Recommended)", description: "State sourced once at the root, read via a context hook in route components. No prop-drilling across route boundaries. Default for mockups and single-user tools." },
        { label: "State library — Zustand / Jotai", description: "For larger apps with complex cross-cutting state. Declare it in PROJECT_KNOWLEDGE §5." },
        { label: "Local state only", description: "Each screen owns its state. Fine for simple, isolated screens." }
      ],
      multiSelect: false
    },
    {
      header: "Auth boundary",
      question: "Are there public vs. protected areas?",
      options: [
        { label: "Public + protected split", description: "Public routes (landing, login) plus a protected namespace (e.g. /app/*) for authenticated pages. Recommended even before auth is wired — leaves the seam in place." },
        { label: "All public — no auth yet", description: "Every route is open. Add the protected namespace when auth lands." }
      ],
      multiSelect: false
    }
  ]
});
```

Record all four answers in `PROJECT_KNOWLEDGE.md §5` as architectural decisions. They determine the route tree, the shell layout route, the context provider, and the public/protected split that the scaffold lays down. For the routing/navigation/data patterns themselves, follow [`COMPONENT_PATTERNS.md`](./COMPONENT_PATTERNS.md) Patterns 15–17.

**Step 1 — Ask for project name.**

Any kebab-case name (e.g. `my-dashboard`, `cashflow-family`). Not restricted to any prefix.

---

## 1-React. Web app — React scaffold questions

**Step 2 — Ask for UI library.** Run an `AskUserQuestion` call:

```ts
AskUserQuestion({
  questions: [
    {
      header: "UI library",
      question: "Which UI library would you like to use for this project?",
      options: [
        { label: "shadcn/ui", description: "Radix primitives + Tailwind CSS. Copy-paste components, fully customizable. Best for custom designs." },
        { label: "Material UI (MUI v6)", description: "Google Material Design. Comprehensive component library with theming. Best for data-heavy apps." },
        { label: "Ant Design", description: "Enterprise-grade, batteries-included. Rich component set, opinionated design. Best for admin/B2B." },
        { label: "Chakra UI", description: "Accessible, composable, style-prop-driven. Best for rapid accessible UI." },
        { label: "No library — local components only", description: "Pure styled-components with a custom theme object. Maximum control, more initial work." },
        { label: "Other — I'll type the name", description: "Claude will research the library, find its install command, and set it up correctly." }
      ],
      multiSelect: false
    }
  ]
});
```

**Step 3 — Ask where GitHub Issues should be created.**

> *"Which GitHub repo should Claude open issues in for this project? Format: `owner/repo`. Press Enter to use the current project repo (default)."*

**Step 4 — Ask for deployment target.**

```ts
AskUserQuestion({
  questions: [
    {
      header: "Deployment",
      question: "Where should this project be deployed for preview?",
      options: [
        { label: "Netlify", description: "Recommended. Continuous deployment from main, instant preview URLs per PR, free tier." },
        { label: "GitHub Pages", description: "No extra account needed. Deploys from main via GitHub Actions. Single URL, no per-PR previews." },
        { label: "None — I'll set up deployment later", description: "Skip deployment setup." }
      ],
      multiSelect: false
    }
  ]
});
```

Then proceed to **§2-React**.

---

## 1-RN. Hybrid app — React Native / Expo scaffold questions

**Step 2 — Ask for component library.**

```ts
AskUserQuestion({
  questions: [
    {
      header: "UI library",
      question: "Which React Native UI library would you like to use?",
      options: [
        { label: "No library — local components only (Recommended)", description: "Pure React Native + StyleSheet with a constants/theme.ts token file. Maximum control, matches the BK Charterline pattern for RN." },
        { label: "React Native Paper", description: "Material Design 3 for React Native. Good for data-heavy apps." },
        { label: "NativeWind", description: "Tailwind CSS for React Native. Utility-class-driven styling via className." },
        { label: "Gluestack UI", description: "Universal components that work across React Native and web. Headless + styled." },
        { label: "Other — I'll type the name", description: "Claude will research the library and set it up correctly." }
      ],
      multiSelect: false
    }
  ]
});
```

**Step 3 — Ask about backend.**

```ts
AskUserQuestion({
  questions: [
    {
      header: "Backend",
      question: "What backend will this app use?",
      options: [
        { label: "Supabase", description: "PostgreSQL + Auth + Storage + Realtime. Recommended for hybrid apps." },
        { label: "Firebase", description: "Firestore + Auth + Storage. Good for real-time apps." },
        { label: "Custom API / BYO backend", description: "Claude will scaffold the client layer; you manage the backend." },
        { label: "None — mocks only for now", description: "No backend. Mock data in src/data/. Upgrade later." }
      ],
      multiSelect: false
    }
  ]
});
```

**Step 4 — Ask for web deployment.**

```ts
AskUserQuestion({
  questions: [
    {
      header: "Web deploy",
      question: "The Expo web build can be deployed for browser preview. Where?",
      options: [
        { label: "Netlify (Recommended)", description: "expo export --platform web → Netlify. Instant preview URLs per PR." },
        { label: "None — mobile only for now", description: "Skip web deployment. Build for iOS/Android only." }
      ],
      multiSelect: false
    }
  ]
});
```

**Step 5 — Ask where GitHub Issues should be created** (same as React step 3).

Then proceed to **§2-RN**.

---

## 1-Angular. Web app — Angular scaffold questions

**Step 2 — Ask for UI library.**

```ts
AskUserQuestion({
  questions: [
    {
      header: "UI library",
      question: "Which Angular UI library would you like to use?",
      options: [
        { label: "Angular Material", description: "Official Google Material Design for Angular. Best integrated with Angular CDK." },
        { label: "PrimeNG", description: "Rich enterprise component set. Charts, tables, form controls." },
        { label: "No library — local components only", description: "Pure Angular + SCSS with a design token file." },
        { label: "Other — I'll type the name", description: "Claude will research the library and set it up." }
      ],
      multiSelect: false
    }
  ]
});
```

**Step 3 & 4** — same GitHub Issues + deployment questions as React.

Then proceed to **§2-Angular**.

---

## 2-React. Web React scaffold procedure

### Base stack

1. Vite + TypeScript + React
2. React Router (`npm install react-router-dom`) — if "Multi-route" was chosen in Step 0.6. Lay down the route tree, the `AppLayout` shell route (`<Outlet/>`), and the public/protected split per the Step 0.6 answers.
3. styled-components (base styling layer; Tailwind if the chosen library requires it)
4. ESLint + TypeScript ESLint + Prettier
5. Vitest + React Testing Library + vitest-axe (unit + component + a11y)
6. Playwright + @axe-core/playwright (E2E + full-page accessibility)
7. Deployment per user choice

### Component rules (Law 12 — full enforcement)

Every component is a 4-file folder:

```text
ComponentName/
  ComponentName.tsx        # logic + JSX only
  ComponentName.styles.ts  # all styled-components declarations
  ComponentName.types.ts   # prop interfaces
  index.ts                 # barrel re-export
```

Banned in `.tsx`: `style={{}}`, CSS template literals, `styled.*` declarations, raw `className` strings as ad-hoc styling.

### Folder skeleton

```text
<project-name>/
├── src/
│   ├── components/
│   │   └── ExampleCard/
│   │       ├── ExampleCard.tsx
│   │       ├── ExampleCard.styles.ts
│   │       ├── ExampleCard.types.ts
│   │       ├── ExampleCard.test.tsx
│   │       └── index.ts
│   ├── pages/
│   │   └── Home/
│   │       ├── Home.tsx
│   │       ├── Home.styles.ts
│   │       ├── Home.types.ts
│   │       └── index.ts
│   ├── hooks/
│   ├── utils/
│   ├── assets/
│   ├── data/
│   ├── services/
│   │   └── storage.ts
│   ├── App.tsx
│   └── main.tsx
├── tests/
│   └── e2e/
│       └── smoke.spec.ts
├── .github/
│   ├── dependabot.yml         ← weekly npm + github-actions updates
│   └── workflows/
│       ├── ci.yml
│       └── pages.yml          ← GitHub Pages only
├── netlify.toml               ← Netlify only
├── .eslintrc.cjs
├── .prettierrc
├── tsconfig.json
├── vite.config.ts
├── vitest.config.ts
├── playwright.config.ts
├── PROJECT_KNOWLEDGE.md
└── CLAUDE.md
```

### Library-specific setup

#### shadcn/ui

```bash
npm create vite@latest <name> -- --template react-ts
cd <name> && npm install
npm install styled-components @types/styled-components
npm install -D tailwindcss postcss autoprefixer && npx tailwindcss init -p
npx shadcn@latest init
```

`vite.config.ts` path alias:

```ts
import path from 'path';
export default { resolve: { alias: { '@': path.resolve(__dirname, './src') } } }
```

#### Material UI (MUI v6)

```bash
npm create vite@latest <name> -- --template react-ts
cd <name> && npm install
npm install @mui/material @emotion/react @emotion/styled
npm install styled-components @types/styled-components
```

Root wrapper: `<ThemeProvider theme={theme}><CssBaseline />{children}</ThemeProvider>`

#### Ant Design

```bash
npm create vite@latest <name> -- --template react-ts
cd <name> && npm install antd styled-components @types/styled-components
```

Root wrapper: `<ConfigProvider>{children}</ConfigProvider>`

#### Chakra UI

```bash
npm create vite@latest <name> -- --template react-ts
cd <name> && npm install @chakra-ui/react styled-components @types/styled-components
```

Root wrapper: `<ChakraProvider>{children}</ChakraProvider>`

#### No library — local components only

```bash
npm create vite@latest <name> -- --template react-ts
cd <name> && npm install styled-components @types/styled-components
```

Create `src/theme.ts`:

```ts
export const theme = {
  colors: { primary: '#3b82f6', background: '#ffffff', surface: '#f8fafc', text: '#0f172a', textSecondary: '#64748b', border: '#e2e8f0', error: '#ef4444', success: '#22c55e' },
  spacing: { 1: '4px', 2: '8px', 3: '12px', 4: '16px', 5: '20px', 6: '24px', 8: '32px', 10: '40px', 12: '48px' },
  typography: { fontFamily: 'Inter, system-ui, sans-serif', sizes: { sm: '0.875rem', md: '1rem', lg: '1.125rem', xl: '1.25rem' }, weights: { regular: 400, medium: 500, bold: 700 } },
  radii: { sm: '4px', md: '8px', lg: '12px', full: '9999px' },
};
export type Theme = typeof theme;
```

#### Other library

1. `npm info <library> description version`
2. Find install command + peer deps.
3. Find root provider/wrapper.
4. Set up per the pattern above.
5. Report findings and ask for confirmation before installing.

### CI workflow (React)

#### `.github/workflows/ci.yml`

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:

jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm }
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm run test
      - run: npm run build
      - name: Install Playwright browsers
        run: npx playwright install --with-deps chromium
      - run: npm run test:e2e
```

#### `.github/dependabot.yml`

Every scaffolded project ships with Dependabot enabled so the user gets weekly dependency-update PRs to review (Law 10). Tracks both the npm packages and the GitHub Actions used by CI:

```yaml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    commit-message:
      prefix: "chore(deps)"
    labels:
      - "dependencies"
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    commit-message:
      prefix: "chore(ci)"
    labels:
      - "dependencies"
```

Dependabot PRs follow the normal review flow — CI runs on each, and the user merges them (Claude never auto-merges, Law 7). The same `dependabot.yml` applies to all platform tracks (React/Vite, React Native/Expo, Angular), since all use npm + GitHub Actions.

#### §4a — GitHub Pages

```yaml
name: Deploy to GitHub Pages
on:
  push:
    branches: [main]
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: false
jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm }
      - run: npm ci && npm run build
      - uses: actions/configure-pages@v4
      - uses: actions/upload-pages-artifact@v3
        with: { path: dist }
      - id: deployment
        uses: actions/deploy-pages@v4
```

#### §4b — Netlify

`netlify.toml`:

```toml
[build]
  command = "npm run build"
  publish = "dist"

[build.environment]
  NODE_VERSION = "20"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

Setup: app.netlify.com → Add new site → Import from GitHub → Deploy.

### `package.json` scripts (React)

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint src --ext .ts,.tsx",
    "lint:fix": "eslint src --ext .ts,.tsx --fix",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:e2e": "playwright test",
    "ci": "npm run lint && npm run typecheck && npm run test && npm run build"
  }
}
```

### Post-scaffold steps (React)

1. Spawn `npm run dev` in the background (Law 18). Every reply ends with `Preview: <url> · status: up`.
2. Create `PROJECT_KNOWLEDGE.md` from the template (§7).
3. Create local `CLAUDE.md` with `@./PROJECT_KNOWLEDGE.md` only — never import `@~/.bk-charterline/CLAUDE.md` (laws load globally via `~/.claude/CLAUDE.md`).
4. Commit: `chore: scaffold <name> project`.
5. Push and open the first PR.
6. User triggers `start feature` — scaffolding does NOT auto-start a feature.

---

## 2-RN. Hybrid app — React Native / Expo scaffold procedure

### Base stack (React Native)

1. Expo (latest) + TypeScript + Expo Router (file-based routing)
2. React Native `StyleSheet` — the RN equivalent of styled-components (see Law 12-RN below)
3. ESLint + TypeScript ESLint + Prettier
4. Jest + React Native Testing Library (unit + component)
5. `expo-github-action` CI (lint + typecheck + build)
6. Supabase / Firebase / mocks per user choice
7. Netlify (web build) or none per user choice

### Law 12 — adapted for React Native (Law 12-RN)

React Native has no DOM, so `styled-components` is not used. The equivalent pattern:

| Web React (Law 12) | React Native equivalent |
| --- | --- |
| `Component.styles.ts` with `styled.*` | `Component.styles.ts` with `StyleSheet.create({})` |
| Theme via `ThemeProvider` | `constants/theme.ts` imported directly |
| `style={{}}` inline — **banned** | `style={styles.foo}` — allowed if StyleSheet is in `.styles.ts` |
| Tailwind `className` — project-dependent | NativeWind `className` — project-dependent |

**The rule:** no raw inline style objects in `.tsx` files. All `StyleSheet.create()` declarations live in the colocated `.styles.ts` file.

**Allowed in `.tsx`:**

```tsx
import { styles } from './MyComponent.styles';
<View style={styles.container} />           // ✅ reference to StyleSheet
<View style={[styles.base, styles.active]} /> // ✅ array of StyleSheet refs
```

**Banned in `.tsx`:**

```tsx
<View style={{ padding: 16 }} />             // ❌ raw object — move to .styles.ts
<View style={{ backgroundColor: accent }} /> // ❌ dynamic inline — use style prop pattern below
```

**Dynamic values** flow as a second argument to the styles function:

```ts
// MyComponent.styles.ts
export const makeStyles = (accent: string) => StyleSheet.create({
  accentBar: { backgroundColor: accent },
});
```

```tsx
// MyComponent.tsx
const styles = makeStyles(props.accent);
<View style={styles.accentBar} />
```

### Folder skeleton (React Native)

```text
<project-name>/
├── app/                          # Expo Router pages (file-based)
│   ├── (auth)/
│   │   ├── login.tsx
│   │   └── callback.tsx
│   ├── (tabs)/
│   │   ├── _layout.tsx
│   │   ├── index.tsx
│   │   └── <screen>.tsx
│   └── _layout.tsx
├── components/
│   └── ComponentName/
│       ├── ComponentName.tsx     # logic + JSX only — no inline style objects
│       ├── ComponentName.styles.ts  # StyleSheet.create() lives here
│       ├── ComponentName.types.ts
│       └── index.ts
├── constants/
│   └── theme.ts                  # Colors, Typography, Spacing, Radii, Shadows
├── store/                        # Zustand stores
├── lib/                          # Supabase client, helpers
├── hooks/
├── services/
├── assets/
├── .github/
│   └── workflows/
│       └── ci.yml
├── netlify.toml                  ← web deployment only
├── app.json
├── babel.config.js
├── tsconfig.json
├── PROJECT_KNOWLEDGE.md
└── CLAUDE.md
```

### `constants/theme.ts` template (React Native)

```ts
import { ViewStyle } from 'react-native';

export const Colors = {
  background: '#F9FAFB',
  surface:    '#FFFFFF',
  primary:    '#00A76F',
  textPrimary:   '#1C252E',
  textSecondary: '#637381',
  border:  '#F0F2F5',
  success: '#22C55E',
  warning: '#FFAB00',
  error:   '#FF5630',
} as const;

export const Typography = {
  fontSans: 'System',
  xs: 11, sm: 13, base: 15, md: 16, lg: 18, xl: 22,
  regular: '400' as const, medium: '500' as const, bold: '700' as const,
} as const;

export const Spacing = {
  xs: 4, sm: 8, md: 12, lg: 16, xl: 20, '2xl': 24, '3xl': 32,
} as const;

export const Radii = {
  sm: 6, md: 8, lg: 12, xl: 16, full: 999,
} as const;

export const Shadows: { card: ViewStyle } = {
  card: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 3,
    elevation: 2,
  },
} as const;
```

### Install commands (React Native)

```bash
npx create-expo-app@latest <name> --template blank-typescript
cd <name>
npx expo install expo-router react-native-safe-area-context react-native-screens
npx expo install expo-font expo-splash-screen expo-linking expo-status-bar
npm install @supabase/supabase-js                   # if Supabase chosen
npm install zustand @tanstack/react-query           # state + server state
npm install -D eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin
```

For NativeWind (if chosen):

```bash
npm install nativewind && npm install -D tailwindcss
npx tailwindcss init
```

### CI workflow (React Native / Expo)

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:

jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm }
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm test
      - uses: expo/expo-github-action@v8
        with:
          expo-version: latest
          token: ${{ secrets.EXPO_TOKEN }}
      - run: npx expo export --platform web   # verifies web build
```

### Netlify config (React Native web build)

```toml
[build]
  command = "npx expo export --platform web"
  publish = "dist"

[build.environment]
  NODE_VERSION = "20"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

### `package.json` scripts (React Native)

```json
{
  "scripts": {
    "start": "expo start",
    "ios": "expo start --ios",
    "android": "expo start --android",
    "web": "expo start --web",
    "build:web": "expo export --platform web",
    "lint": "eslint app components --ext .ts,.tsx",
    "typecheck": "tsc --noEmit",
    "test": "jest --passWithNoTests",
    "ci": "npm run lint && npm run typecheck && npm run test && npm run build:web"
  }
}
```

### Law 18 — preview for React Native

React Native has no single Vite URL. Instead:

- **Mobile preview:** `expo start` — Claude reports the QR code command but cannot embed a URL.
- **Web preview:** `expo start --web` spawns a local server (default `http://localhost:8081`).

Every response while editing source ends with:

```text
Preview: http://localhost:8081/  ·  status: up   (web)
Mobile: expo start → scan QR
```

### Post-scaffold steps (React Native)

1. Spawn `npx expo start --web` in the background. Report web URL.
2. Create `PROJECT_KNOWLEDGE.md` from the template (§7) — note Platform: React Native / Expo hybrid.
3. Create local `CLAUDE.md` with `@./PROJECT_KNOWLEDGE.md` only — never import `@~/.bk-charterline/CLAUDE.md` (laws load globally via `~/.claude/CLAUDE.md`).
4. Commit: `chore: scaffold <name> expo project`.
5. Push and open the first PR.
6. User triggers `start feature`.

---

## 2-Angular. Web app — Angular scaffold procedure

### Base stack (Angular)

1. Angular CLI (latest) + TypeScript
2. SCSS (default Angular styling)
3. ESLint + Prettier
4. Karma + Jasmine (default) or Jest (if user prefers)
5. Cypress or Playwright for E2E
6. Angular Material / PrimeNG / local per user choice
7. Deployment per user choice

### Component rules (Law 12 — Angular adaptation)

Angular's `@Component` already enforces `templateUrl` + `styleUrls` separation — this satisfies the spirit of Law 12. Every component lives in its own folder:

```text
ComponentName/
  component-name.component.ts
  component-name.component.html
  component-name.component.scss
  component-name.component.spec.ts
```

Banned: inline `template: \`...\`` and `styles: [...]` in production components. Use `templateUrl` and `styleUrls` always.

### Install commands (Angular)

```bash
npm install -g @angular/cli
ng new <name> --routing --style=scss --strict
cd <name>
ng add @angular/material   # if Angular Material chosen
```

### CI workflow (Angular)

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm }
      - run: npm ci
      - run: npx ng lint
      - run: npx ng build --configuration=production
      - run: npx ng test --watch=false --browsers=ChromeHeadless
```

### Post-scaffold steps (Angular)

Same as React — spawn dev server (`ng serve`), create `PROJECT_KNOWLEDGE.md`, create `CLAUDE.md`, commit, push PR.

Law 18 preview URL: `http://localhost:4200/`

---

## 7. `PROJECT_KNOWLEDGE.md` template

```markdown
# PROJECT_KNOWLEDGE — <project-name>

**This project is governed by [BK Charterline](https://github.com/BojanKocijan/bk-charterline) — see [`CLAUDE.md`](./CLAUDE.md) for rules and [`~/.bk-charterline`](https://github.com/BojanKocijan/bk-charterline/tree/main) for the knowledge base.**

---

## 1. Project purpose
<one-line description>

## 2. Target users
<who this is for>

## 3. Project-specific components
<!-- Components not in the chosen UI library -->
| Component | Path | Purpose |
|---|---|---|

## 4. Local wrappers / interim overrides
<!-- Overrides of library defaults until upstream fixes land -->
| Wrapper | Path | Why | Ticket |
|---|---|---|---|

## 5. Architectural decisions
| Date | Decision | Why |
|---|---|---|
| <date> | Platform: <Web React / React Native Expo / Angular / Other> | <why this platform> |

## 6. Open questions / known issues
- [ ] <question or issue>

## 7. Upstream PRs opened from this project
| Date | Repo | PR | Status |
|---|---|---|---|

## 8. Data layer
- Default: mocks + localStorage
- DB: none (until upgraded)

## 9. GitHub Issues repo
<!-- Where Claude opens issues: owner/repo format. Defaults to this repo. -->
none yet

## 10. Deployment
<!-- Netlify | GitHub Pages | none | Expo Go (mobile) -->
none yet

## 11. Active feature
| ID | Title | Status | Branch | JTBD |
|---|---|---|---|---|

### Paused features
| ID | Title | Status | Branch | JTBD |
|---|---|---|---|---|

## 12. Feature audit log
| ID | Title | Handed off | Notes |
|---|---|---|---|
```

---

## Changelog

- **1.1.0 (2026-06-06)** — Added platform-target question (Step 0.5) before UI library selection. Scaffold now branches into three tracks: Web React (existing flow, now §2-React), Hybrid React Native / Expo (new §1-RN + §2-RN), and Angular (new §1-Angular + §2-Angular). Added Law 12-RN adaptation for React Native: StyleSheet.create() in .styles.ts files, makeStyles() pattern for dynamic values, banned raw inline style objects in .tsx. Added Expo-specific CI (expo-github-action), Netlify web build config for Expo, and Law 18 dual-surface preview (web URL + mobile QR). Updated PROJECT_KNOWLEDGE.md template to record Platform in §5.
- **1.0.0 (2026-06-06)** — Initial BK Charterline release. Vite + React web scaffold only.
