---
name: wens-dev-principles
description: Use when designing, building, or reviewing any user-facing UI — TUI, web, touch, or app shell — covering keyboard navigation, scrollable lists, text input, focus/selection visuals, popups and menus, reorderable lists, cross-platform/RWD component sharing, single-source-of-truth architecture, native-surface preference, layout/resize, logging, i18n, and PWA/installability/offline-first baseline. Also covers repository documentation layout — root CONTEXT.md index, docs/ folder set (reference, adr, spec, plan, debug, audit, tmp), glossary as first single-source-of-truth document, and freeze-on-landing lifecycle for specs/plans/ADRs. Also the router for Wen's other cross-project engineering-principle domains as they are added. Apply whenever the user works on UI components, navigation, scrolling, input fields, list selection, popups, or asks how a UI element should look or behave, or sets up docs/, a glossary, CONTEXT.md, an ADR, or a spec/plan folder, even if they don't explicitly say "design principles" or "conventions".
---

# Wen's Development Principles

## Overview

Cross-project engineering conventions — high-level and implementation-agnostic. These are
*principles*, not code: apply the spirit, pick the implementation that fits the stack.

This file is a **router only**. Every principle lives under `references/`, grouped by domain.
Universal coding conduct (minimal changes, bug-fix protocol, commit/tooling rules) is *not*
here — that is `CLAUDE.md`'s job. This skill holds the domain conventions too detailed for it.

## How to Use

1. Open the domain's principle list below and match the surface you are building to a
   principle — default to it rather than inventing behaviour.
2. Follow that principle's link into a deep reference only when implementing its contract.

## Importance Grades

Every principle in every domain reference is tagged with one of three grades, prefixed inline
as `**[MUST]**` / `**[SHOULD]**` / `**[CONSIDER]**` immediately after its number:

| Grade | Meaning | Deviating |
|---|---|---|
| `MUST` | Violating it is a bug — the user directly experiences breakage or lost work/state. | Record an ADR. |
| `SHOULD` | Default behavior. Deviation is not automatically wrong but needs a stated reason. | One-line reason in the commit body. |
| `CONSIDER` | A recommendation to adopt where it fits; not a default. | No justification needed. |

## Domains

| Domain | Principle list | Scope |
|---|---|---|
| UI (all surfaces) | [references/ui/principles.md](references/ui/principles.md) | 23 principles (9 MUST / 13 SHOULD / 1 SHOULD-with-inline-CONSIDER) + Common Mistakes: architecture, focus/selection, keyboard & input, popups, reorderable lists, chrome/layout, web PWA |
| Docs (repository documentation) | [references/docs/principles.md](references/docs/principles.md) | 15 principles (10 MUST / 4 SHOULD / 1 CONSIDER) + Common Mistakes: entry point, reference SSOT, working-record lifecycle, ADRs |

## UI Deep References

| Topic | Reference | Principles |
|---|---|---|
| Single source of truth; cross-platform adaptation order; native surfaces; About/Help panel | [references/ui/single-source-and-cross-platform.md](references/ui/single-source-and-cross-platform.md) | 1, 2, 3, 18 |
| Selection state model (committed + preview two-set) | [references/ui/list-selection-model.md](references/ui/list-selection-model.md) | 6 |
| Sticky-cursor viewport scrolling | [references/ui/scrollable-list-viewport.md](references/ui/scrollable-list-viewport.md) | 7 |
| Text field contract: move + select + edit + clipboard | [references/ui/text-editing-contract.md](references/ui/text-editing-contract.md) | 10 |
| Popup / re-render / event contract for pointer UIs | [references/ui/pointer-ui-gotchas.md](references/ui/pointer-ui-gotchas.md) | 15, 19 |
| Downward-move index correction | [references/ui/reorder-index-offsets.md](references/ui/reorder-index-offsets.md) | 17 |

## Docs Deep References

| Topic | Reference | Principles |
|---|---|---|
| Directory tree, CONTEXT.md and README.md templates, Status line values, glossary entry format, script directories, tmp archiving | [references/docs/layout-and-lifecycle.md](references/docs/layout-and-lifecycle.md) | 1, 2, 5, 8, 10, 12, 14 |

## Citation Contract

Principles are cited **by domain and number** across this repo — ADRs, specs, and code comments
carry `wens-dev-principles <domain> <n>` (e.g. `wens-dev-principles ui 7`,
`wens-dev-principles docs 5`). A citation with no domain — `wens-dev-principles <n>` or the
historical `ui-design-principles <n>`, the former skill name — means the `ui` domain. Numbers
are frozen per domain: **append new principles, never renumber or reuse a number.**

## Adding a Domain

Add `references/<domain>/principles.md`, number its principles in that file's own namespace, and
add one row to Domains. Deep material goes in sibling files under the same folder; each domain
also gets a `## <Domain> Deep References` table if it has sibling files. Keep this file a
router — no principle text inline.
