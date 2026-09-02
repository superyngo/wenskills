# Pointer / Web UI Gotchas — Popups, Re-renders, Events

Hard-won mechanics for pointer-first UIs that re-render from a state snapshot. Each item below
was a real shipped bug or an explicit user correction.

## Popups, menus, overlays

1. **Every click-opened surface is a toggle.** A second click on the same trigger **closes** the
   panel/menu/popup — it must never merely reopen/re-place it. Wire this from the start on every
   new trigger (check "already open for this trigger?" → close and return, before opening); audit
   for it in review. One non-toggling chevron among toggling neighbors reads as "I can't close it".
   Per-row triggers (context ⋮, kind badge) toggle keyed on the row identity, not a global flag.

2. **Responsive-popup invariant.** Every overlay frame caps its width with `min(<design px>, 92vw)`
   AND is height-bounded (`max-height: calc(100vh - <margins>)`) with internal scroll. Position
   clamping alone is not enough — an unclamped popup overflows small screens. Apply to every new
   popup class, not just the ones that broke.

3. **Capture geometry BEFORE dispatching.** Read an anchor's `getBoundingClientRect()` *before*
   any state dispatch — a dispatch that rebuilds `innerHTML` detaches the node, and a rect read
   afterwards returns all zeros (popup jumps to 0,0). Order: measure → dispatch → position.

4. **Universal Esc, peeling one layer at a time.** Esc closes the topmost transient layer only
   (popup → filter → selection → clipboard → …), never several at once. Two-step Esc for
   destructive-ish state (first Esc clears the clipboard, second clears selection).

5. **Mode-driven sheets must peel their mode on dismiss.** If a sheet/dialog opens *because* the
   state snapshot says a mode is active, dismissing the sheet must also exit that mode via the
   proper intent — otherwise the next render immediately re-opens it. Every new mode-driven
   surface needs this wired.

6. **Native `dblclick` is unreliable after a re-render** (the first click's render replaces the
   node). Detect double-click manually: two body clicks on the same identity within a threshold.

## Full re-render hygiene

7. **Preserve scroll across `innerHTML` re-renders.** A wholesale rebuild resets the scroll
   container to top; save/restore `scrollTop` on every render (for every scrollable container —
   tree pane, sheet bodies), or keep the cursor row in view via `scrollIntoView`.

8. **Preserve selection/cursor across reloads and edits** — never silently reset to the first
   row. On external text changes, restore expanded state and cursor by identity (path), not index.

9. **Render is a pure function of the snapshot.** If a highlight or row state renders wrong,
   suspect the snapshot, not the DOM code. Never patch the renderer to compensate for wrong state.

## Events & focus

10. **A panel input's Enter/Escape handler MUST `stopPropagation()`** when the app also has a
    document-level key forwarder. Calling `blur()` synchronously inside the keydown handler
    changes `activeElement` *before the same event finishes bubbling*, so an "is an input
    focused?" guard at the document level no longer matches — and the Enter that opened a confirm
    prompt gets re-read as the prompt's answer before the prompt is even painted. This class of
    bug only exists on hosts with global key forwarding, so it hides when you test the other host.

11. **Escape untrusted data in attributes.** Identity carried in `data-*` attributes must be
    attribute-escaped (`"` → `&quot;`); user keys containing quotes otherwise truncate the
    attribute and silently break every click handler that parses it.

12. **Pause global tree/app shortcuts while a modal overlay is open** (help, prompts) so typing
    in the overlay doesn't mutate the document behind it.

13. **Every declarative action hook needs a handler.** If actions are dispatched via a
    `data-act` → switch-case registry, a button whose case is missing fails *silently*. On adding
    any new toolbar/menu action, add the case in the same change; consider a dev-mode warning on
    unmatched actions.

## Input conveniences (wire these by default)

14. **Space cycles single-choice inputs.** Any control choosing one value from a small closed set
    (bool, enum picker, tri-state filter cell, toggle-like popup) advances to the next value on
    Space. Space may also close a toggle-opened info popup (open/close symmetry).

15. **Del clears clearable inputs.** Any input whose value may legitimately be empty (optional
    comment, filter text, optional field) clears to empty on Del/Delete as a single keystroke.

16. **Scroll wheel adjusts scalar values** where cheap: bool toggles, int/float ±step over the
    value control — but route it through a *non-committing* nudge action so the panel/mode stays
    open (a full commit action would close the editing surface out from under the pointer).

17. **Work-in-progress survives failure.** A failed paste/move keeps the clipboard; a cancelled
    add rolls back cleanly; mutations are atomic (failure leaves the document untouched). The
    user must always be able to retry without re-doing setup.
