# winget (Windows Package Manager Community Repository)

**Verified**: this pattern ran in production for `wenget` (superyngo/wenget), first listed
manually 2025-11-26.

## Mechanism

No submission API. `vedantmgoyal9/winget-releaser` (community action, wraps `komac` under the
hood) opens a pull request against `microsoft/winget-pkgs` on your behalf, reading the
already-published GitHub Release directly — unlike every other store in this skill, it does
**not** need a build-artifact download step; there is nothing to authenticate against or
upload to beyond that one PR.

## One-time setup (manual — cannot be automated)

`winget-releaser` explicitly refuses to create a **new** package — it only submits version
updates to a package that already exists in `microsoft/winget-pkgs`. The very first manifest
must be created by hand, once:

```bash
komac new --identifier <Publisher>.<Package> --version <first-version> \
  --urls <windows-installer-urls> --token $WINGET_TOKEN
# or: wingetcreate new <installer-url> --token $WINGET_TOKEN
```

This opens a `New package:` PR reviewed by the winget-pkgs validation pipeline + a moderator.
Only after that PR **merges** does the CI workflow below start working — dispatching it before
merge fails because the action has no existing manifest to diff against.

## Required secrets

| Secret | Source |
|---|---|
| `WINGET_TOKEN` | GitHub **classic** PAT, `public_repo` scope, from an account with a fork of `microsoft/winget-pkgs` — fine-grained tokens are not supported |

## Workflow

Runs on **`windows-latest`** — `komac`/`winget-releaser`'s manifest validation targets the
Windows package-manager ecosystem and is documented and tested against that runner.

```yaml
name: Publish to winget
on:
  workflow_dispatch:
    inputs:
      tag:
        description: "Release tag to publish (e.g. v3.8.6)"
        required: true
        type: string
      run_id:
        description: "Run ID of the Release workflow (unused — winget-releaser reads the public GitHub Release directly)"
        required: false
        type: string

permissions:
  contents: read

jobs:
  publish:
    runs-on: windows-latest
    steps:
      - uses: vedantmgoyal9/winget-releaser@v2   # pin a tag, never @main
        with:
          identifier: <Publisher>.<Package>
          token: ${{ secrets.WINGET_TOKEN }}
          installers-regex: '\.exe$'              # narrow to your Windows assets only
          release-tag: ${{ inputs.tag }}
          max-versions-to-keep: 5
```

## Gotchas

- **New packages are not supported.** First submission is always manual (`komac`/`wingetcreate`
  locally); see "One-time setup" above. Dispatching the CI workflow before that first PR merges
  fails with no manifest to update.
- **`PackageIdentifier` is effectively permanent.** Renaming the source GitHub repo does not
  rename the identifier — the two are unrelated once chosen. Changing it means removing the old
  listing and resubmitting fresh (loses version history, re-triggers full moderator review as a
  new package), so pick the identifier deliberately and don't couple it to the repo name.
- Pin the action to a release tag, not `@main` — see the main SKILL.md's "Treating store
  CLI/API version pins loosely" mistake.
- Release must be public (not draft) before dispatch — the action reads it via the GitHub API,
  same constraint as Obsidian's client-side fetch.
- `installers-regex` must exclude non-Windows release assets (`.tar.gz`, plain macOS/Linux
  binaries) or the action tries to build installer manifests for files that aren't installers.
- Multiple Windows architectures (x86_64, i686/x86, aarch64) in one release are fine — `komac`
  infers architecture per matched asset from its filename; verify your asset naming actually
  contains a recognizable arch token.
- Moderator review (`Moderator-Approved` label) can be near-instant when the automated
  validation pipeline passes cleanly, or take days for manually-flagged installers (unsigned
  `.exe`, first submission from a new publisher) — CI only automates the PR, not the merge.

## Docs

- `winget-releaser`: <https://github.com/vedantmgoyal9/winget-releaser>
- `komac`: <https://github.com/russellbanks/Komac>
- `microsoft/winget-pkgs`: <https://github.com/microsoft/winget-pkgs>
