# VS Code Extension Debug Playbook

This playbook is implementation-agnostic and can be reused across extension projects.

## Goal
Convert ambiguous VS Code extension failures into reproducible, evidence-backed fixes.

## Step 1: Define the Failing Surface
Classify the issue before touching code:
- Native editor provider path: DocumentSymbolProvider / HoverProvider / Diagnostics.
- Custom editor/webview path: message bridge, state sync, CSP/network constraints.
- Build/package path: staged assets, generated artifacts, VSIX contents.

Write one explicit expected behavior statement.

## Step 2: Capture Evidence from Correct Log Surfaces
Use both when relevant:
- Output -> `Log (Extension Host)`
- Developer Tools console

If code currently swallows errors (fallback returns), add temporary logs before fallback.
Capture exact key error lines, not paraphrases.

## Step 3: Verify Artifact Freshness
Validate the chain in order:
1. dependency/build artifacts generated
2. extension bundle rebuilt
3. staged runtime assets refreshed
4. packaged artifact includes expected files

Most recurring regressions are stale-artifact regressions.

## Step 4: Reproduce via API-Level Integration Tests
Use extension-host tests (for example, `@vscode/test-electron`) to avoid manual-only verification.
Recommended checks:
- `executeDocumentSymbolProvider`
- diagnostics collection
- hover provider responses

Use polling/wait helper for async provider updates.

## Step 5: Isolate One Boundary at a Time
Typical boundary buckets:
- module system boundary (CJS vs ESM)
- wasm/glue initialization boundary
- host <-> webview protocol boundary
- local/remote schema/resource fetch boundary

Apply one fix per boundary and rerun verification immediately.

## Step 6: Verify and Record
A fix is only complete when all are true:
- failing case reproduced before fix
- failing case passes after fix
- no regressions in adjacent checks
- verification output lines captured

## Minimal Verification Checklist
- [ ] type check
- [ ] build
- [ ] integration test
- [ ] package check (when release path is affected)
- [ ] incident note updated

## Report Template
1. Symptom
2. Reproduction
3. Error signature
4. Root-cause layer
5. Fix
6. Verification evidence
7. Follow-up guard
