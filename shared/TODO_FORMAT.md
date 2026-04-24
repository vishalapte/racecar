# TODO List Rendering Format

Accessed via [`../README.md`](../README.md). If you arrived here directly, read that first.

When asked for a sorted TODO view (e.g. `/todo`, "show TODO", "sort TODO by DAG", "what's open"), render the project's `TODO.md` in the exact format below. No emojis — the `L0 > L1 > … > Ln` ordering is self-explanatory.

## Grouping

Group all open items by DAG level: `L0`, `L1`, `L2`, …, `Ln` (where `Ln` is reserved for items the user has explicitly designated "LAST"). Skip the `## Completed` section entirely — open items only.

## Level headers

Single-line header per non-empty level:

- `L0 — No internal deps, start anytime`
- `L1 — Depend on L0`
- `L2 — Depend on L1`
- (continue as needed; each level depends on the level above)
- `Ln — LAST` (explicitly-last items)

## Per-level table

Render a Unicode box-drawing table with these columns:

- **L0**: `Prio | Item | Why this tier`
- **L1+**: `Prio | Item | Depends on`

Use the characters `┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼ ─ │`. Do not use ASCII tables (`+---+`).

## Row ordering

Within each level, sort by priority `P0` → `P3` (highest first). Break ties on TODO id ascending (`1A < 1B < 2A`).

## Item cell

`{TODO-id} {short title, ≤8 words}`. If one TODO id has parts that live at different levels, split it with a stable suffix. Suffixes can be alphabetical (`2B-a`, `2B-b`) or semantic (`2B-qp`, `2B-dedup`, `2D-floors`, `2D-override`) — prefer semantic when the parts have distinct identities. Use the same suffix consistently across sessions.

## Priority labels

Values are literally `P0`, `P1`, `P2`, `P3` — nothing else. `P0` = highest within its level. `P3` = lowest / deferred.

## Sprint order footer

After all level tables, append a numbered list headed `Suggested sprint order:`. Reference items by `{TODO-id}` only — do not restate titles. One clause per step (today, next, parallel, background, defer).

## Do not

- Do not reformat, paraphrase, or rewrite the underlying `TODO.md` file itself. Just render.
- Do not include items from the `## Completed` section.
- Do not add prose before or after the output. Tables + sprint order are the entire response.
