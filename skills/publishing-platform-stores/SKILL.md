---
name: publishing-platform-stores
description: Use when adding a GitHub Actions workflow that publishes desktop, mobile, or extension builds (editor plugins, app plugins, or browser extensions) to a platform store (Microsoft Store, Mac App Store, Steam, Google Play, Apple App Store, VS Marketplace, Open VSX, Obsidian, Chrome Web Store, Edge Add-ons, Firefox AMO) — or wiring a new store into an existing tag-triggered release pipeline.
---

# Publishing to Platform Stores

## Overview

Store publishing is a separate concern from building and tagging a release: stores fail
independently (expired secrets, review rejection, API version churn) on their own schedule,
so one build workflow should never be coupled to N store-specific submission flows. Keep the
release build lean, gate publishing behind one manual approval, and give every store its own
small, independently-retryable workflow.

**REQUIRED BACKGROUND:** Use `create-release-workflow` for the base tag-triggered
build/GitHub-Release workflow this pattern hangs off. This skill starts where that one ends.

## When to Use

- Adding the first store publish step to a project that already tags releases via CI
- Wiring a new store into an existing multi-store publish pipeline
- Deciding whether a store submission belongs in the build workflow or a separate one (it
  belongs separate — see Core Pattern)

**Don't use for:** the build/tag/GitHub-Release workflow itself (that's
`create-release-workflow`), or a project with only one store and no review/approval need
(a single `publish:` job appended to the build workflow is simpler and fine).

## Core Pattern

```
release.yml (build + tag → GitHub Release)
        │  workflow_run, completed
        ▼
publish-gate.yml — environment: publish-gate (1 required reviewer)
        │  if event == push && conclusion == success   (excludes manual/dry-run dispatches)
        │  gh workflow run publish-<store>.yml -f tag=$TAG -f run_id=$RUN_ID   (one line per store)
        ├──────────────┬──────────────┬── … ────────────┐
        ▼              ▼              ▼                 ▼
publish-msstore.yml  publish-vscode.yml  publish-play.yml  publish-<new>.yml
  (workflow_dispatch: tag, run_id)
  → download build artifact from that run_id
  → authenticate with store-specific secrets
  → upload / submit via the store's CLI or API
```

Why this shape, not one big workflow:
- **Independent retry.** A rejected Chrome Web Store review or an expired Steam session
  shouldn't force re-running the whole build matrix — `workflow_dispatch` re-runs just that
  store with the same `tag`/`run_id`.
- **One approval, not N.** `publish-gate.yml` is the only workflow behind a required-reviewer
  `environment:`; it fires once per release and fans out, instead of prompting a reviewer once
  per store.
- **Artifacts, not rebuilds.** Publish workflows download the exact binary `release.yml`
  already built and uploaded as a workflow artifact (`actions/download-artifact@v5` with
  `run-id: <the release run>`), so what ships to a store is byte-identical to what's on the
  GitHub Release — never rebuilt from source a second time.
- **Decouple checkout `ref` from the release `tag` for source-building publishers.** Stores
  that build from source at publish time (VS Marketplace/Open VSX, Obsidian, browser
  extensions) rather than re-uploading a prebuilt artifact should take `ref` as an input
  separate from `tag`, defaulting to `tag` when omitted: `ref: ${{ inputs.ref || inputs.tag }}`.
  `tag` is only what the publish is *recorded against* and what the manifest/`package.json`
  version is validated against; `ref` is what actually gets checked out and built. Hardcoding
  the checkout to `inputs.tag` means any post-tag fix (a version-file typo caught only by the
  publish workflow's own validation step) can only be fixed by moving/retagging the whole app
  release — which re-triggers the entire cross-platform build matrix in `release.yml` for a
  one-file change unrelated to any of those builds. With `ref` decoupled, dispatch with the
  original `tag` (so the release record stays correct) and `ref` pointed at whatever branch/SHA
  has the fix.
- **Gate excludes dry runs.** Guard the gate job with
  `github.event.workflow_run.conclusion == 'success' && github.event.workflow_run.event == 'push'`
  so manual `workflow_dispatch` test builds on `main` never trigger real store submissions.
- **Selective publishing.** The default gate is all-or-nothing per release (every configured
  store gets dispatched). If a project needs to choose which stores a given release reaches,
  split the single gate job into one job per store, each behind its own
  `environment: publish-gate-<store>` — GitHub's pending-deployments review screen then shows
  one checkbox per store for that same run. See `docs/adr/0002-selective-publish-gate.md`.

## Platform Reference

Every platform below needs its **first listing created manually** — a store dashboard form for
API-backed stores, or a one-time hand-run CLI submission for PR-based stores (winget, Obsidian);
no researched API can create a brand-new app/extension/product; CI only updates an existing
one. Load the reference file only for the store you're integrating.

| Category | Store | Mechanism | Reference |
|---|---|---|---|
| Desktop | Microsoft Store | `msstore` CLI / Partner Center Submission API | [desktop-microsoft-store.md](references/desktop-microsoft-store.md) |
| Desktop | Mac App Store | Transporter / `altool` + App Store Connect API | [desktop-mac-app-store.md](references/desktop-mac-app-store.md) |
| Desktop | Steam (Linux/cross-platform) | `steamcmd` via `game-ci/steam-deploy` | [desktop-steam.md](references/desktop-steam.md) |
| Desktop | winget (Windows Package Manager) | `vedantmgoyal9/winget-releaser` (Komac) → PR to `microsoft/winget-pkgs` | [desktop-winget.md](references/desktop-winget.md) |
| Mobile | Google Play | Play Developer API via `r0adkll/upload-google-play` | [mobile-google-play.md](references/mobile-google-play.md) |
| Mobile | Apple App Store / TestFlight | App Store Connect API via fastlane `pilot`/`deliver` | [mobile-apple-app-store.md](references/mobile-apple-app-store.md) |
| Extension | VS Marketplace + Open VSX | `vsce` / `ovsx` | [extension-vscode-openvsx.md](references/extension-vscode-openvsx.md) |
| Extension | Obsidian community plugins | GitHub Release assets, no API | [extension-obsidian.md](references/extension-obsidian.md) |
| Extension | Chrome Web Store | Chrome Web Store API v2 | [browser-chrome-web-store.md](references/browser-chrome-web-store.md) |
| Extension | Microsoft Edge Add-ons | Edge Add-ons Update REST API | [browser-edge-addons.md](references/browser-edge-addons.md) |
| Extension | Firefox Add-ons (AMO) | `web-ext sign` | [browser-firefox-amo.md](references/browser-firefox-amo.md) |

**Extending to a new store ("其他"):** add `references/<category>-<store>.md` following the
same shape (mechanism → CI approach → required secrets → workflow snippet → gotchas → official
docs) and one row to the table above. The skill body itself never grows — only the table and
the reference set.

## Checklist: Wiring a New Store

1. Create the app/product listing manually first — a store dashboard form (Partner Center, App
   Store Connect) for API-backed stores, or a one-time hand-run CLI submission (Obsidian's
   first tagged release, winget's first `komac new`) for PR-based stores. Every platform
   researched requires this one-time manual step — don't spend time looking for a
   create-listing API.
2. Read that store's reference file in full before writing YAML.
3. Add the required GitHub secrets, named `<STORE>_<FIELD>` (uppercase, e.g.
   `MSIX_SUBMISSION_CLIENT_SECRET`).
4. Add one dispatch line to `publish-gate.yml`:
   `gh workflow run publish-<store>.yml --repo "${{ github.repository }}" --ref main -f tag="$TAG" -f run_id="$RUN_ID"`.
   Give `publish-gate.yml` itself a `workflow_dispatch` trigger too (`tag`, `run_id` inputs,
   same `if: github.event_name == 'workflow_dispatch' || (...)` pattern), so the whole
   approval gate can be re-run manually for an already-built release — e.g. re-approving after
   a downstream publish failure — without waiting for a fresh `Release` `workflow_run` event.
5. Write `publish-<store>.yml`: `workflow_dispatch` inputs `tag` + `run_id` (artifact-only
   stores that just re-upload what `release.yml` built) or `tag` + optional `ref` defaulting to
   `tag` (source-building stores — see Decouple checkout `ref` above) →
   `actions/download-artifact@v5` (pinned to `run-id: inputs.run_id`) → authenticate (skip for
   API-less stores — go straight to minting the store's own canonical release artifact) →
   upload → submit for review if the store has one.
6. If the submit step is hard to reverse (production track, listed review), add a `dry_run`
   boolean input that stops before the point of no return — see
   `publish-vscode.yml`'s pattern in the VS Marketplace reference.
7. Update the project's own release-status map (channel → method → trigger → current
   version → status) so the new store is discoverable without reading every workflow file.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Coupling store publish to the build job (`if: success()` in the same workflow) | Split into a separate `workflow_dispatch` workflow — a store outage or review rejection then can't fail or block the build/tag/GitHub-Release step |
| One `environment:` approval per store | One shared `publish-gate` environment/approval that fans out to every `publish-*.yml` — see `docs/adr/0001-shared-publish-gate.md` for why |
| Assuming store submission is synchronous | Chrome Web Store, Firefox listed review, Mac/iOS App Review, and Google Play closed review are all asynchronous, human-reviewed, and can take hours to days for *every* release — CI can only automate the *upload*, not the *approval*. (Obsidian's directory-admission review is separate: it's a one-time gate on first listing, not a per-release review — ordinary Obsidian releases are unthrottled.) |
| Running a Linux-only credential flow on `ubuntu-latest` | `msstore`'s Linux keyring needs `libsecret` + a D-Bus Secret Service daemon headless runners lack; use `windows-latest` (DPAPI works headless) — check each store's reference for runner-OS constraints (macOS-only for Apple signing/notarization, etc.) |
| Treating store CLI/API version pins loosely | Pin third-party GitHub Actions to a specific tag; expiring OAuth refresh tokens (Chrome), rotating API keys (Edge), and session files (Steam `config.vdf`) all need scheduled secret rotation, not "set once" |
| Version drift between the tag and the store manifest | Obsidian requires the release tag to equal `manifest.json`'s `version` verbatim (no `v` prefix); VS Marketplace/Open VSX need `package.json`'s version to match the app tag if versioned in lockstep — verify in CI before publishing, fail loud on mismatch |
| Source-building publish workflow's checkout `ref` hardcoded to the same `inputs.tag` used for version validation | Add a separate `ref` input defaulting to `tag` (`ref: ${{ inputs.ref \|\| inputs.tag }}`) — a post-tag version-file fix then only needs a different `ref`, not moving/retagging the whole app release and re-running the entire build matrix |
