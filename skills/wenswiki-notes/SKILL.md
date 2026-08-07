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
