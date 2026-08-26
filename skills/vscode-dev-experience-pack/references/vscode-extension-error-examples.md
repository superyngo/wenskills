# VS Code Extension Error Examples (Generalized from Real Incidents)

These examples are generalized from real failures and rewritten as reusable
extension debugging patterns.

## Example 1: "No symbols found" but feature is registered

### Symptom
- Outline / symbol UI is empty.
- No obvious crash in editor UI.

### Hidden Cause Pattern
- Provider catches runtime exceptions and returns fallback (`[]`), masking root cause.

### Evidence to Collect
- Extension Host log (`Log (Extension Host)`).
- Provider catch-path logs with stack traces.

### Fix Pattern
- Add explicit error logging before fallback return.
- Verify runtime dependencies initialize successfully before provider call.

---

## Example 2: `unknown variant <IntentName>`

### Symptom
- Runtime serde/JSON decode error for enum variant or command name.

### Hidden Cause Pattern
- Caller and runtime module are built from mismatched versions.
- Staged artifact is stale while source code is new.

### Evidence to Collect
- Built artifact timestamps/sizes.
- Runtime module export surface.
- Build chain order and outputs.

### Fix Pattern
- Rebuild full chain in strict order.
- Ensure packaging/staging copies the latest generated artifacts.
- Add CI/integration test that exercises the failing command path.

---

## Example 3: `<method> is not a function`

### Symptom
- Runtime object exists, but expected API method is missing.

### Hidden Cause Pattern
- Loaded module API differs from caller's expected interface.
- Wrong artifact version or wrong module instance loaded.

### Evidence to Collect
- Runtime `Object.getOwnPropertyNames(Object.getPrototypeOf(instance))`.
- Compare expected vs actual method list.

### Fix Pattern
- Verify import target path resolves to correct staged file.
- Enforce artifact freshness before extension build/package.

---

## Example 4: `WebAssembly.instantiate ... requires a callable`

### Symptom
- wasm init fails with import-function callable errors.

### Hidden Cause Pattern
- CJS/ESM boundary mismatch breaks generated wasm glue imports.
- Static bundling of ESM glue into incompatible host context.

### Evidence to Collect
- Stack trace around instantiate/init.
- How module is imported (static vs dynamic, path type).

### Fix Pattern
- Load runtime module dynamically via absolute file URL when needed.
- Initialize wasm with explicit bytes/object form expected by generated glue.

---

## Example 5: Works in custom editor, fails in native text editor

### Symptom
- Webview-based features work.
- Native editor providers (symbols/hover/diagnostics) fail.

### Hidden Cause Pattern
- Two different runtime pipelines:
  - webview pipeline is healthy
  - extension-host pipeline is broken

### Evidence to Collect
- Separate logs per pipeline.
- Provider registration + invocation path in extension host.

### Fix Pattern
- Debug native providers independently.
- Do not infer native-provider health from webview success.

---

## Example 6: Build passes, packaged VSIX still fails

### Symptom
- Local dev run seems fine.
- Installed VSIX reproduces failure.

### Hidden Cause Pattern
- Packaging included stale assets or omitted generated files.

### Evidence to Collect
- VSIX file tree (`vsce ls --tree` or unzip listing).
- Compare packaged staged files with local build outputs.

### Fix Pattern
- Add packaging validation step to CI.
- Ensure build script regenerates and stages runtime artifacts before packaging.

---

## Example 7: Diagnostics missing with no visible errors

### Symptom
- Expected diagnostics never appear.
- No user-facing error message.

### Hidden Cause Pattern
- Async document-open/reparse failure swallowed in event handlers.

### Evidence to Collect
- Wrap async event callbacks with `.catch(...)` logging.
- Add logs around document lifecycle events (`open`, `change`, `close`).

### Fix Pattern
- Never fire-and-forget async handlers without error reporting.
- Preserve graceful UX while making failures observable in logs.

---

## Example 8: Debug result is non-reproducible across machines

### Symptom
- One machine passes, another fails with same source commit.

### Hidden Cause Pattern
- Hidden environment dependency (VS Code executable path, cached test host, extension cache).

### Evidence to Collect
- Exact VS Code runtime used for integration tests.
- Clean/isolated test user-data directory behavior.

### Fix Pattern
- Pin or explicitly select test runtime executable.
- Use deterministic integration-test harness settings.

---

## Reusable Troubleshooting Matrix

| Signal | Most likely layer | First action |
|---|---|---|
| `unknown variant ...` | Artifact/version mismatch | Rebuild full chain and verify staged outputs |
| `... is not a function` | API surface mismatch | Print runtime method list and compare |
| `instantiate ... callable` | Module boundary (CJS/ESM/wasm glue) | Change module loading strategy |
| Symbols/hover empty silently | Provider catch swallowing errors | Add logging before fallback return |
| VSIX only fails | Packaging/staging | Inspect VSIX contents vs local outputs |

## Suggested Report Format per Incident

1. Symptom
2. Reproduction command
3. Error signature (exact key line)
4. Root-cause layer
5. Fix applied
6. Verification command + key success line
7. Guard added (test/check/script)
