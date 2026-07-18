# Single Source of Truth & Cross-Platform Adaptation

Lessons distilled from building one app (confy) across TUI, web desktop, web touch, Tauri
desktop, Android, and a VS Code extension — all on one shared core.

## 1. Single source ALWAYS wins — enumerate what must be single-sourced

For anything that exists in more than one place (platforms, breakpoints, hosts), there must be
exactly one authoritative copy of each of these, and every surface derives from it:

| Concern | Single source | Anti-pattern it prevents |
|---|---|---|
| **State** | One headless session/state machine; every gesture → one intent/command → new snapshot → full re-render | Each UI keeping its own shadow model that drifts from the data |
| **Business rules / legality** | The core answers capability queries (e.g. "what kinds can this node convert to?"); the UI renders the answer and surfaces the core's error verbatim | UI pre-judging legality with duplicated rules that go stale |
| **Strings (i18n)** | One catalog file set, embedded/imported by every host; per-host strings layer *on top*, never fork the shared ones | Hardcoded literals scattered per host |
| **Version** | Stamped at build time from the package manifest into every surface (header, About, sample data) | Hand-updated version strings that lie |
| **Info/About text** | Composed once in the core; each host appends only its host-specific lines (config path, storage disclosure) | Divergent About panels |
| **Assets / styles** | One canonical stylesheet or design file; app-specific additions live in a clearly fenced appendix, never interleaved | Untraceable design drift from the spec |
| **Wire contract** | One protocol/type module imported by both sides (so drift is a compile error), or a hand-mirrored types file with a smoke test | Host and core disagreeing silently |

**Why this is the top priority:** every duplicated copy is a future inconsistency bug. The
cost of wiring a derivation once is far below the cost of chasing "works on desktop, broken on
touch" divergences forever.

**Version display corollary:** the app header (or title bar) should show the app name and
version; a build-stamped version in visible sample/demo content doubles as an instant
"am I running the new build?" check — invaluable when caches (wasm, service worker, webview)
can serve stale bundles.

## 2. Adaptation order: shared component first, dedicated shell second, never bolt-on

When covering multiple form factors (desktop/touch, web/app, RWD breakpoints):

1. **First choice — one component, per-host adaptation.** Extract the surface (edit panel,
   save/convert form, filter grid) into a host-agnostic module that emits the canonical markup
   and takes a tiny host interface for the container (e.g. a `Surface { isOpen/open/close/onCancel }`
   — desktop wraps a `<dialog>`, touch wraps a bottom sheet). Both hosts get identical field
   order, validation, and behavior for free.
2. **Second choice — dedicated shell sharing the same core.** When fidelity demands a genuinely
   different chrome (touch sheets/FAB vs desktop popovers), build a *dedicated* page/module that
   ports the target design faithfully, but drive it from the **same** state core and intent
   contract as every other host. Shared: state, types, I/O helpers, shared components. Owned:
   layout, gestures, chrome.
3. **Never — additive gating.** Bolting touch affordances onto desktop chrome behind
   `pointer: coarse` media checks produces a low-fidelity hybrid that satisfies neither. This
   was tried once and fully reverted; the rework cost exceeded building the dedicated shell.

**Consistency rules that make sharing work:**
- Lock shared field/control order across hosts (users switch devices; muscle memory transfers).
- One mechanism per host for a class of surface (e.g. touch: *all* panels are bottom sheets).
- Responsive chrome folds via container queries with the overflow menu built **dynamically from
  what actually folded** (probe `offsetParent === null`), never a hardcoded parallel list.

## 3. Prefer the platform's native surfaces over custom chrome

If the host platform offers a native menu bar, title bar, dialog, or contribution point, use it
and *remove* the equivalent custom UI on that platform:

- Desktop app shell → native File/Edit/View/Help menu bar + native title bar; hide the in-app
  toolbar header there (web keeps it).
- Editor-extension host → the editor's own title-bar buttons and "…" overflow menu; hide the
  app's header inside the webview.
- Browser → native inputs/dialogs where acceptable; reserve custom overlays for what the
  platform can't do.

**Why:** users already know the native surface's location, shortcuts, and a11y behavior; every
custom equivalent is UI complexity you now maintain per platform. The in-app version of a
control should exist only on platforms with no native home for it.

**Host-ownership corollary:** things the platform owns (file I/O, dirty state, undo stack,
save/revert in an editor host) should be *ceded* to the platform, not duplicated. Fighting the
host's model (e.g. keeping your own dirty flag inside an editor that already tracks one) creates
two sources of truth — see rule 1.
