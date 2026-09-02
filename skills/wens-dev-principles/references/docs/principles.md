# Documentation Layout Principles

High-level conventions for where a repository's documents live, which of them are the source
of truth, and when a document freezes. Applies to any repo that has more than a README. These
are *principles*, not templates — the templates (directory tree, `CONTEXT.md`, folder
`README.md`s, status line, glossary entry) live in [layout-and-lifecycle.md](layout-and-lifecycle.md).

## Index

| # | Grade | Principle |
|---|---|---|
| 1 | MUST | Root `CONTEXT.md` is the single documentation entry point (an index, not a glossary) |
| 2 | MUST | `docs/` has a fixed folder set, each with an indexing `README.md` |
| 3 | SHOULD | Agent instruction file points at `CONTEXT.md`, never restates reference |
| 4 | MUST | `docs/reference/` describes current behavior only |
| 5 | MUST | `docs/reference/glossary.md` is the first document, in a fixed entry format |
| 6 | SHOULD | Reference is one file per subsystem, cross-linked, machine-checks named |
| 7 | MUST | Working records freeze on landing; only `Status:` changes afterward |
| 8 | MUST | Every working record opens with a `Status:` line from a fixed value set |
| 9 | MUST | Working-record filenames are `YYYY-MM-DD-kebab-title.md`, dated when written |
| 10 | SHOULD | A working record may own a same-basename directory for scripts and fixtures |
| 11 | SHOULD | Folder `README.md` lists in-progress work in a section at the top |
| 12 | CONSIDER | `docs/tmp/` is committed scratch, archived as a tarball when stale |
| 13 | MUST | One ADR per expensive decision; never edited, only superseded |
| 14 | MUST | `adr/README.md` is a status table; filenames are `NNNN-kebab-title.md` |
| 15 | MUST | Deviating from any MUST principle in this skill requires an ADR |

## A. Entry point and indexes

1. **[MUST]** Repo root `CONTEXT.md` is the single documentation entry point. It is an *index*:
   one table of the `docs/` folders (what each holds, whether it is canonical, its lifecycle)
   plus a reading order for a newcomer. It holds no glossary terms itself — it links to
   `docs/reference/glossary.md` as the first thing to read. The repo root keeps only
   `README.md`, `CHANGELOG.md`, `CONTEXT.md`, `LICENSE`, and platform-mandated files; every
   other document lives under `docs/`. **Template:** [layout-and-lifecycle.md](layout-and-lifecycle.md) §Root CONTEXT.md template.

2. **[MUST]** `docs/` contains exactly these folders, singular names: `reference/`, `adr/`,
   `spec/`, `plan/`, `debug/`, `audit/`, `tmp/`. Each except `tmp/` has a `README.md` that lists
   every `.md` file in that folder with a one-line summary and its status. Adding or
   re-statusing a document and updating its folder `README.md` happen in the same commit; a
   document absent from its index is a bug. **Templates:** same reference, §Folder README.md templates.

3. **[SHOULD]** The agent instruction file (`CLAUDE.md`, `AGENTS.md`, or equivalent) points at
   `CONTEXT.md` and states repo-specific *conduct* — tooling, commit rules, review gates. It does
   not restate reference content. If a fact is needed by both, it lives in `docs/reference/` and
   the instruction file links to it.

## B. `reference/` — single source of truth

4. **[MUST]** `docs/reference/` describes current behavior only. A superseded design, a shipped
   plan, or a resolved investigation is moved to its lifecycle folder (`spec/`, `plan/`,
   `debug/`, `audit/`), never left in reference with a "historical" note or a "History" section.

5. **[MUST]** `docs/reference/glossary.md` is the first reference document created in any repo,
   before any other `docs/` file. Entry format is fixed: a `**Term**:` line, a definition
   paragraph, and an `_Avoid_:` line listing rejected synonyms. Code identifiers, UI strings,
   commit messages, and every other document use glossary terms; introducing a new term means
   adding its entry in the same commit. **Format:** same reference, §Glossary entry.

6. **[SHOULD]** Reference is split one file per subsystem or surface (e.g. `KEYMAP.md`, `TUI.md`,
   `MESSAGES.md`), each cross-linking the others. `reference/README.md` flags which files are
   machine-checked by a test and names the test, so a reader knows which claims cannot drift.

## C. Working records — `spec/`, `plan/`, `debug/`, `audit/`

7. **[MUST]** A document in `spec/`, `plan/`, `debug/`, or `audit/` is frozen once it lands —
   spec approved, plan shipped, debug resolved, audit findings addressed. After that the only
   permitted edit is its `Status:` line. Corrections, follow-ups, and changed designs are new
   documents that the old one's `Status:` points to. A false start stays in the record; it often
   explains a later design better than the design document does.

8. **[MUST]** Every working-record document opens with a status line as the second line of the
   file, immediately after the H1: `Status: <value>`. Values are exactly `Draft`, `Approved`,
   `In progress`, `Shipped (YYYY-MM-DD)`, `Resolved (YYYY-MM-DD)`, `Superseded by <relative path>`,
   `Abandoned`. `Shipped` is for spec/plan; `Resolved` is for debug/audit. A document with no
   `Status:` line is treated as `In progress`. **Value table + audit grep:** same reference, §Status line.

9. **[MUST]** Filenames are `YYYY-MM-DD-kebab-title.md`, dated when the document was written,
   not when the work landed. A spec and its plan share the kebab title
   (`spec/2026-09-02-foo.md` ↔ `plan/2026-09-02-foo.md`) so they pair by name.

10. **[SHOULD]** A working-record document may own a sibling directory with the same basename
    (`debug/2026-09-02-foo/`) for scripts, fixtures, captured output, and other non-Markdown
    material. The directory exists only if the `.md` exists; the `.md` links to every file in
    it; the directory freezes with the document; the folder `README.md` indexes the `.md` only.
    Scripts are self-contained (standard library, no repo build step) so they still run after
    the code moves on. **Checklist:** same reference, §Script directories.

11. **[SHOULD]** Each folder `README.md` opens with an `## In progress` section listing every
    document whose status is `Draft`, `Approved`, `In progress`, or missing, so live work is
    visible in one place; landed documents follow in a table.

12. **[CONSIDER]** `docs/tmp/` is a committed scratch area with no naming or index rules;
    subdirectories per topic are allowed. When it grows stale, tar the loose files into
    `docs/tmp/archive/YYYY-MM.tar.gz` and remove them in the same commit. **Commands:** same
    reference, §Archiving tmp/.

## D. `adr/`

13. **[MUST]** One ADR per decision that was expensive to reach and would be expensive to
    reverse. It records why, the alternatives rejected, and the date; it is a historical record,
    never edited afterward. Revisiting a decision means a new ADR whose text marks the old one
    (or the exact section) superseded. Current behavior lives in `reference/`, not in the ADR.

14. **[MUST]** `adr/README.md` is a table `# | Decision | Status` with status values `Proposed`,
    `Implemented (YYYY-MM-DD)`, `Superseded by NNNN`, plus a note under the table for partial
    supersessions (`NNNN §k superseded by MMMM`). Filenames are `NNNN-kebab-title.md`,
    zero-padded to four digits. **Template:** same reference, §Folder README.md templates.

15. **[MUST]** Deviating from any `MUST` principle in this skill — any domain — requires an ADR
    in `docs/adr/` citing the principle by domain and number (`wens-dev-principles docs 7`).

## Common Mistakes

- An agent instruction file that grows into a second, drifting copy of reference (violates 3).
- Writing the glossary after the code, so identifiers and docs disagree on names (violates 5).
- A reference doc keeping a "History" or "Previously" section of superseded designs (violates 4).
- Editing a shipped plan to "keep it current" instead of writing a new one (violates 7).
- Emoji-only status banners that cannot be grepped or compared (violates 8).
- Dating a plan by its ship date so the spec/plan slugs no longer pair (violates 9).
- A folder of debug scripts with no `.md` explaining what they reproduce (violates 10).
- Rewriting an ADR to match the new behavior instead of superseding it (violates 13).
- A new document committed without its folder `README.md` row, so the index lies (violates 2).
- Deviating from a MUST principle with a commit-message note instead of an ADR (violates 15).
