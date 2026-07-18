# Text Input & Editing Contract — Cursor, Selection, Clipboard

The full keyboard contract any text field must honor — not just cursor movement, but selection,
deletion, and cut/copy/paste. Implementation-agnostic (TUI, web, native), but the platform
modifiers and TUI fallbacks are called out explicitly because that is where most implementations
break.

The baseline cursor-movement contract (arrows + Home/End; PgUp/PgDn for multi-line) is
principle 10. This reference extends it with the selection + editing half.

## State

A single-line or multi-line text input maintains:

| Field | Type | Purpose |
|---|---|---|
| `value` | `String` | The full text |
| `cursor` | `usize` | Caret offset into `value` (0..=len) |
| `anchor` | `Option<usize>` | Selection anchor; `None` = no selection, caret only |
| `selection` | derived | `min(anchor, cursor)..max(anchor, cursor)` when `anchor.is_some()` |
| `undo_stack` / `redo_stack` | `Vec<Edit>` | Per-field edit history (see "Undo / redo") |

The caret and the selection are mutually exclusive in display: when `anchor.is_some()` render the
range highlight and hide the caret (or draw it at the moving edge); when `anchor.is_none()` render
the blinking caret at `cursor`. Never render both as the same style — that is the text-field
analog of principle 5 (focus must be unambiguous).

## Cursor movement (single-line baseline)

| Move | macOS | Win / Linux | TUI (Emacs-style) |
|---|---|---|---|
| Char left / right | `←` / `→` | `←` / `→` | `←` / `→`, or `Ctrl+B` / `Ctrl+F` |
| Word left / right | `Option+←` / `Option+→` | `Ctrl+←` / `Ctrl+→` | `Meta+B` / `Meta+F` (often unsupported — fall back to char) |
| Line start / end | `Cmd+←` / `Cmd+→`, or `Ctrl+A` / `Ctrl+E` | `Home` / `End` | `Ctrl+A` / `Ctrl+E` |
| Field start / end (multi-line) | `Cmd+↑` / `Cmd+↓` | `Ctrl+Home` / `Ctrl+End` | `Meta+<` / `Meta+>` (rare) |

Multi-line inputs add vertical movement and paging:

| Move | All platforms |
|---|---|
| Line up / down | `↑` / `↓` |
| Page up / down | `PgUp` / `PgDn` |

## Selection

Same as cursor movement, plus the `Shift` modifier extends the selection instead of moving the
caret. `Shift+click` sets the far edge. Every entry in the cursor tables above has a `Shift+`
twin.

| Action | macOS | Win / Linux | TUI |
|---|---|---|---|
| Extend by char | `Shift+←` / `Shift+→` | `Shift+←` / `Shift+→` | Unreliable — see TUI fallback |
| Extend by word | `Shift+Option+←` / `Shift+Option+→` | `Shift+Ctrl+←` / `Shift+Ctrl+→` | Unreliable |
| Extend to line edge | `Shift+Cmd+←` / `Shift+Cmd+→` | `Shift+Home` / `Shift+End` | Unreliable |
| Select all | `Cmd+A` | `Ctrl+A` *(conflict — see below)* | `Ctrl+A` conflicts; use a host binding |
| Collapse selection | `Esc`, or any unshifted move | same | same |

### Selection anchor rules

- A bare (unshifted) cursor move **collapses** the selection: set `anchor = None`, move `cursor`.
- `Shift+<move>` **extends**: if `anchor` is `None`, set `anchor = cursor` first (the caret's
  position before the move becomes the fixed edge), then move `cursor`. This mirrors the
  list-selection model: one edge is fixed (the anchor), one edge moves (the caret), and reversing
  direction naturally shrinks the range because it is recomputed from `min/max(anchor, cursor)`
  each step — no incremental bookkeeping.
- `Select all` sets `anchor = 0`, `cursor = len`.
- Mouse drag sets `anchor` on mousedown, moves `cursor` on mousemove, drops both on mouseup
  (commit). Double-click selects a word (anchor/cursor on word boundaries); triple-click selects
  a line.

### The `Ctrl+A` conflict

On TUI and Win/Linux, `Ctrl+A` is the conventional "select all" — but in a TUI raw-mode input,
`Ctrl+A` is also the Emacs "move to line start". Pick one by convention for the host and document
it; do not silently bind both. In a TUI line editor, prefer `Ctrl+A` = line start (Emacs) and
provide `Select-all` through a different binding (or omit it — single-line fields rarely need it).

### TUI fallback for Shift+arrows

Most terminals **do not transmit** `Shift+←` / `Shift+→` as distinct keys to the application —
they arrive as bare arrows or are swallowed. Do not make `Shift+arrow` the *only* way to select
text in a TUI. Provide at least one fallback:

1. **Emacs mark mode** (most portable): `Ctrl+Space` toggles `mark`; the caret becomes the moving
   edge and selection extends with bare arrows. `Ctrl+G` collapses.
2. **Mouse drag**: modern terminals forward selection to the app via mouse protocols (SGR-1006).
   The app can treat drag as anchor+cursor.
3. **`Ctrl+K`** (kill to end of line) and **`Ctrl+U`** (kill to start) as destructive
   shortcuts that combine "select + cut" — the killed region goes to a kill ring, not the system
   clipboard, unless the host bridges them.

Practical rule: in a TUI, expose the Emacs-style kill/yank shortcuts (`Ctrl+A/E/K/U/W/Y`) as the
primary editing vocabulary, and treat any `Shift+arrow` selection as a bonus when the terminal
delivers it. On web/native, expose the `Shift/Cmd/Ctrl` vocabulary as primary.

## Editing operations

| Action | macOS | Win / Linux | TUI (Emacs-style) |
|---|---|---|---|
| Delete char left | `Backspace` | `Backspace` | `Backspace`, or `Ctrl+H` |
| Delete char right | `Del` | `Del` | `Ctrl+D` |
| Delete word left | `Option+Backspace` | `Ctrl+Backspace` | `Ctrl+W` |
| Delete word right | `Option+Del` | `Ctrl+Del` | `Meta+D` (rare) |
| Delete to line end | — | — | `Ctrl+K` |
| Delete to line start | — | — | `Ctrl+U` |
| Cut selection | `Cmd+X` | `Ctrl+X` | `Ctrl+W` (kill region, if mark set) |
| Copy selection | `Cmd+C` | `Ctrl+C` *(conflict — see below)* | host mouse-select + copy |
| Paste | `Cmd+V` | `Ctrl+V` | `Ctrl+Y` (yank from kill ring) |
| Undo | `Cmd+Z` | `Ctrl+Z` | host-dependent |
| Redo | `Cmd+Shift+Z` | `Ctrl+Y` | host-dependent |
| Select all | `Cmd+A` | `Ctrl+A` | see conflict above |

### The `Ctrl+C` / `Ctrl+Z` conflicts

- **TUI**: `Ctrl+C` is conventionally SIGINT (interrupt the app), not copy. Never bind `Ctrl+C`
  to "copy" inside a TUI raw-mode editor — users will hit it to abort and lose their edit. Use the
  host's mouse-select → copy path, or a dedicated key. Same for `Ctrl+Z` (SIGTSTP / suspend).
- **Win/Linux GUI**: `Ctrl+C` as copy is fine, but inside a terminal-hosted TUI the host still
  owns `Ctrl+C`. Defer to the host's clipboard conventions (OSC 52 for clipboard write, mouse
  selection for read).
- **macOS GUI**: `Cmd+C/X/V/Z` have no SIGINT conflict — use them directly.

### Clipboard failure must preserve work (principle 9)

- **Failed paste** (clipboard has incompatible content, or a guard rejects it) leaves `value`,
  `cursor`, and `anchor` untouched and reports the reason in a status line/toast — never partially
  mutates the field into a broken state.
- **Cut** is `copy + delete`, atomic: if the copy half fails (clipboard locked), the delete half
  must not happen. Implement cut as "copy first, then delete only if copy succeeded", or as a
  single reversible edit on the undo stack.
- **Paste that would exceed a length cap** inserts up to the cap, leaves the cursor at the cut-off
  point, and reports the truncation — it does not abort and discard the whole paste.

## Undo / redo

- Every mutation (typing, delete, cut, paste, replace) pushes one entry onto `undo_stack` and
  clears `redo_stack`. An "entry" may coalesce consecutive char-typing into a single run (so
  undoing a typed word is one step, not N).
- `Undo` restores `value` **and** `cursor`/`anchor` to the recorded snapshot — restoring text but
  dropping the caret at offset 0 is a common bug.
- `Redo` replays the next entry off `redo_stack`. Any new mutation clears `redo_stack`.
- Per-field history, not global: switching focus between fields does not flush undo, but each
  field keeps its own stack.

## Edge cases & guards

- **Empty selection**: cut/copy on `anchor.is_none()` is a no-op (or copies nothing); never
  deletes. Delete-with-selection must check `anchor != cursor`.
- **Cursor at boundary**: `←` at offset 0 and `→` at offset `len` are no-ops, not errors.
- **Multibyte / CJK / grapheme clusters**: offset arithmetic must be grapheme-based, not byte- or
  codepoint-based — `←` must move one user-perceived character, not half of a surrogate pair or
  one byte of a 3-byte CJK glyph. A cursor stuck between combining marks is a bug.
- **IME composition**: during composition, the caret is hidden, the preedit text is rendered, and
  all movement/selection keys are routed to the IME, not the field. Committing composition pushes
  one undo entry for the whole composed string.
- **Field refocus**: restoring focus to a field restores its `cursor` and `anchor` (by principle
  8). Never reset the caret to offset 0 on focus.
- **Password fields**: copy/cut on a masked field is disabled (or copies nothing) — never leak
  the secret through the clipboard silently. Paste remains enabled.

## Common mistakes

| Mistake | Consequence | Fix |
|---|---|---|
| Binding `Ctrl+C` to copy inside a TUI raw-mode editor | User hits `Ctrl+C` to abort, loses edit | Use Emacs-style `Ctrl+W` or host mouse-select; leave `Ctrl+C` to the host |
| Making `Shift+arrow` the only selection path in a TUI | Selection silently broken on terminals that swallow `Shift` | Provide Emacs mark mode (`Ctrl+Space`) as fallback |
| Using byte offsets for cursor movement | Cursor lands inside multibyte chars on CJK / emoji | Operate on grapheme clusters |
| Cut that deletes before copy succeeds | Clipboard locked → text lost, nothing on clipboard | Copy first, delete only on success; or push as one undo entry |
| Restoring `value` on undo but not `cursor` | Caret jumps to offset 0 after undo | Snapshot `cursor`/`anchor` with every undo entry |
| Partial paste discarded when it exceeds a length cap | User loses the whole paste, must re-trim source | Insert up to cap, leave caret at cut-off, report |
| Same highlight style for caret and selection range | Ambiguous whether there is a selection | Distinct styles; hide caret when range is active |

## Tests to write

1. **Type + undo**: type "abc", undo once → empty, caret at 0.
2. **Undo restores caret**: type "abc", move caret to between a/b, undo → caret at the
   pre-typing position, not 0.
3. **Shift+→ selection**: at "a|bc", `Shift+→` → selection "b", caret at 2, anchor at 1.
4. **Reverse selection direction**: extend right 2, then `Shift+←` → range shrinks; anchor stays
   fixed.
5. **Bare move collapses**: with a selection, `→` → selection gone, caret at the moving edge.
6. **Select all**: `Cmd+A`/`Ctrl+A` → anchor 0, cursor len.
7. **Cut is atomic**: stub clipboard to fail → `value` unchanged.
8. **Paste length cap**: cap 5, paste "hello world" → field is "hello", caret at 5, status reports
   truncation.
9. **Copy on empty selection**: no selection → `Cmd+C` is a no-op, clipboard untouched.
10. **CJK cursor**: in "你好|", `←` → caret before 好, `←` again → before 你 (two steps, not six).
11. **IME commit**: compose and commit "が" → one undo entry, not two.
12. **Password copy**: masked field, `Cmd+C` → clipboard unchanged (or explicitly blocked).
