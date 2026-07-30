# Obsidian Community Plugins

**Unverified in production** — general/official guidance, not battle-tested by the authoring
project.

## Mechanism

No CLI or REST API for version releases. Obsidian's client reads `community-plugins.json` for
search metadata, then fetches `manifest.json`/`README.md` directly from the plugin's GitHub
repo, and downloads `manifest.json`, `main.js`, `styles.css` (if present) as **GitHub Release
assets** from a release **tagged exactly to `manifest.json`'s `version`** (no `v` prefix — this
is a hard client-side match, not a convention).

A one-time PR to `obsidianmd/obsidian-releases` (adding an entry to `community-plugins.json`)
is required only for initial directory admission — not for every subsequent release.
`plugin-review-bot` gates that one-time PR (validates manifest shape, `id` match, tag-equals-
version, required assets) and re-scans automatically on pushes to the plugin repo's default
branch, no new PR needed.

## Required files (as release assets)

- `manifest.json` — `id`, `name`, `version`, `minAppVersion`, `description`, `author`,
  `authorUrl`, `isDesktopOnly`
- `main.js` — built/bundled entry point
- `styles.css` — optional, include only if present
- `versions.json` (repo root, not a release asset) — maps historical plugin versions to
  `minAppVersion`, consulted client-side when a user's Obsidian is older than the current
  manifest requires, so an older-but-compatible release can still resolve

## Workflow

Obsidian's own `obsidian-sample-plugin` template ships the de facto standard workflow every
plugin author copies:

```yaml
name: Release Obsidian plugin
on:
  push:
    tags:
      - '*'

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      id-token: write
      attestations: write
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v6

      - name: Build
        run: npm ci && npm run build

      - name: Check for styles.css
        id: styles
        run: echo "exists=$([ -f styles.css ] && echo true || echo false)" >> "$GITHUB_OUTPUT"

      - name: Create release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          tag="${GITHUB_REF#refs/tags/}"
          gh release create "$tag" --title="$tag" --draft main.js manifest.json \
            ${{ steps.styles.outputs.exists == 'true' && 'styles.css' || '' }}
```

This is the shape for a standalone, single-purpose plugin repo. When Obsidian is one store
among several in a larger multi-store pipeline, adapt it to the same
`workflow_dispatch(tag, run_id)` shape every other store in this skill uses — the main build
workflow produces the plugin bundle as one more artifact, and a dispatched `publish-obsidian.yml`
downloads it and runs the same `gh release create` call as its **submit** step. Minting this
second, differently-tagged GitHub Release *is* the submission here — there's just no third
party on the other end of it (see "Submit" in `CONTEXT.md`):

```yaml
name: Publish to Obsidian
on:
  workflow_dispatch:
    inputs:
      tag: { description: "App release tag to publish (e.g. v0.18.0)", required: true }
      run_id: { description: "Run ID of the build that produced the plugin bundle", required: true }

permissions:
  contents: write

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v5
        with: { name: <PLUGIN_BUNDLE>, path: build, run-id: ${{ inputs.run_id }} }

      - name: Create Obsidian release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          version="$(node -p "require('./build/manifest.json').version")"
          gh release create "$version" --title="$version" --draft \
            build/main.js build/manifest.json build/styles.css
```

## Gotchas

- **Tag must equal `manifest.json`'s `version` verbatim** — exact string, case-sensitive, no
  `v` prefix. The most common CI mistake here.
- Repo *Settings → Actions → General → Workflow permissions* must allow "Read and write
  permissions" or `GITHUB_TOKEN` can't create the release.
- The workflow creates a **draft** release — a human must click Publish; this is an
  intentional manual checkpoint even with full automation.
- No release-please/semantic-release convention in the ecosystem; version bumps go through the
  sample plugin's `version-bump.mjs` invoked via `npm version` hooks, keeping `package.json`,
  `manifest.json`, `versions.json` in lockstep before tagging.
- Directory-listing PR review (one-time only) has no SLA and can queue for a long time —
  unrelated to the instant, unthrottled release mechanics above.

## Docs

- `obsidianmd/obsidian-sample-plugin`: <https://github.com/obsidianmd/obsidian-sample-plugin>
- `obsidianmd/obsidian-releases`: <https://github.com/obsidianmd/obsidian-releases>
