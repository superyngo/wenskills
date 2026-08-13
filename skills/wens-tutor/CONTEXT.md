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

**Course**:
A Markdown file of study prose, i.e. one holding no Questions.
_Avoid_: material (too broad), lesson, chapter, guide

**Bank**:
A Markdown file of Questions, i.e. one holding at least one `### 第 N 題` heading.
_Avoid_: material (too broad), quiz, test, paper

**Section**:
One heading in a Course plus the body text belonging to that heading alone, excluding any
nested subsections. The unit of navigation, of Progress, and of Lookup results.
_Avoid_: chapter, block, fragment

**Question**:
A stem, its options, and its answer, parsed out of a Bank. Identified by its own content,
not by where it sits.
_Avoid_: item, problem, exercise

**Defect**:
A data flaw in a Question that makes it unfit to sit: `no_answer` (the source published no
answer, or extraction lost it) or `figure_missing` (the stem refers to a figure, table, or
code listing that is absent from the file). A Defect is a property of the content, fixed by
repairing the content — never by editing user data.
_Avoid_: broken, invalid, bad question

### Sitting

**Paper**:
An ordered set of Questions plus the criteria that selected them. Produced by one act of
composition; sat zero or more times.
_Avoid_: exam, test, quiz (acceptable in conversation, never in code or docs)

**Attempt**:
One sitting of one Paper: the answers given, the time spent, and the resulting score.
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
A user mark anchored to a passage of a Course, re-located on each render by quoting the
passage rather than by storing a position. A **Highlight** is an Annotation with a colour
and no text; a **Note** is an Annotation carrying the human's own words. One concept, two
shapes — not two separate things.
_Avoid_: comment, mark, memo

**Orphan**:
An Annotation whose quoted passage can no longer be found, because the Course was
rewritten under it. An acknowledged state shown to the human, not an error to hide.
_Avoid_: broken annotation, stale highlight

**Progress**:
The set of Sections the human has explicitly ticked as read. Never inferred from scrolling
or from time spent.
_Avoid_: completion, read status, coverage

**Lookup**:
Finding, from a phrase selected anywhere in the interface, the Sections of a Course that
contain that phrase literally. Never semantic, never ranked by relevance models.
_Avoid_: search (too broad), query, retrieval

### Repair

**Backfill**:
Repairing a Defect by restoring the missing content from the authoritative source (the
original PDF beside the Markdown, or the issuing body's published answer key) into the
Bank file.
_Avoid_: fix, patch, import

**Explanation**:
Prose added to a Bank saying *why* an answer is correct. Absent from the published source,
so always attributed to whoever wrote it, and always part of the content — distinct from a
Note, which is the human's private reaction and part of user data.
_Avoid_: solution, rationale, commentary
