# Architecture — Headless Core, Host Shells, Workspace Layout

The load-bearing idea: **one pure Rust core crate, N thin host shells.** Every platform below
(CLI, TUI, web, desktop, mobile, VS Code extension, browser extension) is just another host over
the same core. Proven end-to-end in one project that shipped all of TUI + web + touch web +
macOS/Windows desktop + Android + VS Code from a single workspace.

## 1. The headless core crate — hard rules

The core crate holds ALL domain logic and app state. It must be:

- **Filesystem-free and environment-free at runtime.** No `std::fs`, `std::process`,
  `std::env`, no `tempfile`. The sole constructor is `from_str(text)` (or
  `from_bytes`); there is no `load(path)`/`save(path)` and no `path` field — at most a
  host-set display label (`set_filename`). **Enforce this with a test** that greps the crate
  for forbidden modules/deps (a `no_fs_gate.rs`), not with discipline.
- **UI-toolkit-free.** No terminal, DOM, or GUI deps. Rendering is someone else's job.
- **Wasm-compatible by construction.** Avoid `!Send`-hostile host assumptions, threads, and
  crates that don't build for `wasm32-unknown-unknown`; pin transitive deps that need wasm
  features (e.g. `getrandom`'s js feature) early.
- **The single source of truth for legality.** Hosts never pre-judge what's allowed; they ask
  the core (capability queries like `kind_options(path)`) and surface the core's error strings.
- **Owner of i18n.** The string catalog lives in core (`include_str!`'d JSON, flat keys,
  fallback chain lang → en → raw key so a missing translation never panics); hosts layer only
  host-specific strings on top. Shared About/help text composes in core; hosts append their
  host-only lines.
- **Atomic mutations.** Every state mutation either fully commits or leaves state untouched
  (clone-update-validate-commit). Hosts can then treat every operation as retry-safe.

## 2. The Session / Intent / Snapshot pattern

Lift the entire interactive state machine into core as a `Session`:

```
host gesture/keystroke → Intent (one closed enum of every user action)
    → Session::dispatch(intent) → SessionSnapshot (full serializable view state)
    → host renders the snapshot (pure function, full re-render is fine)
```

- `Intent` and `SessionSnapshot` are plain serde types — they ARE the wire contract for wasm
  and any IPC host. Keep wire-crossing fields simple (strings over enums where it eases the JS
  side).
- The snapshot carries **everything** a renderer needs: rows, cursor, selection, mode, error,
  dirty flag, language. A host holds no shadow model.
- Host-only concerns stay out: scroll offsets, window size, file paths, panel scroll positions
  live in the host shell.
- A `Host` trait covers the rare host-callback (e.g. "open $EDITOR with this text, return the
  result") so core flows that need host services stay testable with a fake host.
- This makes the core fully scriptable in tests: drive `dispatch()` sequences headlessly, and
  reuse the identical script against the built wasm in Node as a smoke test.

**Why dispatch is synchronous:** interactive editing fires from dozens of key handlers; a sync
`dispatch → snapshot` keeps hosts trivial. This is also why, in a Tauri shell, the Session runs
*in the webview via wasm* rather than in Rust-side managed state — `Rc`-based trees are `!Send`
(can't sit in managed state) and `invoke` is async. Don't fight that; see platform guide.

## 3. Workspace layout template

```
myapp/
  Cargo.toml                 # [workspace]; shared [profile.release]
  i18n/                      # canonical string catalogs (en.json + others)
  crates/
    myapp-core/              # headless core: model/ + session/ (Intent, Session, Snapshot, i18n)
      tests/                 #   no_fs_gate.rs, serde roundtrips, headless session scripts
    myapp-tui/               # ratatui TUI + the CLI binary; depends on core, owns all file I/O
    myapp-ffi/               # wasm-bindgen wrapper: from_text/dispatch/snapshot (thin!)
    myapp-tauri/             # Tauri v2 shell (desktop + mobile) over web/dist; native I/O only
    tauri-plugin-*/          # first-party mobile plugins for platform gaps (only if needed)
  web/                       # TypeScript host: types.ts (serde mirror), render/ui/fs modules,
                             #   index.html, build (esbuild), dist/
  editors/vscode/            # VS Code extension; embeds web/dist verbatim; imports the shared
                             #   protocol .ts by relative path so drift = compile error
  extensions/browser/        # (if targeted) MV3 extension; embeds web/dist or a trimmed page
  docs/                      # specs + plans; CLAUDE.md-style skeleton with per-area docs
```

Key layout rules:

- **The web bundle is the shared frontend asset.** Tauri (`frontendDist`), VS Code (`media/`
  copy), and a browser extension all embed the *built* `web/dist` — never fork the web source
  per host. Host differences gate on a runtime host flag (`isTauri()`, `isVsCode()`), each a
  small adapter module that no-ops elsewhere.
- **Shared protocol files are imported by relative path from both sides** (webview ↔ extension
  host), so any drift is a TypeScript compile error, not a runtime surprise.
- **The TUI host re-exports the core model** (`pub use core::model;`) so its modules keep
  stable paths and the split stays invisible to UI code.
- Host state modules that moved into core stay as thin re-export files in the host, so the
  migration doesn't churn every import.

## 4. Mix-and-match adaptability (pick any subset of platforms)

The design must let a project start with one platform and add others on demand, in any order:

- **Adding a platform = adding a shell, never touching core logic.** A new format/feature in
  core reaches every host by rebuilding; a new host is one new crate/dir + an adapter module.
- **Enum-dispatch for pluggable backends** inside core (`AnyDocument`-style: one enum wrapping
  each concrete impl, trait implemented by match-delegation). Adding a variant is mechanical;
  hosts hold the enum and never know which backend is live.
- **The host owns ALL platform I/O** behind one narrow, host-shaped handle abstraction. Define
  the handle contract once (e.g. `getFile()/createWritable()`-shaped), then make every platform
  conform: browser File System Access API, Tauri path strings, Android `content://` URIs, VS
  Code TextDocument. Upstream UI code stays byte-identical across platforms.
- **Cede ownership to hosts that already own a concern.** In VS Code, the `TextDocument` owns
  content/dirty/undo/save/hot-exit — the webview session becomes a *view* that reloads on
  text-change events. Don't run a parallel dirty/undo model; earlier protocol designs that did
  were retired for this.
- Decide per host what the "document boundary" is (file on disk, browser download, SAF URI,
  TextDocument) and keep that decision entirely inside the host's fs/adapter module.

## 5. Testing gates that keep the architecture honest

1. `no_fs_gate` — core stays pure (fails the build if `fs`/`env`/`process`/tempfile creep in).
2. Serde round-trip tests on every wire type (Intent/Snapshot) — the contract is frozen by test.
3. Headless session scripts — full user flows as `dispatch()` sequences, no UI.
4. Fake-`Host` tests for host-callback flows ($EDITOR etc.).
5. A Node smoke script driving the **built wasm** with the same flows — catches wasm-only
   breakage (marshalling, feature flags) that native tests can't. Reproduce bugs against the
   built artifact with the user's exact input; a passing headless test on similar input proves
   nothing.
6. Byte-identical round-trip tests if the app edits user files losslessly.
