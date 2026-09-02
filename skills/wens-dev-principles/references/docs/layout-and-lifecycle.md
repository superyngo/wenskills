# Documentation — Layout, Templates, and Lifecycle

The recurring failure in long-lived repos is not missing documentation but *ambiguous*
documentation: a plan that half-describes the shipped code, a "context" file that is both
glossary and changelog, an ADR quietly edited to match a later decision. Nobody can tell which
file to trust. The fix is structural — a fixed folder set, one canonical folder, a status line on
every historical document, and an index at every level — so trust is decided by *where* a file
sits, not by reading it. Everything below is the concrete form of
[principles.md](principles.md); copy the templates verbatim and fill in the blanks.

## Directory tree

```
README.md
CHANGELOG.md
CONTEXT.md                          # entry index (principle 1)
LICENSE
docs/
  reference/                        # current behavior only — the source of truth
    README.md
    glossary.md                     # first file created (principle 5)
    KEYMAP.md
  adr/
    README.md
    0001-jsonschema-crate-for-validation.md
  spec/
    README.md
    2026-09-02-action-menu.md
  plan/
    README.md
    2026-09-02-action-menu.md       # pairs with the spec by kebab title
  debug/
    README.md
    2026-08-29-drop-index-off-by-one.md
    2026-08-29-drop-index-off-by-one/   # same-basename script directory (principle 10)
      repro.py
      capture.log
  audit/
    README.md
    2026-08-29-dead-code-sweep.md
  tmp/                              # scratch, no rules
    archive/
      2026-05.tar.gz
```

## Root CONTEXT.md template

```markdown
# CONTEXT

Entry point for all documentation. Root-level files (`README.md`, `CHANGELOG.md`, `LICENSE`)
stay here; everything else lives under `docs/`.

| Folder | Holds | Canonical? | Lifecycle |
|---|---|---|---|
| [`docs/reference/`](docs/reference/README.md) | Current behavior: glossary, per-subsystem contracts | Yes — the only source of truth | Kept in sync with the code |
| [`docs/adr/`](docs/adr/README.md) | Decisions that were expensive to reach and would be expensive to reverse | No — historical | Never edited; superseded by a new ADR |
| [`docs/spec/`](docs/spec/README.md) | Design records written before implementation | No — historical | Frozen once approved; only `Status:` changes |
| [`docs/plan/`](docs/plan/README.md) | Task-by-task implementation plans derived from a spec | No — historical | Frozen once shipped; only `Status:` changes |
| [`docs/debug/`](docs/debug/README.md) | Handoff notes from investigations, with repro scripts | No — historical | Frozen once resolved; only `Status:` changes |
| [`docs/audit/`](docs/audit/README.md) | Point-in-time sweeps for bugs, dead code, inconsistency | No — historical | Frozen once findings are addressed; only `Status:` changes |
| `docs/tmp/` | Scratch | No | Archived to `tmp/archive/YYYY-MM.tar.gz` when stale |

## Reading order

1. [`docs/reference/glossary.md`](docs/reference/glossary.md) — the vocabulary every other file uses.
2. [`docs/reference/README.md`](docs/reference/README.md) — the subsystem map.
3. [`docs/adr/README.md`](docs/adr/README.md) — why the shape is what it is.
4. `CHANGELOG.md` — what changed recently.
```

## Folder README.md templates

### `docs/reference/README.md`

```markdown
# Reference

Current behavior only. Anything historical — a superseded design, a shipped plan, a resolved
investigation — lives in `../spec/`, `../plan/`, `../debug/`, or `../audit/`, not here.

- **[glossary.md](glossary.md)** — canonical vocabulary; read first.
- **[KEYMAP.md](KEYMAP.md)** — keyboard-binding table across surfaces.

Machine-checked: `KEYMAP.md` by `web/keymap-parity.spec.mjs`.

See also [`../adr/`](../adr/README.md) for decision records.
```

### `docs/adr/README.md`

```markdown
# Architecture Decision Records

One file per decision that was expensive to reach and would be expensive to reverse. An ADR
records *why* and which alternatives were rejected; it is a historical record, never edited.
Current behavior lives in [`../reference/`](../reference/README.md).

| # | Decision | Status |
|---|---|---|
| [0001](0001-jsonschema-crate-for-validation.md) | Validation uses the `jsonschema` crate, not a hand-rolled validator | Implemented (2026-08-06) |
| [0002](0002-unified-move-targeting.md) | One move-targeting rule across keyboard, pointer, and touch | Implemented (2026-08-19); §1 superseded by 0003 |
| [0003](0003-drops-resolve-through-slot.md) | Pointer drops resolve through the same slot rule as keyboard paste | Proposed |

Partial supersessions: 0002 §1 superseded by 0003.
```

### `docs/spec/README.md`, `docs/plan/README.md`, `docs/debug/README.md`, `docs/audit/README.md`

One template for all four; replace the H1 and the one-line description.

```markdown
# Specs

Design records written before implementation. Every file here is a historical record: frozen
once approved, dated by when it was written, never rewritten. Current behavior lives in
[`../reference/`](../reference/README.md).

## In progress

- [2026-09-02-action-menu.md](2026-09-02-action-menu.md) — `Draft`

## Landed

| Date | Document | Status |
|---|---|---|
| 2026-08-18 | [2026-08-18-row-state-model.md](2026-08-18-row-state-model.md) | Shipped (2026-08-20) |
| 2026-08-10 | [2026-08-10-inline-menu.md](2026-08-10-inline-menu.md) | Superseded by 2026-09-02-action-menu.md |
```

H1 / description per folder:

| Folder | H1 | Description |
|---|---|---|
| `spec/` | `# Specs` | Design records written before implementation. |
| `plan/` | `# Plans` | Task-by-task implementation plans derived from a spec. |
| `debug/` | `# Debug notes` | Handoff notes from investigations, with repro material. |
| `audit/` | `# Audits` | Point-in-time sweeps for bugs, dead code, and inconsistency. |

## Status line

The second line of every file in `spec/`, `plan/`, `debug/`, `audit/`, immediately after the
H1, is `Status: <value>`. Values are exact strings so they can be grepped:

| Value | Used by | Meaning |
|---|---|---|
| `Draft` | all four | Being written; not yet agreed. |
| `Approved` | spec, plan | Agreed; implementation not started. |
| `In progress` | all four | Work under way. Also the implied status of a file with no `Status:` line. |
| `Shipped (YYYY-MM-DD)` | spec, plan | Landed on the given date. Frozen. |
| `Resolved (YYYY-MM-DD)` | debug, audit | Bug fixed / findings addressed on the given date. Frozen. |
| `Superseded by <relative path>` | all four | Replaced; the path names the replacement. Frozen. |
| `Abandoned` | all four | Dropped without replacement. Frozen. |

Example file head:

```markdown
# Centralized action menu
Status: Shipped (2026-08-30)
```

Audit for files missing a status line (each is by definition in progress):

```sh
rg -L '^Status: ' docs/{spec,plan,debug,audit}/*.md
```

List everything frozen:

```sh
rg -n '^Status: (Shipped|Resolved|Superseded|Abandoned)' docs/{spec,plan,debug,audit}/*.md
```

## Glossary entry

Every entry in `docs/reference/glossary.md` uses this shape — bold term with a trailing colon on
its own line, the definition as the next paragraph, and an `_Avoid_:` line. `_Avoid_` is
mandatory even when empty (`_Avoid_: —`) so a reader never wonders whether synonyms were
considered.

```markdown
**Node**:
Any single element in the config tree. The umbrella term for everything the user navigates and
operates on.
_Avoid_: Entry, item.

**Root**:
The single top-of-tree **Node** whose key is the filename. Exactly one Root per open file.
_Avoid_: File header, top node.

**Mutation**:
Any operation that changes the document and is recorded in undo history.
_Avoid_: —
```

Other glossary terms referenced inside a definition are bolded (`**Node**`) so the vocabulary
graph is visible at a glance.

## Script directories

A working-record document may own a directory with the same basename for non-Markdown material:

```
docs/debug/2026-09-02-foo.md
docs/debug/2026-09-02-foo/
  repro.py
  input.toml
  capture.log
```

Checklist:

- [ ] The directory exists only because `2026-09-02-foo.md` exists; no orphan directories.
- [ ] The `.md` links to every file in the directory and says what each is for.
- [ ] Scripts run standalone: standard library only, no repo build step, no import from the
      codebase under test (it will move on; the script must not).
- [ ] The directory freezes when the `.md` does — same `Status:` rule, no later edits.
- [ ] `docs/debug/README.md` lists the `.md` only, never the directory contents.

## Archiving tmp/

`docs/tmp/` is committed and unindexed. When it is stale, archive in one commit:

```sh
mkdir -p docs/tmp/archive
tar -czf docs/tmp/archive/$(date +%Y-%m).tar.gz -C docs/tmp <files and dirs to archive>
git rm -r docs/tmp/<those same files and dirs>
git add docs/tmp/archive
git commit -m "docs: archive tmp/ scratch to tmp/archive/$(date +%Y-%m).tar.gz"
```

Never archive `archive/` itself; never archive files that are still referenced from a
non-frozen document.
