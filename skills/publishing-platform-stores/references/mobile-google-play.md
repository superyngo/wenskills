# Google Play

**Unverified in production** — general/official guidance, not battle-tested by the authoring
project.

## Mechanism

Google Play Developer API (`edits.*` endpoints). CI wrapper: the GitHub Action
`r0adkll/upload-google-play@v1` (purpose-built, no fastlane needed) or fastlane `supply`.

## One-time setup

1. Create a GCP service account, enable "Google Play Android Developer API" on its project,
   download the JSON key.
2. Play Console → *Users and permissions* → invite the service-account email, grant at least
   **Release manager** app-level permission.
3. The **very first** APK/AAB for a brand-new package name must be uploaded manually through
   the Play Console UI — the Developer API cannot create a new app listing.
4. Since Aug 2021, new apps must submit `.aab` and auto-enroll in **Play App Signing**: an
   upload key (developer-held, signs the AAB before upload) and an app signing key
   (Google-held, re-signs for delivery, no developer access, cannot be reset). CI only needs
   the upload keystore to produce the signed AAB before the API upload — the API step itself
   does no additional signing.

## Required secrets

| Secret | Source |
|---|---|
| `PLAY_SERVICE_ACCOUNT_JSON` | GCP service account key (raw JSON, never commit) |
| upload keystore secrets (`storePassword`, `keyPassword`, `keyAlias`, base64 keystore) | app's own signing config, used in the build step before this workflow |

## Workflow

```yaml
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v5
        with: { name: <AAB_ARTIFACT>, path: build, run-id: ${{ inputs.run_id }} }

      - uses: r0adkll/upload-google-play@v1
        with:
          serviceAccountJsonPlainText: ${{ secrets.PLAY_SERVICE_ACCOUNT_JSON }}
          packageName: <APP_PACKAGE_NAME>
          releaseFiles: build/*.aab
          track: internal          # be explicit: internal|alpha|beta|production
          status: completed        # or inProgress/halted/draft
          userFraction: 0.1        # optional staged rollout, production track only
```

## Gotchas

- `track` has no safe default — omitting it risks defaulting to `production`; always set it
  explicitly, and start new pipelines on `internal` (no review, ≤100 testers) before promoting.
- Apps using Firebase/Google Sign-In must register the **App Signing Certificate** fingerprint
  (Google-held key), not the developer's upload-key fingerprint — wrong fingerprint breaks
  OAuth for real Play-Store installs even though local/sideload builds work.
- First APK/AAB for a new package name cannot go through the API — manual upload required once.
- Promotion between tracks (e.g. internal → production) is a separate API call
  (`track_promote_to` in fastlane `supply`), not implied by re-running the upload.

## Docs

- Play Developer API: <https://developers.google.com/android-publisher>
- Play App Signing: <https://support.google.com/googleplay/android-developer/answer/9842756>
- `r0adkll/upload-google-play`: <https://github.com/r0adkll/upload-google-play>
