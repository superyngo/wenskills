# VS Marketplace + Open VSX

**Verified**: this pattern is running in production (confy, live since M1.5).

## Mechanism

`vsce` (VS Marketplace) and `ovsx` (Open VSX) — both thin CLIs over their respective
publisher APIs, both take a prebuilt `.vsix` and a personal access token.

## One-time setup

- **VS Marketplace**: create a publisher at marketplace.visualstudio.com/manage, generate a
  PAT scoped to *Marketplace → Manage* from an Azure DevOps organization.
- **Open VSX**: sign in at open-vsx.org with GitHub, generate an access token from your
  profile, and verify the same publisher namespace (Open VSX requires namespace ownership
  verification independent of the Marketplace).

## Required secrets

| Secret | Used by |
|---|---|
| `VSCE_PAT` | `vsce publish` |
| `OVSX_PAT` | `ovsx publish` |

## Workflow

```yaml
name: Publish VS Code Extension
on:
  workflow_dispatch:
    inputs:
      tag:
        description: "App release tag to check out and publish (e.g. v0.18.0)"
        required: true
      dry_run:
        description: "Build + package only, skip Marketplace/Open VSX publish"
        type: boolean
        default: false

permissions:
  contents: read

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with:
          ref: ${{ inputs.tag }}

      # ... build steps producing the extension's webview bundle ...

      - name: Install extension deps
        working-directory: <EXTENSION_DIR>
        run: npm ci

      - name: Build extension
        working-directory: <EXTENSION_DIR>
        run: npm run build

      - name: Verify package.json version matches tag
        working-directory: <EXTENSION_DIR>
        run: |
          tag_version="${{ inputs.tag }}"
          tag_version="${tag_version#v}"
          pkg_version="$(node -p "require('./package.json').version")"
          if [ "$tag_version" != "$pkg_version" ]; then
            echo "::error::tag ${{ inputs.tag }} does not match package.json version $pkg_version"
            exit 1
          fi

      - name: Package .vsix
        working-directory: <EXTENSION_DIR>
        run: npx vsce package -o extension.vsix

      - uses: actions/upload-artifact@v5
        with:
          name: extension-vsix
          path: <EXTENSION_DIR>/extension.vsix

      - name: Publish to VS Marketplace
        if: ${{ inputs.dry_run != true }}
        working-directory: <EXTENSION_DIR>
        env:
          VSCE_PAT: ${{ secrets.VSCE_PAT }}
        run: npx vsce publish --packagePath extension.vsix

      - name: Publish to Open VSX
        if: ${{ inputs.dry_run != true }}
        working-directory: <EXTENSION_DIR>
        env:
          OVSX_PAT: ${{ secrets.OVSX_PAT }}
        run: npx ovsx publish extension.vsix -p "$OVSX_PAT"
```

## Gotchas

- **Version lockstep**: if the extension is versioned in lockstep with a parent app release
  (one tag, multiple targets), verify `package.json`'s version against the tag *before*
  publishing and fail loud on mismatch — a silent mismatch ships the wrong version number to
  the Marketplace with no easy undo.
- `dry_run` input builds and packages the `.vsix` (uploaded as a workflow artifact for manual
  inspection) without publishing — cheap way to test the pipeline without touching either
  Marketplace.
- Marketplace and Open VSX are two independent publishes with two independent tokens; either
  can fail without the other — don't assume one implies the other succeeded.
- Open VSX requires separate namespace-ownership verification even if you already own the
  Marketplace publisher of the same name.

## Docs

- vsce: <https://github.com/microsoft/vscode-vsce>
- ovsx: <https://github.com/eclipse/openvsx/tree/master/cli>
