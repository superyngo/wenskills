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


if __name__ == "__main__":
    unittest.main()
