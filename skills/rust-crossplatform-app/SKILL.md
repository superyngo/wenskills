---
name: rust-crossplatform-app
description: Use when starting, structuring, or extending a Rust application that targets any combination of CLI, TUI, web (wasm), desktop (Tauri), mobile, VS Code extension, or browser extension — covering workspace/folder layout, headless-core architecture, tech selection and recommended stack, per-platform best practices, and end-to-end packaging/store publishing. Apply for questions like "how should I structure this Rust app", "add a web/desktop/mobile/extension host", "which GUI/wasm/TUI stack", or "how do I ship this to <platform/store>".
---

# Rust Cross-Platform App Development

## Overview

A battle-tested blueprint for building one Rust app that ships to many platforms — derived from
a real project that shipped TUI, web (desktop + touch), macOS/Windows desktop, Android, and a
VS Code extension from a single workspace. The whole system rests on one doctrine, three
patterns, and per-platform playbooks kept in `references/`.

## The doctrine

**One pure Rust core crate; every platform is a thin host shell over it.**

- The core is filesystem-free, environment-free, UI-free, wasm-compatible, and the single
  source of truth for state, legality, i18n, and shared text. Enforced by tests, not
  discipline.
- Hosts own exactly: rendering, input plumbing, and platform I/O (files, dialogs, menus) —
  behind one narrow handle abstraction so upstream code is platform-blind.
- Adding a platform = adding a shell. Removing one deletes a directory. The core never changes
  for a host's sake; a host never re-implements a rule the core owns.

## The three patterns

1. **Session / Intent / Snapshot.** All interactive state lives in a core `Session`; every user
   gesture becomes one `Intent`; `dispatch(intent)` returns a full serializable
   `SessionSnapshot`; hosts re-render from it as a pure function. The serde types ARE the
   wasm/IPC wire contract. Sync dispatch; host holds no shadow model.
2. **One shared frontend bundle.** The web build (`web/dist`) is embedded verbatim by Tauri,
   the VS Code webview, and a browser extension; host differences gate on runtime host flags
   via small adapter modules (`isTauri()`, `isVsCode()`) that no-op elsewhere. Never fork the
   web source per host.
3. **Cede what the host already owns.** VS Code's TextDocument owns dirty/undo/save; the OS
   owns menus/title bar on desktop; SAF owns file permissions on Android. Duplicating a
   host-owned concern creates a second source of truth — the root cause of a whole bug class.

## References (read the one you need)

- **[references/architecture.md](references/architecture.md)** — hard rules for the headless
  core, the Session/Intent/Snapshot pattern in detail, the full workspace/folder layout
  template, mix-and-match platform adaptability, and the five testing gates (no-fs gate, serde
  round-trips, headless scripts, fake Host, built-wasm smoke).
- **[references/tech-stack.md](references/tech-stack.md)** — tech selection tables (core +
  per-platform), the recommended default stack (clap/ratatui/wasm-bindgen+esbuild/Tauri v2/
  CustomTextEditorProvider/MV3), decisions not to re-litigate (session-in-webview, no JS
  framework, no npm Tauri deps), and heuristics for deviating.
- **[references/platform-practices.md](references/platform-practices.md)** — per-platform
  playbooks and shipped-bug gotchas: CLI, TUI, web/wasm (stale-wasm cache, build script
  unification), Tauri desktop (menu GC, capabilities, config merge, custom-protocol), Android
  (SAF URIs, plugin serde field trap, regen-clobbered files), VS Code (keybinding precedence,
  protocol-as-shared-file), browser extension (MV3 CSP, no wasm in service workers).
- **[references/packaging-release.md](references/packaging-release.md)** — the one-pipeline
  release workflow (synchronized version bumps — CI deploy triggers hang off them), and
  channel-by-channel shipping: GH Releases binary matrix, static-host web deploy, dmg/nsis/msix
  signing realities, APK/AAB Play flow, vsce/Marketplace/Open VSX, extension stores, and the
  CI matrix summary.

## Ground rules that span everything

- **Verify on the real artifact.** Rebuilt wasm in the actual browser, installed vsix, debug
  APK on hardware, opened dmg — green unit tests never close a platform milestone; each host
  gets a manual acceptance checklist.
- **Milestone per platform, sequential.** Ship platform N usable (sideload/beta is fine)
  before starting N+1; store publishing is its own later milestone per platform.
- **Document the host seams.** Keep a per-host doc (TAURI.md, VSCODE.md…) plus a skeleton
  top-level guide; record any hand-edits inside generated projects as reapply-after-regen.
- **UI behavior conventions** (focus, popups, re-renders, cross-host component sharing) are in
  the companion `ui-design-principles` skill — apply it alongside this one for anything
  user-facing.

## Common Mistakes

- Putting file paths, `fs` calls, or env reads in the core "just this once" (breaks wasm and
  every future host; the no-fs gate exists to catch this).
- Running app logic Rust-side in Tauri managed state (async invoke + `!Send` state; editing
  belongs in the in-webview wasm session).
- Forking the web frontend per host instead of gating on a host flag.
- Re-implementing dirty/undo/save inside a VS Code webview instead of ceding to TextDocument.
- Testing only the native build and shipping a stale/broken wasm (cache + forgotten rebuild).
- Hand-editing versions in code instead of build-stamping; forgetting the package.json bump
  that triggers the web deploy.
- Treating store publishing as part of the first milestone instead of a follow-up.
