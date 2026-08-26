---
name: vscode-dev-experience-pack
description: Use when doing VS Code extension development tasks, especially debugging runtime issues, setting up reproducible extension-host tests, collecting evidence programmatically, or preparing VSIX validation workflows. Triggers on requests like "VS Code extension debug", "symbols/hover/diagnostics failed", "automate VS Code data collection", or "stabilize VSIX build/test flow".
allowed-tools: Bash, Read, Write
---

# vscode-dev-experience-pack

Concise entrypoint for VS Code extension development and debugging.
Use this file to route the task to the right reference doc.

## When to Use
- Extension runtime bugs in VS Code (native providers, webview bridge, wasm/module loading).
- Need reproducible extension-host validation (integration tests, artifact chain, VSIX checks).
- Need structured incident writeups with evidence.

## Dispatch Rules
1. Start with reproducibility and evidence, not assumptions.
2. Prefer API-level checks over manual UI clicking.
3. Keep build -> stage -> package chain explicit.
4. Do not claim success without fresh verification output.

## Reference Map

1. `references/generic-vscode-extension-debug-commands.md`
- Universal command order for check/build/test/package/log capture.
- Use this first to bootstrap or normalize local/CI debug runs.

2. `references/debug-playbook.md`
- Step-by-step debug flow (surface definition, evidence collection, boundary isolation, verification checklist).
- Use when you need to execute a full investigation.

3. `references/agent-controlled-vscode-data-collection.md`
- How an agent can programmatically control VS Code runtime for data collection.
- Focus: extension-host tests (`@vscode/test-electron`), command-driven probes, deterministic evidence capture.

4. `references/vscode-extension-error-examples.md`
- Generalized failure signatures and fix patterns (artifact mismatch, CJS/ESM boundaries, swallowed async errors, VSIX-only failures).
- Use for troubleshooting and postmortem documentation.

## Output Contract
For any debug report generated under this pack:
1. Symptom
2. Reproduction command
3. Error signature
4. Root-cause layer
5. Fix applied
6. Verification evidence
7. Guard added (test/check/script)
