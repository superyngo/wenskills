# Mac App Store

**Unverified in production** — general/official guidance, not battle-tested by the authoring
project. Re-verify tool status (esp. `altool`) before relying on it long-term.

## Mechanism

Two distinct steps:
1. **Code signing** with an Apple Distribution / Mac Installer Distribution certificate (not
   Developer ID) + a Mac App Store provisioning profile.
2. **Upload to App Store Connect** — `xcrun altool --upload-app` (still functional for
   App Store *uploads* as of 2025-2026, but Apple is steering new adoption toward
   **Transporter**, its GUI app / CLI successor) or fastlane `deliver`.

**Notarization (`notarytool` + `stapler`) is NOT part of the Mac App Store path** — MAS builds
go through Apple's manual App Review instead of the notary service. `notarytool`/`stapler`
only matter if the same project also ships a direct-download (Developer-ID) build outside the
Store.

## One-time setup

- Apple Developer Program membership.
- Create an **Apple Distribution** certificate + **Mac Installer Distribution** certificate,
  bundle both identities into one `.p12` (avoids keychain identity conflicts when
  `import-codesign-certs` runs).
- Create a Mac App Store distribution provisioning profile for the app's bundle ID.
- App Store Connect → *Users and Access → Keys*: create a **Team API Key** (not Individual —
  individual keys can lack provisioning-task permissions), download the `.p8` once, note the
  Key ID and Issuer ID.

## Required secrets

| Secret | Source |
|---|---|
| `APPSTORE_CERTIFICATES_FILE_BASE64` | `base64 -i cert.p12` |
| `APPSTORE_CERTIFICATES_PASSWORD` | `.p12` export password |
| `APP_STORE_CONNECT_KEY_ID` | ASC → Keys |
| `APP_STORE_CONNECT_ISSUER_ID` | ASC → Keys |
| `APP_STORE_CONNECT_PRIVATE_KEY` | downloaded `.p8` contents |

## Workflow

Runs on **`macos-latest`** only (signing/notarization tools are Apple-platform-only).

```yaml
jobs:
  publish:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v5
        with: { ref: ${{ inputs.tag }} }

      - uses: apple-actions/import-codesign-certs@v7
        with:
          p12-file-base64: ${{ secrets.APPSTORE_CERTIFICATES_FILE_BASE64 }}
          p12-password: ${{ secrets.APPSTORE_CERTIFICATES_PASSWORD }}

      # place the provisioning profile at
      # ~/Library/MobileDevice/Provisioning Profiles/

      # ... build & codesign the .app, package as .pkg with productbuild
      # using the Mac Installer Distribution identity ...

      - name: Register App Store Connect API key
        run: |
          xcrun notarytool store-credentials "asc-key" \
            --key <(echo "${{ secrets.APP_STORE_CONNECT_PRIVATE_KEY }}") \
            --key-id ${{ secrets.APP_STORE_CONNECT_KEY_ID }} \
            --issuer ${{ secrets.APP_STORE_CONNECT_ISSUER_ID }}

      - name: Upload to App Store Connect
        run: |
          xcrun altool --upload-app -f App.pkg -t macos \
            --apiKey ${{ secrets.APP_STORE_CONNECT_KEY_ID }} \
            --apiIssuer ${{ secrets.APP_STORE_CONNECT_ISSUER_ID }}
```

## Gotchas

- `altool` was deprecated **only for notarization** (Nov 2023), not for App Store Connect
  uploads — but treat it as legacy; Transporter is Apple's forward path. Re-verify before
  writing new CI around it.
- Keychain must be unlocked and searchable for `codesign`/`productbuild`/`altool` to find the
  imported identity — ephemeral runners mean the import step runs every job, not once.
- App Store Connect API key is the only 2FA-free CI auth path; Apple ID + app-specific-password
  is legacy and less reliable in CI.
- App Review is manual and asynchronous, multi-day latency, possible rejection — CI automates
  the upload, not the release.
- Individual (non-Team) API keys can silently lack permissions for signing/provisioning
  operations.

## Docs

- Notarizing macOS software: <https://developer.apple.com/documentation/xcode/notarizing-macos-software-before-distribution>
- App Store Connect API keys: <https://developer.apple.com/help/account/create-app-store-connect-api-key/>
- `apple-actions/import-codesign-certs`: <https://github.com/apple-actions/import-codesign-certs>
