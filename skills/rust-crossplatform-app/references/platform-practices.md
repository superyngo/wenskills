# Per-Platform Best Practices & Gotchas

Each item below is a shipped lesson, not theory. Organized per host; the shared UI conventions
live in the `ui-design-principles` skill — apply both.

## CLI

- The CLI and TUI share one binary and one loader path: `parse args → host reads file →
  core::from_str_as → run`. Subcommands (e.g. `convert`) call core functions directly — no
  UI-layer logic in them.
- Pure helpers like extension→format detection belong in core (no I/O); the read/write stays in
  the host.
- Integration-test the binary's happy/error paths (assert the source file is unchanged on
  failure), not just core units.

## TUI (ratatui)

- App struct = `Session` + a handful of host-only fields (rows cache, source path, scroll
  offsets). If a field influences behavior, it belongs in core.
- Panic-safe terminal teardown; disable raw mode if setup fails midway.
- Route modal-prompt keys *before* the general keymap; lock input during prompts.
- Never test by driving a pty or long-lived background process — verify core logic headlessly
  and hand the human a manual checklist for the real terminal.

## Web (wasm)

- FFI crate stays thin: constructor + `dispatch` + `snapshot` + a few queries. Logic in the
  wrapper is logic you can't test natively.
- **Rust changes don't reach the browser until wasm-pack + bundler rerun.** Make one build
  script the only path (`cf-build.sh`-style: wasm-pack → esbuild → dist) and use it for dev,
  CI, and every host that embeds the bundle.
- Dev server must send `Cache-Control: no-store` — browsers heuristically cache large wasm and
  a stale binary makes real fixes look like no-ops (even in incognito within a session). A
  build-stamped version visible in the UI is the "am I on new code?" check.
- Watch transitive wasm deps: crates pulling `getrandom` need its js/wasm feature enabled at
  the workspace level.
- File I/O: File System Access API where available, download fallback elsewhere; on iOS Safari
  fix the saved filename/extension via MIME + Web Share. `?url=` deep-link opening is cheap and
  useful.
- PWA (manifest + service worker) gives installability/offline for near-zero cost — do it
  before any store submission.

## Desktop (Tauri v2)

- Native menu bar: keep the root `Menu` in a **module-level variable for the page lifetime** —
  a locally-scoped menu tree gets GC'd and the native bar keeps rendering dead items.
- `PredefinedMenuItem` kinds are not uniformly bare strings (`About` is `{ item: { About: null } }`);
  one wrong shape aborts the whole menu build with zero signal. Wrap every menu handler in
  try/catch → status line (errors are silent unhandled rejections).
- Never bind `CmdOrCtrl+C/X/V/Z/Y/A` as accelerators for app-level menu items — text inputs
  need them. Plain-key hints go in the label only.
- Capabilities: `core:default` bundles are curated subsets — expect to add explicit lines
  (e.g. `core:webview:allow-set-webview-zoom`); custom plugins need their permission listed.
- Hide the in-app toolbar header on desktop; use the native title bar + menus (see
  ui-design-principles §native surfaces).
- Platform-specific config via `tauri.<platform>.conf.json` auto-merge — e.g. Windows override
  empties `beforeBuildCommand` (bash/git don't run under its build shell); Android carries the
  `fileAssociations` so macOS Finder doesn't register handlers you don't implement.
- `beforeBuildCommand` cwd is the **workspace root**, not the crate dir — anchor script paths
  with `$(git rev-parse --show-toplevel)`.
- Plain `cargo build -p <shell> --release` needs `--features custom-protocol` or the exe loads
  the dev URL ("localhost refused"); `cargo tauri build` adds it automatically.
- Aggressive workspace release profiles (lto, codegen-units=1, opt-level z) make release
  bundles slow — use `--debug` bundles for local verification.
- File open at startup: a `startup_file` command for CLI-arg opens; macOS/iOS/Android get
  `RunEvent::Opened` — **cfg-gate it**, it doesn't exist on Windows and breaks the build.

## Mobile (Tauri v2, Android-first)

- The crate body must live in `lib.rs` with `#[cfg_attr(mobile, tauri::mobile_entry_point)]
  pub fn run()`; `main.rs` is a thin desktop-only bin.
- Android file access = SAF `content://` URIs, opaque and persistent-permission-based:
  `ACTION_OPEN_DOCUMENT` + `FLAG_GRANT_*` + `takePersistableUriPermission`, then resolve the
  display name via ContentResolver `DISPLAY_NAME` (with a **null projection** — some providers
  reject narrow ones). Wrap the URI in the same handle shape the web/desktop hosts use.
- **Mobile-plugin responses deserialize through a typed Rust struct — every field the
  Kotlin/Swift side returns must be declared in `models.rs`, or serde silently drops it.**
  (Bug class: the native side computed a value correctly for weeks; Rust never forwarded it.)
- Scope down what mobile can't do (e.g. no Save-As picker) and show a translated hint instead
  of a broken picker; write-in-place on an open handle still works.
- "Open with" file associations: declare in the platform config (several MIME strings per
  extension — `.toml`/`.yaml` have no IANA type and file managers guess differently); cold
  start drains queued URLs via a command, warm start listens for an "opened" event.
- Hand-edited files inside generated projects (`gen/android`: themes.xml edge-to-edge opt-out,
  adaptive-icon removal) **must be documented as reapply-after-regen** — the generator will
  clobber them.
- Launcher icons: a source PNG with no alpha makes Android adaptive icons render as a flat
  block — either design with margin+alpha or ship plain per-density mipmaps.
- Acceptance = manual checklist on real hardware with a sideloaded debug APK (auto-signed, no
  keystore needed).

## VS Code extension

- Use `CustomTextEditorProvider` and **let VS Code's `TextDocument` own content, dirty state,
  undo, save, revert, and hot-exit.** The webview session is a view: apply user edits via
  `WorkspaceEdit`, reload the tree on text-change events (with expanded/cursor state restored
  by identity). Running a parallel dirty/undo protocol was tried and retired.
- Share the protocol as one `.ts` file imported by relative path from both webview and
  extension host — drift becomes a compile error.
- **A webview `keydown` listener cannot reliably beat a matching VS Code keybinding** — the
  workbench claims the keystroke first. Rebind via `contributes.keybindings` with a `when`
  clause (`activeCustomEditorId == '<your.editor>'`); JS `preventDefault()` is not a fix.
- Hide the app's own toolbar in the webview (`body.host-vscode` gate); surface commands through
  the editor title bar and its "…" menu (`contributes.submenus` for pickers like language).
- Opt-in editor priority (`"option"`); leave default-per-glob to users' own
  `workbench.editorAssociations`.
- Tab swapping (custom ⇄ text editor, in place, to the side) has dedicated commands — implement
  real in-place swaps, not open-beside-and-leave-both.
- `media/` is a build-time copy of `web/dist` (gitignored) — the extension ships no forked web
  source.

## Browser extension (MV3)

- Reuse the same built web bundle; the delta is manifest + thin adapter (like the Tauri/VS Code
  adapters).
- wasm requires `"wasm-unsafe-eval"` in the extension CSP; everything must be bundled —
  no remote code (store policy) — which the self-contained esbuild output already satisfies.
- Don't run core/wasm in the MV3 service worker (aggressively killed, no DOM); run it in the
  page (action popup, options page, offscreen document, or content-script-injected UI).
- Storage: `chrome.storage` replaces localStorage in extension contexts — put that behind the
  same host-adapter seam as the other hosts' persistence.
