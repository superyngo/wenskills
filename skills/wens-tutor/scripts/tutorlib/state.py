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
-- Where each qkey sat at the previous parse: the Slot that survives a text edit (ADR 0002).
CREATE TABLE IF NOT EXISTS question_slot(qkey TEXT PRIMARY KEY, bkey TEXT, ordinal INT, ts REAL);
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
    # Slots from the previous parse survive (upsert, never delete), so `reconcile` can match on them.
    record_slots(conn)
    return conn


def record_slots(conn: sqlite3.Connection) -> None:
    """Remember where each qkey sat. Without this, a changed stem has nothing to match on."""
    now = time.time()
    conn.executemany(
        "INSERT INTO question_slot(qkey, bkey, ordinal, ts) VALUES (?,?,?,?)"
        " ON CONFLICT(qkey) DO UPDATE SET bkey=excluded.bkey, ordinal=excluded.ordinal, ts=excluded.ts",
        [
            (r["qkey"], r["bkey"], r["ordinal"], now)
            for r in conn.execute("SELECT qkey, bkey, ordinal FROM cat.question")
        ],
    )
    conn.commit()


def reconcile(conn: sqlite3.Connection, root: Path) -> dict:
    """Relink user-state qkeys whose Question text changed, by their remembered Slot."""
    report = {"relinked_files": [], "relinked_questions": [], "unresolved": []}
    live = {r["qkey"] for r in conn.execute("SELECT qkey FROM cat.question")}
    used = set()
    for table in ("star", "note", "attempt_item"):
        used |= {r["qkey"] for r in conn.execute(f"SELECT DISTINCT qkey FROM {table}")}
    orphaned = sorted(used - live)
    if not orphaned:
        record_slots(conn)
        return report

    by_slot = {
        (r["bkey"], r["ordinal"]): r["qkey"]
        for r in conn.execute("SELECT qkey, bkey, ordinal FROM cat.question")
    }
    remembered = {
        r["qkey"]: (r["bkey"], r["ordinal"])
        for r in conn.execute("SELECT qkey, bkey, ordinal FROM question_slot")
    }
    taken = live & used
    for old in orphaned:
        slot = remembered.get(old)
        new = by_slot.get(slot) if slot else None
        if new is None or new in taken:
            report["unresolved"].append(old)
            continue
        for table in ("star", "note", "attempt_item"):
            conn.execute(f"UPDATE OR IGNORE {table} SET qkey=? WHERE qkey=?", (new, old))
        conn.execute("DELETE FROM question_slot WHERE qkey=?", (old,))
        taken.add(new)
        report["relinked_questions"].append({"from": old, "to": new, "slot": "%s#%d" % slot})
    conn.commit()
    record_slots(conn)
    return report


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
