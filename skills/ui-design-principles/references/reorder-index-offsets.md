# Reorderable Lists — Downward-Move Index Offsets

Moving items **up** a list is naturally safe; moving items **down** is where index bugs live.
This exact class of bug shipped twice in the same codebase (once for plain nodes, once again for
comment nodes) — treat it as a checklist item for any drag-reorder / cut-paste-move feature.

## The failure mode

A move is implemented as *capture → delete sources → re-insert at target index*. The target
index was computed **against the pre-deletion list**. When any source sits **above** the target
(i.e. a downward move), the deletion shifts every later index up, so the stored target index now
points one-past where the item actually lands. Symptoms:

- The item lands one slot lower than the drop indicator showed, or
- The item lands correctly but the *selection/cursor highlight* lands on the **next** row
  (because post-move selection was computed from the stale index).

## The rule

When re-inserting (or re-selecting) after deleting the sources:

```
effective_index = target_index - (count of source items removed above target_index)
```

Count **every removed thing** that occupied a slot above the target — including auxiliary items
that travel with the moved node (attached comments, decorations, multi-row entries). The second
occurrence of this bug was exactly a forgotten auxiliary term: node shift was corrected, comment
shift was not.

Upward moves need no correction (no removed source sits above the target), which is why testing
only upward moves gives false confidence.

## Verification checklist

For every reorder/move implementation, test at minimum:

1. Same-parent move **down** by one — item lands where the indicator showed.
2. Same-parent move down — **selection/cursor follows the moved item**, not its old neighbor.
3. Move down where the moved item carries attached decorations (comments, sub-rows).
4. Multi-select move where some sources are above and some below the target.
5. Cross-parent move down (source parent's indices shift, target parent's don't — verify the
   correction only counts sources removed from the *target's* slot space).

## Debugging tip

If the rendered highlight is wrong but rendering is a pure function of a state snapshot, the
**snapshot** is wrong — fix the index math in the state layer; don't patch the DOM/renderer.
