# skills/wens-tutor/scripts/tutorlib/api.py
"""JSON endpoints over the catalogue and user state."""

import json
import re
import subprocess
import time
from pathlib import Path

from . import compose, registry

ANN_ID = re.compile(r"^/api/annotation/(\d+)$")
ATT_ANSWER = re.compile(r"^/api/attempt/(\d+)/answer$")
ATT_SUBMIT = re.compile(r"^/api/attempt/(\d+)/submit$")
ATT_GET = re.compile(r"^/api/attempt/(\d+)$")
SKILL_DIR = Path(__file__).resolve().parents[2]
_VERSION = None


def version_meta(conn=None) -> dict:
    """There is no build step, so the version is whatever git can tell us, read once."""
    global _VERSION
    if _VERSION is None:
        try:
            _VERSION = subprocess.run(
                ["git", "describe", "--tags", "--always", "--dirty"],
                cwd=str(SKILL_DIR), capture_output=True, text=True, timeout=5,
            ).stdout.strip() or "dev"
        except (OSError, subprocess.SubprocessError):
            _VERSION = "dev"
    return {
        "version": _VERSION,
        "root": str(registry.default_root() or ""),
        "project": "wens-tutor",
        "license": "see repository",
    }


def _one(query, key, default=None):
    v = query.get(key)
    return v[0] if isinstance(v, list) and v else (v if v is not None else default)


def _fid(conn, relpath):
    row = conn.execute("SELECT fid FROM cat.file WHERE relpath=?", (relpath,)).fetchone()
    return row["fid"] if row else None


def _questions_of_attempt(conn, attempt_id):
    """In-flight view: stem, options, Star state. Never `answer`, never `explanation_md` (ADR 0013)."""
    row = conn.execute(
        "SELECT p.qkeys_json FROM attempt a JOIN paper p ON p.id=a.paper_id WHERE a.id=?",
        (attempt_id,),
    ).fetchone()
    out = []
    for qkey in json.loads(row["qkeys_json"]):
        q = conn.execute(
            "SELECT q.qkey, q.ordinal, q.stem_md, q.options_json, q.shared_span,"
            " b.title AS bank_title"
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


def _wrong_detail(conn, attempt_id, qkeys):
    """Post-submission view: the correct option, its Explanation, and any Note."""
    out = []
    for qkey in qkeys:
        q = conn.execute(
            "SELECT q.qkey, q.ordinal, q.stem_md, q.options_json, q.answer, q.explanation_md,"
            " q.explanation_origin, b.title AS bank_title"
            " FROM cat.question q JOIN cat.bank b ON b.bkey=q.bkey WHERE q.qkey=?",
            (qkey,),
        ).fetchone()
        given = conn.execute(
            "SELECT given FROM attempt_item WHERE attempt_id=? AND qkey=?", (attempt_id, qkey)
        ).fetchone()
        note = conn.execute("SELECT note_md FROM note WHERE qkey=?", (qkey,)).fetchone()
        d = dict(q)
        d["options"] = json.loads(d.pop("options_json"))
        d["given"] = given["given"] if given else None
        d["note_md"] = note["note_md"] if note else ""
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
        attempt_id = int(m.group(1))
        result = compose.submit(conn, attempt_id)
        result["wrong"] = _wrong_detail(conn, attempt_id, result["wrong"])
        return 200, result

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

    if path == "/api/version" and method == "GET":
        return 200, version_meta(conn)

    return 404, {"error": "unknown endpoint"}
