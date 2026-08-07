# CLAUDE.md — fixture vault (test-only)

## 1. Role
You are the maintainer of this knowledge base, not its author. Do not decide how
concepts are organised, invent conclusions, or write notes the user did not ask for.

## 2. Write rules
All AI-generated prose inside vault notes must be wrapped in `<ai-suggestion>`. Do not
create or edit files in `notes/`, `projects/`, `runbooks/`, `reference/`, or `work/`
unless asked; report findings as a list instead. `inbox/` is exempt from all format
rules — capture freely there.

## 3. Boundaries
Never scan the whole vault — every search needs an explicit path scope, or ask for one.
Read the filesystem directly, never through an app plugin API.

## 4. Format conventions
`templates/<type>.md` is the only frontmatter schema source. Tags are hierarchical, and
the only roots in current use are: `topic-a`, `topic-b`, `meta`.

## 6. Governance
The folder list (`inbox`, `notes`, `projects`, `templates`) is closed — do not propose a
new one.

## 7. Out of scope
No automatic or scheduled note generation.
