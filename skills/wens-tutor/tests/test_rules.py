# skills/wens-tutor/tests/test_rules.py
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

# Keep the device registry out of the real config while testing (ADR 0003).
os.environ.setdefault("WENS_TUTOR_CONFIG", "/tmp/wens-tutor-tests.json")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from tutorlib import catalog, state  # noqa: E402

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


def bank_md(stems):
    """A Bank of len(stems) Questions. Three is the minimum that makes a relink test real:
    with one Question, any 'find the single free slot' guess resolves by luck."""
    return "".join(
        "### 第 %d 題\n\n**答案：A**\n\n%s\n\n(A) 甲;\n(B) 乙;\n(C) 丙;\n(D) 丁\n\n" % (i, stem)
        for i, stem in enumerate(stems, start=1)
    )


class TestFidReconciliation(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "科目A").mkdir()
        self.f = self.tmp / "科目A" / "bank.md"
        self.f.write_text(bank_md(["題幹一", "題幹二", "題幹三"]), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def qkeys(self):
        conn = state.open_root(self.tmp)
        try:
            return [r[0] for r in conn.execute("SELECT qkey FROM cat.question ORDER BY ordinal")]
        finally:
            conn.close()

    def test_star_survives_a_file_rename(self):
        conn = state.open_root(self.tmp)
        qkey = conn.execute("SELECT qkey FROM cat.question ORDER BY ordinal").fetchone()[0]
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
        conn.close()

    def test_progress_follows_the_file_via_fid(self):
        conn = state.open_root(self.tmp)
        fid = conn.execute("SELECT fid FROM cat.file").fetchone()[0]
        conn.execute("INSERT INTO progress VALUES (?,?,0)", (fid, "第-1-題"))
        conn.commit()
        conn.close()
        self.f.rename(self.f.with_name("renamed2.md"))
        conn = state.open_root(self.tmp)
        self.assertEqual(conn.execute("SELECT fid FROM cat.file").fetchone()[0], fid)
        conn.close()

    def test_slots_are_recorded_for_every_question(self):
        conn = state.open_root(self.tmp)
        rows = conn.execute("SELECT qkey, ordinal FROM question_slot ORDER BY ordinal").fetchall()
        self.assertEqual([r["ordinal"] for r in rows], [1, 2, 3])
        conn.close()

    def test_stem_edit_relinks_by_slot_not_by_guessing(self):
        before = self.qkeys()
        conn = state.open_root(self.tmp)
        conn.execute("INSERT INTO star VALUES (?,'wrong',0)", (before[1],))
        conn.execute("INSERT INTO note VALUES (?,'我的筆記',0)", (before[1],))
        conn.commit()
        conn.close()

        self.f.write_text(bank_md(["題幹一", "題幹貳", "題幹三"]), encoding="utf-8")
        conn = state.open_root(self.tmp)
        report = state.reconcile(conn, self.tmp)
        after = [r[0] for r in conn.execute("SELECT qkey FROM cat.question ORDER BY ordinal")]
        self.assertEqual(after[0], before[0])          # untouched Questions keep their identity
        self.assertEqual(after[2], before[2])
        self.assertNotEqual(after[1], before[1])
        self.assertEqual(len(report["relinked_questions"]), 1)
        self.assertEqual(report["relinked_questions"][0]["to"], after[1])
        self.assertEqual(conn.execute("SELECT qkey FROM star").fetchone()[0], after[1])
        self.assertEqual(conn.execute("SELECT qkey FROM note").fetchone()[0], after[1])
        self.assertEqual(report["unresolved"], [])
        conn.close()

    def test_a_deleted_question_is_reported_unresolved_not_mislinked(self):
        before = self.qkeys()
        conn = state.open_root(self.tmp)
        conn.execute("INSERT INTO star VALUES (?,'wrong',0)", (before[2],))
        conn.commit()
        conn.close()

        self.f.write_text(bank_md(["題幹一", "題幹二"]), encoding="utf-8")
        conn = state.open_root(self.tmp)
        report = state.reconcile(conn, self.tmp)
        self.assertEqual(report["relinked_questions"], [])
        self.assertEqual(report["unresolved"], [before[2]])
        self.assertEqual(conn.execute("SELECT qkey FROM star").fetchone()[0], before[2])
        conn.close()

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
