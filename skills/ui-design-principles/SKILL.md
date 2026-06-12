---
name: ui-design-principles
description: Use when designing, building, or reviewing any user-facing UI — especially terminal UIs (TUIs) — covering keyboard navigation, scrollable lists, text input, layout/resize, logging, i18n, and version display. Apply whenever the user works on UI components, navigation, scrolling, input fields, list selection, or asks how a UI element should look or behave, even if they don't explicitly say "design principles" or "conventions".
---

# UI Design Principles

## Overview

High-level, implementation-agnostic conventions for user-facing UIs (TUI first, but most apply to web/mobile). These are *principles*, not code — apply the spirit, pick the implementation that fits the stack. Heavy detail lives in `references/`.

## When to Use

Designing or reviewing any interactive surface: lists, menus, forms, text fields, navigation, layout. When in doubt about how a control *should* behave, default to the matching principle below rather than inventing one.

## Principles

1. **Shared interface for identical operations.** When the same logical action appears in multiple places (move, select, confirm, delete, search), build one common interface/component and reuse it. *Why:* divergent one-off implementations drift apart and produce inconsistent behavior the user has to relearn per screen.

2. **Text input fields support Home / End / arrow keys.** Every single-line input must allow cursor movement with Left/Right and jump-to-edge with Home/End. *Why:* this is the baseline contract users expect from any text field; missing it feels broken.

3. **Multi-line text input additionally supports PgUp / PgDn.** Paragraph/multi-line fields add page-wise vertical movement on top of principle 2. *Why:* arrow-only navigation through long text is unusably slow.

4. **All scrollable elements support arrow keys / PgUp / PgDn.** Anything that can scroll (lists, logs, viewers, panes) must be keyboard-navigable with line-wise (arrows) and page-wise (PgUp/PgDn) movement. *Why:* keyboard-first surfaces (especially TUIs) must never require a mouse to reach content.

5. **Selection lists use sticky-cursor scrolling.** Move the cursor *within* the viewport first; only push the scroll offset when the cursor hits the top/bottom edge. Maintain `selected_index` (data coordinate) and `scroll_offset` (screen coordinate) separately; the cursor's screen row is their difference, never a stored value. **Full spec, edge cases, and required tests:** see [references/scrollable-list-viewport.md](references/scrollable-list-viewport.md). *Why:* coupling the two coordinates causes the cursor to teleport across page boundaries and feels jarring.

6. **TUIs may display the version number in the top-right corner.** A small, unobtrusive version indicator aids bug reports and "am I on the latest build?" checks.

7. **Layout is resize-aware.** Recompute layout and viewport dimensions on every terminal/window resize; never hardcode width/height. This is the same `viewport_height` that principle 5 depends on. *Why:* fixed dimensions clip content or leave dead space the moment the window changes.

8. **Global keys are consistent, with a key-hint footer.** Use the same global keys everywhere — e.g. Esc = cancel/back, Enter = confirm, `q` = quit — and surface the currently-available keys in a persistent footer hint bar. *Why:* consistency removes per-screen relearning; the hint bar makes the interface discoverable without a manual.

9. **Confirm destructive actions; preserve state across redraws.** Require explicit confirmation before delete/overwrite/irreversible actions. On any redraw/reload/edit, preserve `selected_index` and `scroll_offset` — never silently reset to 0 (reinforces principle 5). *Why:* accidental data loss and "where did my place go?" are the two most common UI frustrations.

10. **Degrade gracefully.** Honor `NO_COLOR`; provide an ASCII fallback when the terminal lacks Unicode or is too narrow; keep color semantics consistent (red = danger/error, green = success, yellow = warning). *Why:* a UI that only works in one ideal terminal isn't portable.

11. **Logging never pollutes the UI.** In a TUI, stdout/stderr are the drawing surface — route logs to a file, a dedicated log pane, or stderr *only when the alternate screen is inactive*. Define one consistent logging scheme (levels, destination, format) shared across the app. *Why:* a stray `print`/`eprintln` corrupts the rendered screen and is a classic TUI bug.

12. **Plan i18n upfront.** Externalize all user-facing strings from day one (no hardcoded literals); design layouts to tolerate variable text length and wider scripts (CJK width, RTL). *Why:* retrofitting i18n after strings are scattered through the code is far more expensive than building for it from the start.

## Common Mistakes

- Re-implementing list movement / input handling per screen instead of one shared component (violates 1).
- Storing the cursor's screen position as mutable state instead of deriving it (violates 5 — see the reference).
- Resetting selection/scroll on every reload (violates 9).
- `print`/`println` for debugging inside an active TUI screen (violates 11).
- Hardcoded English strings that later need extraction (violates 12).
