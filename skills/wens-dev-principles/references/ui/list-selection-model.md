# List Selection Model — Toggle + Shift-Range Multi-Select Spec

Implement (or review/fix) the selection behavior of a selectable list that supports both individual toggle-select and Shift+arrow range-select. The spec is implementation-agnostic — TUI, web, or native.

## State

Maintain these fields:

| Field | Type | Purpose |
|---|---|---|
| `selected` | `Set<ItemKey>` | **Committed** selection — items the user has finalized |
| `shift_range` | `Set<ItemKey>` | **Preview** overlay — items tentatively highlighted by the current Shift-drag, not yet committed |
| `select_anchor` | `Option<Index>` | Visible-row index where the current Shift-drag started; `None` when no drag is active |

`ItemKey` is whatever stably identifies a selectable item (e.g. a tuple of category + group + item index, or a unique ID). Use a key that survives re-sorting or re-filtering whenever possible.

### Derived queries

These helpers keep read-sites clean and avoid scattering union logic:

- **`is_effectively_selected(key)`** → `selected.contains(key) || shift_range.contains(key)`
- **`effective_selection_len()`** → `|selected ∪ shift_range|` (count the union, not the sum)
- **`has_effective_selection()`** → `!selected.is_empty() || !shift_range.is_empty()`

All rendering, count displays, guard conditions (e.g. "is there anything selected?"), and action triggers MUST use these derived queries, never `selected` alone.

## Operations

### 1. Toggle-select (e.g. `s` key or click)

Toggles a single item in the **committed** set.

```
commit_shift_range()          # finalize any in-progress drag first
if selected.remove(key):
    pass                      # was selected → now deselected
else:
    selected.insert(key)      # was not selected → now selected
select_anchor = Some(cursor)  # set anchor for a potential subsequent Shift-drag
```

### 2. Shift+↑/↓ (extend range selection)

Creates or adjusts a **temporary preview** range. `selected` is NEVER modified during the drag — only `shift_range` changes.

```
if select_anchor is None:
    select_anchor = cursor          # anchor the starting point

cursor += delta                     # move cursor (clamped to visible bounds)

# Recompute preview from scratch on every step:
shift_range.clear()
lo = min(select_anchor, cursor)
hi = max(select_anchor, cursor)
for visible_index in lo..=hi:
    if row_at(visible_index) is a selectable leaf:
        shift_range.insert(key_of(row))
```

**Why clear-and-recompute, not incremental?** Reversing direction must *shrink* the preview. Incremental add-only logic cannot shrink and produces the classic "selected everything I passed through" bug.

**Why never touch `selected`?** If `selected` contains manually-toggled items that overlap the Shift-drag range, mutating `selected` during the drag would erase them on recompute. The preview overlay avoids this entirely.

### 3. Commit (finalize the drag)

Merge `shift_range` into `selected` and reset drag state. Call this on **any non-Shift action** that implies the drag is over:

```
for key in shift_range.drain():
    selected.insert(key)
select_anchor = None
```

**Commit trigger points** (all non-Shift cursor/selection actions):

| Action | Example keys |
|---|---|
| Normal cursor movement | ↑ / ↓ / j / k |
| Page movement | PgUp / PgDn |
| Jump to edge | Home / End |
| Toggle-select | `s`, click |
| Select-all-in-group | Ctrl+A |
| Bulk action | `l` (install/uninstall) |

### 4. Clear all (cancel)

Discard both committed and preview selections:

```
selected.clear()
shift_range.clear()
select_anchor = None
```

Trigger: Esc (when there is an effective selection), or after executing a bulk action.

### 5. Select-all-in-group (e.g. Ctrl+A)

Commit any pending drag, then select all visible leaf items belonging to the same group/parent as the cursor:

```
commit_shift_range()
group = group_of(current_row)
for row in visible_rows:
    if is_leaf(row) and group_of(row) == group:
        selected.insert(key_of(row))
```

### 6. Bulk action on selection

Commit the drag first so the action operates on the full set:

```
commit_shift_range()
keys = sorted(selected)
for key in keys:
    perform_action(key)
selected.clear()
select_anchor = None
```

## Rendering

For every selectable row, check `is_effectively_selected(key)` (the union) to decide whether to show the selection marker. Do NOT check `selected` alone — that would hide the Shift-drag preview.

A typical gutter rendering pattern:

```
marker = "●" if is_effectively_selected(key) else " "
style  = HIGHLIGHT if is_cursor else (SELECTED_BG if is_effectively_selected(key) else NORMAL)
```

### Status bar / count display

Show `effective_selection_len()` in the status bar, and use `has_effective_selection()` for the "show selection info" guard:

```
if has_effective_selection():
    status = f"{effective_selection_len()} selected — l to install/uninstall, Esc to clear"
```

## State lifecycle diagram

```
                     ┌─────────────────────┐
                     │   Idle (no drag)     │
                     │ shift_range = ∅      │
                     │ select_anchor = None │
                     └─────┬───────────────┘
                           │ Shift+↑/↓
                           ▼
                ┌──────────────────────┐
           ┌───►│  Dragging (preview)  │◄──┐
           │    │ shift_range = {…}    │   │ Shift+↑/↓
           │    │ select_anchor = Some │   │ (recompute)
           │    └──────────┬───────────┘───┘
           │               │ Any non-Shift action
           │               ▼
           │    ┌──────────────────────┐
           │    │  Commit              │
           │    │ selected ∪= range    │
           │    │ shift_range = ∅      │
           │    │ select_anchor = None │
           │    └──────────┬───────────┘
           │               │
           └───────────────┘
```

## Edge cases & guards

- **Non-selectable rows** (headers, dividers): skip them when building `shift_range`. They should not appear in `selected` or `shift_range`.
- **Filtered/search mode**: the anchor and range operate on *visible* row indices, not absolute data indices. After exiting search, commit or discard the drag.
- **Data refresh** (rescan, reload): clear both `selected` and `shift_range` — item indices may have changed, and stale keys could point to wrong items.
- **Overlap**: an item can be in both `selected` and `shift_range` (manually toggled, then Shift-dragged over). This is fine — `commit` is idempotent (`insert` on a set is a no-op for duplicates). The union queries handle it correctly.

## Common mistakes

| Mistake | Consequence | Fix |
|---|---|---|
| Mutating `selected` inside `extend_selection` | Reversing Shift direction erases manually-toggled items | Use `shift_range` as preview; merge only on commit |
| Not clearing `shift_range` on every recompute | Range only grows, never shrinks on reversal | `shift_range.clear()` before the anchor→cursor loop |
| Checking `selected` alone for rendering | Shift-drag items are invisible until committed | Use `is_effectively_selected()` union query |
| Not committing on normal movement | Old `shift_range` persists and corrupts next drag session | Call `commit_shift_range()` in `move_cursor`, Home/End, etc. |
| Incremental add to `shift_range` instead of recompute | Cannot shrink on direction reversal | Clear + recompute from anchor→cursor each step |

## Tests to write

1. **Toggle select**: `s` on item A → A in selected. `s` again → A removed.
2. **Shift+↓×3**: preview shows 4 items (anchor + 3). `selected` is still empty.
3. **Shift+↓×3 then ↑ (no Shift)**: commit merges 4 items into `selected`. `shift_range` is empty.
4. **Shift+↓×3 then Shift+↑×2**: preview shrinks to 2 items. Previously-selected manual items remain untouched.
5. **Manual select A, then Shift-drag over A**: A appears in both sets. After commit, A is still in `selected` (idempotent).
6. **Esc**: both sets cleared.
7. **Data refresh**: both sets cleared, anchor reset.
