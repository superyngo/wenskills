# skills/wens-tutor/scripts/tutorlib/compose.py
"""Paper composition, grading, Star lifecycle, statistics."""

import json
import random
import time
import unicodedata

SECONDS_PER_QUESTION = 108  # 90 minutes / 50 Questions, official rate


def _selectable(conn, criteria):
    sql = [
        "SELECT q.qkey, q.bkey, q.ordinal FROM cat.question q",
        "JOIN cat.bank b ON b.bkey = q.bkey",
        "JOIN cat.file f ON f.fid = b.fid",
        "WHERE q.answer IS NOT NULL",
    ]
    args = []
    if not criteria.get("include_defective") and not criteria.get("qkeys"):
        sql.append("AND q.qkey NOT IN (SELECT qkey FROM cat.defect)")
    if criteria.get("subjects"):
        sql.append("AND f.subject IN (%s)" % ",".join("?" * len(criteria["subjects"])))
        args += list(criteria["subjects"])
    if criteria.get("bkeys"):
        sql.append("AND q.bkey IN (%s)" % ",".join("?" * len(criteria["bkeys"])))
        args += list(criteria["bkeys"])
    if criteria.get("drill"):
        sql.append("AND q.qkey IN (SELECT qkey FROM star)")
    if criteria.get("qkeys"):
        sql.append("AND q.qkey IN (%s)" % ",".join("?" * len(criteria["qkeys"])))
        args += list(criteria["qkeys"])
    sql.append("ORDER BY f.relpath, b.path, q.ordinal")
    return [r["qkey"] for r in conn.execute(" ".join(sql), args)]


def compose(conn, criteria: dict) -> int:
    criteria = dict(criteria)
    drill = bool(criteria.get("drill"))
    explicit = bool(criteria.get("qkeys"))
    qkeys = _selectable(conn, criteria)
    if not explicit and criteria.get("shuffle", True):
        random.shuffle(qkeys)
    cap = criteria.get("cap")
    if cap and not drill and not explicit:
        qkeys = qkeys[: int(cap)]
    timed = bool(criteria.get("timed", True)) and not drill and not explicit
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
            "SELECT i.qkey, count(*) AS wrong_count, q.ordinal, b.title AS bank_title,"
            " substr(q.stem_md, 1, 80) AS snippet"
            " FROM attempt_item i JOIN cat.question q ON q.qkey=i.qkey"
            " JOIN cat.bank b ON b.bkey=q.bkey"
            " WHERE i.correct=0 AND i.given IS NOT NULL"
            " GROUP BY i.qkey ORDER BY wrong_count DESC, q.ordinal LIMIT 20"
        )
    ]
    # An Attempt belongs to a Bank when every one of its Questions does; a mixed Paper
    # counts toward no Bank rather than being attributed to an arbitrary one.
    per_bank = [
        dict(r)
        for r in conn.execute(
            "SELECT b.bkey, b.title, count(DISTINCT q.qkey) AS n_questions,"
            " (SELECT count(*) FROM star s JOIN cat.question sq ON sq.qkey=s.qkey WHERE sq.bkey=b.bkey) AS stars,"
            " (SELECT count(*) FROM cat.defect d JOIN cat.question dq ON dq.qkey=d.qkey WHERE dq.bkey=b.bkey) AS defects,"
            " (SELECT count(*) FROM attempt a WHERE a.finished IS NOT NULL AND a.id IN ("
            "   SELECT i.attempt_id FROM attempt_item i JOIN cat.question iq ON iq.qkey=i.qkey"
            "   GROUP BY i.attempt_id HAVING count(DISTINCT iq.bkey)=1 AND max(iq.bkey)=b.bkey)) AS attempts,"
            " (SELECT round(a.correct*100.0/a.total,1) FROM attempt a WHERE a.finished IS NOT NULL AND a.id IN ("
            "   SELECT i.attempt_id FROM attempt_item i JOIN cat.question iq ON iq.qkey=i.qkey"
            "   GROUP BY i.attempt_id HAVING count(DISTINCT iq.bkey)=1 AND max(iq.bkey)=b.bkey)"
            "   ORDER BY a.finished DESC LIMIT 1) AS latest_score,"
            " (SELECT max(round(a.correct*100.0/a.total,1)) FROM attempt a WHERE a.finished IS NOT NULL AND a.id IN ("
            "   SELECT i.attempt_id FROM attempt_item i JOIN cat.question iq ON iq.qkey=i.qkey"
            "   GROUP BY i.attempt_id HAVING count(DISTINCT iq.bkey)=1 AND max(iq.bkey)=b.bkey)) AS best_score"
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
