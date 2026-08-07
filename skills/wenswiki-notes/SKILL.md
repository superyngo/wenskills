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
