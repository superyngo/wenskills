# Sections are identified by their ancestor path

A Section's identity — the key Progress rows and Bank regions hang off — is the slugified path
of its heading ancestors (`第三章-ai相關技術應用/3-1-自然語言處理技術與應用/1-前言與章節導覽`),
not a slug with an occurrence counter appended.

Heading text repeats heavily in this corpus: `1. 前言與章節導覽` occurs 9 times in the 科目1
guide and 12 times in the 科目3 guide; `選擇題` and `解答與解析` occur 3 and 4 times
respectively. Counter-based deduplication (`前言與章節導覽-7`) makes identity depend on how many
identical headings precede it, so inserting one chapter renumbers every later duplicate and
quietly moves the human's read-ticks onto different Sections. Ancestor paths are unique across
all eight Material Files measured — zero collisions — because a heading does not repeat within
one parent.

## Consequences

Keys are long, and renaming a chapter heading changes the identity of every Section beneath it.
That is accepted: renaming a heading in an official published document is rare, and `check`
reports read-ticks whose Section no longer exists rather than silently relinking them — unlike
file renames (ADR 0002), which are frequent enough to justify automatic reconciliation.
