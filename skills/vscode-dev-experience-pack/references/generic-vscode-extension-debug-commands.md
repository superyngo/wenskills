# Generic VS Code Extension Debug Commands

This page keeps only reusable commands for extension debugging workflows.
No repo-specific paths, filenames, or product-specific assumptions.

## 1) Basic Environment Check

```bash
# Node / npm versions
node -v
npm -v

# TypeScript availability in project
npx tsc -v
```

Use this first when CI/local mismatch is suspected.

## 2) Install and Static Check

```bash
# install deps from lockfile
npm ci

# type check only
npm run check
# or
npx tsc --noEmit
```

Goal:
- detect compile/type breakages before runtime debugging.

## 3) Build Extension Bundle

```bash
npm run build
```

Goal:
- ensure extension entry and staged assets are updated before tests.

## 4) Package VSIX for Real-World Validation

```bash
npx @vscode/vsce package --allow-missing-repository
```

Goal:
- verify packaged artifact behavior, not only dev-host behavior.

## 5) Run Extension-Host Integration Tests

```bash
npm run integration-test
```

Typical assertions to include in integration tests:
- `vscode.executeDocumentSymbolProvider` returns expected symbols.
- `vscode.languages.getDiagnostics(uri)` contains expected diagnostics.
- `vscode.executeHoverProvider` returns expected hover text.

## 6) Manual Extension-Host Launch (No UI Clicking Required)

```bash
# Example pattern (project-specific script may differ)
node ./test-integration/runTest.mjs
```

Goal:
- deterministic API-level checks instead of manual view interactions.

## 7) Git Safety for Debug Sessions

```bash
# inspect local changes before and after debugging
git status --short

# show current branch and remote tracking state
git status -sb

# refresh remote refs
git fetch --all --prune
```

Goal:
- avoid accidental commits of temp logs/cache files.

## 8) Optional: Capture Build/Test Output for Sharing

PowerShell pattern:

```powershell
npm run build 2>&1 | Tee-Object build.log
npm run integration-test 2>&1 | Tee-Object integration-test.log
```

Goal:
- preserve evidence for issue reports and team handoff.

## 9) Recommended Debug Order

1. `npm ci`
2. `npm run check`
3. `npm run build`
4. `npm run integration-test`
5. `vsce package` (only after tests pass)

This order prevents debugging stale artifacts.
