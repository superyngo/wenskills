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
                          explanation_md TEXT, explanation_origin TEXT,
                          shared_span TEXT, declared_defect INT);
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
                    "INSERT OR IGNORE INTO cat.question VALUES (?,?,?,?,?,?,?,?,?,?,?)",
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
                        "%d-%d" % q.shared_span if q.shared_span else None,
                        1 if q.declared_defect else 0,
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
