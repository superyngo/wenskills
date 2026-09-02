# UI Design Principles

High-level, implementation-agnostic conventions for user-facing UIs (TUI-first roots, extended
with lessons from shipping one app across web desktop/touch, native desktop, Android, and an
editor extension). These are *principles*, not code — apply the spirit, pick the implementation
that fits the stack. Heavy detail lives in the sibling references linked per principle.

## Index

| # | Grade | Principle |
|---|---|---|
| 1 | MUST | Single source of truth, always, for everything |
| 2 | SHOULD | Cross-platform adaptation order |
| 3 | SHOULD | Prefer native surfaces over custom chrome |
| 4 | SHOULD | Shared interface for identical operations |
| 5 | MUST | Focus cursor always visible, unique, unbroken |
| 6 | SHOULD | Committed + preview two-set selection model |
| 7 | MUST | Sticky-cursor viewport scrolling |
| 8 | MUST | Confirm destructive actions; preserve state across redraws |
| 9 | MUST | Failure never destroys work-in-progress |
| 10 | MUST | Text inputs honor full editing contract |
| 11 | SHOULD | Everything overflow-able scrolls, with keys |
| 12 | SHOULD | Space cycles single-choice inputs |
| 13 | SHOULD | Del clears clearable inputs |
| 14 | SHOULD | Global keys consistent, with key-hint footer |
| 15 | SHOULD | Click-opened surfaces toggle closed on second trigger click |
| 16 | MUST | Render is a pure function of state |
| 17 | MUST | Downward moves need index correction |
| 18 | SHOULD | Header/version/About checklist (Help+About panel merge: CONSIDER) |
| 19 | SHOULD | Layout is resize-aware |
| 20 | SHOULD | Degrade gracefully |
| 21 | MUST | Logging never pollutes the UI |
| 22 | SHOULD | Plan i18n upfront |
| 23 | SHOULD | PWA is a baseline, not an afterthought |

## A. Architecture

1. **[MUST]** Single source of truth, always, for everything. State (one headless core; gesture →
   intent → snapshot → render), business rules/legality (UI asks the core, never pre-judges),
   strings (one i18n catalog), version (build-stamped from the manifest), About/info text,
   assets/styles, and the host↔core wire contract. Every duplicated copy is a future
   inconsistency bug. **Full table + why:** [references/ui/single-source-and-cross-platform.md](single-source-and-cross-platform.md).

2. **[SHOULD]** Cross-platform adaptation order: shared component with per-host adaptation first; a
   dedicated shell on the same core second; additive `pointer:coarse`-style bolt-ons never.
   Lock shared field/control order across hosts; one mechanism per host per surface class.
   **Details:** same reference, §2.

3. **[SHOULD]** Prefer the platform's native surfaces over custom chrome. Native menu bar/title
   bar/dialogs/extension contribution points replace (not duplicate) the in-app equivalent on
   that platform; cede host-owned concerns (file I/O, dirty state, undo in an editor host) to
   the host. The custom control should exist only where no native home exists. **Details:**
   same reference, §3.

4. **[SHOULD]** Shared interface for identical operations. The same logical action (move, select,
   confirm, delete, search) is one shared component/interface reused everywhere; divergent
   one-off implementations drift and force per-screen relearning.

## B. Focus, selection, feedback

5. **[MUST]** The focus cursor is always visible, unique, and unbroken. Exactly one row/control gets
   the strong focus treatment (inverse video / solid fill); multi-selection and path/ancestor
   hints use a *distinct, weaker* highlight so they never masquerade as the cursor. No state —
   paste mode, error, filter, prompt — may make the cursor visually disappear or blend in: the
   user must locate the current focus in one glance at all times. Report errors in a status
   line/toast, not by dimming or recoloring rows (row-dim "validity" cues were tried and
   removed — they read as lost focus).

6. **[SHOULD]** Selection uses a committed + preview two-set model for toggle-select plus range-select.
   Shift-drag writes only the preview overlay; it merges on commit. **Full state model:**
   [references/ui/list-selection-model.md](list-selection-model.md).

7. **[MUST]** Selection lists use sticky-cursor scrolling. Cursor moves within the viewport first;
   scroll offset moves only at the edges. Keep `selected_index` (data) and `scroll_offset`
   (screen) separate; derive the screen row. **Full spec:**
   [references/ui/scrollable-list-viewport.md](scrollable-list-viewport.md).

8. **[MUST]** Confirm destructive actions; preserve state across redraws. Explicit confirmation before
   delete/overwrite; on any redraw/reload/edit, preserve cursor, selection, scroll, and expanded
   state (restore by identity, not index) — never silently reset.

9. **[MUST]** Failure never destroys work-in-progress. Failed paste keeps the clipboard; cancelled add
   rolls back; mutations are atomic. The user can always retry without redoing setup.

## C. Keyboard & input contracts

10. **[MUST]** Text inputs honor the full editing contract: move + select + edit + clipboard. Beyond
    arrows + Home/End (and PgUp/PgDn for multi-line), every text field supports Shift+move
    selection, word/line jumps, delete char/word, cut/copy/paste, and undo/redo — using the
    platform-correct modifier (Cmd on macOS, Ctrl on Win/Linux, Emacs-style `Ctrl+A/E/K/U/W/Y`
    in a TUI where `Shift+arrow` and `Ctrl+C`/`Ctrl+Z` are unreliable or host-owned). Cut is
    atomic (copy-first, delete-on-success); failed paste preserves the field; undo restores the
    caret, not just the text. **Full key tables, TUI fallbacks, and the `Ctrl+A`/`Ctrl+C`
    conflicts:** [references/ui/text-editing-contract.md](text-editing-contract.md).

11. **[SHOULD]** Everything that can overflow, scrolls — with keys. Lists, logs, detail popups, help
    overlays, info panels, inline editors: all support line-wise (arrows), page-wise
    (PgUp/PgDn), and jump (Home/End) navigation, and long lines wrap or scroll rather than
    clip. Never require a mouse to reach content.

12. **[SHOULD]** Space cycles single-choice inputs. Any control picking one value from a small closed
    set (bool, enum, tri-state) advances on Space; Space also closes toggle-opened info popups.

13. **[SHOULD]** Del clears clearable inputs. Any input whose value may legitimately be empty clears on
    Del as one keystroke.

14. **[SHOULD]** Global keys are consistent, with a key-hint footer. Esc = cancel/back (peeling ONE
    layer at a time), Enter = confirm, same keys everywhere; surface currently-available keys
    persistently.

## D. Popups, menus, re-renders (pointer UIs)

15. **[SHOULD]** Every click-opened surface toggles closed on a second trigger click. Wire it when the
    trigger is born, not when someone complains. **This plus the rest of the popup/re-render/
    event contract** — geometry-before-dispatch, responsive size caps, mode-peel-on-dismiss,
    scroll restore, `stopPropagation` on panel inputs, attribute escaping, manual dblclick,
    wheel-nudge — **is specified in:**
    [references/ui/pointer-ui-gotchas.md](pointer-ui-gotchas.md).

16. **[MUST]** Render is a pure function of state. A wrong highlight means a wrong snapshot — fix the
    state layer, never patch the renderer to compensate.

## E. Reorderable lists

17. **[MUST]** Downward moves need index correction. After delete-then-reinsert, subtract every source
    (including attached decorations/comments) removed *above* the target index — for both the
    landing slot and the follow-up selection. Upward moves passing proves nothing. **Spec +
    test checklist:** [references/ui/reorder-index-offsets.md](reorder-index-offsets.md).

## F. Chrome, layout, plumbing

18. **[SHOULD]** Header shows app name + version; About has a fixed content checklist; Help and About may
    share one panel. Version is build-stamped (principle 1); a version visible in sample/demo
    content doubles as a stale-cache check. About content is single-sourced and complete: app
    description, version, author, project URL, privacy policy, license — copyright and
    third-party notices only when applicable. Help and About fit naturally as **one switchable
    panel** (tabs/sections) since both are infrequent, short-lived info surfaces — **[CONSIDER]** recommended,
    not mandatory. **Full checklist + panel pattern:**
    [references/ui/single-source-and-cross-platform.md](single-source-and-cross-platform.md) §4.

19. **[SHOULD]** Layout is resize-aware. Recompute layout/viewport on every resize; never hardcode
    dimensions. Popups obey the responsive size caps (reference in 15).

20. **[SHOULD]** Degrade gracefully. Honor `NO_COLOR`; ASCII fallback for narrow/limited terminals;
    consistent color semantics (red danger, green success, yellow warning).

21. **[MUST]** Logging never pollutes the UI. In a TUI, stdout/stderr are the drawing surface — route
    logs to a file/pane; one consistent scheme app-wide.

22. **[SHOULD]** Plan i18n upfront. Externalize all user-facing strings from day one; tolerate variable
    text length, CJK width, RTL. Retrofitting is far costlier.

## G. Web (PWA)

23. **[SHOULD]** On the web, PWA is a baseline, not an afterthought. Ship installable from day one:
    one web manifest sourced from the same app metadata as the version/About panel (principles
    1, 18), a service worker for offline-first shell loading, and standalone display + theme
    color so the installed app sheds browser chrome. Retrofitting a service worker into a
    stateful server-rendered app post-launch is a rewrite — plan it upfront like i18n
    (principle 22).

## Common Mistakes

- Duplicating rules/strings/version per host instead of deriving from one source (violates 1).
- Bolting touch affordances onto desktop chrome behind media queries (violates 2 — was tried, fully reverted).
- Building a custom menu/header on a platform that offers a native one (violates 3).
- Error/paste states that dim rows or recolor the cursor until focus is unfindable (violates 5).
- Storing the cursor's screen position instead of deriving it (violates 7).
- Resetting selection/scroll/expanded state on reload or re-render (violates 8, 15-reference).
- Binding `Ctrl+C` to copy, or `Shift+arrow` as the only selection path, in a TUI raw-mode editor
  (violates 10 — host owns `Ctrl+C`/`Ctrl+Z`; most terminals swallow `Shift+arrow`).
- Cursor moving by byte/codepoint in CJK or emoji text, or landing mid-surrogate (violates 10).
- Cut that deletes before the clipboard copy succeeds, losing the text on a locked clipboard
  (violates 9, 10).
- A dropdown trigger that reopens instead of closing on the second click (violates 15).
- Testing list moves only upward and shipping the downward off-by-one — twice (violates 17).
- `print` debugging inside an active TUI screen (violates 21).
- Hardcoded English strings needing later extraction (violates 22).
- About panel missing license/privacy policy, or forking the privacy/project URL per host
  (violates 18).
- Treating PWA as a post-launch enhancement, then retrofitting a service worker into a
  stateful server-rendered flow (violates 23).
- Forking app name/version/theme color between the web manifest and the About panel
  (violates 1, 18, 23).
