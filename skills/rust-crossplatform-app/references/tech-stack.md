# Tech Selection & Recommended Stack

Default picks with rationale, plus when to deviate. Optimized for: one Rust core, many thin
hosts, minimal JS-ecosystem surface.

## Core

| Concern | Pick | Notes |
|---|---|---|
| Language/layout | Rust, cargo **workspace** | One repo, one version, shared profile |
| Serialization / wire | `serde` (+`serde_json`) | Intent/Snapshot contract; JS mirrors it |
| Lossless text editing | `rowan` green trees | If editing user files, keep a lossless CST; pin the exact `rowan` version across parsers sharing trees |
| Error style | Plain enums / `thiserror` | Hosts show `to_string()`; keep messages user-ready + i18n-keyed |
| i18n | `include_str!`'d flat JSON catalogs in core | No fluent/gettext machinery needed for small apps; fallback chain lang→en→key |

## Per-platform hosts

| Platform | Pick | Why / alternatives |
|---|---|---|
| CLI | `clap` (derive) | Subcommands share the same core entry points as the TUI |
| TUI | `ratatui` + `crossterm` | De-facto standard; keep the App a thin Host wrapper |
| Web frontend | **wasm-bindgen + wasm-pack (`--target web`) + hand-written TypeScript + esbuild** | No framework: full re-render from snapshot makes React/Yew/Leptos unnecessary; `serde-wasm-bindgen` marshals the contract; hand-mirror types in `types.ts` |
| Desktop | **Tauri v2** | Reuses the web bundle; tiny binaries; native menus/dialogs. Electron only if you need Node in-process; egui/iced only for pure-native no-web UIs |
| Mobile | **Tauri v2 mobile** (Android first) | Same shell crate as desktop; iOS later. Flutter/RN would fork the frontend — reject |
| VS Code ext | `CustomTextEditorProvider` + esbuild-bundled extension host | Embed web/dist in the webview; let TextDocument own the document lifecycle |
| Browser ext | MV3 + same web bundle | wasm needs `wasm-unsafe-eval` CSP in MV3; keep core work in the page/offscreen, not the service worker (it's killed aggressively) |
| Static hosting/CDN | Cloudflare Workers static assets (or Pages/Netlify) | Deploy on push; version-bump a package.json to trigger CI builds |

## Key stack decisions & rationale (learned, don't re-litigate)

- **Session-in-webview, not session-in-Rust-process (Tauri).** Sync dispatch from key handlers
  + `Rc`/`!Send` state rule out managed state + async `invoke`. Rust side owns only real file
  I/O and native menus. ("B-lite" architecture.)
- **`withGlobalTauri: true` and `window.__TAURI__.*` globals with minimal inline ambient types
  — never add npm Tauri dependencies.** Keeps the web bundle host-agnostic and the toolchain
  npm-light.
- **No JS framework.** State lives in Rust; the render layer is a pure snapshot→DOM function.
  A framework adds a second state model — exactly what the architecture exists to avoid.
- **Hand-mirrored `types.ts` over codegen** (ts-rs etc.) is fine at small scale IF backed by a
  wasm smoke test that exercises every Intent; switch to codegen when the contract grows past
  easy review.
- **esbuild over webpack/vite** for both web and extension bundles: fast, zero-config JSON
  imports, two entry points are trivial.
- **First-party Tauri mobile plugin** when a stock plugin has a platform gap (e.g. Android
  write-access file picking needs `ACTION_OPEN_DOCUMENT` + persistable permission; stock dialog
  plugin uses `ACTION_GET_CONTENT` = read-only). Budget for one small Kotlin/Swift plugin crate
  rather than distorting the app.

## Selection heuristics for new projects

- Editing user-owned text files losslessly? → CST core (rowan). Pure data app? → plain model
  structs; skip the CST machinery.
- Need offline/installable web? → PWA manifest + service worker on the same bundle before
  considering any app store.
- Only CLI+TUI targeted? → still split core/host crates and keep core fs-free; it costs little
  now and buys wasm later ("the web host is one wrapper crate away").
- GUI-first, no web ever, no extension hosts? → egui/iced native may beat Tauri; the headless
  core pattern still applies unchanged.
