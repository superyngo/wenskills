# wens-tutor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `wens-tutor` skill — a stdlib-only Python engine plus a vanilla-JS site that turns a Markdown courseware tree into a study site with persistent annotations, timed mock papers, wrong-answer drilling, and cross-referencing lookup.

**Architecture:** One process mounts two static roots (engine from the skill, content from the Materials Root) and serves JSON from a SQLite file holding *only* user state; content facts are parsed into an in-memory attached database at every start, so there is no index step and no cache. Question identity is a content hash, Section identity is a heading ancestor path, so user state survives file renames and chapter insertions.

**Tech Stack:** Python ≥3.9 stdlib only (`http.server`, `sqlite3`, `hashlib`, `unicodedata`, `hmac`, `json`, `argparse`, `re`); vanilla ES modules; vendored `markdown-it` (single file, no npm, no build); `unittest` for tests.

**Design authority:** `docs/superpowers/specs/2026-08-13-wens-tutor-design.md`. Domain vocabulary: `skills/wens-tutor/CONTEXT.md`. Decisions: `skills/wens-tutor/docs/adr/0001…0010` — read 0001, 0002, 0006, 0007 before Task 1; 0004 and 0005 before Task 3; 0009 before Task 9; 0010 before Task 12.

## Global Constraints

- Python: stdlib only, no third-party packages, must run on 3.9. Invoke as `uv run --python 3.14 python3 <script>` (repo CLAUDE.md).
- Frontend: no npm, no build step, no framework. `web/vendor/markdown-it.min.js` is the only dependency, vendored as a file.
- The engine NEVER writes to a Material File. Only the agent does, only in the three Backfill/Explanation workflows.
- The Materials Root for all testing is `~/repos/wenswiki/wenswiki/work/平台/2026_AI應用規劃師`. Never modify a file inside it during implementation; never `git push` the wenswiki vault.
- All user-state keys are natural and stable: `qkey` (content hash), `fid` (minted file id), Section ancestor `path`. Never a rowid, never a relpath, never an occurrence counter.
- User-facing strings live in `web/strings.js` only. No inline literals in HTML or JS.
- Ground-truth numbers that tests assert: 270 Questions, 11 Banks, 200 `exam`-shape + 70 `guide`-shape, 3 `no_answer`, 23 `figure_missing`, 70 official Explanations, 0 Questions in the two cheatsheets, 0 Section-path collisions across 8 files, 57 leaf Sections in the 科目1 guide.
- Commit after every task with a conventional-commit message. Append a CHANGELOG `Unreleased` entry in the final task only (one entry for the feature, per repo CLAUDE.md).

---

## File Structure

| File | Responsibility |
|---|---|
| `skills/wens-tutor/scripts/tutor.py` | argparse CLI, subcommand dispatch, exit codes. No logic. |
| `skills/wens-tutor/scripts/tutorlib/parser.py` | Pure functions: Markdown text → Sections, Banks, Questions, Defects. No I/O. |
| `skills/wens-tutor/scripts/tutorlib/catalog.py` | Walk a root, read files, call parser, build the in-memory `cat` schema. |
| `skills/wens-tutor/scripts/tutorlib/state.py` | User-state DDL, connection, `fid` reconciliation, `qkey` relink, export/import. |
| `skills/wens-tutor/scripts/tutorlib/compose.py` | Paper composition, grading, Star lifecycle, statistics queries. |
| `skills/wens-tutor/scripts/tutorlib/registry.py` | `~/.config/wens-tutor/roots.json`: roots, default, port, token. |
| `skills/wens-tutor/scripts/tutorlib/api.py` | Request → JSON handlers over catalogue + state. |
| `skills/wens-tutor/scripts/tutorlib/server.py` | `ThreadingHTTPServer`, routing, path containment, token gate. |
| `skills/wens-tutor/web/app/host.js` | Host detection, per-host behaviour switch. |
| `skills/wens-tutor/web/app/api.js` | `fetch` wrappers for `/api/*`. |
| `skills/wens-tutor/web/app/render.js` | markdown-it setup, `data-line` stamping, anchoring/restore. |
| `skills/wens-tutor/web/app/portal.js`, `reader.js`, `exam.js`, `stats.js` | One page each. |
| `skills/wens-tutor/web/strings.js` | Every user-facing string. |
| `skills/wens-tutor/tests/test_parser.py` | Parser assertions against the eight real Material Files. |
| `skills/wens-tutor/tests/test_rules.py` | The five silently-failing rules, at the pure-function layer. |
| `skills/wens-tutor/SKILL.md` | Agent workflow, triggers, hard rules. |
| `skills/wens-tutor/references/material-format.md` | Both Question shapes, tolerances, Defect heuristics. |
| `skills/wens-tutor/references/db-schema.md` | Schema + key-stability rationale. |

---

### Task 1: Section parsing with ancestor-path identity

**Files:**
- Create: `skills/wens-tutor/scripts/tutorlib/__init__.py` (empty)
- Create: `skills/wens-tutor/scripts/tutorlib/parser.py`
- Test: `skills/wens-tutor/tests/test_parser.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `slugify(text: str) -> str`; `Section(path, level, title, is_leaf, line_start, line_end, text)` as a `NamedTuple`; `parse_sections(md: str) -> list[Section]`.

- [ ] **Step 1: Write the failing test**

```python
# skills/wens-tutor/tests/test_parser.py
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from tutorlib import parser  # noqa: E402

MD = """# 第三章 AI 相關技術應用

導言一段。

## 3.1 自然語言處理

### 1. 前言與章節導覽

甲。

### 選擇題

乙。

## 3.2 電腦視覺

### 1. 前言與章節導覽

丙。
"""


class TestSections(unittest.TestCase):
    def test_paths_are_ancestor_joined_and_unique(self):
        secs = parser.parse_sections(MD)
        paths = [s.path for s in secs]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertIn("第三章-ai-相關技術應用/3-1-自然語言處理/1-前言與章節導覽", paths)
        self.assertIn("第三章-ai-相關技術應用/3-2-電腦視覺/1-前言與章節導覽", paths)

    def test_section_text_excludes_children(self):
        secs = {s.path: s for s in parser.parse_sections(MD)}
        top = secs["第三章-ai-相關技術應用"]
        self.assertIn("導言一段。", top.text)
        self.assertNotIn("甲。", top.text)

    def test_leaf_flag(self):
        secs = {s.path: s for s in parser.parse_sections(MD)}
        self.assertFalse(secs["第三章-ai-相關技術應用"].is_leaf)
        self.assertTrue(secs["第三章-ai-相關技術應用/3-1-自然語言處理/選擇題"].is_leaf)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_parser -v`
Expected: FAIL — `ModuleNotFoundError` or `AttributeError: module 'tutorlib.parser' has no attribute 'parse_sections'`

- [ ] **Step 3: Write minimal implementation**

```python
# skills/wens-tutor/scripts/tutorlib/parser.py
"""Pure Markdown parsing: Sections, Banks, Questions, Defects. No I/O."""

import re
import unicodedata
from typing import List, NamedTuple

HEADING = re.compile(r"^(#{1,4})[ \t]+(.+?)[ \t]*$")


class Section(NamedTuple):
    path: str
    level: int
    title: str
    is_leaf: bool
    line_start: int   # 1-based, the heading line
    line_end: int     # 1-based, exclusive
    text: str         # own body only, children excluded


def slugify(text: str) -> str:
    s = unicodedata.normalize("NFKC", text).strip().lower()
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", s, flags=re.UNICODE)
    return s.strip("-")


def parse_sections(md: str) -> List[Section]:
    lines = md.splitlines()
    heads = []  # (index, level, title)
    for i, line in enumerate(lines):
        m = HEADING.match(line)
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))

    out: List[Section] = []
    stack: List[str] = []
    for n, (i, level, title) in enumerate(heads):
        stack = stack[: level - 1]
        while len(stack) < level - 1:
            stack.append("")
        stack.append(slugify(title))
        path = "/".join(p for p in stack if p)

        next_i = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        next_level = heads[n + 1][1] if n + 1 < len(heads) else 0
        body = "\n".join(lines[i + 1 : next_i]).strip()
        out.append(
            Section(
                path=path,
                level=level,
                title=title,
                is_leaf=(next_level <= level),
                line_start=i + 1,
                line_end=next_i + 1,
                text=body,
            )
        )
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_parser -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Add the real-corpus regression and run it**

Append to `tests/test_parser.py`:

```python
ROOT = Path("~/repos/wenswiki/wenswiki/work/平台/2026_AI應用規劃師").expanduser()


def material_files():
    return sorted(p for p in ROOT.rglob("*.md") if p.name != "README.md" and "/source/" not in str(p))


class TestRealCorpusSections(unittest.TestCase):
    def test_no_path_collisions_in_any_file(self):
        self.assertEqual(len(material_files()), 8)
        for p in material_files():
            paths = [s.path for s in parser.parse_sections(p.read_text(encoding="utf-8"))]
            self.assertEqual(len(paths), len(set(paths)), f"collision in {p.name}")

    def test_leaf_count_of_subject1_guide(self):
        p = next(x for x in material_files() if x.name.startswith("AI應用規劃師(中級)-學習指引-科目1"))
        secs = parser.parse_sections(p.read_text(encoding="utf-8"))
        self.assertEqual(len(secs), 73)
        self.assertEqual(sum(1 for s in secs if s.is_leaf), 57)
```

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_parser -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add skills/wens-tutor/scripts/tutorlib/__init__.py skills/wens-tutor/scripts/tutorlib/parser.py skills/wens-tutor/tests/test_parser.py
git commit -m "feat(wens-tutor): parse Sections with ancestor-path identity"
```

---

### Task 2: Exam-shape Question parsing

**Files:**
- Modify: `skills/wens-tutor/scripts/tutorlib/parser.py`
- Test: `skills/wens-tutor/tests/test_parser.py`

**Interfaces:**
- Consumes: `parse_sections`, `slugify` from Task 1.
- Produces: `Question(qkey, ordinal, type, stem_md, options, answer, explanation_md, explanation_origin)`; `Bank(path, title, shape, questions)`; `qkey_for(stem_md, options) -> str`; `parse_exam_bank(md: str) -> Bank | None`.

- [ ] **Step 1: Write the failing test**

```python
EXAM = """# 115年第一次 公告試題

## 一、選擇題

### 第 1 題

**答案：D**

某工程師正在建置系統，請問目的為何?

(A) 甲;
(B) 乙;
(C) 丙;
(D) 丁

### 第 2 題

**答案：（來源 PDF 此欄位無法擷取，請參閱官方公告）**

以下程式碼中(A)應填入何者？

- tool_a
- tool_b

```
code line
(A) not an option
```

(A) 甲;
(B) 乙;
(C) 丙;
(D) 丁

**解析（AI 生成，未經官方確認）：**

因為如此。

---

《以下空白》
"""


class TestExamBank(unittest.TestCase):
    def setUp(self):
        self.bank = parser.parse_exam_bank(EXAM)

    def test_two_questions_four_options_each(self):
        self.assertEqual(self.bank.shape, "exam")
        self.assertEqual(len(self.bank.questions), 2)
        for q in self.bank.questions:
            self.assertEqual(len(q.options), 4)

    def test_answer_and_missing_answer(self):
        self.assertEqual(self.bank.questions[0].answer, "D")
        self.assertIsNone(self.bank.questions[1].answer)

    def test_fenced_lines_stay_in_stem_and_are_not_options(self):
        q = self.bank.questions[1]
        self.assertIn("code line", q.stem_md)
        self.assertIn("(A) not an option", q.stem_md)
        self.assertEqual(q.options[0][1], "甲")

    def test_trailers_dropped_and_explanation_captured(self):
        q = self.bank.questions[1]
        self.assertNotIn("以下空白", q.stem_md)
        self.assertEqual(q.explanation_origin, "authored")
        self.assertIn("因為如此", q.explanation_md)

    def test_qkey_is_stable_and_content_addressed(self):
        again = parser.parse_exam_bank(EXAM)
        self.assertEqual(
            [q.qkey for q in self.bank.questions], [q.qkey for q in again.questions]
        )
        self.assertEqual(len(self.bank.questions[0].qkey), 12)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_parser.TestExamBank -v`
Expected: FAIL — `AttributeError: module 'tutorlib.parser' has no attribute 'parse_exam_bank'`

- [ ] **Step 3: Write minimal implementation**

Add to `parser.py`:

```python
import hashlib

QHEAD = re.compile(r"^###[ \t]*第[ \t]*(\d+)[ \t]*題[ \t]*$")
ANSWER = re.compile(r"^\*\*答案[：:]\s*([A-E]+)")
OPTION = re.compile(r"^\(([A-E])\)\s*(.+?);?\s*$")
EXPL_HEAD = re.compile(r"^\*\*解析.*[：:]\*\*\s*$")
TRAILER = re.compile(r"^(-{3,}|《以下空白》|\s*)$")
FENCE = re.compile(r"^\s*```")


class Question(NamedTuple):
    qkey: str
    ordinal: int
    type: str                    # 'single' | 'multi'
    stem_md: str
    options: List[tuple]         # [(letter, text), ...]
    answer: str                  # None when unpublished
    explanation_md: str
    explanation_origin: str      # 'official' | 'authored' | None


class Bank(NamedTuple):
    path: str
    title: str
    shape: str                   # 'exam' | 'guide'
    questions: List[Question]


def qkey_for(stem_md: str, options: List[tuple]) -> str:
    norm = unicodedata.normalize("NFKC", stem_md.strip())
    for letter, text in options:
        norm += "\n" + letter + unicodedata.normalize("NFKC", text.strip())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:12]


def _split_question_block(block_lines):
    """Return (stem_md, options, answer, explanation_md, explanation_origin)."""
    answer = None
    stem, options, expl = [], [], []
    in_fence = False
    mode = "stem"
    for line in block_lines:
        if FENCE.match(line):
            in_fence = not in_fence
            stem.append(line)
            continue
        if not in_fence:
            m = ANSWER.match(line)
            if m and answer is None and mode == "stem":
                answer = m.group(1)
                continue
            if line.startswith("**答案") and answer is None and mode == "stem":
                continue  # unparseable placeholder -> stays None
            if EXPL_HEAD.match(line):
                mode = "expl"
                continue
            m = OPTION.match(line)
            if m and mode in ("stem", "options"):
                mode = "options"
                options.append((m.group(1), m.group(2).strip()))
                continue
        if mode == "expl":
            expl.append(line)
        elif mode == "stem":
            stem.append(line)

    def clean(ls):
        out = [l for l in ls if not TRAILER.match(l)] if ls else []
        return "\n".join(ls).strip() if out else ""

    stem_md = "\n".join(stem).strip()
    stem_md = re.sub(r"\n?(-{3,}|《以下空白》)\s*$", "", stem_md).strip()
    expl_md = "\n".join(expl).strip()
    return stem_md, options, answer, expl_md, ("authored" if expl_md else None)


def parse_exam_bank(md: str, path: str = "", title: str = "") -> Bank:
    lines = md.splitlines()
    starts = [i for i, l in enumerate(lines) if QHEAD.match(l)]
    if not starts:
        return None
    questions = []
    for n, i in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        # a following '##' heading ends the bank region too
        for j in range(i + 1, end):
            if lines[j].startswith("## "):
                end = j
                break
        ordinal = int(QHEAD.match(lines[i]).group(1))
        stem, options, answer, expl, origin = _split_question_block(lines[i + 1 : end])
        questions.append(
            Question(
                qkey=qkey_for(stem, options),
                ordinal=ordinal,
                type="multi" if answer and len(answer) > 1 else "single",
                stem_md=stem,
                options=options,
                answer=answer,
                explanation_md=expl,
                explanation_origin=origin,
            )
        )
    return Bank(path=path, title=title, shape="exam", questions=questions)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_parser.TestExamBank -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Add the real-corpus assertions and run**

```python
class TestRealExamBanks(unittest.TestCase):
    def test_four_papers_fifty_each_with_four_options(self):
        banks = []
        for p in material_files():
            b = parser.parse_exam_bank(p.read_text(encoding="utf-8"), path="", title=p.name)
            if b:
                banks.append((p.name, b))
        self.assertEqual(len(banks), 4, [n for n, _ in banks])
        for name, b in banks:
            self.assertEqual(len(b.questions), 50, name)
            for q in b.questions:
                self.assertEqual(len(q.options), 4, f"{name} 第{q.ordinal}題")

    def test_cheatsheets_parse_to_no_questions(self):
        for p in material_files():
            if "cheatsheet" in p.name:
                self.assertIsNone(parser.parse_exam_bank(p.read_text(encoding="utf-8")))

    def test_three_questions_lack_an_answer(self):
        missing = 0
        for p in material_files():
            b = parser.parse_exam_bank(p.read_text(encoding="utf-8"))
            if b:
                missing += sum(1 for q in b.questions if q.answer is None)
        self.assertEqual(missing, 3)
```

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_parser -v`
Expected: PASS (13 tests)

- [ ] **Step 6: Commit**

```bash
git add skills/wens-tutor/scripts/tutorlib/parser.py skills/wens-tutor/tests/test_parser.py
git commit -m "feat(wens-tutor): parse exam-shape Questions with content-addressed keys"
```

---

### Task 3: Guide-shape Question parsing and Defect detection

**Files:**
- Modify: `skills/wens-tutor/scripts/tutorlib/parser.py`
- Test: `skills/wens-tutor/tests/test_parser.py`

**Interfaces:**
- Consumes: `Section`, `Question`, `Bank`, `qkey_for` from Tasks 1–2.
- Produces: `parse_guide_banks(md: str) -> list[Bank]`; `defects_for(q: Question) -> list[str]`; `parse_file(md: str) -> tuple[list[Section], list[Bank]]`.

Read ADR 0004 and ADR 0006 first.

- [ ] **Step 1: Write the failing test**

```python
GUIDE = """# 第三章

## 3.1 NLP

### 選擇題

1. 下列何者為詞嵌入技術？
   - （A）TF-IDF
   - （B）Word2Vec
   - （C）Stop Words
   - （D）Bag-of-Words

2. 下圖中的模型為何？
   - （A）甲
   - （B）乙
   - （C）丙
   - （D）丁

### 解答與解析

**1. Ans（B） Word2Vec**

解析：Word2Vec 可將文字轉為向量。

**2. Ans（A） 甲**

解析：如圖所示。
"""


class TestGuideBanks(unittest.TestCase):
    def setUp(self):
        self.banks = parser.parse_guide_banks(GUIDE)

    def test_one_bank_paired_with_the_next_sibling_region(self):
        self.assertEqual(len(self.banks), 1)
        self.assertEqual(self.banks[0].shape, "guide")
        self.assertEqual(self.banks[0].path, "第三章/3-1-nlp/選擇題")

    def test_answers_and_official_explanations(self):
        qs = self.banks[0].questions
        self.assertEqual([q.answer for q in qs], ["B", "A"])
        self.assertEqual(qs[0].explanation_origin, "official")
        self.assertIn("轉為向量", qs[0].explanation_md)

    def test_options_use_fullwidth_parens(self):
        self.assertEqual(self.banks[0].questions[0].options[1], ("B", "Word2Vec"))

    def test_figure_missing_defect(self):
        qs = self.banks[0].questions
        self.assertEqual(parser.defects_for(qs[0]), [])
        self.assertEqual(parser.defects_for(qs[1]), ["figure_missing"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_parser.TestGuideBanks -v`
Expected: FAIL — `AttributeError: module 'tutorlib.parser' has no attribute 'parse_guide_banks'`

- [ ] **Step 3: Write minimal implementation**

Add to `parser.py`:

```python
GUIDE_Q = re.compile(r"^(\d+)\.\s+(.*)$")
GUIDE_OPT = re.compile(r"^\s+-\s*[（(]([A-E])[)）]\s*(.+?)\s*$")
GUIDE_ANS = re.compile(r"^\*\*(\d+)\.\s*Ans[（(]([A-E])[)）]\s*(.*?)\*\*\s*$")
GUIDE_EXPL = re.compile(r"^解析[：:]\s*(.*)$")
FIGURE_REF = re.compile(
    r"下圖|上圖|圖中|附圖|如圖|下表|上表|表中|以下程式|下列程式|程式碼中|程式中|如下所示"
)
TABLE_ROW = re.compile(r"^\|", re.M)


def _guide_questions(body: str):
    """[(ordinal, stem, options)] from a 選擇題 region body."""
    out = []
    cur_ord, cur_stem, cur_opts = None, [], []
    for line in body.splitlines():
        m = GUIDE_OPT.match(line)
        if m and cur_ord is not None:
            cur_opts.append((m.group(1), m.group(2).strip()))
            continue
        m = GUIDE_Q.match(line)
        if m:
            if cur_ord is not None:
                out.append((cur_ord, "\n".join(cur_stem).strip(), cur_opts))
            cur_ord, cur_stem, cur_opts = int(m.group(1)), [m.group(2)], []
            continue
        if cur_ord is not None:
            cur_stem.append(line)
    if cur_ord is not None:
        out.append((cur_ord, "\n".join(cur_stem).strip(), cur_opts))
    return out


def _guide_answers(body: str):
    """{ordinal: (letter, explanation)} from a 解答與解析 region body."""
    out, cur = {}, None
    for line in body.splitlines():
        m = GUIDE_ANS.match(line)
        if m:
            cur = int(m.group(1))
            out[cur] = [m.group(2), ""]
            continue
        m = GUIDE_EXPL.match(line)
        if m and cur is not None:
            out[cur][1] = m.group(1).strip()
    return {k: tuple(v) for k, v in out.items()}


def parse_guide_banks(md: str) -> List[Bank]:
    sections = parse_sections(md)
    banks = []
    for n, sec in enumerate(sections):
        if sec.title.strip() != "選擇題":
            continue
        nxt = sections[n + 1] if n + 1 < len(sections) else None
        answers = _guide_answers(nxt.text) if nxt and nxt.title.strip() == "解答與解析" else {}
        questions = []
        for ordinal, stem, options in _guide_questions(sec.text):
            letter, expl = answers.get(ordinal, (None, ""))
            questions.append(
                Question(
                    qkey=qkey_for(stem, options),
                    ordinal=ordinal,
                    type="single",
                    stem_md=stem,
                    options=options,
                    answer=letter,
                    explanation_md=expl,
                    explanation_origin="official" if expl else None,
                )
            )
        banks.append(Bank(path=sec.path, title=sec.title, shape="guide", questions=questions))
    return banks


def defects_for(q: Question) -> List[str]:
    out = []
    if not q.answer:
        out.append("no_answer")
    blob = q.stem_md + "\n" + "\n".join(t for _, t in q.options)
    has_artifact = "```" in blob or TABLE_ROW.search(blob) or "![" in blob
    if FIGURE_REF.search(blob) and not has_artifact:
        out.append("figure_missing")
    return out


def parse_file(md: str):
    sections = parse_sections(md)
    exam = parse_exam_bank(md)
    if exam:
        return sections, [exam._replace(path="", title="")]
    return sections, parse_guide_banks(md)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_parser.TestGuideBanks -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Add the corpus totals assertion and run**

```python
class TestCorpusTotals(unittest.TestCase):
    def test_270_questions_11_banks_and_defect_counts(self):
        banks, questions = [], []
        for p in material_files():
            _, bs = parser.parse_file(p.read_text(encoding="utf-8"))
            banks += bs
            for b in bs:
                questions += b.questions
        self.assertEqual(len(banks), 11)
        self.assertEqual(len(questions), 270)
        self.assertEqual(sum(1 for b in banks if b.shape == "exam"), 4)
        self.assertEqual(sum(len(b.questions) for b in banks if b.shape == "guide"), 70)
        kinds = [k for q in questions for k in parser.defects_for(q)]
        self.assertEqual(kinds.count("no_answer"), 3)
        self.assertEqual(kinds.count("figure_missing"), 23)
        official = [q for q in questions if q.explanation_origin == "official"]
        self.assertEqual(len(official), 70)

    def test_guide_defects_are_zero(self):
        for p in material_files():
            _, bs = parser.parse_file(p.read_text(encoding="utf-8"))
            for b in bs:
                if b.shape == "guide":
                    for q in b.questions:
                        self.assertEqual(parser.defects_for(q), [], f"{p.name} {q.ordinal}")
```

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_parser -v`
Expected: PASS (19 tests). If `figure_missing` is not exactly 23, print the offending Questions and reconcile against the spec's Ground-truth table before changing the heuristic — the spec's number was measured, not guessed.

- [ ] **Step 6: Commit**

```bash
git add skills/wens-tutor/scripts/tutorlib/parser.py skills/wens-tutor/tests/test_parser.py
git commit -m "feat(wens-tutor): parse guide-shape Banks and detect Defects"
```

---

### Task 4: Catalogue in memory

**Files:**
- Create: `skills/wens-tutor/scripts/tutorlib/catalog.py`
- Test: `skills/wens-tutor/tests/test_rules.py`

**Interfaces:**
- Consumes: `parser.parse_file`, `parser.defects_for`.
- Produces: `build(conn, root: Path) -> None` creating `cat.file/section/bank/question/defect`; `open_catalog(root) -> sqlite3.Connection` (in-memory only, for CLI use without state).

- [ ] **Step 1: Write the failing test**

```python
# skills/wens-tutor/tests/test_rules.py
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from tutorlib import catalog  # noqa: E402

ROOT = Path("~/repos/wenswiki/wenswiki/work/平台/2026_AI應用規劃師").expanduser()


class TestCatalogue(unittest.TestCase):
    def test_catalogue_counts_match_the_corpus(self):
        conn = catalog.open_catalog(ROOT)
        self.assertEqual(conn.execute("SELECT count(*) FROM cat.file").fetchone()[0], 8)
        self.assertEqual(conn.execute("SELECT count(*) FROM cat.bank").fetchone()[0], 11)
        self.assertEqual(conn.execute("SELECT count(*) FROM cat.question").fetchone()[0], 270)
        self.assertEqual(
            conn.execute("SELECT count(*) FROM cat.defect WHERE kind='figure_missing'").fetchone()[0],
            23,
        )

    def test_subject_comes_from_the_first_path_segment(self):
        conn = catalog.open_catalog(ROOT)
        subjects = {r[0] for r in conn.execute("SELECT DISTINCT subject FROM cat.file")}
        self.assertEqual(subjects, {"AI應用規劃師", "機器學習"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_rules -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tutorlib.catalog'`

- [ ] **Step 3: Write minimal implementation**

```python
# skills/wens-tutor/scripts/tutorlib/catalog.py
"""Build the in-memory content catalogue. Rebuilt every process start (ADR 0001)."""

import hashlib
import json
import sqlite3
from pathlib import Path

from . import parser

DDL = """
CREATE TABLE cat.file(fid TEXT PRIMARY KEY, relpath TEXT, subject TEXT, title TEXT,
                      sha256 TEXT, n_sections INT, n_questions INT);
CREATE TABLE cat.section(fid TEXT, path TEXT, level INT, title TEXT, is_leaf INT,
                         line_start INT, line_end INT, text TEXT);
CREATE TABLE cat.bank(bkey TEXT PRIMARY KEY, fid TEXT, path TEXT, title TEXT, shape TEXT);
CREATE TABLE cat.question(qkey TEXT PRIMARY KEY, bkey TEXT, ordinal INT, type TEXT,
                          stem_md TEXT, options_json TEXT, answer TEXT,
                          explanation_md TEXT, explanation_origin TEXT);
CREATE TABLE cat.defect(qkey TEXT, kind TEXT);
CREATE INDEX cat.i_sec ON section(fid, path);
CREATE INDEX cat.i_q ON question(bkey);
"""


def material_files(root: Path):
    return sorted(
        p
        for p in root.rglob("*.md")
        if p.name != "README.md" and "source" not in p.relative_to(root).parts
    )


def build(conn: sqlite3.Connection, root: Path, fid_for=None) -> None:
    """fid_for(relpath, sections, banks) -> fid; defaults to a path-derived id."""
    conn.executescript(DDL)
    for path in material_files(root):
        rel = str(path.relative_to(root))
        md = path.read_text(encoding="utf-8")
        sections, banks = parser.parse_file(md)
        fid = (
            fid_for(rel, sections, banks)
            if fid_for
            else hashlib.sha256(rel.encode("utf-8")).hexdigest()[:12]
        )
        nq = sum(len(b.questions) for b in banks)
        conn.execute(
            "INSERT INTO cat.file VALUES (?,?,?,?,?,?,?)",
            (
                fid,
                rel,
                rel.split("/")[0],
                sections[0].title if sections else path.stem,
                hashlib.sha256(md.encode("utf-8")).hexdigest(),
                len(sections),
                nq,
            ),
        )
        conn.executemany(
            "INSERT INTO cat.section VALUES (?,?,?,?,?,?,?,?)",
            [
                (fid, s.path, s.level, s.title, 1 if s.is_leaf else 0, s.line_start, s.line_end, s.text)
                for s in sections
            ],
        )
        for b in banks:
            bkey = fid + ":" + (b.path or "*")
            conn.execute(
                "INSERT INTO cat.bank VALUES (?,?,?,?,?)",
                (bkey, fid, b.path, b.title or path.stem, b.shape),
            )
            for q in b.questions:
                conn.execute(
                    "INSERT OR IGNORE INTO cat.question VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        q.qkey,
                        bkey,
                        q.ordinal,
                        q.type,
                        q.stem_md,
                        json.dumps(q.options, ensure_ascii=False),
                        q.answer,
                        q.explanation_md,
                        q.explanation_origin,
                    ),
                )
                conn.executemany(
                    "INSERT INTO cat.defect VALUES (?,?)",
                    [(q.qkey, k) for k in parser.defects_for(q)],
                )
    conn.commit()


def open_catalog(root: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("ATTACH ':memory:' AS cat")
    build(conn, Path(root))
    return conn
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_rules -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/wens-tutor/scripts/tutorlib/catalog.py skills/wens-tutor/tests/test_rules.py
git commit -m "feat(wens-tutor): build the in-memory content catalogue"
```

---

### Task 5: User-state schema, registry, and fid reconciliation

**Files:**
- Create: `skills/wens-tutor/scripts/tutorlib/state.py`
- Create: `skills/wens-tutor/scripts/tutorlib/registry.py`
- Test: `skills/wens-tutor/tests/test_rules.py`

**Interfaces:**
- Consumes: `catalog.build`.
- Produces: `state.open_root(root) -> sqlite3.Connection` (state file as `main`, catalogue attached as `cat`, fids reconciled); `state.reconcile(conn, root) -> dict` returning `{"relinked_files": [...], "relinked_questions": [...], "unresolved": [...]}`; `registry.load()`, `registry.save(data)`, `registry.add_root(path)`, `registry.default_root()`, `registry.token()`.

Read ADR 0002, 0003, 0007 first.

- [ ] **Step 1: Write the failing test**

```python
import shutil
import tempfile

from tutorlib import state  # noqa: E402


class TestFidReconciliation(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "科目A").mkdir()
        self.f = self.tmp / "科目A" / "bank.md"
        self.f.write_text(
            "### 第 1 題\n\n**答案：A**\n\n題幹一\n\n(A) 甲;\n(B) 乙;\n(C) 丙;\n(D) 丁\n",
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_star_survives_a_file_rename(self):
        conn = state.open_root(self.tmp)
        qkey = conn.execute("SELECT qkey FROM cat.question").fetchone()[0]
        conn.execute("INSERT INTO star VALUES (?,'manual',0)", (qkey,))
        conn.commit()
        conn.close()

        self.f.rename(self.f.with_name("renamed.md"))
        conn = state.open_root(self.tmp)
        self.assertEqual(conn.execute("SELECT count(*) FROM star").fetchone()[0], 1)
        joined = conn.execute(
            "SELECT count(*) FROM star s JOIN cat.question q ON q.qkey = s.qkey"
        ).fetchone()[0]
        self.assertEqual(joined, 1)

    def test_progress_follows_the_file_via_fid(self):
        conn = state.open_root(self.tmp)
        fid = conn.execute("SELECT fid FROM cat.file").fetchone()[0]
        conn.execute("INSERT INTO progress VALUES (?,?,0)", (fid, "第-1-題"))
        conn.commit()
        conn.close()
        self.f.rename(self.f.with_name("renamed2.md"))
        conn = state.open_root(self.tmp)
        fid2 = conn.execute("SELECT fid FROM cat.file").fetchone()[0]
        self.assertEqual(fid, fid2)

    def test_stem_edit_relinks_the_qkey(self):
        conn = state.open_root(self.tmp)
        old = conn.execute("SELECT qkey FROM cat.question").fetchone()[0]
        conn.execute("INSERT INTO star VALUES (?,'wrong',0)", (old,))
        conn.commit()
        conn.close()
        self.f.write_text(
            self.f.read_text(encoding="utf-8").replace("題幹一", "題幹壹"), encoding="utf-8"
        )
        conn = state.open_root(self.tmp)
        report = state.reconcile(conn, self.tmp)
        new = conn.execute("SELECT qkey FROM cat.question").fetchone()[0]
        self.assertNotEqual(old, new)
        self.assertEqual(conn.execute("SELECT qkey FROM star").fetchone()[0], new)
        self.assertEqual(len(report["relinked_questions"]), 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_rules.TestFidReconciliation -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tutorlib.state'`

- [ ] **Step 3: Write minimal implementation**

```python
# skills/wens-tutor/scripts/tutorlib/registry.py
"""Device-local registry: roots, default root, port, token (ADR 0003)."""

import json
import os
import secrets
from pathlib import Path

PATH = Path(os.environ.get("WENS_TUTOR_CONFIG", "~/.config/wens-tutor/roots.json")).expanduser()


def load() -> dict:
    if PATH.exists():
        return json.loads(PATH.read_text(encoding="utf-8"))
    return {"roots": [], "default": None, "port": 8765, "token": None}


def save(data: dict) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def add_root(path) -> dict:
    data = load()
    p = str(Path(path).expanduser().resolve())
    if p not in data["roots"]:
        data["roots"].append(p)
    data["default"] = data["default"] or p
    data["token"] = data.get("token") or secrets.token_urlsafe(16)
    save(data)
    return data


def default_root():
    d = load().get("default")
    return Path(d) if d else None


def token():
    return load().get("token")
```

```python
# skills/wens-tutor/scripts/tutorlib/state.py
"""User-state store. Never rebuilt by indexing (ADR 0001); keys are natural (ADR 0002/0007)."""

import hashlib
import json
import sqlite3
import time
from pathlib import Path

from . import catalog

DDL = """
CREATE TABLE IF NOT EXISTS file_id(fid TEXT PRIMARY KEY, relpath TEXT, first_seen REAL,
                                   fingerprint TEXT);
CREATE TABLE IF NOT EXISTS annotation(id INTEGER PRIMARY KEY AUTOINCREMENT, fid TEXT,
                                      block_line INT, exact TEXT, prefix TEXT, suffix TEXT,
                                      color TEXT, note_md TEXT, ts REAL, orphan INT DEFAULT 0);
CREATE TABLE IF NOT EXISTS progress(fid TEXT, path TEXT, read_at REAL, PRIMARY KEY(fid, path));
CREATE TABLE IF NOT EXISTS reading_pos(fid TEXT PRIMARY KEY, line INT, ts REAL);
CREATE TABLE IF NOT EXISTS star(qkey TEXT PRIMARY KEY, origin TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS note(qkey TEXT PRIMARY KEY, note_md TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS paper(id INTEGER PRIMARY KEY AUTOINCREMENT, criteria_json TEXT,
                                 qkeys_json TEXT, limit_ms INT, created REAL);
CREATE TABLE IF NOT EXISTS attempt(id INTEGER PRIMARY KEY AUTOINCREMENT, paper_id INT,
                                   started REAL, finished REAL, elapsed_ms INT, total INT,
                                   correct INT, expired INT DEFAULT 0);
CREATE TABLE IF NOT EXISTS attempt_item(attempt_id INT, qkey TEXT, given TEXT, correct INT,
                                        ms INT, PRIMARY KEY(attempt_id, qkey));
"""


def db_path(root: Path) -> Path:
    return Path(root) / ".tutor" / "tutor.db"


def _fingerprint(sections, banks) -> str:
    if banks and banks[0].questions:
        items = sorted(q.qkey for b in banks for q in b.questions)
    else:
        items = sorted(s.path for s in sections)
    return json.dumps(items[:200], ensure_ascii=False)


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(json.loads(a)), set(json.loads(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def open_root(root: Path) -> sqlite3.Connection:
    root = Path(root)
    p = db_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(DDL)
    conn.execute("ATTACH ':memory:' AS cat")

    known = {r["relpath"]: dict(r) for r in conn.execute("SELECT * FROM file_id")}
    seen_relpaths = set()

    def fid_for(rel, sections, banks):
        seen_relpaths.add(rel)
        fp = _fingerprint(sections, banks)
        row = known.get(rel)
        if row:
            conn.execute("UPDATE file_id SET fingerprint=? WHERE fid=?", (fp, row["fid"]))
            return row["fid"]
        candidates = [
            r
            for r in known.values()
            if r["relpath"] not in seen_relpaths and _jaccard(r["fingerprint"] or "[]", fp) >= 0.6
        ]
        if len(candidates) == 1:
            fid = candidates[0]["fid"]
            conn.execute(
                "UPDATE file_id SET relpath=?, fingerprint=? WHERE fid=?", (rel, fp, fid)
            )
            return fid
        fid = hashlib.sha256((rel + str(time.time())).encode("utf-8")).hexdigest()[:12]
        conn.execute("INSERT INTO file_id VALUES (?,?,?,?)", (fid, rel, time.time(), fp))
        return fid

    catalog.build(conn, root, fid_for=fid_for)
    conn.commit()
    return conn


def reconcile(conn: sqlite3.Connection, root: Path) -> dict:
    """Relink user-state qkeys whose Question text changed, by (bkey, ordinal)."""
    report = {"relinked_files": [], "relinked_questions": [], "unresolved": []}
    live = {r["qkey"] for r in conn.execute("SELECT qkey FROM cat.question")}
    used = set()
    for table in ("star", "note", "attempt_item"):
        used |= {r["qkey"] for r in conn.execute(f"SELECT DISTINCT qkey FROM {table}")}
    orphaned = sorted(used - live)
    if not orphaned:
        return report

    by_slot = {}
    for r in conn.execute("SELECT qkey, bkey, ordinal FROM cat.question"):
        by_slot[(r["bkey"], r["ordinal"])] = r["qkey"]
    taken = set(live & used)

    hist = {
        r["qkey"]: (r["bkey"], r["ordinal"])
        for r in conn.execute("SELECT qkey, bkey, ordinal FROM cat.question")
    }
    for old in orphaned:
        slot = hist.get(old)
        new = by_slot.get(slot) if slot else None
        if new is None:
            # fall back: a single free slot in a bank that lost exactly one qkey
            free = [k for k, v in by_slot.items() if v not in taken]
            new = by_slot[free[0]] if len(free) == 1 else None
        if new is None:
            report["unresolved"].append(old)
            continue
        for table in ("star", "note", "attempt_item"):
            conn.execute(f"UPDATE OR IGNORE {table} SET qkey=? WHERE qkey=?", (new, old))
        taken.add(new)
        report["relinked_questions"].append({"from": old, "to": new})
    conn.commit()
    return report
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_rules -v`
Expected: PASS (5 tests). `WENS_TUTOR_CONFIG` keeps the registry out of the real config during tests — set it in any test that touches `registry`.

- [ ] **Step 5: Commit**

```bash
git add skills/wens-tutor/scripts/tutorlib/state.py skills/wens-tutor/scripts/tutorlib/registry.py skills/wens-tutor/tests/test_rules.py
git commit -m "feat(wens-tutor): user-state store with fid reconciliation and qkey relink"
```

---

### Task 6: Paper composition, grading, and the Star lifecycle

**Files:**
- Create: `skills/wens-tutor/scripts/tutorlib/compose.py`
- Test: `skills/wens-tutor/tests/test_rules.py`

**Interfaces:**
- Consumes: `state.open_root`.
- Produces: `compose(conn, criteria: dict) -> int` (paper id); `start_attempt(conn, paper_id) -> int`; `answer(conn, attempt_id, qkey, given, ms) -> None`; `submit(conn, attempt_id, now=None) -> dict`; `toggle_star(conn, qkey) -> bool`; `remaining_ms(conn, attempt_id, now=None) -> int`; `stats(conn) -> dict`.

Criteria keys: `subjects: list[str]`, `bkeys: list[str]`, `cap: int = 50`, `shuffle: bool = True`, `timed: bool = True`, `include_defective: bool = False`, `drill: bool = False`.

- [ ] **Step 1: Write the failing test**

```python
from tutorlib import compose  # noqa: E402


class TestRules(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "科目A").mkdir()
        qs = []
        for i in range(1, 6):
            qs.append(
                f"### 第 {i} 題\n\n**答案：A**\n\n題幹{i}\n\n(A) 甲;\n(B) 乙;\n(C) 丙;\n(D) 丁\n"
            )
        # one defective question: references a figure with no artifact
        qs.append("### 第 6 題\n\n**答案：B**\n\n如下圖所示為何?\n\n(A) 甲;\n(B) 乙;\n(C) 丙;\n(D) 丁\n")
        (self.tmp / "科目A" / "bank.md").write_text("\n".join(qs), encoding="utf-8")
        self.conn = state.open_root(self.tmp)

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.tmp)

    def qkeys(self):
        return [r["qkey"] for r in self.conn.execute("SELECT qkey FROM cat.question ORDER BY ordinal")]

    def test_composition_excludes_defects_by_default(self):
        pid = compose.compose(self.conn, {"cap": 50})
        row = self.conn.execute("SELECT qkeys_json FROM paper WHERE id=?", (pid,)).fetchone()
        self.assertEqual(len(json.loads(row["qkeys_json"])), 5)
        pid2 = compose.compose(self.conn, {"cap": 50, "include_defective": True})
        row2 = self.conn.execute("SELECT qkeys_json FROM paper WHERE id=?", (pid2,)).fetchone()
        self.assertEqual(len(json.loads(row2["qkeys_json"])), 6)

    def test_star_lifecycle_needs_two_consecutive_corrects(self):
        target = self.qkeys()[0]

        def sit(given):
            pid = compose.compose(self.conn, {"cap": 50, "shuffle": False})
            aid = compose.start_attempt(self.conn, pid)
            compose.answer(self.conn, aid, target, given, 1000)
            return compose.submit(self.conn, aid)

        sit("C")  # wrong
        self.assertEqual(self.conn.execute("SELECT origin FROM star WHERE qkey=?", (target,)).fetchone()["origin"], "wrong")
        sit("A")  # first correct: star holds
        self.assertIsNotNone(self.conn.execute("SELECT 1 FROM star WHERE qkey=?", (target,)).fetchone())
        sit("A")  # second consecutive correct: star clears
        self.assertIsNone(self.conn.execute("SELECT 1 FROM star WHERE qkey=?", (target,)).fetchone())

    def test_manual_star_is_never_auto_cleared(self):
        target = self.qkeys()[1]
        self.assertTrue(compose.toggle_star(self.conn, target))
        for _ in range(3):
            pid = compose.compose(self.conn, {"cap": 50, "shuffle": False})
            aid = compose.start_attempt(self.conn, pid)
            compose.answer(self.conn, aid, target, "A", 500)
            compose.submit(self.conn, aid)
        self.assertEqual(
            self.conn.execute("SELECT origin FROM star WHERE qkey=?", (target,)).fetchone()["origin"],
            "manual",
        )

    def test_drill_contains_exactly_the_starred_questions(self):
        a, b = self.qkeys()[0], self.qkeys()[2]
        compose.toggle_star(self.conn, a)
        compose.toggle_star(self.conn, b)
        pid = compose.compose(self.conn, {"drill": True})
        row = self.conn.execute("SELECT qkeys_json, limit_ms FROM paper WHERE id=?", (pid,)).fetchone()
        self.assertEqual(sorted(json.loads(row["qkeys_json"])), sorted([a, b]))
        self.assertIsNone(row["limit_ms"])

    def test_timed_paper_scales_to_108s_per_question(self):
        pid = compose.compose(self.conn, {"cap": 3, "timed": True})
        row = self.conn.execute("SELECT limit_ms FROM paper WHERE id=?", (pid,)).fetchone()
        self.assertEqual(row["limit_ms"], 3 * 108 * 1000)

    def test_reopening_past_the_limit_submits_and_expires(self):
        pid = compose.compose(self.conn, {"cap": 2, "timed": True, "shuffle": False})
        aid = compose.start_attempt(self.conn, pid)
        compose.answer(self.conn, aid, self.qkeys()[0], "A", 1000)
        started = self.conn.execute("SELECT started FROM attempt WHERE id=?", (aid,)).fetchone()["started"]
        late = started + (2 * 108) + 5
        self.assertEqual(compose.remaining_ms(self.conn, aid, now=late), 0)
        result = compose.submit(self.conn, aid, now=late)
        self.assertTrue(result["expired"])
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["correct"], 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_rules.TestRules -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tutorlib.compose'`

- [ ] **Step 3: Write minimal implementation**

```python
# skills/wens-tutor/scripts/tutorlib/compose.py
"""Paper composition, grading, Star lifecycle, statistics."""

import json
import random
import time

SECONDS_PER_QUESTION = 108  # 90 minutes / 50 Questions, official rate


def _selectable(conn, criteria):
    sql = [
        "SELECT q.qkey, q.bkey, q.ordinal FROM cat.question q",
        "JOIN cat.bank b ON b.bkey = q.bkey",
        "JOIN cat.file f ON f.fid = b.fid",
        "WHERE q.answer IS NOT NULL",
    ]
    args = []
    if not criteria.get("include_defective"):
        sql.append("AND q.qkey NOT IN (SELECT qkey FROM cat.defect)")
    if criteria.get("subjects"):
        sql.append("AND f.subject IN (%s)" % ",".join("?" * len(criteria["subjects"])))
        args += list(criteria["subjects"])
    if criteria.get("bkeys"):
        sql.append("AND q.bkey IN (%s)" % ",".join("?" * len(criteria["bkeys"])))
        args += list(criteria["bkeys"])
    if criteria.get("drill"):
        sql.append("AND q.qkey IN (SELECT qkey FROM star)")
    sql.append("ORDER BY f.relpath, b.path, q.ordinal")
    return [r["qkey"] for r in conn.execute(" ".join(sql), args)]


def compose(conn, criteria: dict) -> int:
    criteria = dict(criteria)
    drill = bool(criteria.get("drill"))
    qkeys = _selectable(conn, criteria)
    if criteria.get("shuffle", True) and not drill:
        random.shuffle(qkeys)
    elif drill:
        random.shuffle(qkeys)
    cap = criteria.get("cap")
    if cap and not drill:
        qkeys = qkeys[: int(cap)]
    timed = bool(criteria.get("timed", True)) and not drill
    limit_ms = len(qkeys) * SECONDS_PER_QUESTION * 1000 if timed else None
    cur = conn.execute(
        "INSERT INTO paper(criteria_json, qkeys_json, limit_ms, created) VALUES (?,?,?,?)",
        (json.dumps(criteria, ensure_ascii=False), json.dumps(qkeys), limit_ms, time.time()),
    )
    conn.commit()
    return cur.lastrowid


def start_attempt(conn, paper_id: int) -> int:
    row = conn.execute(
        "SELECT id FROM attempt WHERE paper_id=? AND finished IS NULL", (paper_id,)
    ).fetchone()
    if row:
        return row["id"]
    qkeys = json.loads(conn.execute("SELECT qkeys_json FROM paper WHERE id=?", (paper_id,)).fetchone()["qkeys_json"])
    cur = conn.execute(
        "INSERT INTO attempt(paper_id, started, total, correct) VALUES (?,?,?,0)",
        (paper_id, time.time(), len(qkeys)),
    )
    conn.commit()
    return cur.lastrowid


def answer(conn, attempt_id: int, qkey: str, given: str, ms: int) -> None:
    conn.execute(
        "INSERT INTO attempt_item(attempt_id, qkey, given, correct, ms) VALUES (?,?,?,0,?)"
        " ON CONFLICT(attempt_id, qkey) DO UPDATE SET given=excluded.given, ms=excluded.ms",
        (attempt_id, qkey, given, ms),
    )
    conn.commit()


def remaining_ms(conn, attempt_id: int, now=None) -> int:
    row = conn.execute(
        "SELECT a.started, p.limit_ms FROM attempt a JOIN paper p ON p.id = a.paper_id WHERE a.id=?",
        (attempt_id,),
    ).fetchone()
    if row["limit_ms"] is None:
        return None
    now = time.time() if now is None else now
    return max(0, int(row["limit_ms"] - (now - row["started"]) * 1000))


def _previous_was_correct(conn, attempt_id, qkey) -> bool:
    row = conn.execute(
        "SELECT i.correct FROM attempt_item i JOIN attempt a ON a.id = i.attempt_id"
        " WHERE i.qkey=? AND i.attempt_id<>? AND a.finished IS NOT NULL"
        " ORDER BY a.finished DESC LIMIT 1",
        (qkey, attempt_id),
    ).fetchone()
    return bool(row and row["correct"])


def submit(conn, attempt_id: int, now=None) -> dict:
    now = time.time() if now is None else now
    att = conn.execute("SELECT * FROM attempt WHERE id=?", (attempt_id,)).fetchone()
    paper = conn.execute("SELECT * FROM paper WHERE id=?", (att["paper_id"],)).fetchone()
    qkeys = json.loads(paper["qkeys_json"])
    answers = {r["qkey"]: r for r in conn.execute("SELECT * FROM attempt_item WHERE attempt_id=?", (attempt_id,))}
    correct = 0
    wrong = []
    for qkey in qkeys:
        truth = conn.execute("SELECT answer FROM cat.question WHERE qkey=?", (qkey,)).fetchone()
        given = answers[qkey]["given"] if qkey in answers else None
        ok = bool(truth and given and set(given) == set(truth["answer"]))
        conn.execute(
            "INSERT INTO attempt_item(attempt_id, qkey, given, correct, ms) VALUES (?,?,?,?,?)"
            " ON CONFLICT(attempt_id, qkey) DO UPDATE SET correct=excluded.correct",
            (attempt_id, qkey, given, 1 if ok else 0, answers[qkey]["ms"] if qkey in answers else 0),
        )
        if ok:
            correct += 1
        else:
            wrong.append(qkey)

    expired = 0
    if paper["limit_ms"] is not None and (now - att["started"]) * 1000 >= paper["limit_ms"]:
        expired = 1
    conn.execute(
        "UPDATE attempt SET finished=?, elapsed_ms=?, total=?, correct=?, expired=? WHERE id=?",
        (now, int((now - att["started"]) * 1000), len(qkeys), correct, expired, attempt_id),
    )

    # Star lifecycle
    for qkey in qkeys:
        row = conn.execute("SELECT origin FROM star WHERE qkey=?", (qkey,)).fetchone()
        if qkey in wrong:
            if row is None:
                conn.execute("INSERT INTO star VALUES (?,'wrong',?)", (qkey, now))
        elif row and row["origin"] == "wrong" and _previous_was_correct(conn, attempt_id, qkey):
            conn.execute("DELETE FROM star WHERE qkey=?", (qkey,))
    conn.commit()
    return {
        "attempt_id": attempt_id,
        "total": len(qkeys),
        "correct": correct,
        "score": round(correct * 100.0 / len(qkeys), 1) if qkeys else 0.0,
        "passed": bool(qkeys) and correct * 100.0 / len(qkeys) >= 60,
        "expired": bool(expired),
        "wrong": wrong,
    }


def toggle_star(conn, qkey: str) -> bool:
    row = conn.execute("SELECT origin FROM star WHERE qkey=?", (qkey,)).fetchone()
    if row:
        conn.execute("DELETE FROM star WHERE qkey=?", (qkey,))
        conn.commit()
        return False
    conn.execute("INSERT INTO star VALUES (?,'manual',?)", (qkey, time.time()))
    conn.commit()
    return True


def stats(conn) -> dict:
    scores = [
        dict(r)
        for r in conn.execute(
            "SELECT a.id, a.finished, a.total, a.correct,"
            " round(a.correct*100.0/a.total,1) AS score, a.expired"
            " FROM attempt a WHERE a.finished IS NOT NULL ORDER BY a.finished"
        )
    ]
    pace = conn.execute(
        "SELECT avg(ms)/1000.0 AS mean_s FROM attempt_item WHERE ms > 0"
    ).fetchone()["mean_s"]
    missed = [
        dict(r)
        for r in conn.execute(
            "SELECT qkey, count(*) AS wrong_count FROM attempt_item WHERE correct=0 AND given IS NOT NULL"
            " GROUP BY qkey ORDER BY wrong_count DESC, qkey LIMIT 20"
        )
    ]
    per_bank = [
        dict(r)
        for r in conn.execute(
            "SELECT b.bkey, b.title, count(DISTINCT q.qkey) AS n_questions,"
            " (SELECT count(*) FROM star s JOIN cat.question sq ON sq.qkey=s.qkey WHERE sq.bkey=b.bkey) AS stars,"
            " (SELECT count(*) FROM cat.defect d JOIN cat.question dq ON dq.qkey=d.qkey WHERE dq.bkey=b.bkey) AS defects"
            " FROM cat.bank b JOIN cat.question q ON q.bkey=b.bkey GROUP BY b.bkey ORDER BY b.bkey"
        )
    ]
    return {
        "scores": scores,
        "pace_seconds_per_question": round(pace, 1) if pace else None,
        "official_pace_seconds": SECONDS_PER_QUESTION,
        "most_missed": missed,
        "per_bank": per_bank,
        "stars": conn.execute("SELECT count(*) AS n FROM star").fetchone()["n"],
        "defects": conn.execute("SELECT count(*) AS n FROM cat.defect").fetchone()["n"],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_rules -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/wens-tutor/scripts/tutorlib/compose.py skills/wens-tutor/tests/test_rules.py
git commit -m "feat(wens-tutor): Paper composition, grading and the Star lifecycle"
```

---

### Task 7: Lookup with right-shortening

**Files:**
- Modify: `skills/wens-tutor/scripts/tutorlib/compose.py`
- Test: `skills/wens-tutor/tests/test_rules.py`

**Interfaces:**
- Consumes: catalogue tables.
- Produces: `lookup(conn, query: str, exclude_qkey: str = None) -> dict` returning `{"query_used": str, "courses": [...], "questions": [...]}`.

- [ ] **Step 1: Write the failing test**

```python
class TestLookup(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "科目A").mkdir()
        (self.tmp / "科目A" / "course.md").write_text(
            "# 章\n\n## 詞嵌入\n\n| 名稱 | 說明 |\n| --- | --- |\n| Word2Vec | 詞向量方法 |\n",
            encoding="utf-8",
        )
        (self.tmp / "科目A" / "bank.md").write_text(
            "### 第 1 題\n\n**答案：A**\n\nWord2Vec 屬於下列哪一類?\n\n(A) 詞嵌入;\n(B) 乙;\n(C) 丙;\n(D) 丁\n",
            encoding="utf-8",
        )
        self.conn = state.open_root(self.tmp)

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.tmp)

    def test_two_scopes(self):
        res = compose.lookup(self.conn, "Word2Vec")
        self.assertEqual(res["query_used"], "Word2Vec")
        self.assertTrue(res["courses"])
        self.assertTrue(res["questions"])

    def test_table_hit_returns_row_and_header(self):
        res = compose.lookup(self.conn, "詞向量方法")
        snippet = res["courses"][0]["snippet"]
        self.assertIn("| Word2Vec | 詞向量方法 |", snippet)
        self.assertIn("| 名稱 | 說明 |", snippet)

    def test_long_query_is_shortened_from_the_right_and_reported(self):
        res = compose.lookup(self.conn, "Word2Vec 是一種完全不存在於教材中的長句子描述")
        self.assertTrue(res["query_used"].startswith("Word2Vec"))
        self.assertLess(len(res["query_used"]), 20)
        self.assertTrue(res["courses"] or res["questions"])

    def test_floor_of_four_characters(self):
        res = compose.lookup(self.conn, "完全不存在的字串內容ABCDEFG")
        self.assertEqual(len(res["query_used"]), 4)
        self.assertEqual(res["courses"], [])
        self.assertEqual(res["questions"], [])

    def test_excludes_the_current_question(self):
        qkey = self.conn.execute("SELECT qkey FROM cat.question").fetchone()["qkey"]
        res = compose.lookup(self.conn, "Word2Vec", exclude_qkey=qkey)
        self.assertEqual(res["questions"], [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_rules.TestLookup -v`
Expected: FAIL — `AttributeError: module 'tutorlib.compose' has no attribute 'lookup'`

- [ ] **Step 3: Write minimal implementation**

Add to `compose.py`:

```python
import unicodedata

LOOKUP_FLOOR = 4


def _fold(s: str) -> str:
    return unicodedata.normalize("NFKC", s).lower()


def _table_snippet(text: str, idx: int) -> str:
    lines = text.splitlines()
    pos, hit = 0, 0
    for i, line in enumerate(lines):
        if pos + len(line) >= idx:
            hit = i
            break
        pos += len(line) + 1
    line = lines[hit] if hit < len(lines) else ""
    if not line.startswith("|"):
        start = max(0, idx - 40)
        return text[start : idx + 60].replace("\n", " ")
    header = ""
    for j in range(hit - 1, -1, -1):
        if lines[j].startswith("|") and not set(lines[j]) <= set("|- :"):
            header = lines[j]
        elif not lines[j].startswith("|"):
            break
    return (header + "\n" + line).strip()


def _scan(conn, needle: str, exclude_qkey):
    courses, questions = [], []
    for r in conn.execute(
        "SELECT f.relpath, f.subject, f.title AS file_title, s.path, s.title, s.text"
        " FROM cat.section s JOIN cat.file f ON f.fid = s.fid"
    ):
        hay = _fold(r["text"] or "")
        n = hay.count(needle)
        if n:
            courses.append(
                {
                    "relpath": r["relpath"],
                    "subject": r["subject"],
                    "file_title": r["file_title"],
                    "path": r["path"],
                    "title": r["title"],
                    "hits": n,
                    "depth": r["path"].count("/"),
                    "snippet": _table_snippet(r["text"], hay.find(needle)),
                }
            )
    for r in conn.execute(
        "SELECT q.qkey, q.ordinal, q.stem_md, q.answer, b.title AS bank_title, f.subject"
        " FROM cat.question q JOIN cat.bank b ON b.bkey=q.bkey JOIN cat.file f ON f.fid=b.fid"
    ):
        if exclude_qkey and r["qkey"] == exclude_qkey:
            continue
        hay = _fold(r["stem_md"] or "")
        if needle in hay:
            questions.append(
                {
                    "qkey": r["qkey"],
                    "ordinal": r["ordinal"],
                    "bank_title": r["bank_title"],
                    "subject": r["subject"],
                    "snippet": r["stem_md"][:120],
                }
            )
    courses.sort(key=lambda c: (-c["hits"], c["depth"], c["path"]))
    return courses[:20], questions[:20]


def lookup(conn, query: str, exclude_qkey: str = None) -> dict:
    q = " ".join((query or "").split())
    while len(q) >= LOOKUP_FLOOR:
        courses, questions = _scan(conn, _fold(q), exclude_qkey)
        if courses or questions or len(q) == LOOKUP_FLOOR:
            return {"query_used": q, "courses": courses, "questions": questions}
        q = q[:-1] if len(q) - 1 >= LOOKUP_FLOOR else q[:LOOKUP_FLOOR]
    return {"query_used": q, "courses": [], "questions": []}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_rules -v`
Expected: PASS (16 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/wens-tutor/scripts/tutorlib/compose.py skills/wens-tutor/tests/test_rules.py
git commit -m "feat(wens-tutor): Lookup over Courses and Banks with right-shortening"
```

---

### Task 8: JSON API layer

**Files:**
- Create: `skills/wens-tutor/scripts/tutorlib/api.py`
- Test: `skills/wens-tutor/tests/test_rules.py`

**Interfaces:**
- Consumes: `state`, `compose`, catalogue tables.
- Produces: `handle(conn, method: str, path: str, query: dict, body: dict) -> tuple[int, object]`.

Endpoints: `GET /api/portal`, `GET /api/file?p=`, `GET /api/annotations?p=`, `POST /api/annotation`, `PATCH /api/annotation/<id>`, `DELETE /api/annotation/<id>`, `POST /api/progress`, `POST /api/reading-pos`, `GET /api/lookup?q=&exclude=`, `POST /api/paper`, `GET /api/attempt/<id>`, `PUT /api/attempt/<id>/answer`, `POST /api/attempt/<id>/submit`, `POST /api/star`, `POST /api/note`, `GET /api/stats`.

- [ ] **Step 1: Write the failing test**

```python
from tutorlib import api  # noqa: E402


class TestApi(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "科目A").mkdir()
        (self.tmp / "科目A" / "course.md").write_text("# 章\n\n## 節\n\n內容一段。\n", encoding="utf-8")
        (self.tmp / "科目A" / "bank.md").write_text(
            "### 第 1 題\n\n**答案：A**\n\n題幹\n\n(A) 甲;\n(B) 乙;\n(C) 丙;\n(D) 丁\n", encoding="utf-8"
        )
        self.conn = state.open_root(self.tmp)

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.tmp)

    def test_portal_lists_files_with_progress_and_bank_counts(self):
        code, data = api.handle(self.conn, "GET", "/api/portal", {}, None)
        self.assertEqual(code, 200)
        subjects = {s["subject"] for s in data["subjects"]}
        self.assertEqual(subjects, {"科目A"})
        files = data["subjects"][0]["files"]
        course = next(f for f in files if f["relpath"].endswith("course.md"))
        self.assertEqual(course["leaf_sections"], 1)
        self.assertEqual(course["read_sections"], 0)

    def test_annotation_round_trip_and_orphan_patch(self):
        code, ann = api.handle(
            self.conn,
            "POST",
            "/api/annotation",
            {},
            {"relpath": "科目A/course.md", "block_line": 5, "exact": "內容", "prefix": "", "suffix": "", "color": "yellow", "note_md": ""},
        )
        self.assertEqual(code, 200)
        code, data = api.handle(self.conn, "GET", "/api/annotations", {"p": ["科目A/course.md"]}, None)
        self.assertEqual(len(data["annotations"]), 1)
        code, _ = api.handle(self.conn, "PATCH", f"/api/annotation/{ann['id']}", {}, {"orphan": 1})
        self.assertEqual(code, 200)
        code, data = api.handle(self.conn, "GET", "/api/annotations", {"p": ["科目A/course.md"]}, None)
        self.assertEqual(data["annotations"][0]["orphan"], 1)

    def test_paper_answer_submit_flow(self):
        code, paper = api.handle(self.conn, "POST", "/api/paper", {}, {"cap": 10, "timed": False})
        aid = paper["attempt_id"]
        qkey = paper["questions"][0]["qkey"]
        code, _ = api.handle(self.conn, "PUT", f"/api/attempt/{aid}/answer", {}, {"qkey": qkey, "given": "A", "ms": 900})
        self.assertEqual(code, 200)
        code, result = api.handle(self.conn, "POST", f"/api/attempt/{aid}/submit", {}, {})
        self.assertEqual(result["correct"], 1)
        self.assertEqual(result["score"], 100.0)

    def test_unknown_route_is_404(self):
        code, _ = api.handle(self.conn, "GET", "/api/nope", {}, None)
        self.assertEqual(code, 404)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_rules.TestApi -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tutorlib.api'`

- [ ] **Step 3: Write minimal implementation**

```python
# skills/wens-tutor/scripts/tutorlib/api.py
"""JSON endpoints over the catalogue and user state."""

import json
import re
import time

from . import compose

ANN_ID = re.compile(r"^/api/annotation/(\d+)$")
ATT_ANSWER = re.compile(r"^/api/attempt/(\d+)/answer$")
ATT_SUBMIT = re.compile(r"^/api/attempt/(\d+)/submit$")
ATT_GET = re.compile(r"^/api/attempt/(\d+)$")


def _one(query, key, default=None):
    v = query.get(key)
    return v[0] if isinstance(v, list) and v else (v if v is not None else default)


def _fid(conn, relpath):
    row = conn.execute("SELECT fid FROM cat.file WHERE relpath=?", (relpath,)).fetchone()
    return row["fid"] if row else None


def _questions_of_attempt(conn, attempt_id):
    row = conn.execute(
        "SELECT p.qkeys_json FROM attempt a JOIN paper p ON p.id=a.paper_id WHERE a.id=?",
        (attempt_id,),
    ).fetchone()
    out = []
    for qkey in json.loads(row["qkeys_json"]):
        q = conn.execute(
            "SELECT q.qkey, q.ordinal, q.stem_md, q.options_json, q.explanation_md,"
            " q.explanation_origin, b.title AS bank_title"
            " FROM cat.question q JOIN cat.bank b ON b.bkey=q.bkey WHERE q.qkey=?",
            (qkey,),
        ).fetchone()
        item = conn.execute(
            "SELECT given FROM attempt_item WHERE attempt_id=? AND qkey=?", (attempt_id, qkey)
        ).fetchone()
        d = dict(q)
        d["options"] = json.loads(d.pop("options_json"))
        d["given"] = item["given"] if item else None
        d["starred"] = bool(conn.execute("SELECT 1 FROM star WHERE qkey=?", (qkey,)).fetchone())
        out.append(d)
    return out


def handle(conn, method, path, query, body):
    if path == "/api/portal" and method == "GET":
        subjects = {}
        for f in conn.execute("SELECT * FROM cat.file ORDER BY relpath"):
            s = subjects.setdefault(f["subject"], {"subject": f["subject"], "files": []})
            leaf = conn.execute(
                "SELECT count(*) AS n FROM cat.section WHERE fid=? AND is_leaf=1", (f["fid"],)
            ).fetchone()["n"]
            read = conn.execute(
                "SELECT count(*) AS n FROM progress WHERE fid=?", (f["fid"],)
            ).fetchone()["n"]
            anns = conn.execute(
                "SELECT count(*) AS n, sum(orphan) AS o FROM annotation WHERE fid=?", (f["fid"],)
            ).fetchone()
            banks = [
                dict(b)
                for b in conn.execute(
                    "SELECT b.bkey, b.title, b.shape,"
                    " (SELECT count(*) FROM cat.question q WHERE q.bkey=b.bkey) AS n_questions,"
                    " (SELECT count(*) FROM cat.question q JOIN cat.defect d ON d.qkey=q.qkey WHERE q.bkey=b.bkey) AS defects,"
                    " (SELECT count(*) FROM cat.question q JOIN star s ON s.qkey=q.qkey WHERE q.bkey=b.bkey) AS stars"
                    " FROM cat.bank b WHERE b.fid=? ORDER BY b.path",
                    (f["fid"],),
                )
            ]
            s["files"].append(
                {
                    "relpath": f["relpath"],
                    "title": f["title"],
                    "leaf_sections": leaf,
                    "read_sections": read,
                    "annotations": anns["n"] or 0,
                    "orphans": anns["o"] or 0,
                    "banks": banks,
                }
            )
        in_flight = [
            dict(r)
            for r in conn.execute(
                "SELECT a.id AS attempt_id, a.paper_id, a.started, p.limit_ms, p.criteria_json"
                " FROM attempt a JOIN paper p ON p.id=a.paper_id WHERE a.finished IS NULL"
            )
        ]
        latest = [
            dict(r)
            for r in conn.execute(
                "SELECT id, finished, total, correct, round(correct*100.0/total,1) AS score"
                " FROM attempt WHERE finished IS NOT NULL ORDER BY finished DESC LIMIT 5"
            )
        ]
        return 200, {"subjects": list(subjects.values()), "in_flight": in_flight, "latest": latest}

    if path == "/api/file" and method == "GET":
        rel = _one(query, "p")
        f = conn.execute("SELECT * FROM cat.file WHERE relpath=?", (rel,)).fetchone()
        if not f:
            return 404, {"error": "unknown file"}
        secs = [dict(s) for s in conn.execute(
            "SELECT path, level, title, is_leaf, line_start FROM cat.section WHERE fid=? ORDER BY line_start",
            (f["fid"],),
        )]
        read = {r["path"] for r in conn.execute("SELECT path FROM progress WHERE fid=?", (f["fid"],))}
        for s in secs:
            s["read"] = s["path"] in read
        pos = conn.execute("SELECT line FROM reading_pos WHERE fid=?", (f["fid"],)).fetchone()
        return 200, {"relpath": rel, "title": f["title"], "sections": secs,
                     "reading_pos": pos["line"] if pos else None}

    if path == "/api/annotations" and method == "GET":
        fid = _fid(conn, _one(query, "p"))
        rows = [dict(r) for r in conn.execute("SELECT * FROM annotation WHERE fid=? ORDER BY id", (fid,))]
        return 200, {"annotations": rows}

    if path == "/api/annotation" and method == "POST":
        fid = _fid(conn, body["relpath"])
        cur = conn.execute(
            "INSERT INTO annotation(fid, block_line, exact, prefix, suffix, color, note_md, ts, orphan)"
            " VALUES (?,?,?,?,?,?,?,?,0)",
            (fid, body["block_line"], body["exact"], body.get("prefix", ""), body.get("suffix", ""),
             body.get("color", "yellow"), body.get("note_md", ""), time.time()),
        )
        conn.commit()
        return 200, {"id": cur.lastrowid}

    m = ANN_ID.match(path)
    if m and method == "PATCH":
        sets, args = [], []
        for k in ("orphan", "color", "note_md"):
            if k in body:
                sets.append(f"{k}=?")
                args.append(body[k])
        if sets:
            conn.execute(f"UPDATE annotation SET {','.join(sets)} WHERE id=?", args + [int(m.group(1))])
            conn.commit()
        return 200, {"ok": True}
    if m and method == "DELETE":
        conn.execute("DELETE FROM annotation WHERE id=?", (int(m.group(1)),))
        conn.commit()
        return 200, {"ok": True}

    if path == "/api/progress" and method == "POST":
        fid = _fid(conn, body["relpath"])
        if body.get("read"):
            conn.execute("INSERT OR REPLACE INTO progress VALUES (?,?,?)", (fid, body["path"], time.time()))
        else:
            conn.execute("DELETE FROM progress WHERE fid=? AND path=?", (fid, body["path"]))
        conn.commit()
        return 200, {"ok": True}

    if path == "/api/reading-pos" and method == "POST":
        fid = _fid(conn, body["relpath"])
        conn.execute("INSERT OR REPLACE INTO reading_pos VALUES (?,?,?)", (fid, body["line"], time.time()))
        conn.commit()
        return 200, {"ok": True}

    if path == "/api/lookup" and method == "GET":
        return 200, compose.lookup(conn, _one(query, "q", ""), _one(query, "exclude"))

    if path == "/api/paper" and method == "POST":
        pid = compose.compose(conn, body or {})
        aid = compose.start_attempt(conn, pid)
        return 200, {
            "paper_id": pid,
            "attempt_id": aid,
            "remaining_ms": compose.remaining_ms(conn, aid),
            "questions": _questions_of_attempt(conn, aid),
        }

    m = ATT_GET.match(path)
    if m and method == "GET":
        aid = int(m.group(1))
        return 200, {
            "attempt_id": aid,
            "remaining_ms": compose.remaining_ms(conn, aid),
            "questions": _questions_of_attempt(conn, aid),
        }

    m = ATT_ANSWER.match(path)
    if m and method == "PUT":
        compose.answer(conn, int(m.group(1)), body["qkey"], body["given"], body.get("ms", 0))
        return 200, {"ok": True}

    m = ATT_SUBMIT.match(path)
    if m and method == "POST":
        return 200, compose.submit(conn, int(m.group(1)))

    if path == "/api/star" and method == "POST":
        return 200, {"starred": compose.toggle_star(conn, body["qkey"])}

    if path == "/api/note" and method == "POST":
        conn.execute(
            "INSERT INTO note VALUES (?,?,?) ON CONFLICT(qkey) DO UPDATE SET note_md=excluded.note_md, ts=excluded.ts",
            (body["qkey"], body.get("note_md", ""), time.time()),
        )
        conn.commit()
        return 200, {"ok": True}

    if path == "/api/stats" and method == "GET":
        return 200, compose.stats(conn)

    return 404, {"error": "unknown endpoint"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_rules -v`
Expected: PASS (20 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/wens-tutor/scripts/tutorlib/api.py skills/wens-tutor/tests/test_rules.py
git commit -m "feat(wens-tutor): JSON API over catalogue and user state"
```

---

### Task 9: Export/import of user state

**Files:**
- Modify: `skills/wens-tutor/scripts/tutorlib/state.py`
- Test: `skills/wens-tutor/tests/test_rules.py`

**Interfaces:**
- Consumes: `state.open_root`.
- Produces: `state.export_json(conn, root) -> Path`; `state.import_json(conn, root, merge=False) -> dict`; `state.json_path(root) -> Path`.

Read ADR 0009 first.

- [ ] **Step 1: Write the failing test**

```python
class TestExportImport(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "科目A").mkdir()
        (self.tmp / "科目A" / "bank.md").write_text(
            "### 第 1 題\n\n**答案：A**\n\n題幹\n\n(A) 甲;\n(B) 乙;\n(C) 丙;\n(D) 丁\n", encoding="utf-8"
        )
        self.conn = state.open_root(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_round_trip_restores_every_row(self):
        qkey = self.conn.execute("SELECT qkey FROM cat.question").fetchone()["qkey"]
        compose.toggle_star(self.conn, qkey)
        fid = self.conn.execute("SELECT fid FROM cat.file").fetchone()["fid"]
        self.conn.execute("INSERT INTO progress VALUES (?,?,0)", (fid, "第-1-題"))
        self.conn.commit()
        p = state.export_json(self.conn, self.tmp)
        self.assertTrue(p.exists())
        self.conn.close()

        state.db_path(self.tmp).unlink()
        conn2 = state.open_root(self.tmp)
        self.assertEqual(conn2.execute("SELECT count(*) FROM star").fetchone()[0], 0)
        state.import_json(conn2, self.tmp)
        self.assertEqual(conn2.execute("SELECT qkey FROM star").fetchone()[0], qkey)
        self.assertEqual(conn2.execute("SELECT count(*) FROM progress").fetchone()[0], 1)
        conn2.close()

    def test_merge_unions_rows_from_two_devices(self):
        qkey = self.conn.execute("SELECT qkey FROM cat.question").fetchone()["qkey"]
        compose.toggle_star(self.conn, qkey)
        self.conn.commit()
        state.export_json(self.conn, self.tmp)
        payload = json.loads(state.json_path(self.tmp).read_text(encoding="utf-8"))
        payload["note"].append({"qkey": qkey, "note_md": "另一台裝置寫的", "ts": 1.0})
        state.json_path(self.tmp).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        state.import_json(self.conn, self.tmp, merge=True)
        self.assertEqual(
            self.conn.execute("SELECT note_md FROM note WHERE qkey=?", (qkey,)).fetchone()[0],
            "另一台裝置寫的",
        )
        self.assertEqual(self.conn.execute("SELECT count(*) FROM star").fetchone()[0], 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_rules.TestExportImport -v`
Expected: FAIL — `AttributeError: module 'tutorlib.state' has no attribute 'export_json'`

- [ ] **Step 3: Write minimal implementation**

Add to `state.py`:

```python
TABLES = (
    "file_id",
    "annotation",
    "progress",
    "reading_pos",
    "star",
    "note",
    "paper",
    "attempt",
    "attempt_item",
)


def json_path(root: Path) -> Path:
    return Path(root) / ".tutor" / "tutor.json"


def export_json(conn: sqlite3.Connection, root: Path) -> Path:
    payload = {"version": 1}
    for t in TABLES:
        payload[t] = [dict(r) for r in conn.execute(f"SELECT * FROM {t}")]
    p = json_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    return p


def import_json(conn: sqlite3.Connection, root: Path, merge: bool = False) -> dict:
    payload = json.loads(json_path(root).read_text(encoding="utf-8"))
    counts = {}
    for t in TABLES:
        rows = payload.get(t) or []
        if not merge:
            conn.execute(f"DELETE FROM {t}")
        for row in rows:
            cols = ",".join(row.keys())
            marks = ",".join("?" * len(row))
            conn.execute(
                f"INSERT OR REPLACE INTO {t}({cols}) VALUES ({marks})", list(row.values())
            )
        counts[t] = len(rows)
    conn.commit()
    return counts
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_rules -v`
Expected: PASS (22 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/wens-tutor/scripts/tutorlib/state.py skills/wens-tutor/tests/test_rules.py
git commit -m "feat(wens-tutor): export and import user state as JSON"
```

---

### Task 10: Server with two static roots, path containment, and the token gate

**Files:**
- Create: `skills/wens-tutor/scripts/tutorlib/server.py`
- Test: `skills/wens-tutor/tests/test_rules.py`

**Interfaces:**
- Consumes: `api.handle`, `state.open_root`, `registry`.
- Produces: `serve(root, port, bind, token=None, open_browser=False) -> None`; `safe_material_path(root, relpath) -> Path | None`.

Read ADR 0010 first.

- [ ] **Step 1: Write the failing test**

```python
from tutorlib import server  # noqa: E402


class TestPathContainment(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "科目A").mkdir()
        (self.tmp / "科目A" / "a.md").write_text("# x\n", encoding="utf-8")
        (self.tmp / "secret.txt").write_text("no", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_allows_a_markdown_file_inside_the_root(self):
        self.assertIsNotNone(server.safe_material_path(self.tmp, "科目A/a.md"))

    def test_refuses_traversal_absolute_and_non_markdown(self):
        for bad in ["../../etc/passwd", "/etc/passwd", "secret.txt", "科目A/../../x.md"]:
            self.assertIsNone(server.safe_material_path(self.tmp, bad), bad)

    def test_refuses_a_symlink_even_inside_the_root(self):
        link = self.tmp / "科目A" / "link.md"
        link.symlink_to(self.tmp / "secret.txt")
        self.assertIsNone(server.safe_material_path(self.tmp, "科目A/link.md"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_rules.TestPathContainment -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tutorlib.server'`

- [ ] **Step 3: Write minimal implementation**

```python
# skills/wens-tutor/scripts/tutorlib/server.py
"""One process, two static roots, JSON API, optional token gate (ADR 0010)."""

import hmac
import http.cookies
import json
import mimetypes
import os
import posixpath
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import api, state

WEB = Path(__file__).resolve().parents[2] / "web"
PAGES = {"/": "index.html", "/reader": "reader.html", "/exam": "exam.html", "/stats": "stats.html"}
LOOPBACK = ("127.0.0.1", "::1", "localhost")


def safe_material_path(root, relpath: str):
    root = Path(root).resolve()
    rel = urllib.parse.unquote(relpath or "")
    if rel.startswith("/") or not rel.endswith(".md"):
        return None
    candidate = (root / rel)
    if candidate.is_symlink():
        return None
    try:
        resolved = candidate.resolve(strict=True)
    except OSError:
        return None
    if os.path.commonpath([str(resolved), str(root)]) != str(root):
        return None
    if resolved != candidate.absolute() and not str(candidate.absolute()).startswith(str(root)):
        return None
    return resolved if resolved.is_file() else None


def safe_web_path(relpath: str):
    clean = posixpath.normpath("/" + (relpath or "")).lstrip("/")
    p = (WEB / clean).resolve()
    if os.path.commonpath([str(p), str(WEB.resolve())]) != str(WEB.resolve()):
        return None
    return p if p.is_file() else None


def make_handler(root, conn, lock, token):
    class Handler(BaseHTTPRequestHandler):
        server_version = "wens-tutor"

        def log_message(self, *a):
            pass  # ui-design-principles 21: never pollute the surface

        def _authorised(self):
            if not token:
                return True
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            supplied = (qs.get("t") or [None])[0]
            if supplied and hmac.compare_digest(supplied, token):
                self._set_cookie = True
                return True
            raw = self.headers.get("Cookie", "")
            jar = http.cookies.SimpleCookie(raw)
            got = jar["tutor_token"].value if "tutor_token" in jar else ""
            return bool(got) and hmac.compare_digest(got, token)

        def _send(self, code, body: bytes, ctype: str):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            if getattr(self, "_set_cookie", False):
                self.send_header("Set-Cookie", f"tutor_token={token}; HttpOnly; Path=/; SameSite=Lax")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _dispatch(self):
            if not self._authorised():
                return self._send(403, b"forbidden", "text/plain; charset=utf-8")
            parsed = urllib.parse.urlparse(self.path)
            path, query = parsed.path, urllib.parse.parse_qs(parsed.query)

            if path.startswith("/api/"):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or "null") if length else None
                with lock:
                    code, payload = api.handle(conn, self.command, path, query, body)
                return self._json(code, payload)

            if path.startswith("/raw/"):
                p = safe_material_path(root, path[len("/raw/"):])
                if not p:
                    return self._send(404, b"not found", "text/plain; charset=utf-8")
                return self._send(200, p.read_bytes(), "text/markdown; charset=utf-8")

            name = PAGES.get(path)
            p = safe_web_path(name) if name else safe_web_path(path.lstrip("/"))
            if not p:
                return self._send(404, b"not found", "text/plain; charset=utf-8")
            ctype = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
                ctype += "; charset=utf-8"
            return self._send(200, p.read_bytes(), ctype)

        do_GET = do_PUT = do_POST = do_PATCH = do_DELETE = do_HEAD = _dispatch

    return Handler


def serve(root, port=8765, bind="127.0.0.1", token=None, open_browser=False) -> None:
    root = Path(root)
    if bind not in LOOPBACK and not token:
        raise SystemExit("refusing to bind %s without a token; run `tutor.py init` first" % bind)
    conn = state.open_root(root)
    report = state.reconcile(conn, root)
    if report["relinked_questions"] or report["unresolved"]:
        print("reconciled:", json.dumps(report, ensure_ascii=False))
    lock = threading.Lock()
    httpd = ThreadingHTTPServer((bind, port), make_handler(root, conn, lock, token))
    shown = "127.0.0.1" if bind in ("0.0.0.0", "::") else bind
    url = "http://%s:%d/%s" % (shown, port, ("?t=" + token) if token else "")
    print(url)
    if open_browser:
        webbrowser.open(url)
    httpd.serve_forever()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest tests.test_rules -v`
Expected: PASS (25 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/wens-tutor/scripts/tutorlib/server.py skills/wens-tutor/tests/test_rules.py
git commit -m "feat(wens-tutor): serve two static roots with containment and a token gate"
```

---

### Task 11: CLI with the three-level check contract

**Files:**
- Create: `skills/wens-tutor/scripts/tutor.py`
- Test: manual runs against the real Materials Root (documented below)

**Interfaces:**
- Consumes: everything above.
- Produces: subcommands `init`, `check`, `relink`, `new course`, `new bank`, `serve`, `stats`, `export`, `import`. Exit codes: 0 clean, 1 content findings, 2 usage/I/O failure.

- [ ] **Step 1: Write the implementation**

```python
#!/usr/bin/env python3
"""wens-tutor CLI. Dispatch only — logic lives in tutorlib."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tutorlib import compose, parser, registry, server, state  # noqa: E402

SKELETON_COURSE = """# {title}

## 1. 前言

（在此撰寫內容）
"""

SKELETON_BANK_EXAM = """# {title}

## 一、選擇題

### 第 1 題

**答案：A**

（題幹）

(A) 甲;
(B) 乙;
(C) 丙;
(D) 丁
"""


def resolve_root(args):
    if getattr(args, "root", None):
        return Path(args.root).expanduser().resolve()
    r = registry.default_root()
    if not r:
        print("no root registered; run: tutor.py init <root>", file=sys.stderr)
        raise SystemExit(2)
    if not r.exists():
        print("registered root is missing: %s" % r, file=sys.stderr)
        raise SystemExit(2)
    return r


def cmd_init(args):
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print("not a directory: %s" % root, file=sys.stderr)
        return 2
    data = registry.add_root(root)
    conn = state.open_root(root)
    conn.close()
    print("registered %s\ntoken %s" % (root, data["token"]))
    return 0


def cmd_check(args):
    root = resolve_root(args)
    findings = []
    try:
        conn = state.open_root(root)
    except OSError as exc:
        print("cannot open state: %s" % exc, file=sys.stderr)
        return 2

    for r in conn.execute(
        "SELECT d.kind, q.ordinal, b.title, f.relpath FROM cat.defect d"
        " JOIN cat.question q ON q.qkey=d.qkey JOIN cat.bank b ON b.bkey=q.bkey"
        " JOIN cat.file f ON f.fid=b.fid ORDER BY f.relpath, q.ordinal"
    ):
        findings.append("%s: %s 第%d題 (%s)" % (r["kind"], r["relpath"], r["ordinal"], r["title"]))

    for r in conn.execute(
        "SELECT q.ordinal, f.relpath, q.options_json FROM cat.question q"
        " JOIN cat.bank b ON b.bkey=q.bkey JOIN cat.file f ON f.fid=b.fid"
    ):
        if len(json.loads(r["options_json"])) != 4:
            findings.append("option_count: %s 第%d題" % (r["relpath"], r["ordinal"]))

    for p in state.catalog.material_files(root):
        md = p.read_text(encoding="utf-8")
        secs, banks = parser.parse_file(md)
        if parser.QHEAD.search(md) and not banks:
            findings.append("unparsed_bank: %s" % p.name)
        titles = [s.title.strip() for s in secs]
        for i, t in enumerate(titles):
            if t == "選擇題":
                nxt = titles[i + 1] if i + 1 < len(titles) else ""
                if nxt != "解答與解析":
                    findings.append("unpaired_guide_bank: %s / %s" % (p.name, secs[i].path))

    report = state.reconcile(conn, root)
    for item in report["relinked_questions"]:
        findings.append("relinked: %s -> %s" % (item["from"], item["to"]))
    for old in report["unresolved"]:
        findings.append("unresolved_qkey: %s" % old)

    for r in conn.execute(
        "SELECT p.fid, p.path FROM progress p LEFT JOIN cat.section s"
        " ON s.fid=p.fid AND s.path=p.path WHERE s.path IS NULL"
    ):
        findings.append("stale_progress: %s %s" % (r["fid"], r["path"]))

    n_orphan = conn.execute("SELECT count(*) AS n FROM annotation WHERE orphan=1").fetchone()["n"]
    if n_orphan:
        findings.append("orphan_annotations: %d" % n_orphan)

    jp = state.json_path(root)
    if jp.exists():
        newest = conn.execute(
            "SELECT max(ts) AS t FROM (SELECT max(ts) AS ts FROM star UNION ALL"
            " SELECT max(ts) FROM annotation UNION ALL SELECT max(ts) FROM note)"
        ).fetchone()["t"]
        if newest and jp.stat().st_mtime < newest:
            findings.append("stale_export: run `tutor.py export`")

    for line in findings:
        print(line)
    print("%d finding(s)" % len(findings))
    return 1 if findings else 0


def cmd_relink(args):
    root = resolve_root(args)
    conn = state.open_root(root)
    fid = conn.execute("SELECT fid FROM file_id WHERE relpath=?", (args.old,)).fetchone()
    if not fid:
        print("no user state recorded for %s" % args.old, file=sys.stderr)
        return 2
    conn.execute("UPDATE file_id SET relpath=? WHERE fid=?", (args.new, fid["fid"]))
    conn.commit()
    print("relinked %s -> %s" % (args.old, args.new))
    return 0


def cmd_new(args):
    root = resolve_root(args)
    target = root / args.subject
    target.mkdir(parents=True, exist_ok=True)
    path = target / (args.title + ".md")
    if path.exists():
        print("exists: %s" % path, file=sys.stderr)
        return 2
    if args.kind == "course":
        path.write_text(SKELETON_COURSE.format(title=args.title), encoding="utf-8")
    else:
        body = [SKELETON_BANK_EXAM.format(title=args.title)]
        for i in range(2, args.questions + 1):
            body.append(
                "### 第 %d 題\n\n**答案：A**\n\n（題幹）\n\n(A) 甲;\n(B) 乙;\n(C) 丙;\n(D) 丁\n" % i
            )
        path.write_text("\n".join(body), encoding="utf-8")
    print(path)
    return 0


def cmd_serve(args):
    root = resolve_root(args)
    data = registry.load()
    server.serve(
        root,
        port=args.port or data.get("port", 8765),
        bind=args.bind,
        token=data.get("token"),
        open_browser=args.open,
    )
    return 0


def cmd_stats(args):
    root = resolve_root(args)
    conn = state.open_root(root)
    s = compose.stats(conn)
    print("attempts: %d" % len(s["scores"]))
    for row in s["scores"][-10:]:
        print("  score %5.1f  %d/%d%s" % (row["score"], row["correct"], row["total"],
                                          "  EXPIRED" if row["expired"] else ""))
    print("pace: %s s/question (official %d)" % (s["pace_seconds_per_question"], s["official_pace_seconds"]))
    print("stars: %d   defects: %d" % (s["stars"], s["defects"]))
    print("most missed:")
    for row in s["most_missed"][:10]:
        print("  %s x%d" % (row["qkey"], row["wrong_count"]))
    return 0


def cmd_export(args):
    root = resolve_root(args)
    conn = state.open_root(root)
    print(state.export_json(conn, root))
    return 0


def cmd_import(args):
    root = resolve_root(args)
    conn = state.open_root(root)
    if not state.json_path(root).exists():
        print("no export at %s" % state.json_path(root), file=sys.stderr)
        return 2
    print(json.dumps(state.import_json(conn, root, merge=args.merge), ensure_ascii=False))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tutor.py")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init"); p.add_argument("root"); p.set_defaults(fn=cmd_init)
    p = sub.add_parser("check"); p.add_argument("--root"); p.set_defaults(fn=cmd_check)
    p = sub.add_parser("relink"); p.add_argument("old"); p.add_argument("new")
    p.add_argument("--root"); p.set_defaults(fn=cmd_relink)
    p = sub.add_parser("new"); p.add_argument("kind", choices=["course", "bank"])
    p.add_argument("subject"); p.add_argument("title"); p.add_argument("--questions", type=int, default=10)
    p.add_argument("--root"); p.set_defaults(fn=cmd_new)
    p = sub.add_parser("serve"); p.add_argument("--root"); p.add_argument("--port", type=int)
    p.add_argument("--bind", default="127.0.0.1"); p.add_argument("--open", action="store_true")
    p.set_defaults(fn=cmd_serve)
    p = sub.add_parser("stats"); p.add_argument("--root"); p.set_defaults(fn=cmd_stats)
    p = sub.add_parser("export"); p.add_argument("--root"); p.set_defaults(fn=cmd_export)
    p = sub.add_parser("import"); p.add_argument("--root")
    p.add_argument("--merge", action="store_true"); p.set_defaults(fn=cmd_import)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
```

Add `import catalog` access used by `cmd_check` by exposing it in `state.py`: add `from . import catalog` (already imported) and nothing else — `state.catalog.material_files` resolves.

- [ ] **Step 2: Verify the three exit codes by hand**

```bash
cd skills/wens-tutor
export WENS_TUTOR_CONFIG=/tmp/wens-tutor-test.json
uv run --python 3.14 python3 scripts/tutor.py check ; echo "exit=$?"   # expect 2 (no root registered)
uv run --python 3.14 python3 scripts/tutor.py init ~/repos/wenswiki/wenswiki/work/平台/2026_AI應用規劃師
uv run --python 3.14 python3 scripts/tutor.py check ; echo "exit=$?"   # expect 1, 26 defect lines
```

Expected: first `exit=2`; after `init`, `exit=1` with 3 `no_answer` and 23 `figure_missing` lines.

- [ ] **Step 3: Verify `stats` and `export` run clean**

```bash
uv run --python 3.14 python3 scripts/tutor.py stats
uv run --python 3.14 python3 scripts/tutor.py export
git -C ~/repos/wenswiki/wenswiki/work/平台/2026_AI應用規劃師 status --short
```

Expected: `stats` prints zero attempts, 0 stars, 26 defects; `export` prints the `.tutor/tutor.json` path; git shows exactly two new untracked paths under `.tutor/`.

- [ ] **Step 4: Commit**

```bash
git add skills/wens-tutor/scripts/tutor.py
git commit -m "feat(wens-tutor): CLI with the three-level check contract"
```

---

### Task 12: Web shell — strings, host detection, API client, renderer

**Files:**
- Create: `skills/wens-tutor/web/strings.js`
- Create: `skills/wens-tutor/web/app/host.js`
- Create: `skills/wens-tutor/web/app/api.js`
- Create: `skills/wens-tutor/web/app/render.js`
- Create: `skills/wens-tutor/web/style.css`
- Create: `skills/wens-tutor/web/manifest.webmanifest`
- Create: `skills/wens-tutor/web/vendor/markdown-it.min.js` (vendored)

**Interfaces:**
- Produces: `S` (strings object, default export of `strings.js`); `host.isTouch`, `host.openLookupResult(url)`; `api.get/post/put/patch/del`; `render.renderInto(el, md)`, `render.anchor(el, ann)`, `render.quoteFromSelection(el)`.

Read ADR 0008 and ADR 0010 first.

- [ ] **Step 1: Vendor markdown-it and verify it loads**

```bash
cd skills/wens-tutor/web/vendor
curl -fsSLO https://unpkg.com/markdown-it@14/dist/markdown-it.min.js
uv run --python 3.14 python3 -c "import pathlib;p=pathlib.Path('markdown-it.min.js');print(p.stat().st_size)"
```

Expected: a file of roughly 100 KB. Commit it as-is; it is the only dependency.

- [ ] **Step 2: Write the four modules**

```js
// skills/wens-tutor/web/strings.js — every user-facing string (ui-design-principles 22)
export const S = {
  app: "wens-tutor",
  portal: { title: "複習入口", courses: "課程", banks: "題庫", progress: "進度",
            annotations: "標註", orphans: "失效標註", stars: "重點題", defects: "殘缺題",
            newPaper: "開始模擬考", drill: "重點模式", stats: "統計", inFlight: "進行中" },
  reader: { toc: "章節", read: "已讀", highlight: "畫線", note: "註記", del: "刪除",
            orphanList: "失效標註（原文找不到了）", lookup: "查課程", resume: "回到上次位置" },
  exam: { compose: "出卷", subjects: "科目", banks: "題庫", cap: "題數", shuffle: "洗題",
          timed: "計時", includeDefective: "含殘缺題", start: "開始",
          submit: "交卷", remaining: "剩餘", expired: "已逾時", score: "分數",
          pass: "及格（60）", wrongOnly: "錯題", explanation: "解析", myNote: "我的筆記",
          star: "重點題", courseTab: "課程", bankTab: "考古題", queryUsed: "實際查詢" },
  stats: { title: "統計", scores: "分數趨勢", pace: "作答節奏", missed: "最常錯的題目",
           perBank: "各題庫", trend: "重點題與殘缺題" },
  keys: { esc: "Esc 返回", enter: "Enter 確認", arrows: "← → 換題", digits: "1-4 選項" },
  about: { help: "說明", version: "版本", project: "專案", license: "授權" },
};
export default S;
```

```js
// skills/wens-tutor/web/app/host.js — one host decision, not scattered media queries (ADR 0010)
export const isTouch = window.matchMedia("(pointer: coarse)").matches;

export function openLookupResult(url) {
  if (!isTouch) { window.open(url, "_blank", "noopener"); return null; }
  const panel = document.createElement("aside");
  panel.className = "slideover";
  panel.innerHTML = `<iframe src="${url}" title="lookup"></iframe>`;
  panel.addEventListener("click", (e) => { if (e.target === panel) panel.remove(); });
  document.body.appendChild(panel);
  return panel;
}

export function mountSelectionBar(el) {
  el.classList.toggle("selection-bar--bottom", isTouch);
  el.classList.toggle("selection-bar--float", !isTouch);
  return el;
}
```

```js
// skills/wens-tutor/web/app/api.js
const base = "";
async function req(method, path, body) {
  const res = await fetch(base + path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(method + " " + path + " -> " + res.status);
  return res.json();
}
export const get = (p) => req("GET", p);
export const post = (p, b) => req("POST", p, b || {});
export const put = (p, b) => req("PUT", p, b || {});
export const patch = (p, b) => req("PATCH", p, b || {});
export const del = (p) => req("DELETE", p);
```

```js
// skills/wens-tutor/web/app/render.js — markdown-it + data-line stamping + text-quote anchoring
const md = window.markdownit({ html: false, linkify: false });
const stamp = (tokens, idx, options, env, self) => {
  const t = tokens[idx];
  if (t.map) t.attrSet("data-line", String(t.map[0] + 1));
  return self.renderToken(tokens, idx, options);
};
for (const rule of ["paragraph_open", "heading_open", "table_open", "blockquote_open",
                    "bullet_list_open", "ordered_list_open"]) {
  md.renderer.rules[rule] = stamp;
}

export function renderInto(el, source) {
  el.innerHTML = md.render(source);
  return el;
}

export function blocks(el) {
  return Array.from(el.querySelectorAll("[data-line]"));
}

/** Wrap `ann.exact` in a mark; returns true when anchored, false when orphaned. */
export function anchor(el, ann) {
  const all = blocks(el);
  const preferred = all.filter((b) => Number(b.dataset.line) === ann.block_line);
  const attempts = [
    { list: preferred, needle: (ann.prefix || "") + ann.exact + (ann.suffix || "") },
    { list: preferred, needle: ann.exact },
    { list: all, needle: ann.exact },
  ];
  for (const { list, needle } of attempts) {
    for (const block of list) {
      const idx = block.textContent.indexOf(needle);
      if (idx < 0) continue;
      const start = idx + (needle === ann.exact ? 0 : (ann.prefix || "").length);
      if (wrapTextRange(block, start, ann.exact.length, ann)) return true;
    }
  }
  return false;
}

function wrapTextRange(block, start, length, ann) {
  const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT);
  let seen = 0, node, range = document.createRange(), set = false;
  while ((node = walker.nextNode())) {
    const next = seen + node.nodeValue.length;
    if (!set && next > start) { range.setStart(node, start - seen); set = true; }
    if (set && next >= start + length) { range.setEnd(node, start + length - seen); break; }
    seen = next;
  }
  if (!set) return false;
  const mark = document.createElement("mark");
  mark.className = "ann ann--" + (ann.color || "yellow");
  mark.dataset.annId = ann.id;
  if (ann.note_md) mark.dataset.note = ann.note_md;
  try { range.surroundContents(mark); } catch (_) { return false; }
  return true;
}

/** {block_line, exact, prefix, suffix} for the current selection, or null. */
export function quoteFromSelection(el) {
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed) return null;
  const exact = sel.toString().trim();
  if (!exact) return null;
  let node = sel.anchorNode;
  while (node && node !== el && !(node.dataset && node.dataset.line)) node = node.parentNode;
  if (!node || node === el) return null;
  const text = node.textContent;
  const at = text.indexOf(exact);
  return {
    block_line: Number(node.dataset.line),
    exact,
    prefix: at > 0 ? text.slice(Math.max(0, at - 32), at) : "",
    suffix: at >= 0 ? text.slice(at + exact.length, at + exact.length + 32) : "",
  };
}
```

```css
/* skills/wens-tutor/web/style.css — fluid, no hardcoded widths (ui-design-principles 19) */
:root { --gap: 1rem; --hit: 44px; }
* { box-sizing: border-box; }
body { margin: 0; font: 16px/1.7 system-ui, "Noto Sans TC", sans-serif; }
header.app { display: flex; gap: var(--gap); align-items: baseline; padding: .5rem var(--gap); border-bottom: 1px solid #ddd; }
footer.keys { position: sticky; bottom: 0; padding: .4rem var(--gap); border-top: 1px solid #ddd; background: #fff; font-size: .85rem; }
.layout { display: grid; gap: var(--gap); padding: var(--gap); grid-template-columns: minmax(12rem, 20%) 1fr minmax(12rem, 22%); }
@media (max-width: 60rem) { .layout { grid-template-columns: 1fr; } .drawer { display: none; } .drawer.open { display: block; } }
.focus { outline: 3px solid #0b5; outline-offset: 2px; }
mark.ann--yellow { background: #fff3a3; } mark.ann--green { background: #b9f6c1; }
mark.ann--blue { background: #b3e0ff; } mark.ann--pink { background: #ffc7e0; }
.selection-bar--float { position: absolute; }
.selection-bar--bottom { position: fixed; left: 0; right: 0; bottom: 0; display: flex; }
.selection-bar--bottom button { min-height: var(--hit); flex: 1; }
.slideover { position: fixed; inset: 0; background: rgba(0,0,0,.35); }
.slideover iframe { position: absolute; inset: 10% 0 0 0; width: 100%; height: 90%; border: 0; background: #fff; }
.option { display: block; width: 100%; text-align: start; min-height: var(--hit); }
.orphan { border-inline-start: 4px solid #d33; padding-inline-start: .5rem; }
```

```json
{
  "name": "wens-tutor",
  "short_name": "tutor",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#0b5",
  "icons": []
}
```

- [ ] **Step 3: Smoke-verify the renderer in the real browser**

Start the server, open the portal route, and check that markdown-it and the modules load:

```bash
cd skills/wens-tutor
uv run --python 3.14 python3 scripts/tutor.py serve --port 8765 &
```

In the browser tool: open `http://127.0.0.1:8765/?t=<token>`, then evaluate
`typeof window.markdownit` → `"function"`, and `(await import('/app/render.js')).renderInto` → a function.

Expected: both truthy, no console errors.

- [ ] **Step 4: Commit**

```bash
git add skills/wens-tutor/web
git commit -m "feat(wens-tutor): web shell — strings, host switch, api client, renderer"
```

---

### Task 13: Portal page

**Files:**
- Create: `skills/wens-tutor/web/index.html`
- Create: `skills/wens-tutor/web/app/portal.js`

**Interfaces:**
- Consumes: `api.get`, `S`.
- Produces: nothing for later tasks.

- [ ] **Step 1: Write the page**

```html
<!doctype html>
<html lang="zh-Hant">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="stylesheet" href="/style.css">
<title>wens-tutor</title>
<header class="app"><strong id="appname"></strong><span id="version"></span>
  <button id="help" type="button"></button></header>
<main id="root" class="layout" style="grid-template-columns: 1fr"></main>
<footer class="keys" id="keys"></footer>
<script type="module" src="/app/portal.js"></script>
</html>
```

```js
// skills/wens-tutor/web/app/portal.js
import S from "/strings.js";
import * as api from "/app/api.js";

const el = (tag, props = {}, ...kids) => Object.assign(document.createElement(tag), props, {}) &&
  (() => { const n = document.createElement(tag); Object.assign(n, props); kids.forEach(k => n.append(k)); return n; })();

function courseCard(f) {
  const pct = f.leaf_sections ? Math.round((f.read_sections / f.leaf_sections) * 100) : 0;
  const card = el("article", { className: "card" });
  const link = el("a", { href: `/reader?p=${encodeURIComponent(f.relpath)}`, textContent: f.title });
  const bar = el("progress");
  bar.max = f.leaf_sections || 1; bar.value = f.read_sections;
  card.append(link, bar, el("span", {
    textContent: ` ${S.portal.progress} ${pct}% · ${S.portal.annotations} ${f.annotations}` +
      (f.orphans ? ` · ${S.portal.orphans} ${f.orphans}` : ""),
  }));
  return card;
}

function bankCard(f, b) {
  const card = el("article", { className: "card" });
  card.append(
    el("a", { href: `/exam?bkey=${encodeURIComponent(b.bkey)}`, textContent: `${f.title} — ${b.title}` }),
    el("span", {
      textContent: ` ${b.n_questions} 題 · ${S.portal.stars} ${b.stars}` +
        (b.defects ? ` · ${S.portal.defects} ${b.defects}` : ""),
    }),
  );
  return card;
}

async function main() {
  document.getElementById("appname").textContent = S.app;
  document.getElementById("keys").textContent = [S.keys.esc, S.keys.enter].join("　");
  const data = await api.get("/api/portal");
  const root = document.getElementById("root");

  const actions = el("nav");
  actions.append(
    el("a", { href: "/exam", textContent: S.portal.newPaper }),
    el("a", { href: "/exam?drill=1", textContent: S.portal.drill }),
    el("a", { href: "/stats", textContent: S.portal.stats }),
  );
  root.append(actions);

  for (const a of data.in_flight) {
    root.append(el("a", {
      href: `/exam?attempt=${a.attempt_id}`,
      className: "card in-flight",
      textContent: `${S.portal.inFlight} · attempt #${a.attempt_id}`,
    }));
  }

  for (const s of data.subjects) {
    const sec = el("section");
    sec.append(el("h2", { textContent: s.subject }));
    sec.append(el("h3", { textContent: S.portal.courses }));
    for (const f of s.files) if (!f.banks.length) sec.append(courseCard(f));
    sec.append(el("h3", { textContent: S.portal.banks }));
    for (const f of s.files) for (const b of f.banks) sec.append(bankCard(f, b));
    root.append(sec);
  }
}
main();
```

- [ ] **Step 2: Verify in the browser**

Open `http://127.0.0.1:8765/?t=<token>` and confirm: two Subject sections; the 學習指引 files appear as Course cards *and* contribute Bank cards (7 guide Banks + 4 exam Banks = 11 Bank cards); Defect badges show 26 total across the exam Banks.

- [ ] **Step 3: Commit**

```bash
git add skills/wens-tutor/web/index.html skills/wens-tutor/web/app/portal.js
git commit -m "feat(wens-tutor): portal page generated from the catalogue"
```

---

### Task 14: Reader page with annotations, progress, and lookup

**Files:**
- Create: `skills/wens-tutor/web/reader.html`
- Create: `skills/wens-tutor/web/app/reader.js`

**Interfaces:**
- Consumes: `api`, `render`, `host`, `S`.
- Produces: `?p=<relpath>&path=<section>&q=<term>` deep-link contract used by Task 15's Lookup.

- [ ] **Step 1: Write the page**

```html
<!doctype html>
<html lang="zh-Hant">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="stylesheet" href="/style.css">
<title>wens-tutor · reader</title>
<header class="app"><a href="/">←</a><strong id="title"></strong>
  <button id="toc-toggle" type="button">章節</button>
  <button id="ann-toggle" type="button">標註</button></header>
<main class="layout">
  <nav id="toc" class="drawer"></nav>
  <article id="doc"></article>
  <aside id="anns" class="drawer"></aside>
</main>
<div id="selbar" class="selection-bar--float" hidden></div>
<footer class="keys" id="keys"></footer>
<script type="module" src="/app/reader.js"></script>
</html>
```

```js
// skills/wens-tutor/web/app/reader.js
import S from "/strings.js";
import * as api from "/app/api.js";
import * as render from "/app/render.js";
import { isTouch, mountSelectionBar, openLookupResult } from "/app/host.js";

const params = new URLSearchParams(location.search);
const relpath = params.get("p");
const doc = document.getElementById("doc");
const COLORS = ["yellow", "green", "blue", "pink"];
let meta = null;

async function load() {
  meta = await api.get(`/api/file?p=${encodeURIComponent(relpath)}`);
  document.getElementById("title").textContent = meta.title;
  document.getElementById("keys").textContent = [S.keys.esc, S.reader.read].join("　");
  const source = await (await fetch(`/raw/${encodeURIComponent(relpath)}`)).text();
  render.renderInto(doc, source);
  buildToc();
  await restoreAnnotations();
  jumpToTarget();
  trackReadingPos();
}

function buildToc() {
  const toc = document.getElementById("toc");
  toc.textContent = "";
  for (const s of meta.sections) {
    const row = document.createElement("div");
    row.style.paddingInlineStart = `${(s.level - 1) * 0.75}rem`;
    const link = document.createElement("a");
    link.href = `#L${s.line_start}`;
    link.textContent = s.title;
    link.addEventListener("click", (e) => {
      e.preventDefault();
      scrollToLine(s.line_start);
    });
    row.append(link);
    if (s.is_leaf) {
      const box = document.createElement("input");
      box.type = "checkbox";
      box.checked = s.read;
      box.title = S.reader.read;
      box.addEventListener("change", () =>
        api.post("/api/progress", { relpath, path: s.path, read: box.checked }));
      row.prepend(box);
    }
    toc.append(row);
  }
}

function scrollToLine(line) {
  const blocks = render.blocks(doc);
  const target = blocks.reduce((best, b) =>
    Number(b.dataset.line) <= line && (!best || Number(b.dataset.line) > Number(best.dataset.line)) ? b : best, null);
  (target || doc).scrollIntoView({ block: "start" });
}

async function restoreAnnotations() {
  const { annotations } = await api.get(`/api/annotations?p=${encodeURIComponent(relpath)}`);
  const list = document.getElementById("anns");
  list.textContent = "";
  const orphans = [];
  for (const ann of annotations) {
    const ok = render.anchor(doc, ann);
    if (!ok) orphans.push(ann);
    if (Boolean(ann.orphan) !== !ok) await api.patch(`/api/annotation/${ann.id}`, { orphan: ok ? 0 : 1 });
    const row = document.createElement("div");
    row.className = ok ? "ann-row" : "ann-row orphan";
    row.textContent = (ann.note_md ? `📝 ${ann.note_md} — ` : "") + `「${ann.exact}」`;
    const del = document.createElement("button");
    del.type = "button";
    del.textContent = S.reader.del;
    del.addEventListener("click", async () => { await api.del(`/api/annotation/${ann.id}`); location.reload(); });
    row.append(del);
    list.append(row);
  }
  if (orphans.length) list.prepend(Object.assign(document.createElement("h3"),
    { textContent: `${S.reader.orphanList} (${orphans.length})` }));
}

function setupSelectionBar() {
  const bar = mountSelectionBar(document.getElementById("selbar"));
  const rebuild = (quote) => {
    bar.textContent = "";
    for (const color of COLORS) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = `swatch swatch--${color}`;
      b.title = S.reader.highlight;
      b.addEventListener("click", async () => {
        await api.post("/api/annotation", { relpath, ...quote, color, note_md: "" });
        location.reload();
      });
      bar.append(b);
    }
    const note = document.createElement("button");
    note.type = "button";
    note.textContent = S.reader.note;
    note.addEventListener("click", async () => {
      const text = prompt(S.reader.note);
      if (text === null) return;
      await api.post("/api/annotation", { relpath, ...quote, color: "yellow", note_md: text });
      location.reload();
    });
    const look = document.createElement("button");
    look.type = "button";
    look.textContent = S.reader.lookup;
    look.addEventListener("click", () => showLookup(quote.exact));
    bar.append(note, look);
  };

  document.addEventListener("selectionchange", () => {
    const quote = render.quoteFromSelection(doc);
    if (!quote) { bar.hidden = true; return; }
    rebuild(quote);
    bar.hidden = false;
    if (!isTouch) {
      const rect = window.getSelection().getRangeAt(0).getBoundingClientRect();
      bar.style.top = `${window.scrollY + rect.top - 40}px`;
      bar.style.left = `${rect.left}px`;
    }
  });
}

async function showLookup(term) {
  const res = await api.get(`/api/lookup?q=${encodeURIComponent(term)}`);
  const panel = document.createElement("div");
  panel.className = "popup";
  panel.append(Object.assign(document.createElement("p"),
    { textContent: `${S.exam.queryUsed}：${res.query_used}` }));
  for (const hit of res.courses) {
    const a = document.createElement("a");
    a.href = `/reader?p=${encodeURIComponent(hit.relpath)}&path=${encodeURIComponent(hit.path)}&q=${encodeURIComponent(res.query_used)}`;
    a.textContent = `${hit.subject} · ${hit.title} — ${hit.snippet.slice(0, 60)}`;
    a.addEventListener("click", (e) => { e.preventDefault(); openLookupResult(a.href); });
    panel.append(a);
  }
  const close = document.createElement("button");
  close.type = "button";
  close.textContent = "×";
  close.addEventListener("click", () => panel.remove());
  panel.prepend(close);
  document.body.append(panel);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") panel.remove(); }, { once: true });
}

function jumpToTarget() {
  const path = params.get("path");
  const term = params.get("q");
  if (path) {
    const sec = meta.sections.find((s) => s.path === path);
    if (sec) scrollToLine(sec.line_start);
  } else if (meta.reading_pos) {
    scrollToLine(meta.reading_pos);
  }
  if (term) {
    for (const b of render.blocks(doc)) {
      if (b.textContent.includes(term)) { b.classList.add("focus"); b.scrollIntoView({ block: "center" }); break; }
    }
  }
}

function trackReadingPos() {
  let timer = null;
  window.addEventListener("scroll", () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      const mid = window.innerHeight / 2;
      const block = render.blocks(doc).find((b) => b.getBoundingClientRect().bottom > mid);
      if (block) api.post("/api/reading-pos", { relpath, line: Number(block.dataset.line) });
    }, 800);
  });
}

for (const [btn, panel] of [["toc-toggle", "toc"], ["ann-toggle", "anns"]]) {
  document.getElementById(btn).addEventListener("click", () =>
    document.getElementById(panel).classList.toggle("open"));
}
setupSelectionBar();
load();
```

- [ ] **Step 2: Verify in the browser**

Open the 學習指引 科目1 in the reader. Confirm: the document renders; the TOC lists 73 rows with 57 checkboxes; selecting text raises the bar; a yellow Highlight persists across a reload; ticking a Section moves the portal's progress bar; `?q=` flashes the term.

- [ ] **Step 3: Commit**

```bash
git add skills/wens-tutor/web/reader.html skills/wens-tutor/web/app/reader.js
git commit -m "feat(wens-tutor): reader with persistent Annotations, Progress and Lookup"
```

---

### Task 15: Exam page

**Files:**
- Create: `skills/wens-tutor/web/exam.html`
- Create: `skills/wens-tutor/web/app/exam.js`

**Interfaces:**
- Consumes: `api`, `render`, `host`, `S`.
- Produces: nothing for later tasks.

- [ ] **Step 1: Write the page**

```html
<!doctype html>
<html lang="zh-Hant">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="stylesheet" href="/style.css">
<title>wens-tutor · exam</title>
<header class="app"><a href="/">←</a><strong id="phase"></strong><span id="clock"></span></header>
<main id="root"></main>
<footer class="keys" id="keys"></footer>
<script type="module" src="/app/exam.js"></script>
</html>
```

```js
// skills/wens-tutor/web/app/exam.js
import S from "/strings.js";
import * as api from "/app/api.js";
import * as render from "/app/render.js";
import { openLookupResult } from "/app/host.js";

const params = new URLSearchParams(location.search);
const root = document.getElementById("root");
const clock = document.getElementById("clock");
let attempt = null, index = 0, shownAt = Date.now(), ticker = null;

async function main() {
  document.getElementById("keys").textContent =
    [S.keys.digits, S.keys.arrows, S.keys.enter, S.keys.esc].join("　");
  if (params.get("attempt")) return openAttempt(Number(params.get("attempt")));
  if (params.get("drill")) return startPaper({ drill: true });
  renderComposeForm();
}

function renderComposeForm() {
  document.getElementById("phase").textContent = S.exam.compose;
  const form = document.createElement("form");
  const fields = [
    ["cap", S.exam.cap, "number", 50],
    ["shuffle", S.exam.shuffle, "checkbox", true],
    ["timed", S.exam.timed, "checkbox", true],
    ["include_defective", S.exam.includeDefective, "checkbox", false],
  ];
  const bank = document.createElement("select");
  bank.multiple = true;
  bank.name = "bkeys";
  api.get("/api/portal").then((data) => {
    for (const s of data.subjects) {
      for (const f of s.files) {
        for (const b of f.banks) {
          const opt = document.createElement("option");
          opt.value = b.bkey;
          opt.selected = params.get("bkey") ? params.get("bkey") === b.bkey : true;
          opt.textContent = `${s.subject} · ${f.title} — ${b.title} (${b.n_questions})`;
          bank.append(opt);
        }
      }
    }
  });
  form.append(Object.assign(document.createElement("label"), { textContent: S.exam.banks }), bank);
  for (const [name, label, type, value] of fields) {
    const wrap = document.createElement("label");
    wrap.textContent = label;
    const input = document.createElement("input");
    input.name = name; input.type = type;
    if (type === "checkbox") input.checked = value; else input.value = value;
    wrap.append(input);
    form.append(wrap);
  }
  const go = document.createElement("button");
  go.type = "submit"; go.textContent = S.exam.start;
  form.append(go);
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    startPaper({
      bkeys: Array.from(bank.selectedOptions).map((o) => o.value),
      cap: Number(fd.get("cap")),
      shuffle: fd.get("shuffle") === "on",
      timed: fd.get("timed") === "on",
      include_defective: fd.get("include_defective") === "on",
    });
  });
  root.textContent = "";
  root.append(form);
}

async function startPaper(criteria) {
  attempt = await api.post("/api/paper", criteria);
  index = 0;
  paint();
}

async function openAttempt(id) {
  attempt = await api.get(`/api/attempt/${id}`);
  attempt.attempt_id = id;
  index = attempt.questions.findIndex((q) => !q.given);
  if (index < 0) index = 0;
  paint();
}

function paint() {
  document.getElementById("phase").textContent = `${index + 1}/${attempt.questions.length}`;
  const q = attempt.questions[index];
  shownAt = Date.now();
  root.textContent = "";

  const stem = document.createElement("div");
  render.renderInto(stem, q.stem_md);
  root.append(stem);

  for (const [letter, text] of q.options) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "option" + (q.given === letter ? " focus" : "");
    btn.textContent = `(${letter}) ${text}`;
    btn.addEventListener("click", () => choose(letter));
    root.append(btn);
  }

  const star = document.createElement("button");
  star.type = "button";
  star.textContent = (q.starred ? "★ " : "☆ ") + S.exam.star;
  star.addEventListener("click", async () => {
    const res = await api.post("/api/star", { qkey: q.qkey });
    q.starred = res.starred;
    paint();
  });

  const look = document.createElement("button");
  look.type = "button";
  look.textContent = S.reader.lookup;
  look.addEventListener("click", () => lookupSelection(q.qkey));

  const submit = document.createElement("button");
  submit.type = "button";
  submit.textContent = S.exam.submit;
  submit.addEventListener("click", finish);

  const map = document.createElement("nav");
  attempt.questions.forEach((item, i) => {
    const dot = document.createElement("button");
    dot.type = "button";
    dot.textContent = String(i + 1);
    dot.className = item.given ? "answered" : "";
    dot.addEventListener("click", () => { index = i; paint(); });
    map.append(dot);
  });

  root.append(star, look, submit, map);
  startClock();
}

async function choose(letter) {
  const q = attempt.questions[index];
  q.given = letter;
  await api.put(`/api/attempt/${attempt.attempt_id}/answer`, {
    qkey: q.qkey, given: letter, ms: Date.now() - shownAt,
  });
  if (index < attempt.questions.length - 1) { index += 1; paint(); } else paint();
}

function startClock() {
  clearInterval(ticker);
  if (attempt.remaining_ms == null) { clock.textContent = ""; return; }
  const deadline = Date.now() + attempt.remaining_ms;
  ticker = setInterval(() => {
    const left = deadline - Date.now();
    if (left <= 0) { clearInterval(ticker); finish(); return; }
    const s = Math.floor(left / 1000);
    clock.textContent = `${S.exam.remaining} ${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  }, 500);
}

async function lookupSelection(excludeQkey) {
  const term = (window.getSelection() || "").toString().trim() || prompt(S.reader.lookup) || "";
  if (!term) return;
  const res = await api.get(`/api/lookup?q=${encodeURIComponent(term)}&exclude=${encodeURIComponent(excludeQkey)}`);
  const panel = document.createElement("div");
  panel.className = "popup";
  panel.append(Object.assign(document.createElement("p"), { textContent: `${S.exam.queryUsed}：${res.query_used}` }));
  const tabs = document.createElement("div");
  const courses = document.createElement("section");
  const questions = document.createElement("section");
  questions.hidden = true;
  for (const [label, section] of [[S.exam.courseTab, courses], [S.exam.bankTab, questions]]) {
    const t = document.createElement("button");
    t.type = "button"; t.textContent = label;
    t.addEventListener("click", () => { courses.hidden = section !== courses; questions.hidden = section !== questions; });
    tabs.append(t);
  }
  for (const hit of res.courses) {
    const a = document.createElement("a");
    a.href = `/reader?p=${encodeURIComponent(hit.relpath)}&path=${encodeURIComponent(hit.path)}&q=${encodeURIComponent(res.query_used)}`;
    a.textContent = `${hit.subject} · ${hit.title}`;
    a.addEventListener("click", (e) => { e.preventDefault(); openLookupResult(a.href); });
    courses.append(a);
  }
  for (const hit of res.questions) {
    questions.append(Object.assign(document.createElement("p"),
      { textContent: `${hit.bank_title} 第${hit.ordinal}題 — ${hit.snippet}` }));
  }
  const close = document.createElement("button");
  close.type = "button"; close.textContent = "×";
  close.addEventListener("click", () => panel.remove());
  panel.append(close, tabs, courses, questions);
  document.body.append(panel);
}

async function finish() {
  clearInterval(ticker);
  const result = await api.post(`/api/attempt/${attempt.attempt_id}/submit`, {});
  root.textContent = "";
  document.getElementById("phase").textContent = S.exam.score;
  root.append(Object.assign(document.createElement("h2"), {
    textContent: `${result.score} ${result.passed ? "✓ " + S.exam.pass : ""} ${result.expired ? S.exam.expired : ""}`,
  }));
  for (const qkey of result.wrong) {
    const q = attempt.questions.find((x) => x.qkey === qkey);
    const box = document.createElement("article");
    const stem = document.createElement("div");
    render.renderInto(stem, q.stem_md);
    box.append(stem);
    box.append(Object.assign(document.createElement("p"),
      { textContent: `✗ ${q.given || "—"} → ${q.options.map(([l]) => l).join("")}` }));
    if (q.explanation_md) {
      const ex = document.createElement("div");
      render.renderInto(ex, `**${S.exam.explanation}（${q.explanation_origin}）**\n\n${q.explanation_md}`);
      box.append(ex);
    }
    const note = document.createElement("textarea");
    note.placeholder = S.exam.myNote;
    note.addEventListener("change", () => api.post("/api/note", { qkey, note_md: note.value }));
    box.append(note);
    root.append(box);
  }
}

document.addEventListener("keydown", (e) => {
  if (!attempt || !attempt.questions) return;
  const q = attempt.questions[index];
  if (!q) return;
  const digit = "1234".indexOf(e.key);
  const letter = "ABCD".indexOf(e.key.toUpperCase());
  if (digit >= 0 && q.options[digit]) choose(q.options[digit][0]);
  else if (letter >= 0 && q.options[letter]) choose(q.options[letter][0]);
  else if (e.key === "ArrowRight" && index < attempt.questions.length - 1) { index += 1; paint(); }
  else if (e.key === "ArrowLeft" && index > 0) { index -= 1; paint(); }
  else if (e.key === " ") {
    const cur = q.options.findIndex(([l]) => l === q.given);
    choose(q.options[(cur + 1) % q.options.length][0]);
    e.preventDefault();
  }
});

main();
```

- [ ] **Step 2: Verify in the browser**

Compose a 10-Question Paper from one exam Bank. Confirm: 10 Questions, no defective ones; `1`–`4` and `A`–`D` answer; the countdown starts at 18:00 for 10 Questions; reloading mid-Attempt resumes with the countdown still falling; submitting shows a score, stars every wrong Question, and renders official Explanations for guide Questions.

- [ ] **Step 3: Commit**

```bash
git add skills/wens-tutor/web/exam.html skills/wens-tutor/web/app/exam.js
git commit -m "feat(wens-tutor): exam page with timing, resumption, Stars and Lookup"
```

---

### Task 16: Statistics page

**Files:**
- Create: `skills/wens-tutor/web/stats.html`
- Create: `skills/wens-tutor/web/app/stats.js`

**Interfaces:**
- Consumes: `api.get("/api/stats")`, `S`.

- [ ] **Step 1: Write the page**

```html
<!doctype html>
<html lang="zh-Hant">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="stylesheet" href="/style.css">
<title>wens-tutor · stats</title>
<header class="app"><a href="/">←</a><strong id="title"></strong></header>
<main id="root"></main>
<script type="module" src="/app/stats.js"></script>
</html>
```

```js
// skills/wens-tutor/web/app/stats.js — panel order: score, pace, most-missed, per-bank, trend
import S from "/strings.js";
import * as api from "/app/api.js";

const root = document.getElementById("root");

function panel(title) {
  const s = document.createElement("section");
  s.append(Object.assign(document.createElement("h2"), { textContent: title }));
  root.append(s);
  return s;
}

function sparkline(values, passLine) {
  const w = 480, h = 120, max = 100;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svg.setAttribute("width", "100%");
  const line = (points, color) => {
    const el = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
    el.setAttribute("points", points);
    el.setAttribute("fill", "none");
    el.setAttribute("stroke", color);
    svg.append(el);
  };
  if (values.length) {
    const step = values.length > 1 ? w / (values.length - 1) : 0;
    line(values.map((v, i) => `${i * step},${h - (v / max) * h}`).join(" "), "#0b5");
  }
  line(`0,${h - (passLine / max) * h} ${w},${h - (passLine / max) * h}`, "#d33");
  return svg;
}

async function main() {
  document.getElementById("title").textContent = S.stats.title;
  const data = await api.get("/api/stats");

  panel(S.stats.scores).append(sparkline(data.scores.map((s) => s.score), 60));

  const pace = panel(S.stats.pace);
  pace.append(Object.assign(document.createElement("p"), {
    textContent: `${data.pace_seconds_per_question ?? "—"} s / ${data.official_pace_seconds} s`,
  }));

  const missed = panel(S.stats.missed);
  for (const row of data.most_missed) {
    missed.append(Object.assign(document.createElement("p"),
      { textContent: `${row.qkey} ×${row.wrong_count}` }));
  }

  const banks = panel(S.stats.perBank);
  for (const b of data.per_bank) {
    banks.append(Object.assign(document.createElement("p"), {
      textContent: `${b.title} — ${b.n_questions} 題 · ${S.portal.stars} ${b.stars} · ${S.portal.defects} ${b.defects}`,
    }));
  }

  const trend = panel(S.stats.trend);
  trend.append(Object.assign(document.createElement("p"),
    { textContent: `${S.portal.stars} ${data.stars} · ${S.portal.defects} ${data.defects}` }));
}
main();
```

- [ ] **Step 2: Verify in the browser**

Open `/stats` after sitting two Papers. Confirm five panels in order, the 60-point line drawn, pace against 108 s, and the Defect count matching `check`.

- [ ] **Step 3: Commit**

```bash
git add skills/wens-tutor/web/stats.html skills/wens-tutor/web/app/stats.js
git commit -m "feat(wens-tutor): statistics page"
```

---

### Task 17: SKILL.md, references, and the real-device smoke run

**Files:**
- Create: `skills/wens-tutor/SKILL.md`
- Create: `skills/wens-tutor/references/material-format.md`
- Create: `skills/wens-tutor/references/db-schema.md`
- Modify: `CHANGELOG.md`

**Interfaces:** none — documentation and final verification.

- [ ] **Step 1: Write `SKILL.md`**

Frontmatter: `name: wens-tutor`; `description` starting with "Use when…", naming the triggers 複習 / 開始讀書 / 模擬考 / 出卷 / 重點題 / 複習進度 / 補答案 / 補圖 and their English equivalents, and stating that it operates on a registered Materials Root of Markdown courseware.

Body sections, in this order:

1. **Dispatch** — five branches: start a study session (`serve`), sit a Paper, drill Stars, check content health (`check`), repair content (Backfill/Explanation).
2. **Hard rules** — the engine never writes to a Material File; the agent writes only in the three repair workflows, only when asked, only after `git status` on the Materials Root; run `export` before committing the Materials Root; never `git push` the wenswiki vault.
3. **Serving** — start via `hub` with a port readiness check, report the tokenised URL, never block the session. Loopback by default; `--bind 0.0.0.0` for the phone, which requires the token.
4. **Repair workflows** — the three from the spec, each with its authoritative source (published answer key from the web; the PDF in `source/`; the register of the 70 official Explanations).
5. **Reference pointers** — `CONTEXT.md` for vocabulary, `docs/adr/` for decisions, `references/*.md` for formats.

- [ ] **Step 2: Write the two references**

`references/material-format.md`: both Bank shapes verbatim, the parser-tolerance table from the spec, the Defect heuristics with their measured counts, and the skeleton emitted by `new`.

`references/db-schema.md`: the `main` and `cat` schemas, why keys are natural (ADR 0002/0007), and the export/import contract (ADR 0009).

- [ ] **Step 3: Run the full test suite**

Run: `cd skills/wens-tutor && uv run --python 3.14 python3 -m unittest discover -s tests -v`
Expected: all tests pass — 19 in `test_parser.py`, 25 in `test_rules.py`.

- [ ] **Step 4: Desktop smoke run against the real Materials Root**

```bash
cd skills/wens-tutor
uv run --python 3.14 python3 scripts/tutor.py check ; echo "exit=$?"
uv run --python 3.14 python3 scripts/tutor.py serve --port 8765 --open
```

Confirm, in order: portal shows 2 Subjects / 4 Course cards / 11 Bank cards / 26 Defects; a Highlight survives a server restart; renaming a Bank file and restarting keeps its Stars (then rename it back); a wrong answer stars a Question, two consecutive corrects clear it, a manual Star survives; a Drill contains exactly the Starred Questions; a 20-Question Paper counts down 36:00 and auto-submits at zero; Lookup from a Question opens the 學習指引 Section in a new window; ticking one leaf Section moves 科目1's progress by 1/57; `export`, delete `tutor.db`, `import`, everything returns.

- [ ] **Step 5: Phone smoke run over the private network**

```bash
uv run --python 3.14 python3 scripts/tutor.py serve --bind 0.0.0.0 --port 8765
```

On the phone, over the virtual network: the tokenised URL admits and a bare URL returns 403; the selection bar sits at the bottom edge and creates a Highlight; Lookup opens as a slide-over, not a new tab; a 10-Question Paper is answerable end to end; record the render time of the 292 KB guide (`performance.now()` around `renderInto`) and note it in the CHANGELOG entry. If it exceeds 1 s, open a follow-up task for chapter-scoped rendering on touch hosts only (ADR 0010).

- [ ] **Step 6: CHANGELOG and commit**

Append one `Unreleased` entry dated today describing the new skill, the engine, the four pages, both hosts, and the measured phone render time.

```bash
git add skills/wens-tutor CHANGELOG.md
git commit -m "feat(wens-tutor): add courseware review skill with study site"
```

---

## Self-Review

**Spec coverage.** Problem/Scope → Tasks 11–17. Ground truth → Tasks 1–3 assertions. Constraints 1–5 → Task 10 (`safe_material_path` refuses symlinks; only a registered root is walked) and Task 4 (content sniffing, no FTS). Architecture/file tree → File Structure table. Path problem → Task 10 routes. Hosts and access → Tasks 10, 12, 17 Step 5. Catalogue → Task 4. Identity/user state → Tasks 5, 9. Material format (both shapes, tolerances, Defects) → Tasks 2, 3. Annotation anchoring → Task 12 (`anchor`, `quoteFromSelection`) and Task 14 (orphan `PATCH`). Sitting a Paper (composition, shuffle, timing, resumption, grading, Star lifecycle, result view) → Tasks 6, 15. Web surface (4 pages, render evidence, chrome, layout, keyboard) → Tasks 12–16. Lookup → Tasks 7, 14, 15. CLI incl. exit codes → Task 11. Agent workflows/triggers → Task 17. Verification → Tasks 1–3, 6–10, 17.

**Placeholder scan.** No TBDs. Every code step carries real code. The two documentation steps in Task 17 enumerate exact sections and sources rather than saying "write docs". The one judgement call left open is deliberate and bounded: if the phone render exceeds 1 s, a follow-up task is opened — the threshold and the fallback are both named.

**Type consistency.** `parse_sections`/`parse_exam_bank`/`parse_guide_banks`/`defects_for`/`parse_file` (Tasks 1–3) are consumed with those exact names in `catalog.build` (Task 4) and `cmd_check` (Task 11). `state.open_root`/`reconcile`/`export_json`/`import_json`/`json_path`/`db_path` (Tasks 5, 9) match their uses in Tasks 6–11. `compose.compose/start_attempt/answer/submit/toggle_star/remaining_ms/stats/lookup` (Tasks 6, 7) match `api.handle` (Task 8) and `tutor.py` (Task 11). The API paths in Task 8 are exactly those fetched in Tasks 13–16. `render.renderInto/blocks/anchor/quoteFromSelection` and `host.isTouch/openLookupResult/mountSelectionBar` (Task 12) are used with those names in Tasks 14–15. Criteria keys (`bkeys`, `cap`, `shuffle`, `timed`, `include_defective`, `drill`) are identical in Tasks 6, 8, 15.
