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

    def test_explicit_qkeys_bypasses_defect_exclusion(self):
        defective_qkey = self.qkeys()[5]
        pid = compose.compose(self.conn, {"qkeys": [defective_qkey], "timed": False})
        row = self.conn.execute("SELECT qkeys_json FROM paper WHERE id=?", (pid,)).fetchone()
        self.assertEqual(json.loads(row["qkeys_json"]), [defective_qkey])

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
        # A whole-file exam Bank consumes every leaf section: no Course prose remains.
        bank_file = next(f for f in files if f["relpath"].endswith("bank.md"))
        self.assertEqual(bank_file["leaf_sections"], 0)

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

    def test_in_flight_payload_never_carries_the_key(self):
        code, paper = api.handle(self.conn, "POST", "/api/paper", {}, {"cap": 10, "timed": False})
        for source in (paper, api.handle(self.conn, "GET", f"/api/attempt/{paper['attempt_id']}", {}, None)[1]):
            for q in source["questions"]:
                self.assertNotIn("answer", q)
                self.assertNotIn("explanation_md", q)
                self.assertNotIn("explanation_origin", q)

    def test_submit_returns_the_key_for_wrong_questions_only(self):
        code, paper = api.handle(self.conn, "POST", "/api/paper", {}, {"cap": 10, "timed": False})
        aid = paper["attempt_id"]
        qkey = paper["questions"][0]["qkey"]
        api.handle(self.conn, "PUT", f"/api/attempt/{aid}/answer", {}, {"qkey": qkey, "given": "C", "ms": 100})
        code, result = api.handle(self.conn, "POST", f"/api/attempt/{aid}/submit", {}, {})
        self.assertEqual(len(result["wrong"]), 1)
        item = result["wrong"][0]
        self.assertEqual(item["qkey"], qkey)
        self.assertEqual(item["answer"], "A")
        self.assertEqual(item["given"], "C")
        self.assertIn("stem_md", item)
        self.assertIn("note_md", item)

    def test_version_is_served(self):
        code, meta = api.handle(self.conn, "GET", "/api/version", {}, None)
        self.assertEqual(code, 200)
        self.assertTrue(meta["version"])
        self.assertEqual(meta["project"], "wens-tutor")

    def test_unknown_route_is_404(self):
        code, _ = api.handle(self.conn, "GET", "/api/nope", {}, None)
        self.assertEqual(code, 404)


class TestPortalCourseProse(unittest.TestCase):
    """A leaf section that is also a Bank's root path is Bank content, not Course prose."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "科目A").mkdir()
        (self.tmp / "科目A" / "guide.md").write_text(
            "# 標題\n\n## 1 練習\n\n### 選擇題\n\n1. 題幹一\n"
            "   - （A）甲\n   - （B）乙\n   - （C）丙\n   - （D）丁\n\n"
            "### 解答與解析\n\n**1. Ans（A） 甲**\n\n解析：內容\n",
            encoding="utf-8",
        )
        self.conn = state.open_root(self.tmp)

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.tmp)

    def test_guide_bank_root_section_excluded_from_leaf_sections(self):
        code, data = api.handle(self.conn, "GET", "/api/portal", {}, None)
        self.assertEqual(code, 200)
        f = data["subjects"][0]["files"][0]
        self.assertEqual(len(f["banks"]), 1)
        # 2 leaf sections total (選擇題, 解答與解析); the Bank's own root ("選擇題")
        # is Bank content, not Course prose, so only 解答與解析 counts.
        self.assertEqual(f["leaf_sections"], 1)

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
