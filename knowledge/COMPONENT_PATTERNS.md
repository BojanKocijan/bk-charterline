# Component Patterns — BK Charterline

**Version:** 1.6.1
**Last Updated:** 2026-10-05
**Binding:** Yes — these patterns represent validated, reusable solutions established across projects. Apply them before building from scratch.

> **Domain-agnostic.** The patterns here are universal. Code examples use a generic CRUD domain (entities like `Customer`, `Order`, `Invoice`, `Task`) **purely as illustration** — substitute your project's own entities. Nothing in this file is tied to a specific project; project-specific component inventories live in that project's `PROJECT_KNOWLEDGE.md §3`, never here.

---

## 1. ResponsiveModal

Forms and creation dialogs should adapt to breakpoint rather than always using a bottom sheet.

```
Desktop (≥1024px) → centred Dialog overlay (Radix Dialog)
Mobile/tablet     → bottom Sheet (Radix Sheet, slides from bottom)
```

**Implementation:**
```tsx
// src/components/shared/ResponsiveModal.tsx
import { useIsDesktop } from '@/hooks/useIsDesktop'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Sheet, SheetContent } from '@/components/ui/sheet'

export function ResponsiveModal({ open, onClose, title, children }) {
  const isDesktop = useIsDesktop() // default 1024px breakpoint

  if (isDesktop) {
    return (
      <Dialog open={open} onOpenChange={onClose}>
        <DialogContent className="max-w-lg rounded-2xl p-0 gap-0">
          <DialogHeader className="px-6 pt-6 pb-0">
            <DialogTitle>{title}</DialogTitle>
          </DialogHeader>
          <div className="px-6 pb-6 pt-5">{children}</div>
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent side="bottom" className="rounded-t-2xl p-0" hideClose>
        {/* handle + title + X + children */}
      </SheetContent>
    </Sheet>
  )
}
```

**useIsDesktop hook:**
```ts
// src/hooks/useIsDesktop.ts
import { useEffect, useState } from 'react'

export function useIsDesktop(breakpoint = 1024) {
  const [isDesktop, setIsDesktop] = useState(() => window.innerWidth >= breakpoint)
  useEffect(() => {
    const mq = window.matchMedia(`(min-width: ${breakpoint}px)`)
    const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [breakpoint])
  return isDesktop
}
```

---

## 2. Speed-dial FAB (mobile-only)

On mobile apps, replace a single FAB with a speed dial that expands upward. Actions are ordered bottom→top by thumb priority (most important action closest to thumb).

**Pattern:**
```
[New Project] ← disabled/coming soon, furthest from thumb
[New Client]
[Send Invoice] ← primary, closest to thumb
[+] FAB toggle ← bottom-right fixed
```

**Rules:**
- Always `lg:hidden` — desktop navigation handles these actions differently
- FAB stacks with flex-col, actions above the toggle button
- Backdrop div closes dial on outside tap
- Primary action gets `bg-primary`, secondary actions get `bg-white border`
- Disabled items get `opacity-50 cursor-not-allowed`
- Desktop FAB: decide per-project — often hidden in favour of sidebar + header buttons

---

## 3. Breakpoint-aware view toggle

When a page has both a card/grid view and a table/list view:
- **Mobile (<640px):** Always show cards. Hide the toggle entirely. Tables are not usable on small screens.
- **Tablet/desktop (≥640px):** Show toggle. Default to table/list for data density.

```tsx
const isDesktop = useIsDesktop(640) // sm breakpoint
const effectiveView: ViewMode = isDesktop ? view : 'grid'

// In JSX:
{isDesktop && <ViewToggle mode={view} onChange={setView} />}
```

---

## 4. Underline tabs with counts

Filter chips are the wrong pattern for list pages. Use underline-style tabs with count badges.

```
All Clients 20  |  Owing 5       ← Clients
All Invoice 20  |  Open 5  |  Past Due 3  |  Paid 12  ← Invoices
```

**Rules:**
- Never pill/chip filter buttons for primary list filtering
- Count badge sits next to the label, same colour as active/inactive text
- "New" tab (recency-based) is usually useless — prefer action-oriented tabs like "Owing"

---

## 5. Data tables

When displaying structured data (invoices, clients):
- Use a proper `<table>` element with column headers (ALL CAPS, muted, tracked)
- Table is horizontally scrollable (`overflow-x-auto`, `min-w-[580px]`)
- Progressive column reveal: critical columns always visible, secondary hidden at `sm:`/`md:`
- Row hover: `hover:bg-muted/40`, full row tappable → detail sheet
- Actions column: hover-reveal on desktop (`opacity-0 group-hover:opacity-100`), always visible on mobile

---

## 6. Card primary action

On entity cards (clients, projects), the primary CTA should be the **business action**, not navigation.

```
❌ "See details ›"  ← navigation, secondary
✓ "Send Invoice"    ← business action, primary
```

- Full card tap → detail/info sheet
- Primary button → the action the user is most likely to want
- 3-dot menu: `opacity-0 group-hover:opacity-100`, white bg + border + shadow + z-10

---

## 7. Live avatar preview in forms

When creating a contact/client/person, show a live colour-coded avatar that updates as the name is typed.

```tsx
const initials = name.trim().split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
const color = name.trim() ? getAvatarColor(name) : '#e5e7eb'

<div className="w-16 h-16 rounded-full flex items-center justify-center text-xl font-bold text-white"
     style={{ background: color }}>
  {initials || <span className="text-white/50 text-sm">?</span>}
</div>
```

Avatar preview is always text/initials until image upload is explicitly added.

---

## 8. Form field layout in modals

Two-column grid for related pairs (email/phone, company/address). Full-width for primary fields (name).

```
Name *                    (full width)
Email       |    Phone    (two columns)
Company     |    Address  (two columns)
            [Cancel] [Create]  (right-aligned)
```

Labels: ALL CAPS, `text-[12px] font-semibold text-muted-foreground uppercase tracking-wide`

---

## 9. No emojis in UI

Never use emoji characters in interactive UI elements, button labels, status text, or any user-facing copy.

Use Lucide icons or plain text instead:
- `💰` → `<CreditCard className="w-4 h-4" />`
- `✓` → `<Check className="w-4 h-4" />`
- `⚠` → `<AlertTriangle className="w-4 h-4" />`
- `→` → `<ChevronRight className="w-4 h-4" />`

Only add emojis if the user explicitly requests them.

---

## 10. Touch target sizing (mobile-first apps)

For apps used on the go — in the field, on-site, or one-handed on a phone:

| Element | Minimum size |
|---|---|
| Inputs | h-12 (48px) |
| Primary buttons | h-12, py-3 |
| List rows | min 64px height |
| Avatar (cards) | 48px |
| Avatar (list rows) | 32-40px |
| Page padding | px-5 (20px) |

See also §21 for the phone sizes validated since (48 px header controls, 56 px sheet rows) and §20 for menus and dialogs as bottom sheets.

---

## 11. 3-dot context menu on cards

Entity cards (clients, projects) should have a context menu accessible via a 3-dot button (MoreHorizontal icon).

### Device-aware visibility — hover AND keyboard
```tsx
// Always visible on touch; hover-reveal on mouse; also reveal when card has keyboard focus
'[@media(hover:none)]:opacity-100',
'[@media(hover:hover)]:opacity-0 [@media(hover:hover)]:group-hover:opacity-100',
'group-focus-within:opacity-100',  // ← required — keyboard users see the trigger as they Tab into the card
```

**Known miss (found 2026-06-14):** The original pattern omitted `group-focus-within:opacity-100`. On desktop (hover:hover), the trigger stayed `opacity-0` even when focused via Tab — keyboard users could Tab to it but never see it. Always include all three classes.

### Card body must be a `<button>`, not a `<div>`
**Critical — WCAG 2.1.1:** The clickable area of a card must be a `<button type="button">` (or `<a>` for navigation), never a bare `<div onClick>`. Tab skips non-interactive elements entirely.

```tsx
// ✅ Correct — keyboard reachable, Enter/Space activates
<button
  type="button"
  onClick={onDetails}
  aria-label={`View details for ${client.name}`}
  className="flex items-center gap-3 flex-1 min-w-0 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 rounded-lg"
>
  <Avatar /> <Name />
</button>

// ❌ Wrong — Tab skips it, Enter does nothing
<div onClick={onDetails} className="cursor-pointer flex-1">
  <Avatar /> <Name />
</div>
```

### No event conflict rule
**Critical:** The 3-dot trigger must be a SIBLING to the clickable area, NOT a child of it. If the whole card is clickable, the trigger must sit outside that clickable button.

```tsx
// ✅ Correct — button body + sibling 3-dot, no conflict
<div className="flex items-start gap-2">
  <button type="button" onClick={onDetails} className="flex-1 text-left ...">
    <Avatar /> <Name />
  </button>
  <DropdownMenu>                                 ← sibling, no conflict
    <DropdownMenuTrigger className="... [@media(hover:none)]:opacity-100 ... group-focus-within:opacity-100">
      <MoreHorizontal />
    </DropdownMenuTrigger>
  </DropdownMenu>
</div>

// ❌ Wrong — 3-dot inside clickable div, stopPropagation needed but brittle
<div onClick={onDetails}>
  <Avatar /> <Name />
  <DropdownMenuTrigger onClick={e => e.stopPropagation()}>  ← fragile
```

### Standard actions for client cards
1. **Send Invoice** — opens wizard with client pre-selected
2. **Edit Client** — opens create form pre-filled, "Update" button
3. **View Details** — opens detail sheet
4. **Remove Client** — shows confirmation dialog (soft delete)

### Soft delete pattern
Always soft-delete rather than hard-delete for entities that have related records (invoices, projects).
```ts
// Storage
removeClient: (id) => {
  lsSet(KEY, lsGet(KEY).map(c => c.id === id ? { ...c, deleted_at: new Date().toISOString() } : c))
}
getClients: () => lsGet(KEY).filter(c => !c.deleted_at)
```

### Confirmation dialog
Always confirm destructive actions via a `ResponsiveModal`:
```tsx
<ResponsiveModal open title="Remove client" onClose={() => setTarget(null)}>
  <p>Remove <b>{target.name}</b>? Their invoices will not be deleted.</p>
  <div className="flex justify-end gap-3 pt-4">
    <button onClick={() => setTarget(null)}>Cancel</button>
    <button onClick={handleConfirm} className="... bg-destructive">Remove</button>
  </div>
</ResponsiveModal>
```

---

## 12. Create = Edit — one component, always

**Rule:** Every entity (invoice, client, project, etc.) has exactly **one form component** that handles both creating a new record and editing an existing one. There is never a separate "detail view" or "edit modal" — the same component, same layout, same sections.

**Implementation pattern:**
```tsx
// The component accepts an optional existing record
interface InvoiceFormProps {
  invoice?: Invoice | null        // absent = create mode, present = edit mode
  onSaveInvoice: (inv: Invoice) => void
  onUpdateInvoice?: (id: string, data: Partial<Invoice>) => void
}

// State initialisation branches on the prop
const [state] = useState(() =>
  invoice ? buildFromInvoice(invoice, contractor) : buildInitialState(contractor, count)
)

// Save branches on the prop
function save() {
  if (invoice) onUpdateInvoice(invoice.id, data)   // edit
  else         onSaveInvoice({ id: genId(), ...data }) // create
}
```

**Desktop:** same split layout (form left, live preview right) in both modes.
**Mobile:** same tab switcher (Form / Preview) in both modes.
**Header:** "Create Invoice" vs "Edit Invoice" — only the title changes.
**Extra sections in edit mode only:** status badge in header, Mark as Paid (if unpaid).

**Why:** Consistency is trust. Users who learned to create an invoice already know how to edit one. Two UIs for the same concept = twice the cognitive load, twice the maintenance.

**Applies to:** Invoices ✓ (implemented) · Clients · Projects · any future entity.

---

## 13. Desktop "Add new" popover — mirrors mobile FAB

The desktop sidebar primary CTA must offer the same actions as the mobile speed-dial FAB, presented as a `DropdownMenu` popover.

**Rule:** One mental model across breakpoints — the user always reaches "create something" from the same conceptual button, just rendered differently.

| Surface | Component | Trigger |
|---|---|---|
| Mobile | Speed-dial FAB (bottom-right, fixed) | `+` button expands upward |
| Desktop | `DropdownMenu` in the sidebar | `Add new` button with chevron |

**Standard items (order fixed):**
1. **Send Invoice** — primary action, always first
2. **New Client** — secondary
3. **New Project** — disabled with "soon" label until the feature ships

```tsx
// Desktop sidebar
<DropdownMenu>
  <DropdownMenuTrigger asChild>
    <button className="w-full flex items-center justify-between ... bg-primary text-white">
      <span className="flex items-center gap-2.5">
        <Plus className="w-4 h-4" /> Add new
      </span>
      <ChevronDown className="w-4 h-4 opacity-70" />
    </button>
  </DropdownMenuTrigger>
  <DropdownMenuContent side="bottom" align="start" className="w-52">
    <DropdownMenuItem onClick={onGetPaid}>
      <CreditCard className="w-4 h-4 mr-3" /> Send Invoice
    </DropdownMenuItem>
    <DropdownMenuItem onClick={onAddClient}>
      <Users className="w-4 h-4 mr-3" /> New Client
    </DropdownMenuItem>
    <DropdownMenuSeparator />
    <DropdownMenuItem disabled>
      <FolderOpen className="w-4 h-4 mr-3" /> New Project
      <span className="ml-auto text-[11px]">soon</span>
    </DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
```

**Why:** Users switching between phone and desktop should find the same creation flow. Never put a single hard-coded action (e.g. "Send Invoice") in the primary sidebar CTA — always use the shared menu so new entity types can be added in one place.

---

## 14. Fixed FAB — pointer-events and scroll clearance

Two rules that must always be applied together when using a fixed FAB over scrollable content.

### 14a. Container must be `pointer-events-none`

A fixed FAB container has a large bounding box that swallows pointer events even when the FAB is closed and actions are invisible. This blocks clicks on cards beneath it.

```tsx
// ✅ Correct — container is transparent to events, only the button catches them
<div className="fixed right-4 bottom-[80px] z-50 flex flex-col items-end gap-3 pointer-events-none">
  <div className={fabOpen ? 'pointer-events-auto ...' : 'pointer-events-none ...'}>
    {/* speed dial actions */}
  </div>
  <button className="w-14 h-14 ... pointer-events-auto">
    {/* FAB toggle */}
  </button>
</div>

// ❌ Wrong — container has no pointer-events-none, blocks entire bottom-right zone
<div className="fixed right-4 bottom-[80px] z-50 ...">
```

### 14b. Scrollable lists need `pb-28` FAB clearance

The FAB (56px tall, `bottom-[80px]`) overlaps the bottom ~72px of the content area. Without bottom padding the last list item is permanently obscured.

```tsx
// Every scrollable list on a page with a FAB
<div className="flex-1 overflow-y-auto pb-28">
  {items.map(...)}
</div>
```

`pb-28` = 112px — enough to scroll the last item fully above the FAB even accounting for safe-area-inset.

---

## 15. React Router navigation — `useNavigate`, never `onNav`/`onBack` prop drilling

Multi-screen apps use **React Router** (`react-router-dom`). Each page is a real route with its own URL — browser back/forward works, deep links work, and navigation is a one-liner from anywhere in the tree.

**Rule:** Navigation happens via `useNavigate()`, not via `onNav` / `onBack` / `onScreenChange` callbacks threaded down through props. The old screen-state model (`const [screen, setScreen] = useState<Screen>()` + callback props) is banned for anything beyond a single screen.

**Route-wrapper pattern.** Keep page components presentational and route-agnostic; put the routing glue in a thin wrapper defined alongside the route tree:

```tsx
// App.tsx — thin route wrapper injects data + navigation
function ClientsRoute() {
  const { clients, invoices, saveClient } = useAppContext()
  const navigate = useNavigate()
  return (
    <Clients
      clients={clients}
      invoices={invoices}
      onSave={saveClient}
      onInvoice={cl => navigate('/app/invoices/new', { state: { client: cl, returnTo: '/app/clients' } })}
    />
  )
}
```

The page (`Clients`) still receives small intent callbacks (`onInvoice`), but it never knows about routes or URLs — the wrapper owns that. This keeps pages testable in isolation and navigation logic in one place.

**Shell layout via `<Outlet />`.** A persistent shell (sidebar + bottom nav) wraps all authenticated routes through a layout route, so it isn't re-mounted on every navigation:

```tsx
<Routes>
  <Route path="/" element={<Landing />} />          {/* public */}
  <Route path="/login" element={<Login />} />        {/* public */}
  <Route path="/app" element={<AppLayout />}>        {/* Shell + <Outlet/> */}
    <Route index element={<Navigate to="home" replace />} />
    <Route path="home" element={<HomeRoute />} />
    <Route path="clients" element={<ClientsRoute />} />
    {/* … */}
  </Route>
  <Route path="*" element={<Navigate to="/" replace />} />
</Routes>
```

---

## 16. Route-level data via root context — not prop chains

App state is provided **once** at the root and consumed directly by route components via a context hook. This avoids prop-drilling data across route boundaries (the router renders route components directly, so there's no natural prop path to them anyway).

```tsx
// context/AppContext.tsx
export const AppContext = createContext<AppContextValue | null>(null)
export function useAppContext() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useAppContext must be used within AppProvider')
  return ctx
}

// App.tsx — data sourced once, injected once
const data = useData()          // localStorage/Supabase adapter
const { toasts, toast } = useToast()
<AppContext.Provider value={{ ...data, toast, toasts }}>
  <Routes>{/* … */}</Routes>
</AppContext.Provider>
```

Route wrappers call `useAppContext()` to read state and actions. For larger apps that outgrow context, graduate to Zustand/Jotai (declare it in `PROJECT_KNOWLEDGE.md §5`) — but context is the default and is enough for most mockups and single-user tools.

---

## 17. Transient route-to-route state via `location.state` + `returnTo`

When one route needs to hand a complex object (a selected client, an invoice being edited) to another route, pass it through `location.state` — not URL params. Keeps deep-link URLs clean and avoids serializing objects into the path.

```tsx
// caller — send the payload + where to come back to
navigate('/app/invoices/new', { state: { client, returnTo: '/app/clients' } })

// receiver — read it, default sensibly
const { client, invoice, returnTo = '/app/invoices' } =
  (useLocation().state as { client?: Client; invoice?: Invoice; returnTo?: string }) ?? {}
// …on save/cancel:
navigate(returnTo)
```

**Always carry `returnTo`** so the destination knows where "back" goes — the same creation route can be reached from Clients, Invoices, or Home, and each should return to its origin. `location.state` is intentionally **not** persisted across a hard reload — correct for a creation flow (a refreshed "new invoice" page should start clean). If the data must survive reload, it belongs in context or storage, not `location.state`.

---

## 18. Shared component promotion — when to extract, how to track

### The rule

A component living inside a page file should be promoted to `src/components/shared/` when **any** of these is true:

- It appears (or will appear) on **2 or more surfaces** — pages, admin panel, sheets, future mobile views
- It encapsulates **domain logic** worth centralising (validation, formatting, business rules)
- It has a **visual identity** that must stay pixel-identical across contexts (status badges, avatars, card layouts)

A component that is purely local to one screen and has no foreseeable reuse stays in its page file.

### Session protocol

At the start of any session that touches component work, Claude must:

1. Read `PROJECT_KNOWLEDGE.md §3b` (current shared library) and `§3c` (promotion candidates).
2. List them concisely and ask: *"Any new candidates to promote before we start?"*
3. Wait for the user's answer before writing any new component code.

This keeps the shared library intentional — not grown through drift.

### Promotion checklist (per component)

When promoting a page-level component to shared:

1. **Create the 4-file folder** in `src/components/shared/<Name>/`:
   - `<Name>.tsx` — JSX only, no inline styles
   - `<Name>.styles.ts` — all `cn()` variants / styled-components
   - `<Name>.types.ts` — prop interface
   - `index.ts` — barrel re-export
2. **Move** the component function, update all import paths.
3. **Export** from `src/components/shared/index.ts`.
4. **Update** `PROJECT_KNOWLEDGE.md §3b` (add row) and `§3c` (remove candidate row).
5. **Open a PR** — even a pure extraction gets its own commit.

### Flat vs folder

`src/components/shared/` contains two shapes:

| Shape | When | Example |
|---|---|---|
| **Flat file** (`.tsx` only) | Simple, stateless, no complex styling | `Avatar.tsx`, `StatusBadge.tsx` |
| **Folder** (4 files) | Has styles, types, or will grow | `FilterBar/`, `ValidatedInput/`, `Timeline/` |

New promotions always start as a **folder** — simpler components can be flattened later but folders never need to be restructured as the component grows.

**Track candidates per project, not here.** Keep your project's promotion candidates (component, where it currently lives, promote-when) in that project's `PROJECT_KNOWLEDGE.md §3` — this shared file stays domain-agnostic.

---

## 19. State-first component design

**The rule:** before writing a single line of JSX for a shared component, enumerate every state it can be in. States discovered after the fact get bolted on inconsistently. States planned upfront become the component's API.

---

### The four state categories

Every data-aware component has states in four categories. Work through all four before opening a file.

| Category | Examples |
|---|---|
| **Data states** | `empty` · `loading` · `error` · `populated` |
| **Interaction states** | `default` · `hover` · `focus` · `active` / `pressed` · `disabled` |
| **Content / business states** | Entity-specific: invoice → `outstanding` / `sent` / `viewed` / `paid` / `overdue`; input → `default` / `validating` / `verified` / `invalid` |
| **Edge case states** | Long text truncation · zero or negative values · missing optional fields · empty avatar (no name) |

Not every component needs all four. A static `Avatar` only needs edge cases. A form field needs interaction + validation. An entity card needs all four.

---

### TypeScript union types — never boolean flags

Boolean flags multiply into impossible combinations. Union types make all valid states explicit and all invalid states unrepresentable.

```ts
// ❌ boolean flags — 2⁵ = 32 combinations, most impossible
interface InvoiceCardProps {
  isPaid?: boolean
  isOverdue?: boolean
  isSent?: boolean
  isViewed?: boolean
  emailFailed?: boolean
}

// ✅ union type — exactly 5 content states, email status separate
type InvoiceStatus = 'outstanding' | 'overdue' | 'sent' | 'viewed' | 'paid'
type EmailStatus = 'sent' | 'failed' | null

interface InvoiceCardProps {
  status: InvoiceStatus
  emailStatus?: EmailStatus
}
```

**Rule:** if you catch yourself writing `isX?: boolean` on a shared component, stop. Add the state to the union type instead.

---

### The state matrix — document it in the component file

Every shared component's `.types.ts` file must include a comment block listing all states before the interface:

```ts
/**
 * InvoiceCard — state matrix
 *
 * Content states (driven by InvoiceStatus):
 *   outstanding  — grey left border, amber due-date label
 *   overdue      — red left border, red amount, "X days late" label
 *   sent         — blue left border, "Awaiting payment" label
 *   viewed       — amber left border, "Seen" label (email tracking)
 *   paid         — green left border, "Paid {date}" label
 *
 * Overlay states:
 *   email-failed — red banner below card body with Retry button
 *
 * Interaction states:
 *   hover        — shadow-md + -translate-y-0.5
 *   focus-within — ring-2 ring-primary/30 (keyboard nav)
 *
 * Edge cases:
 *   no invoice number     — number field omitted silently
 *   client name > 30 chars — truncate with ellipsis, full name on hover tooltip
 *   amount = 0            — show €0 (valid for credit/void invoices)
 *   no due date           — omit due-date label entirely
 */
```

This comment is the contract. If a new state is added, the comment is updated first — that forces the decision to be intentional.

---

### State transitions — make them explicit

For components that move through states over time, document the valid transitions:

```
InvoiceCard state machine:
  outstanding ──[email sent]──► sent
  sent        ──[pixel fired]──► viewed
  viewed      ──[marked paid]──► paid
  outstanding ──[past due date]──► overdue  (computed, not stored)
  overdue     ──[marked paid]──► paid
  any         ──[email bounce]──► + email-failed overlay (additive, not a status)
  any         ──[archived]──► removed from list (not a visual state — filter)
```

Transitions that are computed (like `overdue`) must never be stored — derive them at render time from the data.

---

### Example — a state inventory for common component types

(Generic; map to your own entities.)

| Component | Content states | Key edge cases | Interaction states |
|---|---|---|---|
| `EntityCard` | the entity's business statuses (e.g. `active` · `pending` · `overdue` · `done`) | missing optional field · very long name (truncate) · failed-action overlay | hover (lift) · focus-within (ring) · 3-dot menu reveal |
| `ValidatedInput` | default · validating · valid (checkmark) · invalid (error) · disabled | paste with stray chars stripped · partial entry | focus (ring) · error border |
| `StatusBadge` | one per business status | long/custom status string (truncate) | none (display only) |
| `Avatar` | with name (initials) · no name (placeholder) · with photo | single-word name (one initial) · very short name | none |
| `EmptyState` | no data · loading · error (with retry CTA) | illustration missing (fallback to icon) | CTA hover/focus |

---

### Checklist before writing a shared component

- [ ] State matrix written in `.types.ts` as a comment
- [ ] All content states expressed as a TypeScript union — no boolean flags
- [ ] State transitions documented (if the component moves through states over time)
- [ ] All four categories checked: data / interaction / content / edge cases
- [ ] Each state has a visual spec (border colour, label text, icon, opacity)
- [ ] Empty and error states are designed — not left as "TODO"

---

## 20. Dialogs and menus become bottom sheets on phones — change the shared wrapper, not the call sites

Thumbs reach the bottom of a phone, not the top. A centred dialog or a dropdown that floats under a header button is the
wrong shape for one-handed use. Make **every** dialog and menu a bottom sheet below the `sm` breakpoint (640 px) by changing
the **one shared wrapper** each already goes through, so no screen is edited and none can forget. From `sm` up they are
unchanged. (Complements §1: §1 chooses Dialog or Sheet per form at the desktop breakpoint; this is the project-wide default.)

### Dialogs
- The dialog content is **one element whose classes switch at `sm`** (CSS only, no remount), so a rotation never loses form
  state. Phone: `inset-x-0 bottom-0`, `rounded-t-2xl`, `max-sm:max-h-[90dvh]`, `overflow-y-auto`, slide up/down, bottom
  padding `max(1rem, env(safe-area-inset-bottom))`. From `sm`: the centred box, with the same zoom animation as before.
- A **grab handle** (phone only) that drags down to close; only the handle drags, so scrolling content is never taken for
  a swipe. The swipe presses the real close button, so the normal close path (and any "discard changes?" guard) still runs.
- The footer (Cancel, Save) is **sticky** to the bottom of the sheet so a long form never hides Save.
- A `layout="centered"` prop keeps the box on phones for the rare dialog that is not a form to dismiss (a sign-in card).
- Use `max-sm:` for the phone-only height cap, so a dialog's own `max-h` still rules from `sm` up.

### Menus
- A Radix dropdown positions itself with **inline styles** and cannot be restyled into a sheet. So the menu wrapper chooses
  its branch from a context: on a phone `Menu`, `Trigger`, `Content`, `Item`, `RadioGroup`, `RadioItem`, `Label` and
  `Separator` render the dialog sheet above, with plain buttons for rows; otherwise the Radix dropdown. The menus that use
  the wrapper are written once and are not edited (except for a `sheetTitle` for screen readers).
- The branch comes from a `useIsPhone()` hook (`matchMedia('(max-width: 639px)')` through `useSyncExternalStore`). The usual
  test stub of `matchMedia` never matches, so existing tests keep running the desktop path unchanged.
- **Keep the roles** (`menuitem`, `menuitemradio`, `aria-checked`) so tests and end-to-end selectors written against the
  dropdown still work. A row calls `onClick`, then `onSelect` with a cancelable event, and closes unless a handler calls
  `preventDefault()` — the same contract as Radix.
- Rows are at least **56 px** tall (§21). Sub-menus, checkbox items and shortcuts need no phone version until something uses
  them; say so in a comment rather than building them.

**Verify** by measuring in a real browser at 390 px and 1440 px (the sheet's bottom gap is 0 and its rows are 56 px; at
desktop width it is still the dropdown), then on a real phone — the on-screen keyboard is the risk for any sheet with inputs.

---

## 21. Touch targets and the thumb zone (extends §10)

44 px is the usual minimum and was **not enough** to the people using a phone in the field. Measure real sizes; do not trust
class names (a flex shrink can undercut a `size-11`).

| Element | Phone size |
|---|---|
| Header controls (menu, theme, account buttons) | 48 × 48 px, 22 px icon, at least 8 px apart |
| Menu and list rows in a sheet | at least 56 px tall, 16 px text, the whole row tappable |
| Primary actions | 48 px tall |

- Size up with a `max-sm:` class on top of the desktop class, so desktop is untouched.
- A control floating over imagery (a back or edit button over a hero) is sized by its design; change it only when asked.
- Check by `getBoundingClientRect()` in a real browser at phone width, for every control in the row, and at 360 px for fit.

---

## 22. One top bar for many screens — props, not forks

When two roles (a trainer and a parent) need the same bar with different labels, icons and actions, build **one** bar with
optional props, never a copy. The copy drifts; the prop stays in step.

- `onClose` is optional (nothing to go back to), with `closeLabel` and `closeIcon`; `onEdit` with `editLabel` and `editIcon`;
  each defaults to the original screen's label and icon, so the original screen passes nothing and does not change.
- `placement`: **fixed** over the content (a screen with no app header), or **sticky** as a **zero-height strip** (the bar
  absolutely positioned inside it) for a screen that sits under an app header. A row in the page flow pushes the picture down
  and is not the same look; a fixed bar covers the header's menus. The zero-height sticky strip floats over the content like
  the fixed one, starts below the header, and sticks to the top when the page scrolls.
- The compact identity (small face and name) fades in on scroll in both.

---

## 23. One editor for several roles — a `restrictTo` prop

A role that may change only some fields (a parent, who may recolour but not rename) uses the **same editor** as the full
role, restricted by a prop. The restriction is a UI convenience; **the server is the authority** and re-checks every write.

- `restrictTo="parent"` limits the categories shown, makes the name read-only, and hides everything else; a short line
  names what to ask the trainer for.
- Save sends **only the fields that differ** from the original (a diff), in one request; **nothing changed means close without
  a request**. A field cleared to empty is a change (`null`), not "leave it".
- Map the server's refusals to typed errors the screen understands: too many requests (429) keeps the editor open with a
  plain message; not allowed or no longer editable (403, 409) closes it, hides the entry button and says so.
- Apply the server's **answer** at once (a local override over the loaded record), without waiting for a reload; then the
  saved moment; then any warning the server returned ("another player has this number").
- The same endpoint serves the undo for the owner: send the previous values in one request, as that role.

---

## 24. Every request has a time limit

A lost or very late reply must never leave a dialog on "Saving…" for ever: the work may already be done and the user cannot
tell, cannot close it and cannot retry.

- The one request helper aborts after a fixed time (20 s, a little under the hosting function's own limit) with an
  `AbortController` whose timer covers reading the body and is always cleared. The error carries `timedOut: true` and a plain
  message; an ordinary failure does not.
- A caller that **changed** something treats a timeout as "unknown": reload what it shows, say "it may have saved", and leave
  the form open and closable. A caller that only read shows the message with a retry.
- Test it with fake timers and a fetch that only ends when aborted; check a normal failure is not reported as a timeout and
  the timer is cleared.

---

## 25. Cache derived render work that two screens share

When a list tile and its detail screen draw the **same derived result** from the same inputs (a recoloured image in the same
colours, a computed layout), the detail screen repeating the work is the cost. Find it with a CPU profile before guessing
(the animation guide, §10): in the project it was one per-pixel function, not the animation, and "warming" on tap would not
have helped because the earlier screen had already done the analysis.

- Memoize the **derived output** in a small **LRU** keyed by every input (the source, the layout boxes and each colour), most
  recently used last; cap it by memory (entries of about 2 MB: 16 entries).
- Reuse the **same buffer** wherever it is only read, and draw it with the cheap call; never mutate a cached result.
- Test: the same inputs return the same object; each different input is a different entry; the least recently used is dropped
  first; the result equals the uncached computation.

---

## Changelog

- **1.6.1 (2026-10-05)** — §20 context-menu cards work by keyboard: the 3-dot trigger also reveals on `group-focus-within`, the card body must be a `<button>` (or `<a>`), never `<div onClick>` (WCAG 2.1.1), and the no-event-conflict example uses the button body.

- **1.6.0 (2026-10-03)** — Added Patterns 20–25, validated in a real mobile-first project: dialogs and menus as bottom sheets on phones by changing the shared wrapper (§20), touch targets and the thumb zone (48 px header controls, 56 px rows; §21), one top bar for many screens with a fixed or zero-height sticky placement (§22), one editor for several roles through a `restrictTo` prop (§23), a time limit on every request (§24) and caching derived render work two screens share (§25).

- **1.5.0 (2026-06-16)** — Universalized the file: examples reframed as a generic CRUD domain (illustrative, domain-agnostic), removed the project-specific component inventories (they belong in each project's `PROJECT_KNOWLEDGE.md §3`), and genericized provenance. No pattern changed.

- **1.4.0 (2026-06-11)** — Added Pattern 19: State-first component design — the four state categories (data/interaction/content/edge), TypeScript union over boolean flags, the state-matrix comment contract, state-transition documentation, an example state inventory, and the pre-build checklist.

- **1.3.0 (2026-06-11)** — Added Pattern 18: Shared component promotion — the rule (2+ surfaces / domain logic / visual identity), the session protocol (list §3b + §3c before starting component work), the 4-file promotion checklist, and flat-vs-folder guidance.

- **1.2.1 (2026-06-09)** — Added Patterns 15–17: React Router navigation via `useNavigate` (route-wrapper pattern, `<Outlet/>` shell, no `onNav`/`onBack` prop drilling), route-level data via root context, and transient route-to-route state via `location.state` + `returnTo`.

- **1.2.0 (2026-06-08)** — Added Pattern 13 (Desktop Add new popover mirrors mobile FAB) and Pattern 14 (FAB pointer-events-none + pb-28 scroll clearance).
- **1.1.0 (2026-06-08)** — Added Pattern 12: Create = Edit (one component per entity). Binding rule going forward.
- **1.0.0 (2026-06-06)** — Initial version. Covers: ResponsiveModal, speed-dial FAB, breakpoint view toggle, underline tabs, data tables, card primary action, live avatar, form layout, no-emoji rule, mobile touch sizing.
