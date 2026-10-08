# Plan: an opt-in Coworker output style (#229)

Gate tier: Standard (an opt-in file; no law changes)

## Goal

A Claude Code output style that makes Claude a knowledgeable coworker with a sense of humor: dry, a little sarcastic, playing along with the rules ("I know I can't merge, just joking 🙂"). It's off until the user turns it on, and it now and then says how to turn it off.

## Why an output style, not a law

- Claude Code loads an output style only when the user picks it, so it adds nothing to the rules' 33,000-token budget for anyone else.
- `keep-coding-instructions: true` keeps Claude Code's coding instructions; the laws load from `CLAUDE.md` as always. The style only changes the voice.
- Users switch with `/output-style` or the app's output style setting; **Default** turns it off.
- Ruled out: the ready-made styles in [awesome-claude-code-output-styles-that-i-really-like](https://github.com/hesreallyhim/awesome-claude-code-output-styles-that-i-really-like) (MIT). They're full costumes (pirate, zen master, tabloid), fun once and tiring by the third session. We take only the file format.

## The style: `output-styles/coworker.md`

Frontmatter: `name: Coworker`, a one-line `description`, `keep-coding-instructions: true`. About 15 lines of instructions:

1. **Coworker first.** Knowledge, accuracy and the laws come before any joke. A joke never changes a fact, a number, an announcement or the merge order.
2. **Humor:** dry and situational, about once every few replies, never the same joke twice in a session, at most one emoji per reply.
3. **Plays along with the rules,** never complains about them: *"I'd love to, but Law 7 and I have an agreement 🙂 It's all yours."*
4. **Teases the situation, never the person:** no jokes about the user's typos, skills or decisions.
5. **Chat only.** Commits, PR bodies, issues, release notes, docs and code comments stay plain.
6. **Goes quiet** during incidents, a leaked secret, a failed deploy or CI, or when the user sounds frustrated or in a hurry, and stays plain until the mood lifts.
7. **The off switch:** with the first joke of a session, one short line: *"Too much? `/output-style default` brings back plain me."* Not again in that session.
8. Follows the reply language (Law 1).

## Where it ships

- **Plugin installs:** Claude Code loads `<plugin>/output-styles/*.md` itself.
- **`install.sh` installs:** link `output-styles/*.md` into `~/.claude/output-styles/`, using the same `link_into` and `prune_dangling` as agents and skills. The summary line becomes "Linked 9 agents, 18 skills and 1 output style".
- Never switched on for anyone: install doesn't touch the `outputStyle` setting.

## Docs

- README: a short "A coworker with a sense of humor" section on turning it on, turning it off, and where the jokes never go.
- `RELEASES.md`: an Unreleased note.

## Tests

- `tests/test_update.py`: the install links the style into `~/.claude/output-styles/`, an update keeps it, and a user's own file with the same name is never overwritten (the same cases as skills).
- A test that `output-styles/coworker.md` has `name`, `description` and `keep-coding-instructions: true`, and names the off switch.
- By hand before the PR: turn it on in a session and check the switch name shows up (a plugin style may show under a plugin prefix), then turn it off.

## PRs

One PR, about 120 lines across 5 files: the style, `install.sh`, the tests, README and RELEASES. It ships in the next release; no extra steps after merging beyond `update rules`.

## Edge cases

- **A user already has `~/.claude/output-styles/coworker.md`:** skipped and named in the install summary, never overwritten.
- **The style drifts back to the default tone in a long session** (reported by others): the instructions stay short and concrete, which helps; there's nothing to enforce.
- **A joke lands in a commit message:** rule 5 forbids it, and the Law 13 hook still checks the format.
- **The user writes in another language:** the humor follows Law 1's reply language.
