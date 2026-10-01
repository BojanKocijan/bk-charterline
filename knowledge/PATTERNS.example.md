# Cross-Project Pattern Catalogue (EXAMPLE)

Copy this file to `knowledge/PATTERNS.md` (gitignored, same convention as
`projects.yaml`) and let Claude maintain it. It logs bugs and patterns
already solved in one of your projects, so the next time the same symptom
shows up in a *different* project, Claude can recognize it and offer the
known fix instead of re-solving it from scratch.

**Binding (Law 36):** Claude reads this file when a bug fix or pattern it's
about to build looks reusable, checks for a matching entry, and — if found —
surfaces the match and **asks before applying it**, never silently. When
Claude solves something that looks reusable across your other registered
projects (`projects.yaml`), it offers to log a new entry here; it never logs
one without asking first.

---

## Format

Each entry is a level-3 heading `### P-NNN — <short title>`, numbered
sequentially, followed by:

- **Found in:** `<project>` — `<file or area>`
- **Symptom:** what you'd notice if this bug/pattern were present
- **Fix:** the actual fix, concrete enough to apply directly
- **Also check:** which other registered projects might have the same issue
  (if obvious from the symptom — e.g. "any project using the same hook/config")
- **Date:** when it was logged

---

## Entries

### P-001 — example entry, delete me

- **Found in:** `example-project` — `src/hooks/useDebounce.ts`
- **Symptom:** a search input fires one request per keystroke instead of
  debouncing, because the debounce `useEffect` had a missing dependency that
  let a stale closure capture an old callback.
- **Fix:** include the callback in the effect's dependency array, or wrap it
  in `useCallback` at the call site so the reference is stable.
- **Also check:** any other project with a debounced search/filter input.
- **Date:** 2026-01-01
