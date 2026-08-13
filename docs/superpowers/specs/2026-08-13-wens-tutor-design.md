# wens-tutor skill — design

Domain vocabulary: [`skills/wens-tutor/CONTEXT.md`](../../../skills/wens-tutor/CONTEXT.md).
Decisions: [`skills/wens-tutor/docs/adr/`](../../../skills/wens-tutor/docs/adr/) (0001–0009).
Terms defined there — Materials Root, Subject, Material File, Course, Bank, Section, Question,
Defect, Paper, Attempt, Drill, Star, Annotation, Orphan, Progress, Lookup, Backfill,
Explanation — are used here with exactly those meanings.

## Problem

The user is preparing for the 2026 iPAS 中級 AI 應用規劃師 certification. The material lives as
Markdown in a private repo, `superyngo/ipas-ai-planner-2026`, mounted as a git submodule of the
wenswiki vault at `~/repos/wenswiki/wenswiki/work/平台/2026_AI應用規劃師`. Today that material
is inert text: there is no way to

- see Progress across Subjects,
- annotate while reading and have the marks survive a restart,
- sit a Paper under exam conditions, keep per-Attempt statistics, and Drill the Questions
  answered wrong,
- while sitting a Paper, jump from a phrase in a Question to where it is explained.

The requirement is unusual in shape: the content is static files curated by a human and an
agent, but the site over it must be generated from a database of user state. Neither a
static-site generator nor a conventional web app fits cleanly.

## Scope

One skill, `skills/wens-tutor/`, holding both the agent-facing workflow (`SKILL.md`) and the
engine (`scripts/`, `web/`). It operates on any registered Materials Root; the iPAS repo is the
first one, not a hardcoded target.

Out of scope, decided explicitly: 考點代碼 (L21101…) level statistics (the Banks carry no such
markers, so any mapping would be invented); multi-user, authentication, remote hosting, cloud
sync; embedding or vector retrieval (also forbidden by the vault's `CLAUDE.md` §6); inferring
Progress from scroll position; non-multiple-choice Question types; a crawler.

## Ground truth (measured 2026-08-13)

### Material Files

| Path relative to the Materials Root | Content | Facts |
|---|---|---|
| `AI應用規劃師/…學習指引-科目1…_20251222101833.md` | Course + 3 Banks | 274 KB, 73 headings (8/14/51 by level), 57 leaf Sections, **30 Questions** |
| `AI應用規劃師/ipas_ai_planner_L21_cheatsheet.md` | Course | 136 headings, 104 leaf, 636 table rows |
| `AI應用規劃師/114年第二梯次…第一科…_20251226000616.md` | 1 Bank | 50 Q, 3 `no_answer`, 2 `figure_missing` |
| `AI應用規劃師/115年第一次…第一科…_20260615003359.md` | 1 Bank | 50 Q, 2 `figure_missing`, 1 fenced stem |
| `機器學習/…學習指引-科目3…_20251222101907.md` | Course + 4 Banks | 286 KB, 89 headings, 68 leaf, **40 Questions** |
| `機器學習/ipas_ai_planner_L23_cheatsheet.md` | Course | 160 headings, 119 leaf |
| `機器學習/114年第二梯次…第三科…_20251226000650.md` | 1 Bank | 50 Q, 10 `figure_missing`, 1 fenced stem |
| `機器學習/115年第一次…第三科…_20260615003428.md` | 1 Bank | 50 Q, 9 `figure_missing` |

**270 Questions in 11 Banks**, all single-answer, all with exactly 4 options:

- **200** from the four exam papers: 3 `no_answer`, 23 `figure_missing` (11.5%), no
  Explanations, zero images anywhere in the corpus.
- **70** from the two study guides: 7 regions of exactly 10, **100% answered, 100% carrying an
  official Explanation, zero Defects** (ADR 0006).

Section identity: ancestor paths are **unique across all eight files, zero collisions**, while
heading *text* repeats hard — `1. 前言與章節導覽` 9 times in the 科目1 guide and 12 times in the
科目3 guide (ADR 0007).

`README.md` and the `source/` folders (the original PDFs) are not catalogued.

### Exam conditions

ipas.org.tw 115年度簡章 and ipd.nat.gov.tw 考試資訊: **90 minutes, 50 Questions per subject,
computer-based; a subject must score ≥60 and the two-subject average must reach 70.** From
114年第二梯次 onward the 機器學習 subject includes roughly 25% Python code-reading Questions —
which is exactly where the `figure_missing` Defects cluster.

### Repos

`wenskills` is clean and in sync with `origin/main`. The vault is 12 commits ahead of origin
with a large uncommitted migration in flight, so **nothing outside the `ipas-ai-planner-2026`
submodule is touched**; that submodule is clean and in sync. Its four-commit history already
contains a mass rename (six PDFs moved into `source/`) — the evidence behind ADR 0002.

## Constraints

From `~/repos/wenswiki/CLAUDE.md`, authoritative for anything under the vault:

| # | Rule | § | Consequence |
|---|---|---|---|
| 1 | Filenames are Notion page titles verbatim; no renaming, flattening, normalising | 2 | Course/Bank cannot be a folder layout; both are sniffed from content |
| 2 | **No symlinks anywhere in the vault** | 2 | The engine cannot be linked into the material tree; two static roots in one server is the only option |
| 3 | Never scan the whole vault; every operation needs an explicit path scope | 2 | The tooling only ever walks a registered Materials Root |
| 4 | No vector indexes or embedding databases | 6 | Lookup is literal substring matching |
| 5 | Do not `git push` the vault repo | 6 | Only the `ipas-ai-planner-2026` submodule is pushed, and only when asked |

Measured technical constraints:

| Finding | Evidence | Consequence |
|---|---|---|
| SQLite FTS5 cannot tokenise CJK usefully | sqlite 3.51.0: `unicode61` and `trigram` both return 0 rows for `MATCH '語言'` against `'自然語言處理技術與應用'` | No FTS5 table; Lookup is a plain scan |
| A whole-corpus scan is free | 0.33 ms over all 660 KB | No index needed for Lookup |
| Bank detection needs the strict pattern | `^###\s*第\s*\d+\s*題\s*$`; the loose `### 第` matches 58 cheatsheet chapter headings | Sniffing is exact, with no override list |
| Stems are real Markdown | fenced code in 115-科1 Q16 and 114-科3 Q41; bold labels; bullet lists | Stems render through markdown-it; the option scanner skips fenced regions |
| Heading text is not unique, ancestor paths are | 9 and 12 repeats of one heading; 0 path collisions in 8 files | ADR 0007 |

## Architecture

Three layers, one seam each. The seam that matters: **the agent owns content (a judgement
task); the engine owns presentation (a deterministic task).**

```
skills/wens-tutor/                  the engine, in the wenskills repo
  SKILL.md                          agent workflow + triggers
  CONTEXT.md                        domain glossary
  docs/adr/0001…0009                decisions
  references/material-format.md     both Question shapes, parser tolerances, Defect rules
  references/db-schema.md           user-state schema + key-stability rationale
  scripts/tutor.py                  CLI: arg parsing and dispatch only
  scripts/tutorlib/parser.py        pure: Markdown -> Sections, Banks, Questions, Defects
  scripts/tutorlib/catalog.py       walk a root, build the in-memory catalogue
  scripts/tutorlib/state.py         user-state DDL, connection, fid/qkey reconciliation
  scripts/tutorlib/compose.py       Paper composition, grading, Star lifecycle
  scripts/tutorlib/server.py        ThreadingHTTPServer, routes, path containment
  scripts/tutorlib/api.py           JSON endpoints
  web/index.html web/reader.html web/exam.html web/stats.html
  web/app/*.js  web/style.css  web/strings.js  web/manifest.webmanifest
  web/vendor/markdown-it.min.js     vendored; no npm, no build step
  tests/test_parser.py  tests/test_rules.py

~/.config/wens-tutor/roots.json     device-local registry: roots, default root, port

<Materials Root>/                   the content, in the ipas-ai-planner-2026 repo
  <Subject>/*.md                    modified only by the agent or the human, never the engine
  .tutor/tutor.db                   user state only (ADR 0001), committed
  .tutor/tutor.json                 the same state, diffable (ADR 0009), committed
```

Python is stdlib-only, so any interpreter ≥3.9 runs it; the skill invokes it as
`uv run --python 3.14 python3 scripts/tutor.py …` per this repo's CLAUDE.md (3.14.3 installed).

### The path problem (requirement 3.2)

One process, two static roots:

| Route | Served from | Notes |
|---|---|---|
| `/`, `/reader`, `/exam`, `/stats`, `/app/*`, `/vendor/*`, `/style.css` | the skill's `web/` | engine source stays inside the skill (3.1) |
| `/raw/<relpath>` | the Materials Root | `.md` only; `realpath` + `commonpath` containment; symlinks refused |
| `/api/*` | the catalogue + `tutor.db` | JSON |

This replaces symlinking, copying the engine into the material tree, or copying material into
the skill — the first violates constraint 2, the others duplicate the source of truth.

### Catalogue (ADR 0001)

Every process start walks the Materials Root, parses it, and inserts the result into an
in-memory database attached as `cat`:

```sql
cat.file(fid, relpath, subject, title, sha256, n_sections, n_questions)
cat.section(fid, path, level, title, is_leaf, line_start, line_end, text)
cat.bank(bkey, fid, path, title, shape)          -- shape: 'exam' | 'guide'
cat.question(qkey, bkey, ordinal, type, stem_md, options_json, answer,
             explanation_md, explanation_origin)  -- origin: 'official' | 'authored' | NULL
cat.defect(qkey, kind)                            -- 'no_answer' | 'figure_missing'
```

`bkey = (fid, path)`; `path` is the Section ancestor path (ADR 0007), so Bank identity survives
edits elsewhere in the file. `main` is the user-state database; joins across `main` and `cat`
are ordinary SQLite. There is no `index` command, no cache file, and no staleness — the
catalogue is rebuilt from the Markdown, so it cannot disagree with it.

The server holds one connection (`check_same_thread=False`) behind a single lock rather than one
per thread, because the catalogue lives on that connection. Single user, millisecond queries.

## Identity and user state (ADR 0002, 0007)

```sql
-- main: user state, never rebuilt, committed to the Materials Root
file_id(fid PK, relpath, first_seen, fingerprint)
annotation(id PK, fid, block_line, exact, prefix, suffix, color, note_md, ts, orphan)
progress(fid, path, read_at, PRIMARY KEY(fid, path))       -- leaf Sections only
reading_pos(fid PK, line, ts)
star(qkey PK, origin, ts)                                   -- 'wrong' | 'manual'
note(qkey PK, note_md, ts)                                  -- private, per Question
paper(id PK, criteria_json, qkeys_json, limit_ms, created)
attempt(id PK, paper_id, started, finished, elapsed_ms, total, correct, expired)
attempt_item(attempt_id, qkey, given, correct, ms, PRIMARY KEY(attempt_id, qkey))
```

- **`qkey = sha256(NFKC(stem) + NFKC(options))[:12]`** — identity follows the Question text, so
  renaming or moving a file costs nothing.
- **`fid`** is minted on first sight and reconciled at every startup: exact `relpath` first;
  then, for a vanished path, a `fingerprint` match (Jaccard ≥ 0.6 over Section paths for prose,
  over stem hashes for Banks) when exactly one candidate qualifies. Ambiguity is reported for an
  explicit `relink`, never guessed.
- **Stem edits** (fixing OCR typos is frequent here) change `qkey`; startup relinks orphaned
  keys by `(bkey, ordinal)` and reports each relink.
- **Section renames** are *not* relinked — `check` reports read-ticks whose Section path is gone
  (ADR 0007).
- Statistics derive from `attempt`/`attempt_item` at query time; no aggregate columns, so there
  is no second copy of the truth.
- `type` is `single` or `multi`, derived from answer length; the corpus is 270/270 `single`.
  Grading a `multi` Question is exact-set-match, no partial credit.
- The database is committed because the Materials Root exists to sync across devices. SQLite is
  binary, so git cannot merge it: the discipline is pull-before-studying, and a real two-device
  conflict is resolved by keeping one side. Journal mode stays at the default, so there are no
  `-wal`/`-shm` sidecars to ignore.

## Material format

**Sections.** Cut at ATX headings `#`–`####`. A Section's `text` is its own body only, up to
the next heading of *any* level, so Lookup cannot return a parent and its child as two hits on
one passage. Identity is the ancestor path; `is_leaf` marks Sections with no children, which is
what Progress counts.

**Bank shape `exam`** — the whole file, as published in both generations of exam papers:

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

**Bank shape `guide`** — a `選擇題` region plus the `解答與解析` region that immediately
follows it, as published in both study guides:

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

Parser tolerances, each driven by a real case in the corpus:

| Tolerance | Real case |
|---|---|
| `exam` detection requires `^###\s*第\s*\d+\s*題\s*$` | the loose form matches 58 cheatsheet chapter headings |
| A Question ends at the next `###`/`##` or EOF; `---` separators and `《以下空白》` trailers are dropped | 114年 files separate Questions with `---`, 115年 files do not |
| Everything between the answer line and the first option line is stem, including fenced blocks | 115-科1 Q16: bullet list, two bold labels, two fenced blocks |
| The option scanner ignores lines inside fenced regions | same Question |
| `exam` options are `^\(([A-E])\)\s*(.+?);?$` in source order | uniform across all 4 papers |
| `guide` stems are `^\d+\.\s`, options are indented `-\s*（[A-E]）`, numbering restarts per region | 7 regions × 10 Questions, 4 options each |
| A `guide` Bank pairs with the **next sibling** `解答與解析` region; answers are `^\*\*(\d+)\.\s*Ans（([A-E])）`, Explanations are `^解析[：:]` | region order is `選擇題, 解答與解析` × 7, always adjacent |
| An `**解析…：**` block after `exam` options is an authored Explanation, not stem, not an option | ADR 0005 |
| Answers parse as `答案[：:]\s*([A-E]+)`; anything else stores `NULL` and a `no_answer` Defect | 3 Questions in 114-科1 hold the placeholder "（來源 PDF 此欄位無法擷取…）" |
| `figure_missing` = the Question references 下圖/上圖/圖中/附圖/如圖/下表/上表/表中/以下程式/下列程式/程式碼中/程式中/如下所示 **and** contains no fenced block, no table row, no image | 23 Questions; 8 say so explicitly (`〔註：…省略。〕`), 15 say nothing at all |
| Both half-width and full-width punctuation, and full-width option parens | 115年 uses `,` `?`; 114年 uses `，` `？`; guides use `（A）` |
| An inline `(A)` that is a *blank marker*, not an option, stays in the stem | 115-科3 Q40/Q46: "圖中(A)與(B)的函數應填入何者" |

## Annotation anchoring

DOM paths and character offsets both break on any edit, so neither is used. Text-quote
anchoring instead:

1. markdown-it exposes `token.map` per top-level block; a renderer rule stamps `data-line`.
2. An Annotation stores `{fid, block_line, exact, prefix(32), suffix(32)}` — on any Material
   File, Course prose or Question stem alike.
3. Restore order: the block at `data-line` searched for `prefix + exact + suffix`; then `exact`
   within that block; then `exact` anywhere in the file; otherwise it becomes an **Orphan**.
4. Orphan status is decided by the client (it owns the rendered DOM) and persisted via
   `PATCH /api/annotation/<id>`, so portal counts and `check` agree with what the reader saw.
5. Orphans are listed in the reader sidebar with their quoted text, to re-anchor or delete.

This fails visibly rather than silently: rewritten text orphans its Annotations, and the UI
says so.

## Sitting a Paper

**Composition.** Six fields, in this fixed order (`ui-design-principles` 2 locks field order),
with these defaults:

| Field | Default | Note |
|---|---|---|
| Subject | all | |
| Bank | all 11 | includes the 7 guide practice regions alongside the 4 exam papers |
| Question cap | 50 | the official paper size |
| Shuffle | on | Questions only — see below |
| Timed | on | 108 s per Question |
| Include defective | off | ADR 0004 |

Drill is not a field on this form: it is a separate portal entry point, because "Starred only,
untimed" is a different thing to compose, and folding it in would allow self-contradicting
combinations. Criteria and the resulting `qkeys` are stored as a `paper` row, so an Attempt is
reproducible and two Attempts of one Paper are comparable.

**Shuffle covers Questions, never options.** Shuffled options would put the UI's letters out of
step with the Markdown, and would invalidate all 70 official Explanations, which name their
answer as `Ans（B）`. The accepted cost is that repeated Drills teach the position of an answer
as well as its content; losing the official Explanations would cost more.

**Timing.** A Paper is timed at the official rate — 90 minutes per 50 Questions, i.e. 108 s per
Question, scaled to the Paper's size (20 Questions → 36 minutes) so the pacing pressure is real
rather than decorative. `limit_ms` can be switched off; Drills are always untimed. The countdown
is **wall-clock**: closing the tab does not pause the exam, because the exam hall does not.
Remaining time is always computed as `limit_ms - (now - started)`, never accumulated from frame
deltas, so a throttled or backgrounded tab cannot gain the candidate time. Reaching zero
auto-submits.

**Resumption.** At most one Attempt per Paper is in flight; the portal shows it as a
「進行中」 card. Each answer is `PUT` as it is given, so nothing is lost. Reopening after the
limit has already elapsed submits what was answered and sets `expired`.

**Grading.** Submission grades the whole Paper (mock-exam semantics, no feedback while
sitting), writes `attempt` and `attempt_item`, reports `score = correct / total × 100` against
the official 60-point pass line, and runs the Star lifecycle:

- a wrong answer sets `star(qkey, 'wrong')` if no Star exists;
- a correct answer clears a `'wrong'` Star **only if the previous Attempt of that Question was
  also correct** — two consecutive corrects, computed from `attempt_item` history, no streak
  column;
- `'manual'` Stars are never cleared automatically.

Without the clearing rule the Starred set only grows and Drill mode degenerates into the full
corpus; with a one-correct rule a 25% guess would clear it.

**Result view** lists every wrong Question with its correct option, its Explanation (official or
authored, attribution shown), and the human's Note field; each Question has a Star toggle.

## Web surface

Four pages sharing one `api.js` and one `strings.js` string catalogue (externalised from day
one — `ui-design-principles` 22; the UI is zh-TW, but the strings live in one place, not inline).
Markdown renders client-side (vendored markdown-it): required anyway, because Annotation
anchoring operates on the rendered DOM, and server-rendering would split that logic across two
languages.

Rendering the largest Material File in one pass is measured, not assumed — headless Chromium,
vendored markdown-it, with the `data-line` stamping rule active:

| File | Blocks | DOM nodes | parse | render | innerHTML | layout | total |
|---|---|---|---|---|---|---|---|
| 學習指引 科3 (292 KB, cold) | 1330 | 3777 | 14.7 ms | 1.7 ms | 3.4 ms | 62.6 ms | **82.4 ms** |
| 學習指引 科3 (warm) | 1330 | 3777 | 3.4 ms | 0.5 ms | 3.2 ms | 18.7 ms | **25.8 ms** |
| cheatsheet L23 (115 KB) | 425 | 3482 | 3.1 ms | 0.7 ms | 3.7 ms | 12.8 ms | **20.3 ms** |

Restoring 200 Annotations by the naive scan (200 quotes × 1330 blocks) costs **17.6 ms**. So
there is no chunked rendering, no virtualised TOC, no `content-visibility`, and no anchor index:
the whole file renders at once and the dumbest anchoring loop is fast enough.

**Portal (`index.html`)** — catalogue joined against user state: Subjects, then Course cards
(Progress bar = ticked leaf Sections / leaf Sections, Annotation count, Orphan count) and Bank
cards (Question count, Defect count, Star count, latest score), plus an in-flight Attempt card,
and entry points for a new Paper, a Drill, and statistics.

**Reader (`reader.html`)** — opens any Material File. TOC with per-leaf-Section read ticks;
selection toolbar for a 4-colour Highlight or a Note; Annotation list with an Orphan section;
resume position; `?p=&path=&q=` deep-links scroll to the target and flash the term.

**Exam (`exam.html`)** — composition form, one Question at a time with a countdown and a
Question map, submit, result view.

**Statistics (`stats.html`)** — five panels, ordered by what a candidate actually needs to
decide: (1) score over time per Subject with the 60-point line; (2) pace — mean seconds per
Question against the official 108 s; (3) most-missed Questions, top 20, linking to each
Question; (4) per-Bank latest / best / attempts; (5) Star and Defect counts over time, where the
Defect series doubles as content-repair progress.

**Lookup (3.4)** — selecting text raises 「查課程」 and returns two tabs: **課程** (Course
Sections) and **考古題** (Questions in Banks, excluding the current one — "how has this concept
been asked before?"). Literal substring only (constraint 4, plus the CJK tokeniser finding),
NFKC-folded. If the selection yields nothing, the query is shortened from the right down to a
floor of 4 characters, and the popup **states the query it actually used** rather than implying
the selection matched. A hit inside a table row returns that row plus the table's header row,
never a mid-row cut.

**Keyboard contract** (`ui-design-principles` 5, 11, 12, 14): every page has a persistent
key-hint footer; `Esc` peels exactly one layer (popup → panel → page); `Enter` confirms; arrows
and PgUp/PgDn/Home/End scroll every overflowing surface including the Annotation list and the
Lookup popup; in the exam, `1`–`4`/`A`–`D` select an option, `Space` cycles options, `←`/`→`
move between Questions, and the focused Question is always visibly unique.

**Chrome and install** (`ui-design-principles` 18, 23; ADR 0008): a header carrying the app name
and a build-stamped version, one switchable Help/About panel single-sourced from the same
metadata, and a web manifest with `standalone` display so the site installs as its own window.
**No service worker** — the deviation and its reasoning are recorded in ADR 0008, because the
absence otherwise reads as an oversight.

**Layout** (`ui-design-principles` 19): fluid and resize-aware — no hardcoded widths, the
reader's TOC/content/annotation columns collapse to fewer columns as width shrinks, and popups
obey responsive size caps. Target host is a desktop browser on the machine running `serve`;
touch hosts are out of scope while the server binds 127.0.0.1 only, and would be a shared
component with per-host adaptation rather than media-query bolt-ons if that ever changes
(principle 2).

## CLI

| Subcommand | Behaviour |
|---|---|
| `init <root>` | register the root in `~/.config/wens-tutor/roots.json`, create `.tutor/tutor.db` |
| `check [--root]` | the format/consistency gate; **exit 0 clean, 1 findings in the content, 2 usage or I/O failure** — the agent must be able to tell "the material needs repair" from "the tool is broken" |
| `relink <old-relpath> <new-relpath>` | resolve a reconciliation the startup heuristic refused to guess |
| `new course <subject> <title>` | write a Course skeleton into the Subject folder |
| `new bank <subject> <title> [--questions N] [--shape exam\|guide]` | write a Bank skeleton in the chosen parseable shape |
| `serve [--root] [--port] [--open]` | bind 127.0.0.1 only; three route families |
| `stats [--root]` | the same five panels as text, for terminal and agent use |
| `export [--root]` | write all user state to `.tutor/tutor.json` — diffable, mergeable, committed (ADR 0009) |
| `import [--root] [--merge]` | rebuild the database from `tutor.json`; `--merge` unions two devices' rows instead of replacing |

`check` findings: Defects by kind and Question; files holding a `第 N 題` heading that parse to
zero Questions; Questions whose option count is not 4; a `選擇題` region with no sibling
`解答與解析`, or a count mismatch between them; relinked and unresolvable `qkey`s; read-ticks
whose Section path is gone; Orphan Annotations; registered-but-missing roots; a `tutor.json`
older than the newest row in `tutor.db` (ADR 0009).

`serve` runs as a supervised long-lived process (`hub` with a port readiness check), reports
`http://127.0.0.1:<port>/`, and does not block the session that started it.

## Agent workflows (requirement 1)

No crawler is written. `SKILL.md` drives three content jobs, all judgement work:

1. **Backfill a `no_answer` Defect** — read the issuing body's published answer key with the
   agent's own `read`, write `**答案：X**`, re-run `check`. First target: the 3 Questions in
   114-科1.
2. **Backfill a `figure_missing` Defect** — the authoritative source is local: the original PDF
   sits in `source/` beside the Markdown. Transcribe a code listing into a fenced block, a table
   into a Markdown table; for a genuine diagram, describe it and say that it is a description.
   Re-run `check` and watch the Defect count fall. 23 Questions, most of them the Python
   code-reading type.
3. **Author an Explanation** — on request, for Questions answered wrong in an exam-paper Bank,
   with the AI-generated attribution (ADR 0005), imitating the register of the 70 official
   Explanations in the guides.

Importing new material from the web follows the same shape: fetch with `read`, convert to the
formats above, write into the Materials Root, run `check`. This avoids maintaining an
HTML→Markdown converter under a stdlib-only constraint, avoids robots and licensing exposure,
and produces better output because the judgement is done by the component capable of judgement.

**Hard rule for `SKILL.md`:** the engine never writes to a Material File, and the agent writes
to one only in these three workflows, only when asked, and only after checking the materials
repo's git state (per `~/.claude/CLAUDE.md`). Before any commit of the Materials Root, run
`export` so the JSON recovery/merge artifact matches the database (ADR 0009).

**Triggers:** 複習 / 開始讀書 / 模擬考 / 出卷 / 重點題 / 複習進度 / 補答案 / 補圖, plus their
English equivalents (review, mock exam, drill, study progress).

## Verification

1. `tests/test_parser.py` against the eight real Material Files:
   - 270 Questions in 11 Banks; 4 options each; 200 from `exam` shape, 70 from `guide` shape;
   - 3 `no_answer`, 23 `figure_missing`, all 26 inside exam papers, zero in the guides;
   - 70 Explanations parsed with `origin='official'`;
   - the two cheatsheets parse to zero Questions (strict-pattern regression);
   - zero Section-path collisions across all eight files;
   - `qkey` stable across two consecutive parses.
2. `tests/test_rules.py` — the five rules that fail silently rather than crashing, tested at the
   pure-function layer (`compose.py`, `state.py`), never through HTTP:
   - the Star lifecycle: wrong → Star; correct → Star holds; correct again → Star clears; a
     `manual` Star survives all three;
   - `qkey` stability, and relink by `(bkey, ordinal)` after a stem edit;
   - composition excludes Defects, and includes them when asked;
   - an Attempt reopened past its limit submits what was answered and sets `expired`;
   - Lookup's right-shortening stops at 4 characters and reports the query it used.
   No tests are written for the HTTP layer: its logic is path containment plus JSON
   serialisation, and the smoke run covers it.
3. End-to-end smoke on the real Materials Root, not a fixture:
   - highlight a passage, restart `serve`, confirm it restores; highlight a Question stem too;
   - rename a Material File, restart, confirm Stars, Notes and Attempt history follow it;
   - answer one Question wrong, confirm the Star appears; answer it right twice, confirm it
     clears; a `manual` Star survives both;
   - confirm a Drill contains exactly the Starred Questions and no defective one;
   - confirm a 20-Question Paper counts down 36 minutes, survives a browser restart mid-Attempt
     with the countdown still falling, and auto-submits at zero;
   - select a phrase in a Question, confirm the 課程 tab lists a matching 學習指引 Section, the
     考古題 tab lists other Questions on the same concept, and the new window scrolls to it;
   - tick a leaf Section, confirm the portal's Progress bar moves by exactly 1/57 for 科目1;
   - `export`, delete the database, `import`, confirm every Star, Annotation, Note and Attempt
     returns byte-identical (ADR 0009).
4. `check` exits 1 on the current corpus (26 Defects) and 0 once they are Backfilled; exits 2
   for an unregistered root — the three-level contract is proven, not assumed.

## Decisions

| Decision | Alternative rejected | Why |
|---|---|---|
| Two static roots in one stdlib server | symlink the engine into the material tree; copy either side | constraint 2 forbids symlinks; copying duplicates the source of truth |
| Content sniffing for Course/Bank | `courses/`/`banks/` folders | constraint 1 forbids reorganising; strict-pattern sniffing is exact |
| Substring scan | FTS5, embeddings | FTS5 cannot tokenise CJK here; a scan is 0.33 ms; embeddings forbidden |
| Client-side markdown-it | server-side rendering | anchoring runs on the rendered DOM; one language per concern |
| Text-quote anchoring | DOM paths, character offsets | survives edits; fails visibly as an Orphan |
| User-state-only database, catalogue in memory (ADR 0001) | one combined database; state + gitignored cache | deletes the `index` command, the cache, its invalidation, and a 1 MB binary blob per commit |
| Content-addressed Question identity (ADR 0002) | path keys; hash-only keys | the Materials Root has already done a mass rename; OCR typo fixes must not cost review history |
| Device-local registry (ADR 0003) | committed `config.json`; walk up from cwd | an absolute path inside a synced repo is wrong on the second device; agent sessions run outside the root |
| Defects excluded by default (ADR 0004) | catalogue everything | 23 of 200 exam Questions silently lack their figure; most are the Python code-reading type |
| Explanations in content, Notes in state (ADR 0005) | both in the database | Explanations must be Lookup-able, diffable, synced; Notes are private |
| Bank is a region (ADR 0006) | ignore the guides' practice Questions; extract them to new files | +70 defect-free Questions and the only 70 official Explanations, without duplicating official content |
| Ancestor-path Section identity (ADR 0007) | counter-deduplicated slugs | one heading repeats 12 times; a counter moves read-ticks when a chapter is inserted |
| Official timing, wall-clock, auto-submit | untimed; decorative timer; active-time-only clock | 1.8 min/Question is a real source of lost marks; a pausable clock trains a habit the exam hall does not allow |
| Two consecutive corrects clears a `wrong` Star | manual-only; one correct | manual-only makes the Starred set grow forever; one correct is inside guessing range |
| Lookup shortens the query and says so | fail with zero hits; silent truncation | a 100-character selection can never match literally, and a silent truncation misrepresents what was searched |
| `check` exits 0/1/2 | 0/1 | the agent must distinguish "repair the content" from "the tool is broken" |
| Derived statistics | aggregate columns | no second copy of the truth |
| Agent-driven Backfill | an `import-url` subcommand | no HTML→Markdown converter to maintain; the figure sources are local PDFs anyway |
| Installable, no service worker (ADR 0008) | full offline-first PWA | the data lives behind the local server; an offline shell would load a UI with no content and no way to persist an answer |
| Externalised strings, one language | inline zh-TW strings | one `strings.js` costs nothing now and is a rewrite later (`ui-design-principles` 22) |
| JSON export beside the database (ADR 0009) | the binary database alone | git cannot merge SQLite: two devices would discard one side's Attempts, and a corrupt file would lose everything |
| Shuffle Questions, never options | shuffle both | shuffled options invalidate all 70 official Explanations, which name their answer as `Ans（B）` |
| Composition defaults: 50 Questions, all Banks, shuffled, timed, defects off | ask every time; remember the last Paper | the default is the official paper shape, so the common case is one click |
| Rules tested at the pure-function layer; HTTP smoke-tested only | full HTTP test suite | the five rules fail silently, so they need assertions; the HTTP layer is path containment plus JSON |
| Remaining time from `started`, never accumulated | tick-based countdown | a backgrounded tab is throttled, so accumulation hands the candidate free time |
