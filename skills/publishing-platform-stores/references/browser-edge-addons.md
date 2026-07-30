# Microsoft Edge Add-ons

**Unverified in production** — general/official guidance, not battle-tested by the authoring
project. Official docs on the v1 legacy-flow sunset date are internally inconsistent — verify
current status before depending on it.

## Mechanism

Edge Add-ons **Update REST API** (`api.addons.microsoftedge.microsoft.com`), enabled per
extension via Partner Center's "Publish API" page. Endpoints: upload package
(`POST /v1/products/{productID}/submissions/draft/package`), check upload status, publish
submission, check publish status. **No endpoint creates a new product or edits listing
metadata** — first publish and metadata edits are Partner Center UI only.

Two auth generations, both currently documented:
- **v1.1 (current, recommended)** — API key: headers `Authorization: ApiKey $ApiKey` +
  `X-ClientID: $ClientID`.
- **v1 (legacy)** — `client_id`/`client_secret` → Azure AD client-credentials token exchange →
  `Authorization: Bearer $TOKEN`. Use v1.1 for anything new.

## GitHub Action

`wdzeng/edge-addon` (community-maintained, no first-party Microsoft action exists). Inputs:
`product-id`, `zip-path`, `api-key`, `client-id`.

## One-time setup

1. Partner Center → *Publish API* page → enable the new experience → create API credentials →
   yields Client ID + API Key (v1.1).
2. Note the product's `productID` (128-bit GUID, shown in Partner Center overview / package
   URL).

## Required secrets

| Secret | Source |
|---|---|
| `EDGE_PRODUCT_ID` | Partner Center, extension overview |
| `EDGE_CLIENT_ID` | Partner Center → Publish API credentials |
| `EDGE_API_KEY` | Partner Center → Publish API credentials |

## Workflow

```yaml
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v5
        with: { name: <EXTENSION_ZIP>, path: build, run-id: ${{ inputs.run_id }} }

      - uses: wdzeng/edge-addon@v2
        with:
          product-id: ${{ secrets.EDGE_PRODUCT_ID }}
          zip-path: build/extension.zip
          api-key: ${{ secrets.EDGE_API_KEY }}
          client-id: ${{ secrets.EDGE_CLIENT_ID }}
```

## Gotchas

- API keys reportedly expire on a rotation window commonly cited as ~72 days — not confirmed
  in the official docs read; verify the current value in Partner Center and plan secret
  rotation regardless.
- Client secret (legacy v1 flow) is shown only once at creation — capture immediately if using
  the legacy path at all.
- No API for editing store listing metadata — description/screenshots stay Partner Center only.
- First publish of a brand-new extension must be done manually; the REST API only updates an
  existing submission.

## Docs

- Update REST API: <https://learn.microsoft.com/microsoft-edge/extensions/update/api/using-addons-api>
- Partner Center: <https://partner.microsoft.com/dashboard/microsoftedge/public/login>
