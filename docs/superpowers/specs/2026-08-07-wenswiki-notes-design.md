# wenswiki-notes skill — design

## Problem

The user maintains a personal Obsidian vault at `~/repos/wenswiki/wenswiki`, governed by
`~/repos/wenswiki/CLAUDE.md`. There is currently no repeatable way, from an arbitrary
coding session (in any project, not just `wenswiki` itself), to:

- capture a session's key insight (project decision, technical highlight, best practice,
  optimization approach) into the vault, or
- query/synthesize what the vault already says about a topic.

Doing this by hand each time is friction; doing it via an unscoped "auto-record
everything" tool would violate the vault's own governance rules (see Constraints).

## Scope

One skill, `wenswiki-notes`, added to this repo (`skills/wenswiki-notes/`) so it is
available from any project session, not vault-specific tooling. It always targets the
fixed path `~/repos/wenswiki/wenswiki` (with `~/repos/wenswiki/CLAUDE.md` as its
governing document) — it is not a general-purpose "note taking" skill for arbitrary
vaults.

Out of scope: automatic/scheduled capture, any mechanism that writes to the vault without
the user asking in the current turn, and any change to the vault's own folder/tag
taxonomy.

## Constraints (from `~/repos/wenswiki/CLAUDE.md`, authoritative)

| # | Rule | Section |
|---|---|---|
| 1 | Agent is maintainer, not author — do not decide organization, do not invent conclusions, do not write notes the user didn't ask for. Retrieval is the highest-value use. | §1 |
| 2 | Outside `inbox/`, do not create/edit vault notes unless asked; report findings as a list otherwise. | §2 |
| 3 | All AI-generated prose written into vault notes must be wrapped in `<ai-suggestion>`. Exempt: frontmatter fields, wikilink insertion/repair, renames, formatting. | §2 |
| 4 | Never bulk-edit without a backup; every change must be reviewable as a diff. | §2 |
| 5 | Never scan the whole vault; every search needs an explicit path scope, or the agent asks for one. | §3 |
| 6 | No symlinks; read the filesystem directly, not the Obsidian plugin API. | §3 |
| 7 | `templates/*.md` is the only schema source — no ad hoc frontmatter fields. | §4 |
| 8 | Tags are hierarchical, root-capped at 10, currently exactly 6 in active use (`cs/*`, `homelab`, `life/*`, `work/*`, `meta/*`, `projects/*`) — do not invent a new root or leaf pattern. | §4 |
| 9 | Folder list is closed (10 top-level folders) — never propose or create a new one. | §6 |
| 10 | No automated/scheduled note generation of any kind. | §7 |

These are re-read from the live files at skill run time (see Architecture) rather than
copied verbatim into the skill body, so a future edit to `CLAUDE.md` (e.g. a tag-table
change) can't silently go stale inside the skill.

## Architecture

Single `SKILL.md` with three branches sharing one entry point (all three need the same
governance read-in), instead of three separate skills — they operate on the same vault
under the same rules, and a request often blends capture + a lookup ("does a note like
this already exist?").

```
wenswiki-notes/
  SKILL.md                 # branch dispatch + all three workflows
  references/vault-rules.md  # short checklist pointing back at CLAUDE.md §1-§7;
                              # NOT a copy of the tag table or template schemas
```

### Branch 1 — Quick capture (`inbox/`)

Trigger: "先記一下", "丟到 inbox", low-ceremony ask.

- Append/create a file under `wenswiki/inbox/`. No frontmatter, no `<ai-suggestion>`
  wrapping (§4 exempts `inbox/` from all format rules).
- No confirmation step — this is the vault's designated low-friction capture zone.

### Branch 2 — Structured capture (`notes/`, `projects/`, `runbooks/`, `reference/`, `work/`)

Trigger: "記到我的 X 專案筆記", "加一個 best practice 筆記", "把這個優化方案存到 wiki".

Steps, always in this order:

1. **Search first.** `grep`/`glob` a scoped subtree (never the whole vault) for an
   existing note on the same concept — matched via `title`/`aliases`, not loose
   substring, mirroring the existing `link-audit` command's approach. One-concept-per-file
   is a vault rule; duplicating a concept into a second file is a defect, not a shortcut.
2. **Read the schema live.** Load `CLAUDE.md` §4's tag table and the matching
   `wenswiki/templates/<type>.md` for the note type in play. Never hardcode either.
3. **Draft, don't write.**
   - Existing note found → draft the addition (which section, what text) as a diff-shaped
     preview.
   - No existing note → draft a full new file: frontmatter (`title/type/created/updated/
     tags/aliases`, `tags` drawn only from the live §4 table) + body inside
     `<ai-suggestion>`.
4. **Stop and show the full draft.** Wait for explicit confirm/edit/cancel. No
   auto-write, ever — this is non-negotiable per §1/§2/§7 and was the user's explicit
   choice among the write-policy options presented.
5. **On confirm:** single-file change → normal edit (git diff is the review trail).
   Multi-file/batch change → back up the pre-edit files first (matching the pattern in
   the vault's own `CHANGELOG.md` entries), per §2.

### Branch 3 — Query / cross-note synthesis

Trigger: "我筆記裡關於 X 的重點/best practice 是什麼", "查一下有沒有提到 Y".

1. Narrow scope from the topic before searching: check the §4 tag table for a matching
   root/leaf, and/or an obvious folder (e.g. an AWS question → `notes/`, `reference/`
   filtered by `cs/aws/*`). This keeps the search targeted (never a full-vault read) while
   avoiding an extra round-trip for a scope that's inferable.
2. If the topic is genuinely too broad to infer a scope (e.g. "summarize everything I
   know"), stop and ask which subtree/tag to search, per §3's explicit rule.
3. Run scoped `grep`/`glob` reads directly against the filesystem (never the Obsidian
   plugin API, per §3).
4. Answer in the chat, citing the source file path(s) per claim — this is a spoken
   answer, not a vault write, so `<ai-suggestion>` wrapping doesn't apply.

## Error handling / edge cases

- **Ambiguous match in Branch 2 step 1** (two candidate existing notes): present both,
  let the user pick — do not guess (mirrors `link-audit`'s existing rule for ambiguous
  link targets).
- **No matching template type**: if the content doesn't cleanly fit one of the nine
  `type:` values, say so and ask, rather than forcing a mismatched type.
- **Tag doesn't fit the current 6-root table**: propose the closest existing root/leaf
  and flag the mismatch instead of minting a new one — creating a 7th root is a
  governance decision for the user, not the skill.
- **CLAUDE.md/templates unreadable or vault path missing**: fail closed — report the
  problem, do not fall back to guessed conventions.

## Testing / verification

This is a discipline-adjacent skill (must resist "just write it" pressure) with
verifiable file outputs, so both `wens-skill-creater` testing modes apply:

- **Pressure scenario (Mode A):** run a fresh agent against a prompt like "把這次 session
  討論的 XX 優化方案記到我的 wiki 裡" and confirm it stops at the draft-preview step
  instead of writing directly — this is the rule most likely to be rationalized away
  ("it's clearly what they want, just save it").
- **Eval prompts (Mode B):** 2-3 realistic prompts covering each branch (quick capture,
  structured capture with an existing note to extend, structured capture with no existing
  note, cross-note query) run against the real vault in a throwaway git branch/backup, and
  the resulting diffs reviewed by hand.

## Related

- `skills/research/SKILL.md` — precedent for a session-agnostic capture-to-repo skill.
- `~/repos/wenswiki/.claude/commands/link-audit.md` — precedent for "report only, wait for
  the user to say which rows to apply" and ambiguous-match handling in this same vault.
