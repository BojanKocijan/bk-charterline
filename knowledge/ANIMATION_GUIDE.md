# Animation Guide — Design Forge

**Version:** 1.0.0
**Last Updated:** 2026-10-03
**Binding:** Yes — apply these rules to every animation, transition, celebration and motion effect. They were validated in a real project (a mobile-first React app given a fluid, game-like look), by measuring in a real browser and on a phone, not by taste alone.

> **Domain-agnostic.** The rules here are universal. Examples use generic names (a "tile", a "hero", a "character") and the numbers are the ones that worked, offered as starting points. Project-specific components and tunings live in that project's `PROJECT_KNOWLEDGE.md`, never here.

---

## 1. Principles

1. **Every animation answers a question the user has:** where did this come from (a morph), did it save (a celebration), what changed (an entrance), what is it (an introduction). If it answers none, it is decoration — leave it out.
2. **Specific beats generic.** The owner rejected the same glow or spark on every step, and random reactions on a character: *"every step needs something specific to it."* An effect is tied to the field that just changed, plays only for a pick made in that step, and is never chosen at random.
3. **Content first.** An animation never delays or hides content from assistive tech; the element is in the DOM and the accessibility tree from the first render, only its painted state moves.
4. **It must never read as a broken screen.** An entrance that starts bigger than the viewport paints one flat block of colour for a moment, which users report as "an empty screen". Start big, not screen-filling (a scale of 1.7 worked; 2.6 did not) and fade in as it moves.
5. **Measure, don't guess** (§10). Smoothness claims need a profile; sequences need a sampled timeline.

---

## 2. One library, one token file

- Use **one** motion library. Use its lazy-loaded, strict mode (`LazyMotion` with `m` components) so only the features used are bundled, and so a stray full component fails the build.
- **One token file** holds every duration, spring, distance and stagger (`SPRING_SOFT`, `SPRING_SNAPPY`, a slide distance, a stagger, a maximum number of staggered items). Nothing invents its own value; a new value goes into the file first.
- **A single root** (`MotionRoot`) sets the library's reduced-motion handling to follow the user's setting for every component beneath it.
- Past about **8 children nothing extra animates**, so a big list never plays a long cascade.

## 3. What may animate

**Only `transform` and `opacity`** animate: they run on the compositor and cost no layout. Exceptions must be short and justified:

| Exception | Why it is allowed |
|---|---|
| A short `blur` (about 0.45 s or less) | The "mist" of a morph between two characters, and the ink-bleed of a stamp; it ends at `none`, so a settled screen has no filter layer |
| A relative `top` offset | The screen transition (§5): a transform would break fixed children |
| `borderRadius` during a tile morph | The hero's corners round into its final shape |

Never animate `width`, `height`, `left`, `margin` or a shadow. A bar that fills uses `scaleX` on a full-width bar (the track is the parent), not `width`.

## 4. Reduced motion

- Honour it twice: through the root (declarative components) **and** through the library's `useReducedMotion` hook for anything imperative (`animate()`, motion values).
- Under reduced motion every element is in its **final state** and no sequence runs; the content is still announced. Decide `play` once, at mount, and initialise motion values to their final values when it is off, so there is no flash of the hidden state.
- **Test gotcha:** the hook's result is cached for the whole test file. Mock it (`vi.mock('motion/react', …)` returning a mutable value) when a test needs both modes.

## 5. Screen transitions

- A remount-on-key wrapper that slides the new screen up a little and fades it in. **No exit animation**: switching never waits on the old screen, and an old and a new screen are never on screen together.
- **Slide with a relative `top` offset, not a transform.** While any ancestor has a transform, a `position: fixed` child (a footer above the bottom nav) is placed against that ancestor instead of the viewport: it sat 56 px too high for the length of the animation and then jumped. A relative offset moves only its own box.
- If a list item changes in place (a number on a dial), the old item must leave **at once** (`exit` with duration 0), or two items overlap for a moment and read as a doubled element.

## 6. Morph from a pressed tile into the detail screen

The detail screen's hero grows out of the tile the user pressed.

- The press stores the tile's rectangle **in memory only**; the screen takes it **once**. A rectangle older than about 2 s, for another item, or already taken is ignored, so a screen opened any other way (a refresh, a deep link, returning from an editor) simply opens normally and never replays.
- Provide a **peek** (`has`) that does not consume the rectangle, for code that must decide what to do before the morph runs.
- Run it as **one animation with a start and an end value per property** (`x`, `y`, `scale`, `opacity`, `borderRadius`). Two animations queued on the same element in the same frame collapse into the last one: the hero is never seen at the tile.
- Skip it when the rectangle or the target cannot be measured, or under reduced motion.

## 7. Entrances, fills and counts

| Piece | Behaviour |
|---|---|
| **Grow-in** | Scale from about 0.92 and fade; one per section, started when it scrolls into view |
| **Stagger list** | Children arrive about 0.04 s apart; capped (§2) |
| **Fill bar** | `scaleX` from 0 over about 0.6 s, bars about 0.06 s apart, each starting when it scrolls into view |
| **Count-up** | Counts on from the value already shown (never back to 0) over about 0.7 s; the final number is the accessible name from the first render |

Loading states keep a fixed layout (skeletons of the final shape), so data arriving late moves nothing: with the hero's layout fixed, the measured layout shift was 0 even with the API 400 ms late.

## 8. Per-step effects, introductions and celebrations

### Per-step effects (wizards and editors)
- One effect per step, specific to it: a reveal for a body type, a paint splat for a colour, a sparkle on the eyes for an eye colour, a number that swells in the direction of change. Each plays **only for a pick made in that step** (track the category of the last pick), never when the step is merely opened.
- A display that belongs to a step (a big number behind the character) stays while the step is open; it is not an effect.
- The **first** appearance of a big element may be dramatic; **later changes** (a dial ticking) are a quick swap in the direction of the change, never a full entrance on every tick.

### Introductions (an arena-style arrival)
A sequence for an element a user has just opened, "like a player being presented":

| Beat | When | What |
|---|---|---|
| Number | 0 to about 0.5 s | Starts large and faint, drops past its size with a hard stop (an undershoot to 0.93), settles; one short shake of about 8 px on impact |
| Team | from about 0.35 s | Stamped on: larger and tilted a few degrees, settles flat with a brief blur that clears |
| Name | from about 0.6 s | Pops up with an overshoot (scale to about 1.1 and back) |

Rules that made it work:
1. **Compose with motion values on the one element.** The element already follows scroll (opacity and scale from the scroll position); multiply the arrival value into it (`useTransform([scroll, arrival], ([a, b]) => a * b)`). **Do not wrap the element**: a wrapper with a transform or opacity creates a stacking context and cuts a `mix-blend-mode` (multiply into a background) off from what is behind it.
2. **Play once, only on a user-initiated entry:** when the screen opened from a tile (after the morph, with a short wait) or has no tile at all; not on a data refresh, on return from an editor, or on scrolling back up.
3. Everything starts hidden only visually; the content is in the accessibility tree at the first render.
4. Verify the sequence by **sampling computed style every 50 ms** in a real browser (scale, opacity, offset, filter of each element), not by eye.

### Celebrations
- **Confetti** (a burst plus falling pieces, drawn with the motion library) for saves and rewards. A heavier Lottie player was considered and rejected for these: the confetti is lighter and matches the app's own look.
- About **2.2 s**, then a callback that closes the screen. It plays **only after success**, never on an error; it **blocks taps** while it plays, so a saved form cannot be saved twice; the message is announced to screen readers; green for a save, gold for a reward; under reduced motion the badge and message show still for the same time.
- A reward that can be earned again (a badge) is remembered per user so it celebrates once, and the memory is cleared when the identity changes.

## 9. Typography under animation

A **single-weight display font** (a slab-serif numeral face with only a 400 weight) styled bold gets a browser-invented bold. iOS Safari paints that as the glyph filled and then stroked, both in the same translucent colour, so the inside of each digit is two layers deep and the rim one: a bright rim with a dark core that users describe as "doubled" or "with a shadow". Chromium paints it as one path, so **it does not show on desktop or in automated checks**.

- Use the font's real weight: `font-normal` plus `font-synthesis-weight: none`.
- Keep the translucent ink on the glyph only after confirming on a real iPhone; if a core still shows, use a solid colour with the element's `opacity` instead.
- Remember to re-check the digit size: the real weight is a little narrower than the fake bold.

## 10. Measuring

Do this before claiming a screen is smooth, and again after any change to its landing:

1. Emulate a phone with the CPU throttled (4×) through the browser's debugging protocol (`Emulation.setCPUThrottlingRate`).
2. Record **long tasks** and **layout shifts** with `PerformanceObserver` (`longtask`, `layout-shift`) from the click; run it with the API instant and with every request delayed (about 400 ms).
3. For a stubborn long task, record a **CPU profile** (`Profiler.start` / `stop`) and sum self time per function: the answer is usually one function, not the animation. (In the project it was the per-pixel recolour of character art: the roster tile had already done the identical work.)
4. Targets: **no task over 50 ms** during the landing, **layout shift 0**.
5. **Reuse before you warm up.** If two screens need the same derived work (a recolour of the same image in the same colours), cache the result (a small LRU keyed by the inputs; each entry can be megabytes) instead of adding a warm-up step.
6. Keep the measuring spec out of the repository (a throwaway), and put its numbers in the PR.

## 11. Testing animations

- jsdom and happy-dom do not run layout or real animations: assert **classes, inline initial styles and final states** (with reduced motion mocked), and that the content is in the accessibility tree.
- **A test that changes a value while a native animation is running must remove the browser's animation API for that file** (`delete Element.prototype.animate`), so the library uses its own JavaScript animations. Otherwise happy-dom rejects the cancelled animation's `finished` promise with nothing listening: *"AbortError: The animation was canceled"* is reported as an **unhandled error** and the test run exits non-zero **even though every test passes**.
- **Read the exit code and the `Errors` line of the unit run, not only the pass count.** A hosting build that runs `npm run test:run && npm run build` fails its deploy on that exit code. Run it exactly as CI does (`CI=true`), to a log, before pushing.
- Verify the real look and timing in a real browser (a screenshot or a sampled timeline), and on a phone for anything that is platform-specific (§9).

## 12. Checklist before opening a PR with animation

- [ ] Only `transform` and `opacity` (plus the listed exceptions); values come from the token file.
- [ ] Reduced motion: final state, no sequence, content in the accessibility tree.
- [ ] No wrapper around an element that uses a blend mode; no start state that fills the screen.
- [ ] An old and a new element never overlap; entrances play once, on a user-initiated entry only.
- [ ] Measured: no task over 50 ms, layout shift 0, API instant and delayed.
- [ ] `CI=true` unit run exits 0 with no `Errors` line; animation tests removed the animation API where needed.
- [ ] Checked on a real phone for platform-specific rendering.

---

## Changelog

- **1.0.0 (2026-10-03)** — Initial version, from the fluid, game-like UI work of a real project: principles, one library and token file, what may animate, reduced motion, screen transitions, tile morph, entrances and fills, per-step effects, introductions, celebrations, faux-bold typography, measuring, testing (including the unhandled-error gotcha that fails a build) and a PR checklist.
