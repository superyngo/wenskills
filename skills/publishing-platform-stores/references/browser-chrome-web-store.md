# Chrome Web Store

**Unverified in production** — general/official guidance, not battle-tested by the authoring
project.

## Mechanism

Chrome Web Store API. Google's official docs (as of mid-2026) document **v2**
(`/v2/publishers/{publisherId}/items/{itemId}:upload|publish`) as current; the legacy v1.1
REST surface is deprecated, end-of-support Oct 15, 2026 — write new integrations against v2.

## GitHub Action

`mnao305/chrome-extension-upload` (actively maintained, wraps `fregante/chrome-webstore-upload`).
Inputs: `file-path`, `extension-id`, `client-id`, `client-secret`, `refresh-token`, optional
`glob`, `publish` (bool, default true), `publish-target`.

## One-time setup

1. Google Cloud project with the Chrome Web Store API enabled.
2. OAuth client (Web application type), redirect URI
   `https://developers.google.com/oauthplayground` — yields client_id + client_secret.
3. Obtain a refresh_token once via OAuth 2.0 Playground, scope
   `https://www.googleapis.com/auth/chromewebstore`.
4. **2-Step Verification is mandatory** on the publishing Google account (explicit official
   prerequisite).
5. **First publish must be done manually** in the Developer Dashboard — the API only
   updates/publishes an *existing* item.
6. Note the Publisher ID (Developer Dashboard → Publisher → Settings) for v2 endpoints.

A newer **service account** auth path also exists as an alternative to refresh tokens
(CI-friendlier — doesn't expire the same way); check
`developer.chrome.com/docs/webstore/service-accounts` before defaulting to OAuth refresh
tokens on a new integration.

## Required secrets

| Secret | Source |
|---|---|
| `CHROME_EXTENSION_ID` | Developer Dashboard, item URL |
| `CHROME_CLIENT_ID` | GCP OAuth client |
| `CHROME_CLIENT_SECRET` | GCP OAuth client |
| `CHROME_REFRESH_TOKEN` | OAuth Playground, `chromewebstore` scope |

## Workflow

```yaml
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v5
        with: { name: <EXTENSION_ZIP>, path: build, run-id: ${{ inputs.run_id }} }

      - uses: mnao305/chrome-extension-upload@v6.0.0
        with:
          file-path: build/extension.zip
          extension-id: ${{ secrets.CHROME_EXTENSION_ID }}
          client-id: ${{ secrets.CHROME_CLIENT_ID }}
          client-secret: ${{ secrets.CHROME_CLIENT_SECRET }}
          refresh-token: ${{ secrets.CHROME_REFRESH_TOKEN }}
          publish: true
```

## Gotchas

- If the OAuth consent screen is stuck in "Testing" mode, refresh tokens expire every 7 days —
  set it to "In Production" for durable CI tokens.
- `manifest.json`'s `version` must be incremented every upload or it fails outright.
- Review delay is not fixed — minutes to several days, worse for extensions requesting
  sensitive permissions.
- If visibility was changed manually in the dashboard, the first publish after that change
  must also be done manually once.

## Docs

- Chrome Web Store API: <https://developer.chrome.com/docs/webstore/using-api>
- Service accounts: <https://developer.chrome.com/docs/webstore/service-accounts>
- `mnao305/chrome-extension-upload`: <https://github.com/mnao305/chrome-extension-upload>
