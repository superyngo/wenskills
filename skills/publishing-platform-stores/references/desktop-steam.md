# Steam

**Unverified in production** — general/official guidance, not battle-tested by the authoring
project.

## Mechanism

`steamcmd` (Valve's official CLI) driving the Steamworks SDK **ContentBuilder**
(`+login` / `+run_app_build <app_build.vdf>`). No REST API for uploads — steamcmd is the only
supported path. No app-review gate for updates to an existing app: pushing to a branch goes
live per Steamworks branch config immediately (unlike Apple/Google review queues).

## GitHub Action

`game-ci/steam-deploy@v3` — wraps steamcmd, handles depot definitions inline (no hand-written
`app_build.vdf` needed, though still possible).

## One-time setup

1. Create a dedicated **Steam Build Account** (Steamworks partner sub-account) scoped to only
   *Edit App Metadata* + *Publish App Changes to Steam* — not the main partner account.
2. Choose one auth method:
   - **`config.vdf` (Steam Guard MFA)**: run `steamcmd +login <user> <pass> +quit` locally
     once, resolve the Steam Guard code, base64-encode the resulting `config/config.vdf`.
   - **TOTP**: extract the shared secret from the Steam Mobile Authenticator; generate a live
     code per CI run via the companion action `CyberAndrii/steam-totp`. More CI-robust — no
     static session file to expire.

## Required secrets

| Secret | Auth method |
|---|---|
| `STEAM_USERNAME` | both |
| `STEAM_CONFIG_VDF` (base64) | config.vdf method |
| `STEAM_PASSWORD` + `STEAM_SHARED_SECRET` | TOTP method |

## Workflow

```yaml
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v5
        with: { name: <LINUX_BUILD_ARTIFACT>, path: build, run-id: ${{ inputs.run_id }} }

      # TOTP method — skip if using configVdf instead
      - uses: CyberAndrii/steam-totp@v1
        id: steam-totp
        with: { shared_secret: ${{ secrets.STEAM_SHARED_SECRET }} }

      - uses: game-ci/steam-deploy@v3
        with:
          username: ${{ secrets.STEAM_USERNAME }}
          password: ${{ secrets.STEAM_PASSWORD }}
          totp: ${{ steps.steam-totp.outputs.code }}
          appId: <STEAM_APP_ID>
          rootPath: build
          depot1Path: .
          releaseBranch: prerelease   # NOT "default" — documented as broken
          buildDescription: ${{ inputs.tag }}
```

## Gotchas

- `config.vdf` sessions expire and need periodic re-auth + secret rotation; TOTP avoids this.
- Only run one deploy job per Steam account at a time — concurrent logins invalidate sessions
  ("License expired" errors).
- `releaseBranch: default` is documented as broken in `game-ci/steam-deploy`'s issue tracker —
  use a named branch (e.g. `prerelease`) and promote manually, or a different named branch per
  channel.
- Debug artifacts (`*.pdb`, Unity `*_BurstDebugInformation_DoNotShip`) are auto-excluded unless
  `debugBranch: true`.
- No review gate — a bad build on a live branch ships immediately; keep it off `default`/live
  branches until validated.

## Docs

- Steamworks ContentBuilder: <https://partner.steamgames.com/doc/sdk/uploading>
- `game-ci/steam-deploy`: <https://github.com/game-ci/steam-deploy>
