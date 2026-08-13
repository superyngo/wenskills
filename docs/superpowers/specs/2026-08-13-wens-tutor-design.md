# wens-tutor skill — design

## Problem

The user is preparing for the 2026 iPAS 中級 AI 應用規劃師 certification. The study
material lives as Markdown in a dedicated private repo,
`superyngo/ipas-ai-planner-2026`, mounted as a git submodule of the wenswiki vault at
`~/repos/wenswiki/wenswiki/work/平台/2026_AI應用規劃師`. Today that material is inert
text: there is no way to

- see study progress across subjects,
- highlight/annotate while reading and have those marks survive a restart,
- sit a mock exam, record per-attempt statistics, and drill only the questions that were
  answered wrong,
- while sitting an exam, jump from a phrase in a question to the place in the course
  material that explains it.

The requirement is unusual in shape: the content is static files authored/curated by an
agent, but the site over it must be generated dynamically from a database of user state.
Neither a pure static-site generator nor a conventional web app fits cleanly.

## Scope

One skill, `skills/wens-tutor/`, containing both the agent-facing workflow (`SKILL.md`)
and the rendering engine (`scripts/`, `web/`). It operates on an arbitrary *materials
root* passed once and remembered; the iPAS repo above is the first such root, not a
hardcoded target.

In scope: material indexing, a portal, a reader with persistent highlights/notes, mock
exams with per-attempt statistics, starred-question ("重點題") tracking and a starred-only
exam mode, and selection-driven lookup from exam into course material.

Out of scope, decided explicitly:

- 考點代碼 (L21101…) level statistics — the exam files carry no such markers, so any
  mapping would be invented.
- Multi-user, authentication, remote hosting, cloud sync.
- Embedding/vector retrieval (also forbidden by the vault's `CLAUDE.md` §6).
- Automatic "已讀" inference from scroll position — replaced by an explicit per-section
  checkbox plus resume-position restore.
- Non-multiple-choice question types (short answer, fill-in-the-blank).
- A crawler. Web import is done by the agent's own `read` tool (see §8).

## Material inventory (measured 2026-08-13, not assumed)

| Path (relative to materials root) | Kind | Facts |
|---|---|---|
| `AI應用規劃師/AI應用規劃師(中級)-學習指引-科目1人工智慧技術應用規劃_20251222101833.md` | course | 73 headings, 274 KB |
| `AI應用規劃師/ipas_ai_planner_L21_cheatsheet.md` | course | 136 headings |
| `AI應用規劃師/114年第二梯次…第一科…_20251226000616.md` | bank | 50 questions, **3 with no answer** |
| `AI應用規劃師/115年第一次…第一科…_20260615003359.md` | bank | 50 questions |
| `機器學習/AI應用規劃師(中級)-學習指引-科目3機器學習技術與應用_20251222101907.md` | course | 89 headings |
| `機器學習/ipas_ai_planner_L23_cheatsheet.md` | course | 160 headings |
| `機器學習/114年第二梯次…第三科…_20251226000650.md` | bank | 50 questions |
| `機器學習/115年第一次…第三科…_20260615003428.md` | bank | 50 questions |

Totals: 200 questions, all single-choice, every question with exactly 4 options `(A)`–`(D)`,
no explanation field. Whole-corpus text is 406 KB. `README.md` at the root and the
`source/` folders (PDF originals) are excluded from indexing.

## Constraints

From `~/repos/wenswiki/CLAUDE.md` (authoritative for anything under the vault):

| # | Rule | Section | Consequence for this design |
|---|---|---|---|
| 1 | Filenames are Notion page titles verbatim; no renaming, flattening, normalising | §2 | Course/bank classification cannot be expressed as folder layout; it is derived from content |
| 2 | **No symlinks anywhere in the vault** | §2 | The engine cannot be linked into the materials tree; a two-static-root server is the only option |
| 3 | Never scan the whole vault; every operation needs an explicit path scope | §2 | `tutor.py` only ever walks the configured materials root |
| 4 | No vector indexes or embedding databases | §6 | Lookup is literal substring matching |
| 5 | Do not `git push` the vault repo | §6 | Only the `ipas-ai-planner-2026` submodule is pushed, and only when the user asks |

Measured technical constraints:

| Finding | Evidence | Consequence |
|---|---|---|
| SQLite FTS5 cannot tokenize CJK usefully | sqlite 3.51.0: `unicode61` and `trigram` both return 0 rows for `MATCH '語言'` against `'自然語言處理技術與應用'` | No FTS5 table |
| Whole-corpus substring scan is free | 0.33 ms to scan all 406 KB in Python | Lookup is a plain scan over `section.text`, ranked in SQL/Python |
| Bank/course detection is unambiguous | `### 第 N 題` present in exactly the 4 bank files, absent in all 4 course files | Content sniffing needs no override list |

State of the two repos at design time: `wenskills` clean and in sync with `origin/main`;
the vault is 12 commits ahead of origin with a large uncommitted migration in flight, so
**no file outside the `ipas-ai-planner-2026` submodule is touched**. That submodule is
clean and in sync.

## Architecture

Three layers with one seam each. The seam that matters: the agent owns content (a
judgement task), the scripts own indexing and serving (a deterministic task).

```
skills/wens-tutor/                        wenskills repo (the engine)
  SKILL.md                                agent workflow
  references/material-format.md           md conventions + parser tolerances
  references/db-schema.md                 schema + key-stability rationale
  scripts/tutor.py                        CLI: arg parsing and dispatch only
  scripts/tutorlib/db.py                  DDL, connection, migration
  scripts/tutorlib/parser.py              pure: md -> sections; md -> questions
  scripts/tutorlib/indexer.py             walk, classify, upsert
  scripts/tutorlib/server.py              ThreadingHTTPServer, routes, path guard
  scripts/tutorlib/api.py                 JSON endpoints over the db
  web/index.html web/reader.html web/exam.html
  web/app/*.js  web/style.css
  web/vendor/markdown-it.min.js           vendored; no npm, no build step
  tests/test_parser.py

<materials root>/                         ipas-ai-planner-2026 repo (the content)
  科目/*.md                                never modified by the renderer
  .tutor/config.json                      root, port
  .tutor/tutor.db                          all indexed facts + all user state
```

Python is stdlib-only, so any interpreter ≥3.9 runs it; the skill invokes it as
`uv run --python 3.14 python3 scripts/tutor.py …` per this repo's CLAUDE.md convention
(3.14.3 is installed).

### The path problem (requirement 3.2)

One process, two static roots:

| Route | Served from | Notes |
|---|---|---|
| `/`, `/reader`, `/exam`, `/app/*`, `/vendor/*`, `/style.css` | the skill's `web/` | engine source stays inside the skill (3.1) |
| `/raw/<relpath>` | the materials root | `.md` only; `realpath` + `commonpath` containment check; symlinks rejected |
| `/api/*` | `.tutor/tutor.db` | JSON |

`tutor.py` discovers `.tutor/` by walking up from the cwd, so every subcommand after
`init` needs no path argument. This replaces symlinking, copying the engine into the
material tree, or copying material into the skill — all of which either violate
constraint 2 or duplicate the source of truth.

## Data model

Invariant: **re-indexing may freely rebuild material facts and must never touch user
state.** User-state tables are therefore keyed on natural stable keys (`relpath`, `slug`,
`qkey`), never on a recyclable rowid.

```sql
-- material facts: DELETE + INSERT on every index run
material(relpath PK, kind, subject, title, sha256, mtime, n_sections, n_questions)
section(relpath, slug, level, title, line_start, line_end, text)
question(qkey PK, relpath, ordinal, type, stem_md, options_json, answer, stem_sha)

-- user state: never deleted by indexing
annotation(id PK, relpath, block_line, exact, prefix, suffix, color, note_md, ts, orphan)
progress(relpath, slug, read_at, PRIMARY KEY(relpath, slug))
reading_pos(relpath PK, line, ts)
star(qkey PK, starred, reason, ts)
attempt(id PK, mode, scope, started, finished, total, correct, ms)
attempt_item(attempt_id, qkey, given, correct, ms, PRIMARY KEY(attempt_id, qkey))
```

- `qkey = '<relpath>#第N題'` — human-readable, debuggable, stable across re-index.
  `stem_sha` detects that a question's text drifted under a stable key; `tutor.py check`
  reports it rather than silently re-keying.
- `answer IS NULL` means the source file has no published answer. Such questions are
  excluded from generated exams and listed by `tutor.py check`.
- `type` is `single` or `multi`, derived from answer length. Current data is 100%
  `single`; multi costs nothing to carry and avoids a schema change later.
- `subject` is the first path segment of `relpath` (`AI應用規劃師`, `機器學習`) — grouping
  follows the human's existing folders, per constraint 1.
- All statistics are derived from `attempt`/`attempt_item` at query time. No aggregate
  columns, so there is no second copy of the truth to drift.
- The DB is committed to the materials repo (owner decision, 2026-08-13) because that
  repo exists to sync across devices. Cost: SQLite is binary, so git cannot merge it —
  the discipline is "pull before studying"; a genuine two-device conflict is resolved by
  picking one side. Journal mode stays at the default (no `-wal`/`-shm` sidecars to
  ignore).

## Material format

Course files: any Markdown. Sections are cut at ATX headings `#`–`####`; each gets a slug
(deduplicated), a title, and `[line_start, line_end)`. `section.text` holds the plain text
of the section body and is what lookup scans.

Bank files: the format already used by both generations of published exam papers, so the
parser adapts to the data rather than the data being rewritten.

```markdown
### 第 12 題

**答案：B**

<stem paragraph, may be several paragraphs>

(A) …;
(B) …;
(C) …;
(D) …
```

Parser tolerances, each driven by a real case in the corpus:

| Tolerance | Real case |
|---|---|
| Question ends at the next `###`/`##` or EOF; `---` separators and `《以下空白》` trailers are dropped | 114年 files separate questions with `---`; 115年 files do not |
| Multi-paragraph stems: everything between the answer line and the first option line is stem | 114年第一科 Q43 has three stem paragraphs |
| Answer parsed as `答案[：:]\s*([A-E]+)`; anything else (including the placeholder "（來源 PDF 此欄位無法擷取…）") stores `NULL` | 3 questions in 114年第一科 |
| Options are lines matching `^\(([A-E])\)\s*(.+?);?$`, kept in source order | uniform across all 4 bank files |
| Both half-width and full-width punctuation accepted | 115年 uses `,` and `?`, 114年 uses `，` and `？` |

`tutor.py check` is the format gate: it reports missing answers, questions whose option
count is not 4, files that parse to zero questions but contain `第 N 題`, drifted
`stem_sha`, and orphaned annotations.

## Annotation anchoring

DOM paths and raw-character offsets both break on any edit to the Markdown, so neither is
used. Instead, text-quote anchoring:

1. markdown-it exposes `token.map` (source line range) for every top-level block; a
   renderer rule stamps `data-line` onto each rendered block element.
2. An annotation stores `{relpath, block_line, exact, prefix(32), suffix(32)}`.
3. Restore order: search the block at `data-line` for `prefix + exact + suffix`; else
   `exact` within that block; else `exact` across the document; else mark `orphan = 1`.
4. Orphans are listed in the reader's sidebar with their quoted text, so the user can
   re-anchor or delete them.

This fails visibly rather than silently: heavily rewritten material orphans its
annotations, and the UI says so.

## Web surface

Three pages, one shared `api.js`. Markdown is rendered client-side (vendored
markdown-it) — required anyway, because highlight anchoring operates on the rendered DOM,
and server-side rendering would split that logic across two languages. A 274 KB document
renders in one pass; no chunking.

**Portal (`index.html`)** — generated from the DB: subjects, then course cards (progress
bar = read sections / total, annotation count) and bank cards (question count, starred
count, latest score), plus entry points for a new exam, starred-only mode, and statistics.

**Reader (`reader.html`)** — TOC with per-section "已讀" checkboxes; selection toolbar for
4-colour highlight and note; annotation list with orphan section; resume position;
`?p=&slug=&q=` deep-links scroll to the target and flash-highlight the term.

**Exam (`exam.html`)** — requirements 3.3–3.6:

- Compose a paper: by bank, across all banks, or **starred-only mode** (3.6); optional
  shuffle and question cap. Questions with `answer IS NULL` are never included.
- Each answer is POSTed as it is given, so closing the tab loses nothing.
- Submit grades the whole paper (mock-exam semantics), writes `attempt` +
  `attempt_item`, and **auto-stars every wrong question** (3.3, 3.5). Auto-starring
  records `reason='wrong'`; a manual toggle sets `reason='manual'`. Default is unstarred.
- Result view lists wrong questions with the correct answer and links to statistics.

**Lookup (3.4)** — selecting text on the exam page raises a "查課程" affordance;
`GET /api/lookup?q=` scans `section.text` for `kind='course'` rows only and returns
subject / file title / section heading / snippet, ranked by match count then heading
depth. Clicking a result `window.open`s the reader deep-link in a new window. Matching is
literal substring only — not semantic — because of constraints 4 and the CJK tokenizer
finding.

## CLI

| Subcommand | Behaviour |
|---|---|
| `init <root>` | create `.tutor/`, write `config.json`, create the schema |
| `index` | walk the root, classify, parse, rebuild material facts, leave user state intact |
| `check` | the format/consistency gate described above; non-zero exit on any finding |
| `new course <subject> <title>` | write a course skeleton md into the subject folder |
| `new bank <subject> <title> [--questions N]` | write a bank skeleton in the parseable format |
| `serve [--port 8765] [--open]` | bind 127.0.0.1 only; serves the three routes |
| `stats` | attempt history and accuracy as text, for use from the terminal/agent |

## Web import (requirement 1)

No crawler is written. `SKILL.md` instructs the agent to fetch a URL with its own `read`
tool, convert the content into the formats above, write it into the materials repo, then
run `index` and `check`. This avoids an HTML→Markdown converter (the largest cost in a
stdlib-only design), avoids robots/licensing exposure, and produces better output because
a judgement task is done by the component capable of judgement.

Its first real use is the 3 unanswered questions in 114年第一科: `check` lists them, and
the user has chosen to look up the official published answers after the implementation
lands.

## Verification

1. `tests/test_parser.py` asserts against the four real bank files: 200 questions total,
   every question exactly 4 options, exactly 3 questions with `answer IS NULL`, and stable
   `qkey`s across two consecutive parses.
2. End-to-end smoke on the real materials root, not a fixture:
   - start `serve`, highlight a passage, restart, confirm the highlight restores;
   - answer one question wrong, confirm its star lights up automatically, then confirm
     starred-only mode produces a paper containing exactly the starred questions;
   - select a phrase on the exam page, confirm the popup lists a matching 學習指引 section
     and that the new window scrolls to it;
   - re-run `index` and confirm annotations, stars, progress, and attempts all survive.
3. `check` exits non-zero on the current corpus (3 missing answers) and zero once they are
   filled — the gate is proven to actually gate.

## Decisions

| Decision | Alternative rejected | Why |
|---|---|---|
| Two static roots in one stdlib server | symlink the engine into the materials tree; copy either side | vault constraint 2 forbids symlinks; copying duplicates the source of truth |
| Content sniffing for course/bank | `courses/`/`banks/` folders | vault constraint 1 forbids reorganising; sniffing is 8/8 correct on real data |
| Substring scan | SQLite FTS5, embeddings | FTS5 cannot tokenize CJK here; scan is 0.33 ms; embeddings forbidden by constraint 4 |
| Client-side markdown-it | server-side Markdown rendering | anchoring runs on the rendered DOM; one language for one concern |
| Text-quote anchoring | DOM path or character offsets | survives edits; fails visibly as `orphan` instead of silently |
| Natural keys for user state | rowid foreign keys | lets `index` rebuild facts destructively without risking user data |
| Derived statistics | aggregate columns on `attempt` | no second copy of the truth |
| Commit the DB | gitignore it | the materials repo exists for cross-device sync (its README says so); cost is manual conflict resolution, accepted by the owner |
| Agent-driven web import | `import-url` subcommand | no HTML→md converter to maintain; better output; no robots exposure |
