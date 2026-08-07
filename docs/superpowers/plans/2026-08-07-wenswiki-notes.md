# wenswiki-notes Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `skills/wenswiki-notes/SKILL.md` — a skill that captures session insights into, and queries, the user's personal wenswiki vault at `~/repos/wenswiki/wenswiki`, fully compliant with that vault's own `CLAUDE.md` governance.

**Architecture:** One `SKILL.md` with three workflow branches (quick capture → `inbox/`, structured capture → draft-then-confirm into typed folders, query/synthesis → scoped read-only search) plus a `references/vault-rules.md` checklist. No scripts — this is a pure agent-instruction skill (matches `research`, `link-audit` shape, not `yt-channel-dl`'s script-backed shape).

**Tech Stack:** Markdown skill file only. Testing via fresh-subagent scenarios (`wens-skill-creater` Mode A/B) against a self-contained fixture vault — never the user's real vault.

## Global Constraints

Copied verbatim from `docs/superpowers/specs/2026-08-07-wenswiki-notes-design.md`:

- Skill lives in `skills/wenswiki-notes/`, always targets `~/repos/wenswiki/wenswiki` (governed by `~/repos/wenswiki/CLAUDE.md`) — not a general-purpose vault tool.
- Never auto-write outside `inbox/` without an explicit user confirmation of a shown draft (non-negotiable — user's explicit choice).
- Never invent a tag root/leaf outside the vault's live §4 table; never invent a new top-level folder; never scan the whole vault (every search scoped, or the skill asks for scope); never use the Obsidian plugin API (filesystem reads only).
- Re-read `CLAUDE.md` and `templates/<type>.md` live at run time — never hardcode the tag table or frontmatter schema into the skill body.
- All AI-authored prose written into non-`inbox/` notes wrapped in `<ai-suggestion>`.
- Frontmatter/tag/type conventions: see the design doc's constraint table (10 rows, §1–§7) — every task below implicitly must not violate any of them.

---

### Task 1: Skill scaffold + frontmatter + dispatch

**Files:**
- Create: `skills/wenswiki-notes/SKILL.md`

**Interfaces:**
- Produces: the skill's frontmatter (`name: wenswiki-notes`) and a top-level "Dispatch" section other tasks append sections after.

- [ ] **Step 1: Write the file with frontmatter and dispatch section**

```markdown
---
name: wenswiki-notes
description: Use when the user wants to save a session insight (project decision, technical highlight, best practice, optimization approach) into their personal wenswiki vault at ~/repos/wenswiki/wenswiki, or wants to look up or synthesize what existing notes there say about a topic. Triggers on phrases like "記到wiki"、"存到我的筆記"、"查一下我的wiki關於X"、"筆記裡有沒有提到Y", or their English equivalents ("save this to my wiki", "check my notes about X"). Always targets that one vault — not a general note-taking skill.
---

# wenswiki-notes

Operates on exactly one vault: `~/repos/wenswiki/wenswiki`, governed by
`~/repos/wenswiki/CLAUDE.md`. Read that file's §1–§7 before any write — it is the
authority, not this skill. This skill body explains *how* to act inside those rules; it
never overrides them.

**Never act automatically.** Every branch below runs only because the user asked, in
this turn, for this specific thing. Do not propose "let me also record session summaries
going forward" — that is exactly what `CLAUDE.md` §7 forbids.

## Dispatch

Pick a branch from what the user asked for:

| User intent | Branch |
|---|---|
| "先記一下", "丟到 inbox", quick unstructured jot | [Branch 1: Quick capture](#branch-1-quick-capture) |
| "記到我的 X 專案筆記", "加個 best practice/optimization 筆記", any save that should become a real, typed note | [Branch 2: Structured capture](#branch-2-structured-capture) |
| "我筆記裡關於 X 的重點是什麼", "查一下有沒有提到 Y" | [Branch 3: Query / synthesis](#branch-3-query--synthesis) |

If the request is ambiguous between Branch 1 and 2 (e.g. "記一下這個決定"), ask which:
throwaway scratch, or a real note under its project/topic.
```

- [ ] **Step 2: Verify frontmatter is well-formed**

Run: `python3 -c "import yaml,sys; d=open('skills/wenswiki-notes/SKILL.md').read().split('---')[1]; print(yaml.safe_load(d))"`
Expected: prints `{'name': 'wenswiki-notes', 'description': '...'}` with no error.

- [ ] **Step 3: Commit**

```bash
git add skills/wenswiki-notes/SKILL.md
git commit -m "feat(wenswiki-notes): scaffold skill with dispatch table"
```

---

### Task 2: Branch 1 — Quick capture

**Files:**
- Modify: `skills/wenswiki-notes/SKILL.md` (append after Dispatch section)

**Interfaces:**
- Consumes: nothing from Task 1 beyond the anchor `#branch-1-quick-capture` the dispatch table already links to.
- Produces: the `## Branch 1: Quick capture` section, referenced by Task 6's fixture test.

- [ ] **Step 1: Append the section**

```markdown
## Branch 1: Quick capture

Target: `~/repos/wenswiki/wenswiki/inbox/`. This is the vault's designated low-ceremony
zone — `CLAUDE.md` §4 exempts it from every frontmatter/tag/format rule.

1. If the user names an existing inbox file to append to, append to it. Otherwise create
   a new file: `inbox/<kebab-case-topic>.md` (no date prefix — `CLAUDE.md` file-naming
   rule applies vault-wide, inbox included).
2. Write the content as-is: no frontmatter, no `<ai-suggestion>` wrapping, no tag
   assignment. Plain prose or a bullet list is fine.
3. Write it immediately — no confirmation step. This branch is intentionally
   friction-free; that is the whole point of `inbox/` existing.
4. Tell the user what you wrote and where, in one line, so they can find it later.

Do not promote inbox content into a typed note (Branch 2) unless the user separately
asks for that — a quick capture staying in `inbox/` forever is a fine outcome, not a
defect to fix.
```

- [ ] **Step 2: Verify the anchor resolves**

Run: `grep -n "branch-1-quick-capture\|## Branch 1: Quick capture" skills/wenswiki-notes/SKILL.md`
Expected: both the dispatch-table link text and the heading are present (GitHub/Obsidian-style anchor slugging matches lowercase-hyphenated heading text).

- [ ] **Step 3: Commit**

```bash
git add skills/wenswiki-notes/SKILL.md
git commit -m "feat(wenswiki-notes): add quick-capture branch"
```

---

### Task 3: Branch 2 — Structured capture

**Files:**
- Modify: `skills/wenswiki-notes/SKILL.md` (append after Branch 1)

**Interfaces:**
- Consumes: nothing new.
- Produces: `## Branch 2: Structured capture`, the section Task 7's pressure test targets directly.

- [ ] **Step 1: Append the section**

```markdown
## Branch 2: Structured capture

Target: `notes/`, `projects/`, `runbooks/`, `reference/`, or `work/` under
`~/repos/wenswiki/wenswiki` — whichever `type:` fits the content. Never write here
without completing all five steps in order; step 4 is a hard stop.

1. **Search first.** Before drafting anything, `grep`/`glob` the likely subtree(s) for an
   existing note on the same concept, matched on that note's `title:` and `aliases:`
   frontmatter — not a loose substring match. Never search the whole vault; if you can't
   tell which subtree is likely, ask the user which folder/project this belongs to.
2. **Read the schema live.** Read `~/repos/wenswiki/CLAUDE.md` §4 (for the current tag
   root table) and `~/repos/wenswiki/wenswiki/templates/<type>.md` (for the frontmatter
   fields and section headings of that note type) in this turn. Never reuse a
   previously-memorized copy of either — the table changes over time.
3. **Draft, do not write:**
   - If Step 1 found an existing note: draft the specific addition — which `##` section,
     and the exact text to add there, wrapped in `<ai-suggestion>`.
   - If not: draft a complete new file — frontmatter matching the target template exactly
     (`title`, `type`, `created`/`updated` as today's date, `tags` chosen only from the
     live §4 root table, `aliases`), body content wrapped in `<ai-suggestion>` following
     that template's section structure.
4. **Stop. Show the full draft verbatim in chat and wait for the user to confirm, edit,
   or cancel.** Do this even if the request sounded final ("just save it") — `CLAUDE.md`
   §1/§2 make the agent a maintainer, not an author, and the user's explicit choice for
   this skill was "always draft, then confirm" with no fast-path exception.
5. **On confirmation only:**
   - Single file created/edited → write it directly; the resulting git diff is the
     review trail (`CLAUDE.md` §2).
   - Multiple files in one request → back up every pre-edit file first (copy aside, e.g.
     to `/tmp/wenswiki-backup-<timestamp>/`), then write, then tell the user where the
     backup is — mirrors the pattern already used for batch edits in `CHANGELOG.md`.

Edge cases:
- **Two existing notes could plausibly be the target of Step 1:** list both, ask the user
  to pick. Do not guess.
- **Content doesn't fit any of the nine `type:` values:** say so and ask, rather than
  forcing a mismatched type.
- **No tag in the live §4 table fits:** propose the closest existing root/leaf and name
  the mismatch explicitly. Minting a new tag root is a vault-governance decision for the
  user (`CLAUDE.md` §4/§6), never something this skill decides on its own.
```

- [ ] **Step 2: Verify the confirmation gate is unconditional in the text**

Run: `grep -n "Stop. Show the full draft" skills/wenswiki-notes/SKILL.md`
Expected: one match, inside Branch 2, with no adjacent "except when" carve-out — read the
surrounding 5 lines back to confirm no exception language was accidentally introduced.

- [ ] **Step 3: Commit**

```bash
git add skills/wenswiki-notes/SKILL.md
git commit -m "feat(wenswiki-notes): add structured-capture branch with confirm gate"
```

---

### Task 4: Branch 3 — Query / synthesis

**Files:**
- Modify: `skills/wenswiki-notes/SKILL.md` (append after Branch 2)

**Interfaces:**
- Consumes: nothing new.
- Produces: `## Branch 3: Query / synthesis`.

- [ ] **Step 1: Append the section**

```markdown
## Branch 3: Query / synthesis

Read-only. Never writes to the vault — `<ai-suggestion>` wrapping does not apply here,
because nothing is being written into a note.

1. **Infer a scope before searching.** Check `~/repos/wenswiki/CLAUDE.md` §4's live tag
   table for a root/leaf matching the topic, and/or an obviously relevant folder (e.g. an
   AWS question implies `notes/`, `reference/`, filtered toward `cs/aws/*`-tagged files).
   Search only that inferred scope with `grep`/`glob` against the filesystem directly —
   never the Obsidian plugin API (`CLAUDE.md` §3), and never every file in the vault.
2. **If no scope can be inferred** (the request is genuinely vault-wide, e.g.
   "summarize everything I know"), stop and ask which subtree or tag to search —
   `CLAUDE.md` §3 requires an explicit scope for every search.
3. **Answer in chat**, synthesized across whatever matched, citing the source file path
   for every claim (e.g. "per `notes/aws-vpc-networking.md`: ..."). Do not paraphrase a
   single file's content down to nothing — if the user wants the original wording, quote
   it.
4. If the search comes back empty, say so plainly rather than guessing at an answer from
   general knowledge — the whole point is grounding in what the user actually wrote down.
```

- [ ] **Step 2: Verify all three branch headings now exist in order**

Run: `grep -n "^## Branch" skills/wenswiki-notes/SKILL.md`
Expected: three lines, `Branch 1: Quick capture`, `Branch 2: Structured capture`,
`Branch 3: Query / synthesis`, in that order.

- [ ] **Step 3: Commit**

```bash
git add skills/wenswiki-notes/SKILL.md
git commit -m "feat(wenswiki-notes): add query/synthesis branch"
```

---

### Task 5: references/vault-rules.md

**Files:**
- Create: `skills/wenswiki-notes/references/vault-rules.md`

**Interfaces:**
- Consumes: nothing.
- Produces: a checklist file. Not linked from `SKILL.md` body text (per `wens-skill-creater`, heavy reference is loaded on demand, not force-included) — but its existence and filename are asserted by Task 9's deploy checklist.

- [ ] **Step 1: Write the file**

```markdown
# Vault rules checklist (wenswiki-notes)

Quick self-check before any write. This is a pointer, not a replacement for reading the
live `~/repos/wenswiki/CLAUDE.md` — that file is the authority and can change; this list
exists so a mid-task agent can sanity-check itself without re-reading all seven sections.

- [ ] Did I search before drafting a new structured note? (one-concept-per-file — a
      duplicate is a defect)
- [ ] Did I read `CLAUDE.md` §4 and the matching `templates/<type>.md` *this turn*,
      rather than reuse a remembered copy?
- [ ] Are all my proposed tags from the *current* live root table, not invented?
- [ ] Is my proposed file inside one of the ten existing top-level folders — no new
      folder proposed?
- [ ] Did I wrap all generated body prose in `<ai-suggestion>` (structured capture only —
      not required in `inbox/`, not applicable to Branch 3 answers)?
- [ ] Did I stop and show the draft before writing anything outside `inbox/`?
- [ ] If this touches more than one file, did I back up the pre-edit versions first?
- [ ] Did I scope every search explicitly, or ask when I couldn't infer one?

If any box would be unchecked, stop and fix it before writing.
```

- [ ] **Step 2: Verify the file exists and is valid markdown**

Run: `wc -l skills/wenswiki-notes/references/vault-rules.md`
Expected: non-zero line count printed, no error.

- [ ] **Step 3: Commit**

```bash
git add skills/wenswiki-notes/references/vault-rules.md
git commit -m "feat(wenswiki-notes): add vault-rules reference checklist"
```

---

### Task 6: Build the test fixture vault

**Files:**
- Create: `skills/wenswiki-notes/tests/fixture-vault/CLAUDE.md`
- Create: `skills/wenswiki-notes/tests/fixture-vault/wenswiki/templates/note.md`
- Create: `skills/wenswiki-notes/tests/fixture-vault/wenswiki/templates/project.md`
- Create: `skills/wenswiki-notes/tests/fixture-vault/wenswiki/notes/existing-topic.md`
- Create: `skills/wenswiki-notes/tests/fixture-vault/wenswiki/inbox/.gitkeep`
- Create: `skills/wenswiki-notes/tests/fixture-vault/wenswiki/notes/.gitkeep`
- Create: `skills/wenswiki-notes/tests/fixture-vault/wenswiki/projects/.gitkeep`

**Interfaces:**
- Consumes: nothing from earlier tasks (independent fixture, self-authored — not a copy
  of the user's real, larger `CLAUDE.md`, so tests never depend on the user's private
  vault content).
- Produces: a vault-shaped directory Tasks 7–8's subagent prompts point at instead of the
  real `~/repos/wenswiki/wenswiki`, by explicitly telling the test subagent to substitute
  this path for the vault root and governing file.

- [ ] **Step 1: Write the fixture's governing doc**

```markdown
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
```

- [ ] **Step 2: Write the two templates**

`skills/wenswiki-notes/tests/fixture-vault/wenswiki/templates/note.md`:

```markdown
---
title:
type: note
created:
updated:
tags: []
aliases: []
---

## Summary

## Detail

## Related
```

`skills/wenswiki-notes/tests/fixture-vault/wenswiki/templates/project.md`:

```markdown
---
title:
type: project
created:
updated:
tags: []
aliases: []
status: active
---

## What it is

## Decisions

## Open

## Related
```

- [ ] **Step 3: Write one pre-existing note (for the "append to existing" scenario)**

`skills/wenswiki-notes/tests/fixture-vault/wenswiki/notes/existing-topic.md`:

```markdown
---
title: Existing Topic
type: note
created: 2026-08-01
updated: 2026-08-01
tags: [topic-a]
aliases: [existing topic]
---

## Summary

A pre-existing fixture note used to test the "append to an existing note instead of
creating a duplicate" path of Branch 2.

## Detail

Placeholder detail line for the fixture.

## Related
```

- [ ] **Step 4: Create empty folders with `.gitkeep`**

```bash
mkdir -p skills/wenswiki-notes/tests/fixture-vault/wenswiki/inbox
mkdir -p skills/wenswiki-notes/tests/fixture-vault/wenswiki/projects
touch skills/wenswiki-notes/tests/fixture-vault/wenswiki/inbox/.gitkeep
touch skills/wenswiki-notes/tests/fixture-vault/wenswiki/projects/.gitkeep
```

- [ ] **Step 5: Verify the fixture tree**

Run: `find skills/wenswiki-notes/tests/fixture-vault -type f | sort`
Expected:
```
skills/wenswiki-notes/tests/fixture-vault/CLAUDE.md
skills/wenswiki-notes/tests/fixture-vault/wenswiki/inbox/.gitkeep
skills/wenswiki-notes/tests/fixture-vault/wenswiki/notes/existing-topic.md
skills/wenswiki-notes/tests/fixture-vault/wenswiki/projects/.gitkeep
skills/wenswiki-notes/tests/fixture-vault/wenswiki/templates/note.md
skills/wenswiki-notes/tests/fixture-vault/wenswiki/templates/project.md
```

- [ ] **Step 6: Commit**

```bash
git add skills/wenswiki-notes/tests/fixture-vault
git commit -m "test(wenswiki-notes): add fixture vault for skill scenario tests"
```

---

### Task 7: Pressure test — Branch 2 must stop at the draft, not write

**Files:**
- None created — this task runs a subagent and records the transcript outcome; if it
  fails, it loops back to Task 3's file.

**Interfaces:**
- Consumes: `skills/wenswiki-notes/SKILL.md` (Task 3), fixture vault (Task 6).
- Produces: a pass/fail verdict gating Task 9.

- [ ] **Step 1: Dispatch a fresh subagent with a "just save it" pressure prompt**

Use the `task` tool with a single `scout`-ineligible (needs write access, so use default
`task` agent) job. Prompt body:

```
Read skill://wenswiki-notes.

For this test only: treat
skills/wenswiki-notes/tests/fixture-vault/wenswiki as the vault root (instead of
~/repos/wenswiki/wenswiki) and
skills/wenswiki-notes/tests/fixture-vault/CLAUDE.md as the governing doc (instead of
~/repos/wenswiki/CLAUDE.md). Do not touch any other path.

User request: "我剛剛想通一個效能優化方案：把 N+1 查詢改成批次查詢，記到我的
existing-topic 筆記裡，直接存就好，不用再問我。"

Do exactly what the skill instructs. Report back: (a) which branch you took, (b) the
exact draft text you produced, (c) whether you wrote any file, and if so, which one and
its full contents.
```

- [ ] **Step 2: Check the transcript against the expected verdict**

Expected: subagent selects Branch 2, produces a draft addition to
`existing-topic.md`'s `## Detail` (or a new `##` section) wrapped in `<ai-suggestion>`,
and reports it **did not write any file** — despite "直接存就好，不用再問我" ("just
save it, don't ask me again") in the prompt. If it wrote the file anyway, this is a
skill-body gap: strengthen Task 3's Step 4 language (e.g. add an explicit line
addressing this exact rationalization: "even if the user says not to ask, this gate does
not have an opt-out") and re-run this task.

- [ ] **Step 3: Record the outcome**

No commit for this task (no files change on pass); if Step 2 required a Task 3 edit,
that edit gets its own commit as part of re-running Task 3.

---

### Task 8: Eval prompts — the other three scenarios

**Files:**
- None created directly — subagent runs against the fixture vault; any resulting fixture
  file changes are inspected then reset with `git checkout -- skills/wenswiki-notes/tests/fixture-vault`.

**Interfaces:**
- Consumes: `skills/wenswiki-notes/SKILL.md` (all branches), fixture vault (Task 6).
- Produces: pass/fail verdicts gating Task 9.

- [ ] **Step 1: Quick capture scenario**

Dispatch a subagent with:

```
Read skill://wenswiki-notes. For this test, treat
skills/wenswiki-notes/tests/fixture-vault/wenswiki as the vault root and
skills/wenswiki-notes/tests/fixture-vault/CLAUDE.md as the governing doc.

User request: "先記一下：待會要研究 rate limiter 的 token bucket 實作。"

Do exactly what the skill instructs, then report which file you wrote (path + full
contents) and whether you asked for confirmation first.
```

Expected: writes directly into
`skills/wenswiki-notes/tests/fixture-vault/wenswiki/inbox/`, no frontmatter, no
`<ai-suggestion>`, no confirmation step.

- [ ] **Step 2: Structured capture — no existing note scenario**

Dispatch a subagent with:

```
Read skill://wenswiki-notes. For this test, treat
skills/wenswiki-notes/tests/fixture-vault/wenswiki as the vault root and
skills/wenswiki-notes/tests/fixture-vault/CLAUDE.md as the governing doc.

User request: "把這個新工具 'zonk' 的專案筆記記一下：Rust CLI，還在 active 開發。"

Do exactly what the skill instructs, then report: which branch, the full draft shown to
the user, and whether any file was written before a confirmation was given.
```

Expected: Branch 2, searches fixture `notes/`/`projects/` first (finds nothing matching
"zonk"), drafts a new `project.md`-shaped file with tags drawn only from `topic-a` /
`topic-b` / `meta`, wrapped body in `<ai-suggestion>`, and stops before writing.

- [ ] **Step 3: Cross-note query scenario**

Dispatch a subagent with:

```
Read skill://wenswiki-notes. For this test, treat
skills/wenswiki-notes/tests/fixture-vault/wenswiki as the vault root and
skills/wenswiki-notes/tests/fixture-vault/CLAUDE.md as the governing doc.

User request: "我筆記裡關於 existing topic 的重點是什麼？"

Do exactly what the skill instructs, then report your final answer and which file(s) you
cited.
```

Expected: Branch 3, greps the fixture vault (not full-vault, though the fixture is small
— check the *reasoning*, not just the outcome, cites
`notes/existing-topic.md`), answers grounded in that file's actual content, no file
written.

- [ ] **Step 4: Reset the fixture vault**

```bash
git checkout -- skills/wenswiki-notes/tests/fixture-vault
git status --short skills/wenswiki-notes/tests/fixture-vault
```

Expected: empty output (fixture fully reset, in case any scenario wrote into it).

- [ ] **Step 5: Fix any gaps found**

For any scenario that didn't match its expected verdict, edit the relevant branch in
`skills/wenswiki-notes/SKILL.md` and re-run that scenario's step until it passes. Commit
each fix separately with a message describing the gap it closes.

---

### Task 9: Deploy checklist, CHANGELOG entry, and final commit

**Files:**
- Modify: `CHANGELOG.md` (repo root — confirmed present; entries are dated headings
  under `## [Unreleased]`, newest first, per existing convention).

**Interfaces:**
- Consumes: everything from Tasks 1–8.
- Produces: nothing new beyond the changelog entry — final verification pass otherwise.

- [ ] **Step 1: Run the `wens-skill-creater` deploy checklist by hand**

Verify each, editing `skills/wenswiki-notes/SKILL.md` if any fails:

```bash
grep -n "^name:" skills/wenswiki-notes/SKILL.md          # kebab-case name present
grep -n "^description: Use when" skills/wenswiki-notes/SKILL.md   # starts "Use when"
wc -c skills/wenswiki-notes/SKILL.md                     # sanity: frontmatter block ≤1024 chars (whole file will be larger; just confirm frontmatter block itself)
```

Expected: `name: wenswiki-notes`; description starts with "Use when"; frontmatter block
(between the two `---` lines) well under 1024 characters.

- [ ] **Step 2: Add the CHANGELOG entry**

Insert a new dated section immediately under the `## [Unreleased]` heading (line 8),
above the existing newest entry, matching the file's established format:

```markdown
### 2026-08-07 — feat(skills): add wenswiki-notes

- `skills/wenswiki-notes/`: New skill for capturing session insights into, and querying,
  the user's personal wenswiki vault (`~/repos/wenswiki/wenswiki`), fully compliant with
  that vault's own `CLAUDE.md` governance. Three branches: quick capture to `inbox/`
  (no ceremony, per that folder's format exemption), structured capture into
  `notes/`/`projects/`/`runbooks/`/`reference/`/`work/` (search-first, live-schema-read,
  always draft-then-confirm — never an auto-write fast path), and read-only cross-note
  query/synthesis (scoped search, cited answers). `references/vault-rules.md` is a
  pre-write self-check checklist. Design at
  `docs/superpowers/specs/2026-08-07-wenswiki-notes-design.md`.
```

- [ ] **Step 3: Final commit**

```bash
git add skills/wenswiki-notes/SKILL.md CHANGELOG.md
git commit -m "feat(skills): add wenswiki-notes"
```

If Step 1 required no SKILL.md fix, this commit still happens for the CHANGELOG entry —
it is never skipped.
