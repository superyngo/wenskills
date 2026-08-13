# wens-tutor skill — design

Domain vocabulary: [`skills/wens-tutor/CONTEXT.md`](../../../skills/wens-tutor/CONTEXT.md).
Decisions: [`skills/wens-tutor/docs/adr/`](../../../skills/wens-tutor/docs/adr/).
Terms defined there (Materials Root, Subject, Course, Bank, Section, Question, Defect,
Paper, Attempt, Drill, Star, Annotation, Orphan, Progress, Lookup, Backfill, Explanation)
are used here with exactly those meanings.

## Problem

The user is preparing for the 2026 iPAS 中級 AI 應用規劃師 certification. The material lives
as Markdown in a private repo, `superyngo/ipas-ai-planner-2026`, mounted as a git submodule
of the wenswiki vault at `~/repos/wenswiki/wenswiki/work/平台/2026_AI應用規劃師`. Today that
material is inert text: there is no way to

- see Progress across Subjects,
- annotate while reading and have the marks survive a restart,
- sit a Paper under exam conditions, keep per-Attempt statistics, and Drill the Questions
  that were answered wrong,
- while sitting a Paper, jump from a phrase in a Question to the Course Section that
  explains it.

The requirement is unusual in shape: the content is static files curated by a human and an
agent, but the site over it must be generated from a database of user state. Neither a
static-site generator nor a conventional web app fits cleanly.

## Scope

One skill, `skills/wens-tutor/`, containing both the agent-facing workflow (`SKILL.md`) and
the rendering engine (`scripts/`, `web/`). It operates on any registered Materials Root; the
iPAS repo is the first one, not a hardcoded target.

In scope: the catalogue, a portal, a reader with persistent Annotations, timed Papers with
per-Attempt statistics, Stars and Drills, Lookup, Defect detection, and the agent workflows
for Backfill and Explanation authoring.

Out of scope, decided explicitly:

- 考點代碼 (L21101…) level statistics — the Banks carry no such markers, so any mapping
  would be invented.
- Multi-user, authentication, remote hosting, cloud sync.
- Embedding or vector retrieval (also forbidden by the vault's `CLAUDE.md` §6).
- Inferring Progress from scroll position — Progress is ticked by hand.
- Non-multiple-choice Question types.
- A crawler.

## Ground truth (measured 2026-08-13)

Corpus, after strict Bank detection (`^###\s*第\s*\d+\s*題\s*$` — the loose form `### 第`
matches 58 chapter headings in the cheatsheets and misclassifies them as Banks):

| Path relative to the Materials Root | Kind | Facts |
|---|---|---|
| `AI應用規劃師/AI應用規劃師(中級)-學習指引-科目1…_20251222101833.md` | Course | 73 headings, 274 KB |
| `AI應用規劃師/ipas_ai_planner_L21_cheatsheet.md` | Course | 136 headings, 636 table rows |
| `AI應用規劃師/114年第二梯次…第一科…_20251226000616.md` | Bank | 50 Q, 3 `no_answer`, 2 `figure_missing` |
| `AI應用規劃師/115年第一次…第一科…_20260615003359.md` | Bank | 50 Q, 2 `figure_missing`, 1 fenced stem |
| `機器學習/AI應用規劃師(中級)-學習指引-科目3…_20251222101907.md` | Course | 89 headings, 286 KB |
| `機器學習/ipas_ai_planner_L23_cheatsheet.md` | Course | 160 headings |
| `機器學習/114年第二梯次…第三科…_20251226000650.md` | Bank | 50 Q, 10 `figure_missing`, 1 fenced stem |
| `機器學習/115年第一次…第三科…_20260615003428.md` | Bank | 50 Q, 9 `figure_missing` |

Totals: **200 Questions, all single-answer, exactly 4 options each, 3 `no_answer`,
23 `figure_missing` (11.5%), zero images anywhere in the corpus.** Text is 660 KB.
`README.md` and the `source/` folders (the original PDFs) are not catalogued.

Exam facts (ipas.org.tw 115年度簡章; ipd.nat.gov.tw 考試資訊): **90 minutes, 50 Questions
per subject, computer-based; a subject scores ≥60 to pass and the two-subject average must
reach 70.** From 114年第二梯次 onward the 機器學習 subject includes roughly 25% Python
code-reading Questions — which is exactly where the `figure_missing` Defects cluster.

Repo facts: `wenskills` is clean and in sync with `origin/main`. The vault is 12 commits
ahead of origin with a large uncommitted migration in flight, so **nothing outside the
`ipas-ai-planner-2026` submodule is touched**; that submodule is clean and in sync. Its
four-commit history already contains a mass rename (six PDFs moved into `source/`), which is
the evidence behind ADR 0002.

## Constraints

From `~/repos/wenswiki/CLAUDE.md`, authoritative for anything under the vault:

| # | Rule | § | Consequence |
|---|---|---|---|
| 1 | Filenames are Notion page titles verbatim; no renaming, flattening, normalising | 2 | Course/Bank classification cannot be a folder layout; it is sniffed from content |
| 2 | **No symlinks anywhere in the vault** | 2 | The engine cannot be linked into the material tree; two static roots in one server is the only option |
| 3 | Never scan the whole vault; every operation needs an explicit path scope | 2 | The tooling only ever walks a registered Materials Root |
| 4 | No vector indexes or embedding databases | 6 | Lookup is literal substring matching |
| 5 | Do not `git push` the vault repo | 6 | Only the `ipas-ai-planner-2026` submodule is pushed, and only when asked |

Measured technical constraints:

| Finding | Evidence | Consequence |
|---|---|---|
| SQLite FTS5 cannot tokenise CJK usefully | sqlite 3.51.0: `unicode61` and `trigram` both return 0 rows for `MATCH '語言'` against `'自然語言處理技術與應用'` | No FTS5 table; Lookup is a plain scan |
| A whole-corpus scan is free | 0.33 ms over all 660 KB | No index needed for Lookup |
| Bank/Course sniffing is unambiguous | strict heading pattern: 4 files match, 4 do not, 0 errors | No override list |
| Stems are real Markdown | fenced code in 115-科1 Q16 and 114-科3 Q41; bold labels; bullet lists | Stems render through markdown-it; the option scanner must skip fenced regions |

## Architecture

Three layers, one seam each. The seam that matters: **the agent owns content (a judgement
task); the scripts own presentation (a deterministic task).**

```
skills/wens-tutor/                  the engine, in the wenskills repo
  SKILL.md                          agent workflow + triggers
  CONTEXT.md                        domain glossary
  docs/adr/0001…0005                decisions
  references/material-format.md     Bank/Course conventions, parser tolerances, Defect rules
  references/db-schema.md           user-state schema + key-stability rationale
  scripts/tutor.py                  CLI: arg parsing and dispatch only
  scripts/tutorlib/parser.py        pure: Markdown -> Sections, Questions, Defects
  scripts/tutorlib/catalog.py       walk a root, sniff kinds, build the in-memory catalogue
  scripts/tutorlib/state.py         user-state DDL, connection, fid/qkey reconciliation
  scripts/tutorlib/compose.py       Paper composition, grading, Star lifecycle
  scripts/tutorlib/server.py        ThreadingHTTPServer, routes, path containment
  scripts/tutorlib/api.py           JSON endpoints
  web/index.html web/reader.html web/exam.html
  web/app/*.js  web/style.css
  web/vendor/markdown-it.min.js     vendored; no npm, no build step
  tests/test_parser.py

~/.config/wens-tutor/roots.json     device-local registry: roots, default root, port

<Materials Root>/                   the content, in the ipas-ai-planner-2026 repo
  <Subject>/*.md                    never modified by the engine, only by the agent/human
  .tutor/tutor.db                   user state only (ADR 0001), committed
```

Python is stdlib-only, so any interpreter ≥3.9 runs it; the skill invokes it as
`uv run --python 3.14 python3 scripts/tutor.py …` per this repo's CLAUDE.md (3.14.3 is
installed).

### The path problem (requirement 3.2)

One process, two static roots:

| Route | Served from | Notes |
|---|---|---|
| `/`, `/reader`, `/exam`, `/app/*`, `/vendor/*`, `/style.css` | the skill's `web/` | engine source stays inside the skill (3.1) |
| `/raw/<relpath>` | the Materials Root | `.md` only; `realpath` + `commonpath` containment; symlinks refused |
| `/api/*` | the catalogue + `tutor.db` | JSON |

This replaces symlinking, copying the engine into the material tree, or copying material
into the skill — the first violates constraint 2, the others duplicate the source of truth.

### Catalogue (ADR 0001)

Every process start walks the Materials Root, parses it, and inserts the result into an
in-memory database attached as `cat`:

```sql
cat.file(fid, relpath, kind, subject, title, sha256, n_sections, n_questions)
cat.section(fid, slug, level, title, line_start, line_end, text)
cat.question(qkey, fid, ordinal, type, stem_md, options_json, answer, explanation_md)
cat.defect(qkey, kind)                              -- 'no_answer' | 'figure_missing'
```

`main` is the user-state database; joins across `main` and `cat` are ordinary SQLite. There
is no `index` command, no cache file, and no staleness: the catalogue cannot disagree with
the Markdown because it is rebuilt from it.

The server holds one connection (`check_same_thread=False`) behind a single lock rather than
one connection per thread, because the catalogue lives on that connection. Single user,
millisecond queries — contention is not a concern.

## Identity and user state (ADR 0002)

```sql
-- main: user state, never rebuilt, committed to the Materials Root
file_id(fid PK, relpath, first_seen, fingerprint)   -- fingerprint: sorted section slugs / stem hashes
annotation(id PK, fid, block_line, exact, prefix, suffix, color, note_md, ts, orphan)
progress(fid, slug, read_at, PRIMARY KEY(fid, slug))
reading_pos(fid PK, line, ts)
star(qkey PK, origin, ts)                            -- origin: 'wrong' | 'manual'
paper(id PK, criteria_json, qkeys_json, created)
attempt(id PK, paper_id, started, finished, limit_ms, elapsed_ms, total, correct)
attempt_item(attempt_id, qkey, given, correct, ms, PRIMARY KEY(attempt_id, qkey))
```

- **`qkey = sha256(NFKC(stem) + NFKC(options))[:12]`** — identity follows the Question text,
  so renaming or moving a Bank costs nothing.
- **`fid`** is minted on first sight and reconciled at every startup: exact `relpath` match
  first; then, for a vanished path, a `fingerprint` match (Jaccard ≥ 0.6 over Section slugs
  for a Course, over stem hashes for a Bank) when exactly one candidate qualifies. Anything
  ambiguous is left alone and reported for an explicit `relink`.
- **Stem edits** (fixing OCR typos is frequent in this corpus) change `qkey`. Startup
  relinks orphaned keys by `(fid, ordinal)` and reports what it relinked.
- Statistics are derived from `attempt`/`attempt_item` at query time. No aggregate columns,
  so there is no second copy of the truth.
- `type` is `single` or `multi`, derived from answer length; the corpus is 200/200 `single`.
  Grading a `multi` Question is exact-set-match, no partial credit.
- The database is committed because the Materials Root exists to sync across devices. SQLite
  is binary, so git cannot merge it: the discipline is pull-before-studying, and a genuine
  two-device conflict is resolved by keeping one side. Journal mode stays at the default, so
  there are no `-wal`/`-shm` sidecars to ignore.

## Material format

**Course**: any Markdown. Sections are cut at ATX headings `#`–`####`. A Section's `text` is
its own body only, up to the next heading of *any* level — nested subsections are separate
Sections — so Lookup cannot return a parent and its child as two hits on the same passage.

**Bank**: the format already used by both generations of published papers, so the parser
adapts to the data rather than the data being rewritten.

```markdown
### 第 12 題

**答案：B**

<stem: one or more Markdown blocks, may include fenced code, bold labels, bullet lists>

(A) …;
(B) …;
(C) …;
(D) …

**解析（AI 生成，未經官方確認）：**

<Explanation prose — optional, authored, never from the published source>
```

Parser tolerances, each driven by a real case in the corpus:

| Tolerance | Real case |
|---|---|
| Bank detection requires `^###\s*第\s*\d+\s*題\s*$` | the loose form matches 58 cheatsheet chapter headings |
| A Question ends at the next `###`/`##` or EOF; `---` separators and `《以下空白》` trailers are dropped | 114年 files separate Questions with `---`, 115年 files do not |
| Everything between the answer line and the first option line is stem, including fenced blocks | 115-科1 Q16 has a bullet list, two bold labels and two fenced blocks |
| The option scanner ignores lines inside fenced regions | same Question — fenced content contains lines that look like prose options |
| Options are `^\(([A-E])\)\s*(.+?);?$` in source order | uniform across all 4 Banks |
| An `**解析…：**` block after the options is an Explanation, not stem and not an option | ADR 0005 |
| Answers parse as `答案[：:]\s*([A-E]+)`; anything else stores `NULL` and a `no_answer` Defect | 3 Questions in 114-科1 hold the placeholder "（來源 PDF 此欄位無法擷取…）" |
| `figure_missing` = the Question references 下圖/上圖/圖中/附圖/如圖/下表/上表/表中/以下程式/下列程式/程式碼中/程式中/如下所示 **and** contains no fenced block, no table row, no image | 23 Questions; 8 say so explicitly (`〔註：…省略。〕`), 15 do not say anything at all |
| Both half-width and full-width punctuation | 115年 uses `,` `?`, 114年 uses `，` `？` |
| Options carrying an inline `(A)` as a *blank marker*, not an option reference, stay in the stem | 115-科3 Q40/Q46: "圖中(A)與(B)的函數應填入何者" |

`tutor.py check` is the format gate: Defects by kind and Question, files that hold a
`第 N 題` heading but parse to zero Questions, Questions whose option count is not 4,
relinked and unresolvable `qkey`s, unregistered/missing roots, and Orphan Annotations.

## Annotation anchoring

DOM paths and character offsets both break on any edit to the Markdown, so neither is used.
Instead, text-quote anchoring:

1. markdown-it exposes `token.map` (source line range) per top-level block; a renderer rule
   stamps `data-line` on each rendered block.
2. An Annotation stores `{fid, block_line, exact, prefix(32), suffix(32)}`.
3. Restore order: the block at `data-line` searched for `prefix + exact + suffix`; then
   `exact` within that block; then `exact` anywhere in the file; otherwise the Annotation
   becomes an **Orphan**.
4. Orphan resolution is decided by the client (it owns the rendered DOM) and persisted with
   a `PATCH /api/annotation/<id>` so the portal's counts and the `check` report agree with
   what the reader actually saw.
5. Orphans are listed in the reader sidebar with their quoted text, so the human can
   re-anchor or delete them.

This fails visibly rather than silently: heavily rewritten Courses orphan their Annotations,
and the UI says so.

## Sitting a Paper

Composition criteria: Subject and/or Bank, question cap, shuffle, and Drill mode (Starred
Questions only). Defective Questions are excluded unless `include_defective` is set
(ADR 0004). The criteria and the resulting `qkeys` are stored as a `paper` row, so an
Attempt is always reproducible and two Attempts of the same Paper are comparable.

**Timing.** A full Paper is timed at the official rate — 90 minutes for 50 Questions, i.e.
108 s per Question, scaled to the Paper's size (20 Questions → 36 minutes) so the pacing
pressure is real rather than decorative. The limit is a Paper property (`limit_ms`), can be
switched off, and Drills are always untimed. Reaching zero auto-submits.

**Answering.** Each answer is `PUT` as it is given, so closing the tab loses nothing.

**Grading.** Submission grades the whole Paper (mock-exam semantics, no per-Question
feedback while sitting), writes `attempt` and `attempt_item`, reports
`score = correct / total × 100` against the official 60-point pass line, and runs the Star
lifecycle:

- a wrong answer sets `star(qkey, 'wrong')` if no Star exists;
- a correct answer clears a `'wrong'` Star **only if the previous Attempt of that Question
  was also correct** (two consecutive corrects), computed from `attempt_item` history — no
  streak column;
- `'manual'` Stars are never cleared automatically; the human toggles them.

Without the clearing rule the Starred set only grows and Drill mode degenerates into the
full corpus; with a one-correct rule a 25% guess would clear it.

**Result view** lists every wrong Question with its correct option, its Explanation if the
Bank has one, and the human's Note field; each Question shows a Star toggle.

## Web surface

Three pages sharing one `api.js`. Markdown renders client-side (vendored markdown-it):
required anyway, because Annotation anchoring operates on the rendered DOM, and
server-rendering would split that logic across two languages.

**Portal (`index.html`)** — generated from the catalogue joined against user state:
Subjects, then Course cards (Progress bar = ticked Sections / total, Annotation count,
Orphan count) and Bank cards (Question count, Defect count, Star count, latest score), plus
entry points for a new Paper, a Drill, and statistics.

**Reader (`reader.html`)** — TOC with per-Section read ticks; selection toolbar for a
4-colour Highlight or a Note; Annotation list with an Orphan section; resume position;
`?p=&slug=&q=` deep-links scroll to the target and flash the term.

**Exam (`exam.html`)** — composition form, one-Question-at-a-time sitting with a countdown
and a Question map, submit, and the result view described above.

**Lookup (3.4)** — selecting text raises 「查課程」; `GET /api/lookup?q=` scans
`cat.section.text` for Course rows only and returns Subject / file title / Section heading /
snippet. Literal substring only — constraint 4 and the CJK tokeniser finding.

## CLI

| Subcommand | Behaviour |
|---|---|
| `init <root>` | register the root in `~/.config/wens-tutor/roots.json`, create `.tutor/tutor.db` |
| `check [--root]` | the format/consistency gate above; non-zero exit on findings |
| `relink <old-relpath> <new-relpath>` | resolve a reconciliation the startup heuristic refused to guess |
| `new course <subject> <title>` | write a Course skeleton into the Subject folder |
| `new bank <subject> <title> [--questions N]` | write a Bank skeleton in the parseable format |
| `serve [--root] [--port] [--open]` | bind 127.0.0.1 only; three routes; blocking |
| `stats [--root]` | Attempt history, accuracy, Star and Defect counts as text |

## Agent workflows (requirement 1)

No crawler is written. `SKILL.md` drives three content jobs, all of which are judgement
work:

1. **Backfill a `no_answer` Defect** — read the issuing body's published answer key (the
   agent's own `read` on a URL), write `**答案：X**` into the Bank, re-run `check`.
2. **Backfill a `figure_missing` Defect** — the authoritative source is local: the original
   PDF sits in `source/` beside the Markdown. Transcribe the code listing into a fenced
   block or the table into a Markdown table; if it is a genuine diagram, describe it in
   prose and say so. Re-run `check` and watch the Defect count fall.
3. **Author an Explanation** — on request, for Questions the human got wrong; written into
   the Bank with the AI-generated attribution (ADR 0005).

Import of new material from the web follows the same shape: the agent fetches with `read`,
converts to the formats above, writes into the Materials Root, then runs `check`. This avoids
maintaining an HTML→Markdown converter under a stdlib-only constraint, avoids robots and
licensing exposure, and produces better output because the judgement is done by the
component capable of judgement.

## Verification

1. `tests/test_parser.py` against the four real Banks: 200 Questions, 4 options each,
   3 `no_answer`, 23 `figure_missing`, zero Questions parsed from the two cheatsheets, and
   `qkey` stability across two consecutive parses.
2. End-to-end smoke on the real Materials Root, not a fixture:
   - highlight a passage, restart `serve`, confirm it restores;
   - rename a Bank file, restart, confirm Stars and Attempt history follow it (ADR 0002);
   - answer one Question wrong, confirm its Star appears, answer it right twice, confirm the
     Star clears; a `manual` Star survives both;
   - confirm a Drill contains exactly the Starred Questions and no defective one;
   - confirm a 20-Question Paper counts down 36 minutes and auto-submits at zero;
   - select a phrase in a Question, confirm the popup lists a matching 學習指引 Section and
     the new window scrolls to it.
3. `check` exits non-zero on the current corpus (26 Defects) and zero once they are
   Backfilled — the gate is proven to gate.

## Decisions

| Decision | Alternative rejected | Why |
|---|---|---|
| Two static roots in one stdlib server | symlink the engine into the material tree; copy either side | constraint 2 forbids symlinks; copying duplicates the source of truth |
| Content sniffing for Course/Bank | `courses/`/`banks/` folders | constraint 1 forbids reorganising; strict-pattern sniffing is 8/8 correct |
| Substring scan | FTS5, embeddings | FTS5 cannot tokenise CJK here; a scan is 0.33 ms; embeddings forbidden |
| Client-side markdown-it | server-side rendering | anchoring runs on the rendered DOM; one language per concern |
| Text-quote anchoring | DOM paths, character offsets | survives edits; fails visibly as an Orphan |
| User-state-only database, catalogue in memory (ADR 0001) | one combined database; state + gitignored cache | deletes the `index` command, the cache, its invalidation, and a 1 MB binary blob per commit |
| Content-addressed identity (ADR 0002) | path keys; hash-only keys | the Materials Root has already done a mass rename; OCR typo fixes must not cost review history |
| Device-local registry (ADR 0003) | committed `config.json`; walk up from cwd | an absolute path inside a synced repo is wrong on the second device; agent sessions run outside the root |
| Defects excluded by default (ADR 0004) | index everything | 23 of 200 Questions silently lack their figure; most are the Python code-reading type |
| Explanations in content, Notes in state (ADR 0005) | both in the database; neither | Explanations must be Lookup-able, diffable and synced; Notes are private |
| Official timing by default | untimed; decorative timer | 1.8 min/Question is a real source of lost marks in a 90-minute computer-based exam |
| Two consecutive corrects clears a `wrong` Star | manual-only; one correct | manual-only makes the Starred set grow forever; one correct is inside guessing range |
| Derived statistics | aggregate columns | no second copy of the truth |
| Agent-driven Backfill | an `import-url` subcommand | no HTML→Markdown converter to maintain; the figure sources are local PDFs anyway |
