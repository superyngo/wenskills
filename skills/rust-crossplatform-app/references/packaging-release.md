# Packaging & Publishing — One Pipeline, Every Platform

End-to-end guide from `cargo build` to each platform's distribution channel, plus the release
workflow that keeps them in sync.

## 0. Release workflow (do this every release)

1. One version, everywhere: bump `Cargo.toml` (workspace), `web/package.json`, extension
   `package.json`(s), Tauri config version. **A web deploy triggered by CI on push may key off
   `package.json` — forgetting that bump silently skips the deploy.** Script the bump.
2. Update `CHANGELOG.md`; the About/version surfaces are build-stamped so they follow
   automatically (never hand-edit a version string in code).
3. Tag `vX.Y.Z`; the tag triggers the release CI matrix.
4. Verify order: core tests → wasm smoke (Node, built artifact) → tsc → per-host manual
   acceptance checklists on real builds/hardware. Green unit tests alone never close a release.

## 1. CLI / TUI binaries

- **Channel:** GitHub Releases via a tag-triggered CI workflow (`softprops/action-gh-release`),
  cross-compiled matrix: linux x86_64 + aarch64 (musl for portability), macOS x86_64 + arm64,
  Windows x86_64 + arm64.
- Optionally `cargo install` via crates.io (publish the host crate; core publishes as its dep),
  and Homebrew tap / winget manifest once there's an audience.
- Scope CI release builds to the binary crate (`-p myapp-tui`), not the whole workspace —
  building GUI shells in the CLI job wastes CI and can require platform SDKs.
- Cache release builds in CI; the aggressive release profile is slow.

## 2. Web

- **Channel:** static hosting with CI/CD on push to main (Cloudflare Workers static assets:
  a `wrangler.toml` at root + a build script that runs wasm-pack → esbuild → `web/dist`;
  Pages/Netlify equivalent).
- The same build script is the local dev build — one pipeline, no drift.
- PWA manifest + service worker for installability; mind service-worker caching vs. the
  stale-wasm problem (version-stamped assets).
- Custom domain + HTTPS from the host; deploys are effectively free per push, so the web build
  is the always-current reference host.

## 3. Desktop (Tauri v2)

- **Build:** `cargo tauri build` from the shell crate (adds `custom-protocol` itself).
  - macOS → `.app`/`.dmg`. Distribution outside the App Store wants Developer ID signing +
    notarization; unsigned builds hit Gatekeeper (document the right-click-Open workaround in
    the release notes until signed).
  - Windows → NSIS installer / portable exe / MSIX (Store). **Must build on a Windows host**
    (WebView2; no cross-build) — a separate CI runner with the web bundle prebuilt (its config
    override empties before-commands).
  - Linux → AppImage/deb/rpm if targeted.
- **Channels:** GitHub Releases (dmg + exe) first; macOS App Store and Microsoft Store (MSIX)
  later — both add signing, sandbox entitlements, and review cycles; keep them out of the MVP.
- Icons: regen the full set from one source PNG via `cargo tauri icon` (must be RGBA).
- Updater: Tauri's updater plugin once signing exists; until then, releases page + in-app
  version check is enough.

## 4. Mobile

- **Android:** `cargo tauri android build --debug --apk` → sideload-able auto-signed debug APK
  (M1: personal use, manual acceptance on hardware). For Play: generate an upload keystore,
  build a signed `.aab` (`cargo tauri android build --aab`), Play Console listing, content
  rating, data-safety form, closed-track rollout first. File associations declared in the
  platform config surface in the Play listing's intent filters automatically.
- **iOS:** requires macOS + Xcode + Apple Developer program; `cargo tauri ios` flow; TestFlight
  as the sideload analogue. Plan it as its own milestone — capability gaps (document picker
  semantics, file associations) differ from Android and may need another first-party plugin.
- Ship mobile milestones sequentially (Android → iOS), each with a hardware acceptance
  checklist; don't block one on the other.

## 5. VS Code extension

- **Package:** `vsce package` → `.vsix`. It **must run from inside the git-tracked repo
  directory** — run outside and it silently packages an empty file list. Verify the vsix file
  list (icon, media/, dist) every time.
- **Sideload channel first** (`code --install-extension myapp.vsix`) with a manual acceptance
  checklist on the installed vsix; Marketplace is its own milestone:
  publisher account (Azure DevOps org) + PAT → `vsce publish`; Marketplace-facing README/
  CHANGELOG/icon (`package.json` `icon` field, verified in the vsix list); keep `.vsix`
  sideload supported alongside the listing.
- Also consider Open VSX (VSCodium/Cursor users) — same vsix, separate publish.

## 6. Browser extension

- **Package:** zip of the bundled extension dir (manifest + built assets; all code local, CSP
  includes `wasm-unsafe-eval`).
- **Channels:** Chrome Web Store (one-time dev fee, review), Firefox AMO (separate signing,
  MV3 dialect differences), Edge Add-ons (fast follow from the Chrome zip). Keep a per-store
  manifest overlay rather than forked sources — same pattern as Tauri's per-platform configs.

## 7. CI matrix summary

| Trigger | Job | Output |
|---|---|---|
| push to main | test + clippy + fmt; web build & deploy | live web host |
| tag `v*` | binary matrix (scoped `-p`) | GH Release: CLI/TUI archives |
| tag `v*` | macOS runner: `cargo tauri build` | dmg |
| tag `v*` | Windows runner: prebuilt dist + tauri build | nsis exe / msix |
| manual/milestone | Android signed build | apk/aab |
| manual/milestone | `vsce package`/`publish` | vsix / Marketplace |
| manual/milestone | store zips | Chrome/Firefox/Edge |

Keep manual-milestone lanes manual until each store's review overhead is worth automating;
automate the push/tag lanes from day one.
