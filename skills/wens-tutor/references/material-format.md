# Material format

`tutorlib.parser` reads plain Markdown; nothing here is a custom syntax, it is a set of
conventions the source corpus already uses, recognised by pattern. This is the reference for
recognising them by eye and for Backfilling a Defect without breaking the parse. See
`skills/wens-tutor/CONTEXT.md` for the vocabulary (Section, Bank, Question, Shared Stem,
Defect) and `docs/adr/0011…0012` for the decisions behind the two rules below.

## Sections

Cut at ATX headings `#`–`####`. A Section's identity is the slugified path of its heading
ancestors (`第三章-ai相關技術應用/3-1-自然語言處理技術與應用/1-前言與章節導覽`), not an
occurrence-counted slug — heading text repeats heavily in this corpus (`1. 前言與章節導覽`
occurs 9–12 times per guide), so a counter would silently renumber every later duplicate
whenever a chapter is inserted (ADR 0007). A Section's `text` is its own body only, up to the
next heading of any level; `is_leaf` marks a Section with no children, which is what Progress
counts.

## Bank shape `exam`

The whole file, as published in both generations of exam papers — one Question per `###`
heading, verbatim:

```markdown
### 第 12 題

**答案：B**

<stem: one or more Markdown blocks, may include fenced code, bold labels, bullet lists>

(A) …;
(B) …;
(C) …;
(D) …

**解析（AI 生成，未經官方確認）：**

<authored Explanation — optional, never from the published source>
```

Detection requires `^###\s*第\s*\d+\s*題\s*$` exactly — the loose form also matches 58 cheatsheet
chapter headings, which must not parse as Questions. A Question ends at the next `###`/`##` or
EOF; `---` separators (114年 files) and `《以下空白》` trailers are recognised as trailers and
dropped, not treated as content (see Line attribution below). Everything between the answer
line and the first option line is stem, including fenced blocks and bullet lists; the option
scanner ignores lines inside fenced regions, so an inline `(A)` inside a code fence is never
mistaken for an option. Options are `^\(([A-E])\)\s*(.+?);?$` in source order. An `**解析…：**`
block after the options is an authored Explanation (ADR 0005) — never stem, never an option.
Answers parse as `^\*\*答案[：:]\s*([A-E]+)`; anything else (three Questions in 114-科1 hold the
placeholder "（來源 PDF 此欄位無法擷取，請參閱官方公告）") stores `NULL` and a `no_answer` Defect.

## Bank shape `guide`

A `選擇題` region paired with the `解答與解析` region that immediately follows it, as published
in both study guides — numbering restarts per region, 7 regions × 10 Questions:

```markdown
### 選擇題

1. 下列何者為自然語言處理（NLP）中的詞嵌入技術…？
   - （A）TF-IDF
   - （B）Word2Vec
   - （C）Stop Words
   - （D）Bag-of-Words

### 解答與解析

**1. Ans（B） Word2Vec**

解析：Word2Vec 是一種詞嵌入方法，可將文字轉換為…
```

A `guide` Bank pairs with the **next sibling** `解答與解析` region (`check` reports
`unpaired_guide_bank` if that sibling is missing). Stems are `^\d+\.\s`, options are indented
`-\s*（[A-E]）`. Answers are `^\*\*(\d+)\.\s*Ans（([A-E])）`; Explanations are `^解析[：:]` —
these are the corpus's 70 **official** Explanations (ADR 0005), parsed verbatim, never rewritten.

## Shared stem (題組)

18 of the 270 Questions cannot be answered from their own text: they belong to a 題組 whose
stem is written once and referred to by 2–4 consecutive Questions, across 7 spans. The parser
recognises both conventions the corpus uses and **folds** the shared text into every member
Question's `stem_md` as an attributed blockquote, so a Question stays answerable alone
(ADR 0011 — no `Stimulus` entity is modelled):

| Convention | Where it sits | Seen in |
|---|---|---|
| `## 第 46～50 題（題組）` heading, prose beneath | between Questions, as a Bank sub-heading | 114年-科3 |
| `> 以下第46~48 題共用題幹：…` blockquote | at the tail of the *previous* Question's region | 115年-科3 |

Folded attribution format, prepended to `stem_md`:

```markdown
> **共用題幹（第46～48題）**
>
> <the quoted shared text>
```

Folding runs before `qkey_for`, so a folded Question's identity covers its shared stem — two
Questions with identical own-text under different preambles are different Questions. `shared_for`
returns the *first* span covering an ordinal, which is unambiguous only because spans never
overlap inside a file in this corpus; `check` reports `overlapping_shared_stems` as a finding
rather than resolving an overlap by luck.

## Line attribution (ADR 0012)

Every non-blank line inside a Question's region must land somewhere nameable: the stem, an
option, the answer, an Explanation, or a recognised Shared Stem. A line that fits none of those
becomes an `unattributed_lines` Defect on that Question. **Only `---` and `《以下空白》` are
whitelisted as trailers** — nothing else is silently tolerated. This is what surfaced the
Shared Stem and declared-Defect conventions in the first place: the first draft tolerated stray
prose and dropped 14 Questions' worth of lines, including every declared-Defect marker and
every shared-stem group marker, without a single visible failure. The corpus is at 0
`unattributed_lines` only *after* both conventions were recognised — that count is a to-do list
for the parser, not a tolerance to widen.

## Defects

Three kinds, all flowing through `cat.defect(qkey, kind)` and excluded from composed Papers by
default (ADR 0004):

| Kind | Measured count | Rule |
|---|---|---|
| `no_answer` | 3 | The answer line does not parse as `答案[：:]\s*([A-E]+)` — PDF extraction lost the field. |
| `figure_missing` | 25 | See below — the stem refers to a figure/table/listing that is not in the file. |
| `unattributed_lines` | 0 | A line in the Question region the parser could not place. |

**28 Defects total** on the current corpus at this commit — a measurement, expected to fall as
Backfill proceeds, not a constant.

`figure_missing` is the union of two provenances:

- **Declared** — the transcriber wrote the omission down in words: `※ …請對照原始 PDF。`,
  `〔註：…於此省略。〕`, or `見原始 P…`. This is authoritative: the marker line is **kept in the
  stem, never dropped**, and marks the Question directly. 18 of the 25 are declared.
- **Inferred** — a keyword heuristic: the stem references
  下圖/上圖/圖中/附圖/如圖/下表/上表/表中/以下程式/下列程式/程式碼中/程式中/如下所示 **and** the
  Question contains no fenced block, no table row, no image. 24 of the 25 are inferred.

The two sets overlap on 17: 7 are inferred-only, 1 (114-科3 第45題) is declared-only and
reachable *only* through its declaration — deleting that one line drops the corpus's
`figure_missing` count from 25 to 24 (verified by the Task 17 adversarial pass). The declared
form always wins when the two disagree; the keyword heuristic is advisory and will occasionally
flag a Question that reads fine, which is why `check`'s report is a list to review, not an
automatic exclusion beyond the composition default.

## Skeleton emitted by `new bank`

`tutor.py new bank <subject> <title> --shape exam|guide --questions N` writes a parseable
skeleton with **distinct placeholder stems** per Question — identical placeholder text produces
identical `qkey`s, and `INSERT OR IGNORE` would silently collapse the whole skeleton into one
Question row (ADR 0002). `check` after `new` must show N parsed Questions and no
`collapsed_questions` finding.

`--shape exam`:

```markdown
# <title>

## 一、選擇題

### 第 1 題

**答案：A**

（第 1 題題幹）

(A) 甲;
(B) 乙;
(C) 丙;
(D) 丁
```

(repeated for `第 2 題` … `第 N 題`, each stem `（第 N 題題幹）`).

`--shape guide`:

```markdown
# <title>

## 1. 練習

### 選擇題

1. （第 1 題題幹）
   - （A）甲
   - （B）乙
   - （C）丙
   - （D）丁

### 解答與解析

**1. Ans（A） 甲**

解析：（在此撰寫解析）
```

(repeated for `2.` … `N.`, each stem `（第 N 題題幹）`, each answer block scaffolded as `Ans（A）`
with a placeholder Explanation to fill in).

`new course <subject> <title>` writes a plain prose skeleton (`# <title>` / `## 1. 前言` /
placeholder body) — it carries no Bank region and produces no Questions.
