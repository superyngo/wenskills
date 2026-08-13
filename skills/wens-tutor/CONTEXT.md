# Courseware Review — Domain

Vocabulary for reviewing Markdown courseware: reading it with persistent annotations,
sitting mock papers built from its question banks, and drilling the questions that were
answered wrong.

## Language

### Content

**Materials Root**:
The one directory tree a review session operates on, holding all Subjects for one
qualification. Owned by the human, never restructured by the tooling.
_Avoid_: vault, library, corpus

**Subject**:
A first-level folder inside the Materials Root, corresponding to one examinable subject.
_Avoid_: folder, category, topic

**Material File**:
Any Markdown file under a Subject. A Material File is not typed as a whole: it is a sequence
of regions, some Course, some Bank.
_Avoid_: document, page, note

**Course**:
The prose regions of a Material File — the part you read rather than answer.
_Avoid_: material (too broad), lesson, chapter, guide

**Bank**:
A contiguous region of a Material File holding Questions, identified by its file and its
Section path. Two shapes occur: a whole published exam paper (the file is one Bank), and a
`選擇題` region inside a study guide paired with the `解答與解析` region that follows it.
_Avoid_: material (too broad), quiz, test, paper, file of questions

**Section**:
One heading plus the body text belonging to that heading alone, excluding nested
subsections. Identified by its **ancestor path** (`第三章…/3.1…/1. 前言與章節導覽`), never by
an occurrence counter — the same heading text repeats up to twelve times per file, so a
counter-based identity silently shifts when a chapter is inserted.
_Avoid_: chapter, block, fragment

**Question**:
A stem, its options, and its answer, parsed out of a Bank. Identified by its own content, not
by where it sits.
_Avoid_: item, problem, exercise

**Defect**:
A data flaw in a Question that makes it unfit to sit: `no_answer` (the source published no
answer, or extraction lost it) or `figure_missing` (the stem refers to a figure, table, or
code listing that is absent from the file). A Defect is a property of the content, repaired
by Backfill — never by editing user data.
_Avoid_: broken, invalid, bad question

### Sitting

**Paper**:
An ordered set of Questions plus the criteria that selected them. Produced by one act of
composition; sat zero or more times.
_Avoid_: exam, test, quiz (acceptable in conversation, never in code or docs)

**Attempt**:
One sitting of one Paper: the answers given, the time spent, and the resulting score. At most
one Attempt per Paper is in flight; it is resumable, and its countdown is wall-clock — a
closed tab does not pause the exam.
_Avoid_: session, run, submission

**Drill**:
An Attempt whose Paper was composed from Starred Questions only, and which is untimed.
_Avoid_: practice, review mode, focus mode

**Star**:
A marker on a Question flagging it for repeat review — the "重點題" of the original
requirements. Its origin is either `wrong` (set automatically on a wrong answer, cleared
automatically after two consecutive corrects) or `manual` (set by the human, never cleared
automatically).
_Avoid_: flag, bookmark, favourite, important

### Reading

**Annotation**:
A user mark anchored to a passage of any Material File — Course prose or a Question stem
alike — re-located on each render by quoting the passage rather than by storing a position. A
**Highlight** is an Annotation with a colour and no text; a **Note** is an Annotation carrying
the human's own words. One concept, two shapes.
_Avoid_: comment, mark, memo

**Orphan**:
An Annotation whose quoted passage can no longer be found, because the text was rewritten
under it. An acknowledged state shown to the human, not an error to hide.
_Avoid_: broken annotation, stale highlight

**Progress**:
The set of leaf Sections the human has explicitly ticked as read. Ticking a Section covers
that Section alone — never its children — and only leaf Sections count toward the total.
Never inferred from scrolling or time spent.
_Avoid_: completion, read status, coverage

**Lookup**:
Finding, from a phrase selected anywhere in the interface, where that phrase literally occurs
— in Course Sections, and separately in the Questions of Banks. Never semantic, never ranked
by relevance models.
_Avoid_: search (too broad), query, retrieval

### Repair

**Backfill**:
Repairing a Defect by restoring the missing content from the authoritative source (the
original PDF beside the Markdown, or the issuing body's published answer key) into the
Material File.
_Avoid_: fix, patch, import

**Explanation**:
Prose in a Bank saying *why* an answer is correct. The study guides publish one per practice
Question; the exam papers publish none, so any Explanation added to one is authored and
carries its attribution. Always content — distinct from a Note, which is the human's private
reaction and is user state.
_Avoid_: solution, rationale, commentary
