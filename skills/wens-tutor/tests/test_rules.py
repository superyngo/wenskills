# skills/wens-tutor/tests/test_rules.py
import json
import os
import sqlite3
import sys
import unittest
from pathlib import Path

# Keep the device registry out of the real config while testing (ADR 0003).
os.environ.setdefault("WENS_TUTOR_CONFIG", "/tmp/wens-tutor-tests.json")

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
            25,
        )
        self.assertEqual(conn.execute("SELECT count(*) FROM cat.defect").fetchone()[0], 28)
        self.assertEqual(
            conn.execute("SELECT count(*) FROM cat.question WHERE shared_span IS NOT NULL").fetchone()[0],
            18,
        )
        self.assertEqual(
            conn.execute("SELECT count(*) FROM cat.question WHERE declared_defect=1").fetchone()[0],
            18,
        )

    def test_subject_comes_from_the_first_path_segment(self):
        conn = catalog.open_catalog(ROOT)
        subjects = {r[0] for r in conn.execute("SELECT DISTINCT subject FROM cat.file")}
        self.assertEqual(subjects, {"AI應用規劃師", "機器學習"})
