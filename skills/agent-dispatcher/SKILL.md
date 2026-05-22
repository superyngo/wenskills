---
name: agent-dispatcher
description: Dispatch tasks to other agent CLIs with tier-based fallback
argument-hint: "[init | detect | config <show|list|path|edit> | -p <prompt> | -f <file>] [--timeout N] [--tier ID] [--agent ID] [--config PATH] [--dry-run] [--verbose]"
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# agent-dispatcher

Thin shell over the `agd` CLI (https://github.com/superyngo/agd).

**Default path:** assume `agd` is installed and configured. Forward argv verbatim:

```bash
agd <argv>
```

This is the right behavior for the common cases — `dispatch -p`, `dispatch -f`, `detect`, `config show|list|path`, `--help`, `--version`, any flag-only invocation with `--dry-run`. Only fall back to a reference file when one of the situations below applies.

## When to load a reference

| Situation | Reference |
|---|---|
| `command -v agd` returns non-zero (binary missing) | `references/install-guide.md` |
| First argv token is `init` | `references/init-guide.md` (assembles stdin JSON; has overwrite guard) |
| First argv token is `config edit`, or bare `config` with no sub | `references/config-guide.md` (TTY required — intercept, do not forward) |
| First argv token is `dispatch` with no `-p`, `-f`, or `--dry-run` | `references/dispatch-guide.md` (collect prompt via AskUserQuestion; would otherwise hang) |
| `detect` route, or you need to interpret detect JSON | `references/detect-guide.md` |
| CLI exits non-zero | Load the reference matching the route; surface stderr unchanged |

Each reference contains the full workflow for its route — load it in full when triggered, then follow it.

## `--config PATH`

Forwarded verbatim on every route **except** `agd init`, where it is stripped (with a one-time warning) — init's output location is controlled only by the JSON `save_location` field.
