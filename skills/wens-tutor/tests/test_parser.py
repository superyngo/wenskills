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

```
code line
(A) not an option
```

(A) 甲;
(B) 乙;
(C) 丙;
(D) 丁

> ※ 本題附有程式碼圖，請對照原始 PDF。

**解析（AI 生成，未經官方確認）：**

因為如此。

---

## 第 3～4 題（題組）

下圖為某資料集的分佈，請根據此圖回答第 3～4 題。

### 第 3 題

**答案：A**

此分佈最接近何者?

(A) 常態;
(B) 均勻;
(C) 偏態;
(D) 雙峰

### 第 4 題

**答案：B**

若移除離群值，何者改變最大?

(A) 中位數;
(B) 標準差;
(C) 眾數;
(D) 四分位距

> 以下第5~5 題共用題幹：
> 〔註：原題附有 PCA 降噪程式碼圖，於此省略。〕

### 第 5 題

**答案：C**

此步驟的目的為何?

(A) 甲;
(B) 乙;
(C) 丙;
(D) 丁

《以下空白》
"""


class TestExamBank(unittest.TestCase):
    def setUp(self):
        self.bank = parser.parse_exam_bank(EXAM)
        self.q = {q.ordinal: q for q in self.bank.questions}

    def test_five_questions_four_options_each(self):
        self.assertEqual(self.bank.shape, "exam")
        self.assertEqual(len(self.bank.questions), 5)
        for q in self.bank.questions:
            self.assertEqual(len(q.options), 4)

    def test_answer_and_missing_answer(self):
        self.assertEqual(self.q[1].answer, "D")
        self.assertIsNone(self.q[2].answer)

    def test_fenced_lines_stay_in_stem_and_are_not_options(self):
        self.assertIn("code line", self.q[2].stem_md)
        self.assertIn("(A) not an option", self.q[2].stem_md)
        self.assertEqual(self.q[2].options[0][1], "甲")

    def test_trailers_dropped_and_explanation_captured(self):
        self.assertNotIn("以下空白", self.q[5].stem_md)
        self.assertEqual(self.q[2].explanation_origin, "authored")
        self.assertIn("因為如此", self.q[2].explanation_md)

    def test_declared_marker_is_kept_not_dropped(self):
        self.assertIn("請對照原始 PDF", self.q[2].stem_md)
        self.assertTrue(self.q[2].declared_defect)
        self.assertEqual(self.q[2].unattributed, [])

    def test_nothing_is_left_unattributed(self):
        for q in self.bank.questions:
            self.assertEqual(q.unattributed, [], f"第{q.ordinal}題")

    def test_heading_shared_stem_is_folded_into_both_members(self):
        for ordinal in (3, 4):
            self.assertEqual(self.q[ordinal].shared_span, (3, 4))
            self.assertIn("共用題幹（第3～4題）", self.q[ordinal].stem_md)
            self.assertIn("下圖為某資料集的分佈", self.q[ordinal].stem_md)
        self.assertIn("此分佈最接近何者", self.q[3].stem_md)
        self.assertIn("若移除離群值", self.q[4].stem_md)

    def test_blockquote_shared_stem_is_folded_and_its_lines_consumed(self):
        self.assertEqual(self.q[5].shared_span, (5, 5))
        self.assertIn("PCA 降噪程式碼圖", self.q[5].stem_md)
        self.assertTrue(self.q[5].declared_defect)
        # the blockquote sat in 第 4 題's region but belongs to 第 5 題: consumed, not leaked
        self.assertEqual(self.q[4].shared_span, (3, 4))
        self.assertNotIn("PCA 降噪", self.q[4].stem_md)
        self.assertEqual(self.q[4].unattributed, [])

    def test_unattributed_line_is_reported(self):
        broken = EXAM.replace("(D) 丁\n\n《以下空白》", "(D) 丁\n\n沒人認領的一行\n\n《以下空白》")
        q5 = parser.parse_exam_bank(broken).questions[-1]
        self.assertEqual(q5.unattributed, ["沒人認領的一行"])

    def test_qkey_is_stable_content_addressed_and_covers_the_shared_stem(self):
        again = parser.parse_exam_bank(EXAM)
        self.assertEqual([q.qkey for q in self.bank.questions], [q.qkey for q in again.questions])
        self.assertEqual(len(self.q[1].qkey), 12)
        without = EXAM.replace("下圖為某資料集的分佈，請根據此圖回答第 3～4 題。", "另一段完全不同的共用題幹。")
        moved = {q.ordinal: q.qkey for q in parser.parse_exam_bank(without).questions}
        self.assertNotEqual(moved[3], self.q[3].qkey)
        self.assertEqual(moved[1], self.q[1].qkey)

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

    def test_eighteen_questions_carry_a_folded_shared_stem(self):
        folded, spans = [], set()
        for p in material_files():
            b = parser.parse_exam_bank(p.read_text(encoding="utf-8"))
            if not b:
                continue
            for q in b.questions:
                if q.shared_span:
                    folded.append((p.name, q.ordinal))
                    spans.add((p.name, q.shared_span))
                    self.assertIn(parser.SHARED_STEM_LABEL, q.stem_md)
        self.assertEqual(len(folded), 18)
        self.assertEqual(len(spans), 7)
        # both 科目3 papers, nine Questions each, by two different conventions
        per_file = {name for name, _ in folded}
        self.assertEqual(len(per_file), 2)

    def test_no_line_is_left_unattributed_anywhere(self):
        orphans = []
        for p in material_files():
            b = parser.parse_exam_bank(p.read_text(encoding="utf-8"))
            if b:
                orphans += [(p.name, q.ordinal, q.unattributed) for q in b.questions if q.unattributed]
        self.assertEqual(orphans, [])

    def test_eighteen_questions_declare_their_own_defect(self):
        declared = sum(
            1
            for p in material_files()
            for b in [parser.parse_exam_bank(p.read_text(encoding="utf-8"))]
            if b
            for q in b.questions
            if q.declared_defect
        )
        self.assertEqual(declared, 18)

    def test_shared_stem_spans_never_overlap_inside_a_file(self):
        for p in material_files():
            spans = sorted(parser.find_shared_stems(p.read_text(encoding="utf-8").splitlines())[0])
            for a, b in zip(spans, spans[1:]):
                self.assertGreater(b[0], a[1], f"{p.name} {a} vs {b}")

if __name__ == "__main__":
    unittest.main()
