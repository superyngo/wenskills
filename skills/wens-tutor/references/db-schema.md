# Database schema

Two SQLite schemas attached on one connection: `main` is user state, committed and never
rebuilt; `cat` is content fact, rebuilt in memory from the Markdown at every process start
(ADR 0001). There is no `index` command, no cache file, and no staleness between `cat` and the
Materials Root — the catalogue cannot disagree with the files it was just parsed from. Joins
across `main` and `cat` are ordinary SQLite.

## `main` — user state

```sql
file_id(fid PK, relpath, first_seen, fingerprint)
question_slot(qkey PK, bkey, ordinal, ts)                    -- written on every parse
annotation(id PK, fid, block_line, exact, prefix, suffix, color, note_md, ts, orphan)
progress(fid, path, read_at, PRIMARY KEY(fid, path))          -- leaf Sections only
reading_pos(fid PK, line, ts)
star(qkey PK, origin, ts)                                     -- 'wrong' | 'manual'
note(qkey PK, note_md, ts)                                    -- private, per Question
paper(id PK, criteria_json, qkeys_json, limit_ms, created)
attempt(id PK, paper_id, started, finished, elapsed_ms, total, correct, expired)
attempt_item(attempt_id, qkey, given, correct, ms, PRIMARY KEY(attempt_id, qkey))
```

Lives at `<root>/.tutor/tutor.db`, committed to the Materials Root: the root exists to sync
study state across devices, and SQLite is binary, so git can only pick one side of a two-device
conflict. The discipline is pull-before-studying; see the export/import contract below for the
mergeable fallback.

Statistics (`compose.stats`) derive from `attempt`/`attempt_item` at query time — there are no
aggregate columns, so there is no second copy of the truth to drift.

## `cat` — content, rebuilt every start

```sql
cat.file(fid, relpath, subject, title, sha256, n_sections, n_questions)
cat.section(fid, path, level, title, is_leaf, line_start, line_end, text)
cat.bank(bkey PK, fid, path, title, shape)                     -- shape: 'exam' | 'guide'
cat.question(qkey PK, bkey, ordinal, type, stem_md, options_json, answer,
             explanation_md, explanation_origin,               -- origin: 'official' | 'authored' | NULL
             shared_span, declared_defect)
cat.defect(qkey, kind)                                          -- 'no_answer' | 'figure_missing' | 'unattributed_lines'
```

`bkey = fid + ":" + path`, where `path` is the Bank's Section ancestor path — Bank identity
survives edits elsewhere in the file. `type` is `single` or `multi`, derived from answer
length; the corpus is 270/270 `single`, so grading a `multi` Question (exact-set-match, no
partial credit) is exercised only by the test fixtures, never by the real corpus today.

The server holds one connection (`check_same_thread=False`) behind a single lock rather than
one per thread, because the catalogue lives on that connection and is single-user,
millisecond-query work — there is no concurrency to buy with a pool.

## Why keys are natural, not surrogate (ADR 0002, ADR 0007)

Every user-state foreign key is content- or path-derived, never a rowid, a relpath, or an
occurrence counter:

- **`qkey = sha256(NFKC(stem_md) + NFKC(options))[:12]`.** A Question's identity follows its
  text, so renaming or moving the file that holds it costs nothing — Stars, Attempts,
  Annotations and Notes all key on `qkey`. The Materials Root's own history (a four-commit mass
  rename of six source PDFs into `source/`) is what proved a path-keyed design would have
  silently dropped every Star and Annotation on that commit.

  Folding a Shared Stem (ADR 0011) runs *before* `qkey_for`, so a folded Question's identity
  covers its shared preamble — editing the shared text changes 2–4 `qkey`s at once, in bulk,
  which is exactly the case the Slot mechanism below exists for.

  Editing a stem to fix an OCR typo — a frequent, expected edit in PDF-derived material — also
  changes `qkey`. The **Slot** record, `question_slot(qkey, bkey, ordinal, ts)`, is written at
  every parse and remembers where each `qkey` last sat; `state.reconcile` relinks an orphaned
  key to whatever `qkey` now occupies that same `(bkey, ordinal)` coordinate, and reports the
  relink. Ambiguous cases (the target slot is already taken) are reported as `unresolved`
  instead of guessed, because the only fallback without a Slot record — "exactly one free slot
  in the Bank" — resolves in a one-Question fixture and fails at 270.

- **`fid`** is minted on first sight and reconciled at every startup: exact `relpath` match
  first, then, for a vanished path, a `fingerprint` match (Jaccard ≥ 0.6 over Section paths for
  prose files, over stem hashes for Bank files) when exactly one candidate qualifies. Ambiguity
  is reported for an explicit `tutor.py relink <old> <new>`, never guessed.

- **Section identity is the ancestor path** of its heading chain
  (`第三章-ai相關技術應用/3-1-自然語言處理技術與應用/1-前言與章節導覽`), not a slug with an
  occurrence counter. Heading text repeats heavily in this corpus (`1. 前言與章節導覽` occurs
  9–12 times per guide; `選擇題`/`解答與解析` 3–4 times); a counter-based identity would
  renumber every later duplicate whenever a chapter is inserted, silently moving read-ticks
  onto the wrong Section. This is accepted to be less forgiving than `fid` reconciliation: a
  Section rename is **not** relinked, and `check` reports `stale_progress` for a read-tick
  whose Section path no longer resolves — renaming a heading in an official published document
  is rare enough that automatic reconciliation isn't worth the risk of relinking onto the wrong
  content.

## Export/import contract (ADR 0009)

`tutor.py export` writes every `main` table into one human-readable JSON file,
`<root>/.tutor/tutor.json`, committed beside `tutor.db`. `tutor.py import [--merge]` rebuilds
`main` from it — plain replace by default, `--merge` unions rows from two devices instead of
picking one side.

Both representations of the same data are committed on purpose: `tutor.db` is binary, so git
cannot merge two devices' independent study sessions — the JSON is diffable and mergeable,
turning "pick a side" into a real three-way merge and "corrupted or deleted `tutor.db`" into
"restore from the last commit." The JSON is authoritative only as a recovery/merge artifact,
**never as the live store** — `main` stays the database.

The two can drift if `export` is skipped after studying, so:

- `SKILL.md`'s hard rules require running `export` before any commit of the Materials Root.
- `check` reports `stale_export` when `tutor.json`'s mtime is older than the newest `ts` across
  `star`/`annotation`/`note` — a JSON that predates a database row nobody exported yet.
