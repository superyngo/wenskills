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

# Placeholder stems MUST differ: identical text produces identical qkeys and
# `INSERT OR IGNORE` would silently collapse the whole skeleton into one Question (ADR 0002).
EXAM_HEAD = "# {title}\n\n## 一、選擇題\n"
EXAM_Q = """
### 第 {n} 題

**答案：A**

（第 {n} 題題幹）

(A) 甲;
(B) 乙;
(C) 丙;
(D) 丁
"""
GUIDE_HEAD = "# {title}\n\n## 1. 練習\n\n### 選擇題\n"
GUIDE_Q = """
{n}. （第 {n} 題題幹）
   - （A）甲
   - （B）乙
   - （C）丙
   - （D）丁
"""
GUIDE_ANSWER_HEAD = "\n### 解答與解析\n"
GUIDE_ANSWER = """
**{n}. Ans（A） 甲**

解析：（在此撰寫解析）
"""


def skeleton_bank(title: str, shape: str, questions: int) -> str:
    if shape == "guide":
        body = [GUIDE_HEAD.format(title=title)]
        body += [GUIDE_Q.format(n=i) for i in range(1, questions + 1)]
        body.append(GUIDE_ANSWER_HEAD)
        body += [GUIDE_ANSWER.format(n=i) for i in range(1, questions + 1)]
        return "".join(body)
    body = [EXAM_HEAD.format(title=title)]
    body += [EXAM_Q.format(n=i) for i in range(1, questions + 1)]
    return "".join(body)


def resolve_root(args):
    """Pick the Materials Root from --root, else the registered default.

    Without a registered default the only honest answer is a usage failure
    (exit 2): `open_root` cannot guess where the corpus lives."""
    if getattr(args, "root", None):
        return Path(args.root).expanduser().resolve()
    root = registry.default_root()
    if root is None:
        print("no root registered; run `tutor.py init <root>`", file=sys.stderr)
        sys.exit(2)
    return root


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
        lines = md.splitlines()
        secs, banks = parser.parse_file(md)
        if parser.QHEAD.search(md) and not banks:
            findings.append("unparsed_bank: %s" % p.name)
        titles = [s.title.strip() for s in secs]
        for i, t in enumerate(titles):
            if t == "選擇題":
                nxt = titles[i + 1] if i + 1 < len(titles) else ""
                if nxt != "解答與解析":
                    findings.append("unpaired_guide_bank: %s / %s" % (p.name, secs[i].path))

        # A `第 N 題` heading that produced no Question, or two Questions that collapsed
        # into one row, both show up as a count mismatch (ADR 0002).
        headings = len([l for l in lines if parser.QHEAD.match(l)])
        parsed = sum(len(b.questions) for b in banks if b.shape == "exam")
        if headings and parsed != headings:
            findings.append("collapsed_questions: %s %d headings -> %d Questions"
                            % (p.name, headings, parsed))

        # Folding resolves an ordinal against the first covering span, which is only
        # unambiguous while spans do not overlap (ADR 0011).
        spans = sorted(parser.find_shared_stems(lines)[0])
        for a, b in zip(spans, spans[1:]):
            if b[0] <= a[1]:
                findings.append("overlapping_shared_stems: %s 第%d～%d題 vs 第%d～%d題"
                                % (p.name, a[0], a[1], b[0], b[1]))

        for b in banks:
            for q in b.questions:
                for line in q.unattributed:
                    findings.append("unattributed_line: %s 第%d題 %r" % (p.name, q.ordinal, line))

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
        path.write_text(skeleton_bank(args.title, args.shape, args.questions), encoding="utf-8")
    print(path)
    return 0


def cmd_serve(args):
    root = resolve_root(args)
    server.serve(
        root,
        port=args.port or registry.load().get("port", 8765),
        bind=args.bind,
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
    p.add_argument("--shape", choices=["exam", "guide"], default="exam")
    p.add_argument("--root"); p.set_defaults(fn=cmd_new)
    p = sub.add_parser("serve"); p.add_argument("--root"); p.add_argument("--port", type=int)
    p.add_argument("--bind", default="0.0.0.0"); p.add_argument("--open", action="store_true")
    p.set_defaults(fn=cmd_serve)
    p = sub.add_parser("stats"); p.add_argument("--root"); p.set_defaults(fn=cmd_stats)
    p = sub.add_parser("export"); p.add_argument("--root"); p.set_defaults(fn=cmd_export)
    p = sub.add_parser("import"); p.add_argument("--root")
    p.add_argument("--merge", action="store_true"); p.set_defaults(fn=cmd_import)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
