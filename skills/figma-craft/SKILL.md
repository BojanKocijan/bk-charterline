---
name: figma-craft
description: Figma construction craft — Auto Layout (→ flexbox), constraints, layout grids + breakpoints (1280/720/390), Figma variables bound to design tokens, components/variants/properties, pixel-perfect checklist, Dev Mode handoff readiness, naming conventions. Invoke when the user is building or reviewing a Figma file, asking about Auto Layout, variants, variables, constraints, or handoff-readiness. The Figma MCP is read — the agent guides/reviews/specs; it does not hand-author the canvas.
license: GPL-3.0-only
---

# Figma Craft

This skill covers the **design construction** craft in Figma. It is used alongside `design-critique`, `design-resources`, and `developer-handoff`.

---

## 1. Auto Layout → flexbox mapping

Auto Layout in Figma maps directly to CSS flexbox/grid. When building or reviewing:

| Figma setting | CSS equivalent |
|---|---|
| Direction: Horizontal | `flex-direction: row` |
| Direction: Vertical | `flex-direction: column` |
| Gap (between items) | `gap` |
| Padding | `padding` |
| Hug contents | `width/height: fit-content` |
| Fill container | `flex: 1` or `width: 100%` |
| Fixed size | explicit `width`/`height` |

**Gap, never margins between items.** Use Auto Layout gap, not margins on individual frames, for consistent spacing.

---

## 2. Constraints

| Constraint | Use |
|---|---|
| Left + Right (stretch) | Full-width elements (inputs, banners) |
| Left | Elements that pin to the left edge |
| Right | Elements that pin to the right edge |
| Center | Centered elements (dialog content) |
| Scale | Decorative images that scale with the container |

For responsive frames, use **Left + Right** stretch for content areas and **Fixed** for sidebars/rails.

---

## 3. Layout grids + breakpoints

Use Figma layout grids to mirror the three breakpoints:

| Device | Frame width | Columns | Gutter | Margin |
|---|---|---|---|---|
| Desktop | 1280px | 12 | 24px | 24px |
| Tablet | 720px | 8 | 24px | 24px |
| Mobile | 390px | 4 | 16px | 16px |

Every artboard should have the grid visible so spacing decisions are anchored to the column system.

---

## 4. Figma variables

Use Figma variables (not raw hex) for:

- **Color tokens** — bind to the project's design token set. Modes: Light / Dark.
- **Size tokens** — spacing scale (4, 8, 12, 16, 24, 32, 40, 48px…).
- **Breakpoint tokens** — frame width values.

**Never hardcode hex values in Figma.** Variables make dark-mode and token-update workflows automatic.

---

## 5. Components + variants

When building a component:

1. **Create a base component** with Auto Layout.
2. **Define variants** for each state axis (e.g. Size: sm/md/lg; State: default/hover/disabled/error; Emphasis: primary/secondary/ghost).
3. **Name variant properties** to match the code library's prop names where possible (e.g., if the library uses `size="sm"`, the Figma property is also `Size` with value `sm`).
4. **Add component properties** (text, boolean, nested-instance swaps) for content that varies per use.

---

## 6. Pixel-perfect checklist

Before marking a frame as ready for Dev Mode:

- [ ] All elements use Auto Layout (no absolute positioning unless intentional)
- [ ] All gaps use layout gap, not individual margins
- [ ] All colors bound to Figma variables (no raw hex)
- [ ] All typography uses text styles (no ad-hoc font values)
- [ ] All components use the project's component library (no one-off shapes that replicate a component)
- [ ] Constraints set correctly for responsive behavior
- [ ] Frame named descriptively (not "Frame 123")
- [ ] Layers named semantically (not "Rectangle 45")
- [ ] Grid visible and aligned to the correct breakpoint

---

## 7. Dev Mode handoff readiness

Before sharing a Figma link for developer handoff:

1. **Dev Mode enabled** on the file.
2. **All frames inspectable** — no password-locked pages unless the whole project is locked.
3. **Redlines accurate** — Auto Layout gap/padding values show in the right panel.
4. **Variables resolving** — tokens show their alias name (e.g., `color/primary/500`), not raw hex.
5. **Component specs linked** — component properties visible in the Inspect panel.
6. **Prototype flows visible** — interaction destinations linked so devs can see the full flow.

---

## 8. Naming conventions

| Thing | Convention | Example |
|---|---|---|
| Page | Kebab-case category | `01-flows`, `02-components`, `03-specs` |
| Frame / artboard | PascalCase feature name + breakpoint | `Dashboard/Desktop`, `Dashboard/Mobile` |
| Component | PascalCase + variant suffix | `Button/Primary/Default` |
| Layer | Semantic camelCase | `headerRow`, `iconLeft`, `labelText` |
| Variable collection | TitleCase | `Colors`, `Spacing`, `Typography` |
| Variable | slash-delimited semantic path | `color/text/primary`, `spacing/md` |

---

## 9. Honest boundary

The Figma MCP provides **read access** (inspect, metadata, variables). Claude **guides, reviews, and specs** Figma work — it does not hand-author frames on the canvas. For actions that require the Figma canvas (creating frames, running plugins), the designer does them manually based on Claude's guidance.
