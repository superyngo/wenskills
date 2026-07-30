# Firefox Add-ons (AMO)

**Unverified in production** — general/official guidance, not battle-tested by the authoring
project.

## Mechanism

`web-ext sign` (Mozilla's official CLI) talks to the AMO **Add-on Submission API**,
authenticated via a JWT built from an API key (issuer) and API secret, generated once at the
AMO Developer Hub.

```
web-ext sign --api-key=<JWT_ISSUER> --api-secret=<JWT_SECRET> --channel=listed|unlisted
```

- `--channel=unlisted` — self-distribution; signed `.xpi` returned for self-hosting, minimal
  automated review.
- `--channel=listed` — published/discoverable on AMO, subject to full human + automated review
  (delay ranges same-day to multi-day, worse for broad host permissions or remote code).

## GitHub Action

No first-party Mozilla action. Community options wrap `web-ext sign` /
`mozilla/sign-addon` (the library `web-ext` itself uses): `browser-actions/release-firefox-addon`,
`wdzeng/firefox-addon`. Verify current maintenance status before adopting either.

## One-time setup

1. AMO Developer Hub → *API key* page → generate JWT issuer (`user:<numericID>:<n>`) + JWT
   secret (long hex string).
2. First add-on still requires a one-time manual submission via the AMO Developer Hub to
   establish the add-on and mint API credentials tied to it.
3. Set `browser_specific_settings.gecko.id` in `manifest.json` — a stable UUID or email-style
   ID identifying the add-on across submissions.
4. If the source is minified/bundled/transpiled, prepare a separate source archive — AMO
   review requires inspectable source, not just the built bundle.

## Required secrets

| Secret | Source |
|---|---|
| `AMO_JWT_ISSUER` | AMO Developer Hub API key page |
| `AMO_JWT_SECRET` | AMO Developer Hub API key page |

## Workflow

```yaml
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v5
        with: { name: <EXTENSION_SOURCE>, path: build, run-id: ${{ inputs.run_id }} }

      - name: Sign and submit to AMO
        run: |
          npx web-ext sign \
            --source-dir build \
            --api-key "${{ secrets.AMO_JWT_ISSUER }}" \
            --api-secret "${{ secrets.AMO_JWT_SECRET }}" \
            --channel listed
```

## Gotchas

- Listed vs unlisted is a hard per-submission choice, not a later toggle — pick the
  distribution channel before signing.
- Minified/bundled source needs a separate source upload for review; skipping it stalls listed
  review.
- No documented secret-expiry gotcha (unlike Chrome's 7-day refresh-token trap or Edge's
  rotating API key) — JWT issuer/secret are long-lived, revocable manually.
- Third-party signing actions here are smaller/less-starred than Chrome's or Edge's — pin a
  specific tag and re-verify maintenance before relying on one long-term.

## Docs

- `web-ext` CLI: <https://github.com/mozilla/web-ext>
- Command reference: <https://extensionworkshop.com/documentation/develop/web-ext-command-reference/#web-ext-sign>
- API key generation: <https://addons.mozilla.org/developers/addon/api/key/>
