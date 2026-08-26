# Agent-Controlled VS Code Data Collection

How to collect VS Code extension runtime evidence programmatically (without relying on manual UI clicks).

## Why
Manual clicking is useful for UX confirmation, but weak for deterministic debugging.
Agent-controlled runs provide repeatable, scriptable evidence.

## Control Modes

## 1) Extension-host integration mode (recommended)
Use a test harness (commonly `@vscode/test-electron`) to launch VS Code and run commands.

Typical flow:
1. open fixture document
2. invoke VS Code commands (`executeDocumentSymbolProvider`, hover, diagnostics)
3. assert outputs
4. emit machine-readable failures

Best for:
- provider behavior validation
- regression tests
- CI reproducibility

## 2) Build/package inspection mode
Programmatically verify runtime artifacts and packaging outputs:
- staged media/runtime files exist and are fresh
- VSIX contains required runtime files
- generated module API shape matches caller expectations

Best for:
- stale artifact detection
- release pipeline confidence

## 3) Runtime introspection mode
Add temporary instrumentation to log:
- resolved runtime file paths
- module init success/failure
- method surface of loaded runtime object
- async handler failures otherwise swallowed

Best for:
- narrowing root-cause layer quickly

## Data to Collect per Run
- command executed
- runtime used (VS Code executable/version if pinned)
- key error signature line(s)
- pass/fail assertion summary
- artifact identity clues (size/hash/timestamp as needed)

## Suggested Probe Set
1. Symbol probe
- command: document symbol provider
- output: symbol count and key names

2. Diagnostics probe
- command: diagnostics fetch
- output: count + representative messages

3. Hover probe
- command: hover provider at selected positions
- output: hover text fragments

4. Runtime API probe
- command: inspect loaded module/session methods
- output: available method names

## Failure-Mode Mapping
- `unknown variant ...` -> version/artifact mismatch
- `... is not a function` -> runtime API surface mismatch
- `instantiate ... requires a callable` -> module boundary mismatch
- "works in custom editor only" -> split pipeline issue (webview vs extension host)

## Guardrails
- Do not conclude from UI only; always include command-level evidence.
- Do not patch multiple boundaries at once unless blocked.
- Re-run full probe set after each fix.

## Example Evidence Block
Use this structure in reports:

```text
[probe] symbols
command: executeDocumentSymbolProvider
result: FAIL
error: TypeError: session.outline is not a function

[probe] runtime-api
result: PASS
methods: dispatch,snapshot,visible_rows
missing: outline,schema_violations
```

## Outcome Standard
A debug cycle is complete when:
- pre-fix failure is captured by probe(s)
- post-fix probe(s) pass
- regression guard (integration test or equivalent) is committed
