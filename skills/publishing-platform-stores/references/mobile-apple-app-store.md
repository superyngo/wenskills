# Apple App Store / TestFlight

**Unverified in production** — general/official guidance, not battle-tested by the authoring
project. No single dominant marketplace GitHub Action exists here (unlike Google Play); the
de facto CI convention is running fastlane directly on `macos-latest`.

## Mechanism

App Store Connect API (REST, JWT-signed with a `.p8` key) is canonical. On top of it: fastlane
`pilot` (upload_to_testflight) for TestFlight distribution, and `deliver` (upload_to_app_store)
for full App Store submission — a separate, heavier step than TestFlight.

- **TestFlight**: internal testing (≤100 App Store Connect users) is available almost
  immediately after processing; external testing requires a lightweight Apple Beta App Review
  (usually <24h) the first time a build goes external.
- **App Store**: `deliver` submits metadata + binary for full, manual App Review (days-scale,
  not guaranteed to pass) — the final step after TestFlight validation, not a substitute.

## One-time setup

- App Store Connect → *Users and Access → Keys*: create a **Team API Key** (Individual keys
  can lack provisioning-task permissions) — yields Key ID, Issuer ID, one-time-downloadable
  `.p8`.
- Code signing (fastlane `match` convention): a Distribution certificate + App Store
  provisioning profile stored encrypted in a private git repo, synced via `match`. Needs
  `MATCH_PASSWORD` (encryption passphrase) and SSH/token access to clone the match repo.
  Fastfile calls `setup_ci` (temporary CI keychain) before `match(type: "appstore", readonly:
  true)` — always `readonly: true` in CI so a runner never mutates team-shared certs.

## Required secrets

| Secret | Source |
|---|---|
| `APP_STORE_CONNECT_KEY_ID` | ASC → Keys |
| `APP_STORE_CONNECT_ISSUER_ID` | ASC → Keys |
| `APP_STORE_CONNECT_PRIVATE_KEY` | downloaded `.p8` |
| `MATCH_PASSWORD` | match repo encryption passphrase |
| `MATCH_GIT_SSH_KEY` (or token) | access to the private match repo |

## Workflow

```yaml
jobs:
  publish:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v5
        with: { ref: ${{ inputs.tag }} }

      - uses: webfactory/ssh-agent@v0.9
        with: { ssh-private-key: ${{ secrets.MATCH_GIT_SSH_KEY }} }

      - name: Fetch signing identity (readonly)
        run: bundle exec fastlane run setup_ci
        # then in the Fastfile: match(type: "appstore", readonly: true, ...)

      - name: Upload to TestFlight
        env:
          APP_STORE_CONNECT_API_KEY_KEY_ID: ${{ secrets.APP_STORE_CONNECT_KEY_ID }}
          APP_STORE_CONNECT_API_KEY_ISSUER_ID: ${{ secrets.APP_STORE_CONNECT_ISSUER_ID }}
          APP_STORE_CONNECT_API_KEY_KEY: ${{ secrets.APP_STORE_CONNECT_PRIVATE_KEY }}
          MATCH_PASSWORD: ${{ secrets.MATCH_PASSWORD }}
        run: bundle exec fastlane pilot upload

      # separate, heavier step — only once TestFlight has validated the build
      - name: Submit to App Store
        if: ${{ inputs.submit_for_review == 'true' }}
        run: bundle exec fastlane deliver --submit_for_review
```

## Gotchas

- Individual (non-Team) API keys can silently lack permissions for provisioning/cert
  operations — use a Team Key for full CI automation.
- Build processing (App Store Connect virus/malware scan) takes minutes; `pilot`/`deliver` may
  need `--wait_processing_interval` / polling before the build is usable.
- External TestFlight and full App Store submission both hit human review queues — plan the
  pipeline to not block synchronously on approval.
- `match readonly: true` is essential in CI — a writable runner can silently regenerate certs
  and invalidate every other team member's local signing setup.
- Never commit the `.p8` file or the match encryption passphrase.

## Docs

- App Store Connect API: <https://developer.apple.com/documentation/appstoreconnectapi>
- fastlane `pilot`: <https://docs.fastlane.tools/actions/pilot/>
- fastlane `deliver`: <https://docs.fastlane.tools/actions/deliver/>
- fastlane `match`: <https://docs.fastlane.tools/actions/match/>
