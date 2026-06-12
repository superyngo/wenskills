# Scrollable List Viewport — Sticky Cursor Scrolling Spec

Implement (or review/fix) the selection-cursor and scrolling behavior of a scrollable list against this spec. It applies to any "viewport + selectable rows" scrolling list UI — TUI, web, or mobile.

## Core principle: data coordinate and screen coordinate MUST be separate

Maintain these three independent pieces of state:

- `selected_index: usize` — position of the selected row within the **full dataset**, range `[0, total_items)`
- `scroll_offset: usize` — the data index the viewport's first visible row maps to, range `[0, max(0, total_items - viewport_height)]`
- `viewport_height: usize` — current number of visible rows (dynamic; updates immediately on terminal/window resize)

**Derived value** (do NOT store it — compute it every render):
- `cursor_screen_row = selected_index - scroll_offset`

Never store "the selection's on-screen position" as independent mutable state; it must always be the difference of the two values above.

## Scrolling rule (sticky cursor / minimal scroll)

After every change to `selected_index`, adjust `scroll_offset` with the following rules, and **only** these two rules:

```
if selected_index >= scroll_offset + viewport_height:
    scroll_offset = selected_index - viewport_height + 1   # overflowed bottom

if selected_index < scroll_offset:
    scroll_offset = selected_index                          # overflowed top
```

**Forbidden** approaches:
- Centering the selection on every move (`scroll_offset = selected_index - viewport_height / 2`)
- Binding `selected_index` and `scroll_offset` in a fixed relationship
- Computing the screen position with `selected_index % viewport_height` (causes the cursor to teleport across pages)
- Touching `scroll_offset` when the cursor has NOT overflowed an edge

## Expected behavior (must hold)

Using `viewport_height = 10`, `total_items = 50` as an example:

1. While the selection moves **inside** the viewport, `scroll_offset` must stay unchanged — only the cursor moves on screen.
2. When the selection reaches the **bottom** of the viewport (screen row = 9), pressing ↓ again pushes `scroll_offset += 1`; the cursor visually stays on the last screen row.
3. Reversing from the bottom with ↑: the cursor first **leaves the bottom and moves up to screen row 0**, with `scroll_offset` unchanged throughout; only after reaching screen row 0 does pressing ↑ push `scroll_offset -= 1`, with the cursor visually staying on the first screen row.
4. Top and bottom edges are symmetric — there is no "cursor instantly jumps to the opposite side after crossing a boundary" behavior.

## Edge cases & guards

- After `selected_index` changes, clamp it to `[0, total_items - 1]` first, then apply the scrolling rules.
- After applying the scrolling rules, clamp `scroll_offset` again to `[0, max(0, total_items - viewport_height)]`, so the bottom of the viewport never exposes blank space when data shrinks or on resize.
- When `total_items < viewport_height`, `scroll_offset` is always 0.
- When `viewport_height` changes (resize): recompute the `scroll_offset` clamp, but **do not reset** `selected_index`; if `selected_index` is no longer within the viewport after recomputation, apply the two scrolling rules above to bring it back into view.
- Page Up/Down, Home/End, jump-to-specific-index, etc. all go through the same path of "change `selected_index` first, then apply the scrolling rules" — do not write a separate scrolling implementation per input.

## State preservation

- Operations that trigger a redraw (edit / save / reload) **must preserve** `selected_index` and `scroll_offset`; never reset them to 0.
- When the item count changes (add/remove), first try to preserve the **original item** that `selected_index` pointed to (relocate by id, not by index); only if relocation fails fall back to keeping the index value and clamping it.

## Implementation deliverables

Provide:
1. The definition and initialization of the state fields above.
2. A single unified `fn move_selection(delta: isize)` (or equivalent method) that internally handles clamp + scrolling rules.
3. Rendering that slices data by `scroll_offset..scroll_offset + viewport_height` and marks the selected row by `cursor_screen_row`.
4. A resize handler.
5. Tests covering at least these scenarios: movement inside the viewport, bottom overflow downward, top overflow upward, scrolling from the bottom all the way back up to the top, item count smaller than the viewport, and cursor still visible after resize.
