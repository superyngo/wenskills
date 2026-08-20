---
name: create-release-workflow
description: Use when generating a GitHub Actions release workflow (.github/workflows/release.yml) for a Rust project with multi-platform binary builds (Linux/Windows/macOS, gnu/musl, x86/arm) triggered by v*.*.* tags
---

# Create Release Workflow (Rust)

## Overview

Generates a complete `.github/workflows/release.yml` for cross-platform Rust binary releases. Acts as a DevOps engineer: collects project + target info from the user, then emits the full YAML.

## When to Use

- User wants to add release automation to a Rust project
- Need multi-platform builds (Linux gnu/musl, Windows MSVC, macOS Intel/ARM)
- Release is triggered by pushing `v*.*.*` tags
- Need SHA256SUMS, tar.gz packaging, and auto-generated changelogs

**Don't use for:** non-Rust projects, library-only crates (no binary), or projects that already have a working release workflow (edit instead).

## Required Inputs

Ask the user before generating:

1. **Binary name** — `<BINARY_NAME>` (Windows uses `<BINARY_NAME>.exe`)
2. **Cargo workspace?** — yes/no
3. **Build features** — e.g. `--features tls`, or none
4. **Target platforms** (let user check from the list below)
5. **Custom RUSTFLAGS per target** — e.g. armv7 needs `-C linker=arm-linux-gnueabihf-gcc`

### Target Platform Menu

**Linux (ubuntu-latest):**
- `x86_64-unknown-linux-gnu`, `i686-unknown-linux-gnu`
- `x86_64-unknown-linux-musl`, `i686-unknown-linux-musl`
- `armv7-unknown-linux-gnueabihf`, `armv7-unknown-linux-musleabihf`
- `aarch64-unknown-linux-gnu`, `aarch64-unknown-linux-musl`

**Windows (windows-latest):**
- `x86_64-pc-windows-msvc`, `i686-pc-windows-msvc`

**macOS:**
- `x86_64-apple-darwin` → `macos-15-intel`
- `aarch64-apple-darwin` → `macos-latest`

## Build Strategy

### Optimization

| Platform | Strategy |
|----------|----------|
| Linux / macOS | Use `Cargo.toml` release profile (aggressive) |
| Windows | Override via env to avoid AV false positives: `opt-level=3`, `lto="thin"`, `strip=false`, `codegen-units=16`, `panic="unwind"`, `RUSTFLAGS="-C target-feature=+crt-static"` |

### Cross-Compilation

| Target group | Tool |
|--------------|------|
| musl (i686, armv7, aarch64) | `cross` (`cargo install cross --git https://github.com/cross-rs/cross`) |
| ARM GNU | install `gcc-arm-linux-gnueabihf`, configure `~/.cargo/config.toml` linker |
| Other Linux | native `cargo build` |

Any step that shells out to `apt-get install` (ARM GNU linker, musl-tools, etc.) MUST be
wrapped in a bounded timeout + retry loop, not a bare `sudo apt-get update && sudo apt-get
install -y <pkg>`. GitHub-hosted `ubuntu-latest` runners occasionally hold a background
dpkg/apt lock (e.g. `unattended-upgrades`) that makes a bare `apt-get` hang for 10+ minutes
with no error — it doesn't fail, it just never returns, silently stalling the whole matrix
(`fail-fast: false` doesn't help; the job itself never completes). Emit every such step as:

```yaml
- name: Install <pkg>
  if: matrix.kind == '<kind>'
  timeout-minutes: 6
  run: |
    for i in 1 2 3; do
      sudo timeout 90 apt-get update && sudo timeout 180 apt-get install -y <pkg> && exit 0
      echo "apt-get attempt $i failed/timed out, retrying in 10s..."
      sleep 10
    done
    exit 1
```

### Strip

| Target | Command |
|--------|---------|
| x86 Linux (gnu/musl) | `strip` |
| armv7 gnueabihf | `arm-linux-gnueabihf-strip` (skip if missing) |
| aarch64-linux-gnu | `aarch64-linux-gnu-strip` |
| aarch64-musl | skip (cross handles it) |
| Windows / macOS | no strip |

## Line Endings (`.gitattributes`)

Always emit a repo-root `.gitattributes` with `* text=auto eol=lf` alongside the workflow —
or confirm one already exists — whenever the matrix includes a `windows-latest` runner.
Windows checkouts default to git `core.autocrlf=true`, which silently rewrites LF source to
CRLF. This is invisible to any Linux-only CI (`ubuntu-latest` typecheck/test workflows never
see it) and only surfaces on the Windows leg of the release build itself — as spurious
failures in anything that does line-anchored text matching (build scripts, codegen, test
fixtures asserting on `\n`-delimited source). Diagnosed once as "Windows build fails a check
that never fails in CI" → check `.gitattributes` before anything else.

## Bundled Frontend / Webview Legs (Tauri, wasm, embedded web UI)

If a Desktop/Tauri leg builds a bundled web frontend (wasm core + TS/JS UI) as part of its
`beforeBuildCommand`, that build gate (typecheck + test) runs on every OS in the matrix —
including Windows and macOS — even if the project's separate "Web CI" workflow only runs on
`ubuntu-latest`. A frontend regression (e.g. a strict-null-check violation) can pass "Web CI"
green and still break every platform's Release build simultaneously. Before tagging a release
that touches the frontend, run its exact typecheck + test commands locally (same commands the
release workflow's frontend-build step runs, e.g. `tsc --noEmit && npm test`) — don't rely on
a same-OS CI workflow as a sufficient gate for a build step that also runs cross-platform.

## Release Artifacts

- **Linux / macOS:** `<BINARY_NAME>-<platform>.tar.gz`
- **Windows:** `<BINARY_NAME>-windows-<arch>.exe` (no archive)
- Always emit `SHA256SUMS`

## Release Metadata

- **Trigger:** push tags matching `v*.*.*`
- **Body:** annotated tag message as preamble + `generate_release_notes: true`
- `draft: false`, `prerelease: false`

## Workflow Requirements

- `fail-fast: false` — platforms independent
- Publish job MUST `needs: [<every build job>]` — a single failed leg blocks the release; never let publish run against a partial artifact set
- Every build job MUST `needs: verify-versions` — see Version Consistency Gate below
- `permissions: contents: write, actions: write`
- Toolchain: `dtolnay/rust-toolchain@stable`
- Release action: `softprops/action-gh-release@v1`
- Ask user about extras: winget workflow_dispatch, `cargo-deny`, test runs, etc.

## Version Consistency Gate

Add a `verify-versions` job that every build job `needs:`, running before any platform starts
building. Check every version-bearing file in the repo against the tag being released, and
fail fast — not discovered N minutes into a multi-platform build, or worse, only at a
store-publish step run hours/days later (see `publishing-platform-stores`'s checkout-`ref`/
`tag` decoupling, whose whole reason to exist is this exact failure mode reaching all the way
to store submission after a tag is already cut and a full matrix already built).

- **Skip on dry runs.** Guard with `if: github.ref_type == 'tag'` — `workflow_dispatch` dry
  runs execute on a branch, not a release tag, and have no tag-derived version to check
  against. A skipped `needs:` dependency still counts as success for downstream jobs, so this
  doesn't block dry-run builds.
- **Every build/desktop job depends on it.** Add `needs: verify-versions` to each one (the
  publish job's existing `needs: [<every build job>]` then chains through automatically).
- **List every version-bearing file, not just `Cargo.toml`.** A workspace's crates typically
  inherit `version.workspace = true` from the root `Cargo.toml`, so one check there covers all
  of them — but a bundled web frontend (`web/package.json`), an editor extension
  (`editors/vscode/package.json`), or any other manifest with its own independent version
  field needs its own check line. Miss one and it silently drifts until something downstream
  discovers it — a publish workflow's own version-validation step, a store's manifest-mismatch
  rejection — by which point the tag is already cut and the full matrix already built.
- **Check the changelog too.** Verify `CHANGELOG.md` has a `## [vX.Y.Z]` heading matching the
  tag — catches "forgot to convert `[Unreleased]`" the same way.

```yaml
jobs:
  verify-versions:
    name: Verify version consistency
    if: github.ref_type == 'tag'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - name: Check all version files + CHANGELOG match the tag
        run: |
          tag="${GITHUB_REF_NAME#v}"
          fail=0
          check() {
            local label="$1" actual="$2"
            if [ "$actual" != "$tag" ]; then
              echo "::error::$label is '$actual', expected '$tag' (from tag ${GITHUB_REF_NAME})"
              fail=1
            fi
          }
          check "Cargo.toml [workspace.package].version" \
            "$(grep -m1 '^version' Cargo.toml | sed -E 's/version = "(.*)"/\1/')"
          # One `check` line per additional version-bearing file, e.g.:
          # check "web/package.json .version" "$(node -p "require('./web/package.json').version")"
          if ! grep -q "^## \[v${tag}\]" CHANGELOG.md; then
            echo "::error::CHANGELOG.md has no '## [v${tag}]' section"
            fail=1
          fi
          exit $fail

  build:
    needs: verify-versions
    # ...
```

## Diagnosing a Failed Release Run

The final publish job MUST gate on `needs: [<every build job>]` (already covered under
Workflow Requirements) so a single failed matrix leg blocks the GitHub Release entirely — no
partial release ever gets published. This makes failures cheap to fix forward:

- **Triage per-leg:** `gh run view <run-id>` lists every matrix leg's status;
  `gh run view <run-id> --job <job-id> --log-failed` (once the job has completed) pulls just
  the failing step's log. Don't guess from the summary — read the actual error.
- **Retry only what broke:** `gh run cancel <run-id>` then `gh run rerun <run-id> --failed`
  reruns only the failed/cancelled legs and reuses already-succeeded ones — far cheaper than
  re-tagging for a transient runner hang (see apt-get retry above; a genuine infra hang can
  still require one cancel+rerun cycle even with the retry loop in place).
- **Fix-forward the same tag, don't bump the version:** if the run failed before the publish
  job ran, nothing was released — confirm with `gh release view vX.Y.Z` (404 = nothing
  published). It's then safe to commit the fix, then move the tag to the new commit instead
  of cutting `vX.Y.(Z+1)` for a build-only fix:
  ```bash
  git tag -d vX.Y.Z && git push origin :refs/tags/vX.Y.Z
  git tag -a vX.Y.Z -m "..." && git push origin main && git push origin vX.Y.Z
  ```
  Never move a tag that a `gh release view` confirms already has published assets.
- **Don't move the tag for a downstream-only fix.** If the Release build/publish itself
  succeeded and only a *store* publish step failed on something unrelated to the built
  binaries (e.g. a version file the store publisher checks but the Rust build never touches),
  moving/retagging the app release just to fix that one file wastes the entire multi-platform
  build matrix on a rebuild that changes nothing about the binaries. Use
  `publishing-platform-stores`'s checkout-`ref`/`tag` decoupling instead — dispatch the store's
  publish workflow with the original `tag` and a `ref` pointing at the fix.

## Output

Emit the complete YAML file. No truncation, no placeholders left unresolved — substitute every `<...>` with the user's answers.
