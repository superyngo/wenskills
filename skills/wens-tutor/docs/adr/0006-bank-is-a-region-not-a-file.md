# A Bank is a region of a Material File, not a file

Course and Bank are properties of *regions* within a Material File, not of the file itself. A
published exam paper is one Bank spanning the whole file; a study guide is mostly Course prose
with a Bank at each `選擇題` region, whose answers and Explanations come from the
`解答與解析` region that immediately follows it.

The two study guides were assumed to be pure prose. They are not: they carry **70 official
practice Questions — 7 regions of exactly 10, every one with 4 options, an official answer, and
an official Explanation, and not one Defect among them.** That is 26% of the corpus and the
only place official Explanations exist at all. A file-typed model discards it silently, which
is the same class of failure as the missing figures in ADR 0004.

## Considered Options

- **Ignore the guide Questions** (the original design). Loses 70 defect-free Questions and all
  70 official Explanations.
- **Have the agent extract them into standalone Bank files.** Keeps a file-level type but
  duplicates official content, so the guide and the extract must be kept in sync by hand
  forever, and every extraction is a diff against an official document.

## Consequences

The parser handles two Question shapes: the exam-paper shape (`### 第 N 題`, `**答案：X**`,
line-initial `(A)` options) and the guide shape (`N.` numbered stems, indented `- （A）`
options with full-width parens, answers as `**N. Ans（B） …**` plus `解析：` in the sibling
region). Bank identity is `(fid, section path)`, which depends on ADR 0007's stable Section
paths. Composition criteria name Banks by that path, so a Bank that disappears is reported
rather than silently dropped from a Paper.
