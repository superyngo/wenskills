# skills/wens-tutor/scripts/tutorlib/parser.py
"""Pure Markdown parsing: Sections, Banks, Questions, Defects. No I/O."""

import re
import unicodedata
from typing import List, NamedTuple

HEADING = re.compile(r"^(#{1,4})[ \t]+(.+?)[ \t]*$")


class Section(NamedTuple):
    path: str
    level: int
    title: str
    is_leaf: bool
    line_start: int   # 1-based, the heading line
    line_end: int     # 1-based, exclusive
    text: str         # own body only, children excluded


def slugify(text: str) -> str:
    s = unicodedata.normalize("NFKC", text).strip().lower()
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", s, flags=re.UNICODE)
    return s.strip("-")


def parse_sections(md: str) -> List[Section]:
    lines = md.splitlines()
    heads = []  # (index, level, title)
    for i, line in enumerate(lines):
        m = HEADING.match(line)
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))

    out: List[Section] = []
    stack: List[str] = []
    for n, (i, level, title) in enumerate(heads):
        stack = stack[: level - 1]
        while len(stack) < level - 1:
            stack.append("")
        stack.append(slugify(title))
        path = "/".join(p for p in stack if p)

        next_i = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        next_level = heads[n + 1][1] if n + 1 < len(heads) else 0
        body = "\n".join(lines[i + 1 : next_i]).strip()
        out.append(
            Section(
                path=path,
                level=level,
                title=title,
                is_leaf=(next_level <= level),
                line_start=i + 1,
                line_end=next_i + 1,
                text=body,
            )
        )
    return out

import hashlib

QHEAD = re.compile(r"^###[ \t]*第[ \t]*(\d+)[ \t]*題[ \t]*$")
GROUP_HEAD = re.compile(r"^##[ \t]*第[ \t]*(\d+)[ \t]*[～~－-][ \t]*(\d+)[ \t]*題")
GROUP_QUOTE = re.compile(r"以下第[ \t]*(\d+)[ \t]*[～~－-][ \t]*(\d+)[ \t]*題共用題幹[：:]?[ \t]*(.*)$")
ANSWER = re.compile(r"^\*\*答案[：:]\s*([A-E]+)")
ANSWER_ANY = re.compile(r"^\*\*答案[：:]")
OPTION = re.compile(r"^\(([A-E])\)\s*(.+?);?\s*$")
EXPL_HEAD = re.compile(r"^\*\*解析.*[：:]\*\*\s*$")
TRAILER = re.compile(r"^(-{3,}|《以下空白》)\s*$")
FENCE = re.compile(r"^\s*```")
# Three conventions, all authoritative: the transcriber saying the figure is gone.
DECLARED = re.compile(r"※[^\n]*(圖|表|程式|PDF)|〔註[^〕]*(省略|圖)[^〕]*〕|請對照原始\s*PDF|見原始\s*P")
SHARED_STEM_LABEL = "共用題幹"


class Question(NamedTuple):
    qkey: str
    ordinal: int
    type: str                    # 'single' | 'multi'
    stem_md: str
    options: List[tuple]         # [(letter, text), ...]
    answer: str                  # None when unpublished
    explanation_md: str
    explanation_origin: str      # 'official' | 'authored' | None
    shared_span: tuple           # (lo, hi) when a Shared Stem was folded in, else None
    declared_defect: bool        # the content says its figure is missing
    unattributed: List[str]      # lines the parser could not place (ADR 0012)


class Bank(NamedTuple):
    path: str
    title: str
    shape: str                   # 'exam' | 'guide'
    questions: List[Question]


def qkey_for(stem_md: str, options: List[tuple]) -> str:
    norm = unicodedata.normalize("NFKC", stem_md.strip())
    for letter, text in options:
        norm += "\n" + letter + unicodedata.normalize("NFKC", text.strip())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:12]


def find_shared_stems(lines):
    """({(lo, hi): text}, consumed_line_indices) — both transcription conventions."""
    out, consumed = {}, set()
    for i, line in enumerate(lines):
        m = GROUP_QUOTE.search(line)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            body = [m.group(3).strip()]
            consumed.add(i)
            for j in range(i + 1, len(lines)):
                s = lines[j].lstrip()
                if not s.startswith(">"):
                    break
                body.append(s.lstrip(">").strip())
                consumed.add(j)
            out[(lo, hi)] = "\n".join(x for x in body if x)
            continue
        m = GROUP_HEAD.match(line)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            body = []
            for j in range(i + 1, len(lines)):
                if QHEAD.match(lines[j]) or lines[j].startswith("## "):
                    break
                body.append(lines[j])
            text = re.sub(r"\n?(-{3,}|《以下空白》)\s*$", "", "\n".join(body).strip()).strip()
            if text:
                out[(lo, hi)] = text
    return out, consumed


def shared_for(shared, ordinal):
    """First covering span. Unambiguous only while spans do not overlap — `check` enforces that."""
    for span, text in sorted(shared.items()):
        if span[0] <= ordinal <= span[1]:
            return span, text
    return None, None


def fold_shared(shared_span, shared_text: str, stem_md: str) -> str:
    quoted = shared_text.replace("\n", "\n> ")
    header = "> **%s（第%d～%d題）**" % (SHARED_STEM_LABEL, shared_span[0], shared_span[1])
    return "%s\n> %s\n\n%s" % (header, quoted, stem_md)


def split_block(block_lines):
    """(stem, options, answer, explanation, unattributed) — every line is accounted for."""
    answer, stem, options, expl, extra, notes = None, [], [], [], [], []
    in_fence, mode = False, "stem"
    for line in block_lines:
        if FENCE.match(line) or in_fence:
            if FENCE.match(line):
                in_fence = not in_fence
            (expl if mode == "expl" else stem).append(line)
            continue
        if ANSWER_ANY.match(line):
            m = ANSWER.match(line)
            if m and answer is None:
                answer = m.group(1)          # unparseable placeholder leaves it None
            continue
        if EXPL_HEAD.match(line):
            mode = "expl"
            continue
        m = OPTION.match(line)
        if m and mode in ("stem", "options"):
            mode = "options"
            options.append((m.group(1), m.group(2).strip()))
            continue
        if mode == "expl":
            expl.append(line)
        elif mode == "stem":
            stem.append(line)
        elif DECLARED.search(line):
            notes.append(line.strip())       # a declaration after the options is still content
        elif line.strip() and not TRAILER.match(line):
            extra.append(line.strip())
    stem_md = re.sub(r"\n?(-{3,}|《以下空白》)\s*$", "", "\n".join(stem).strip()).strip()
    if notes:
        stem_md = (stem_md + "\n\n" + "\n".join(notes)).strip()
    return stem_md, options, answer, "\n".join(expl).strip(), extra


def parse_exam_bank(md: str, path: str = "", title: str = "") -> Bank:
    lines = md.splitlines()
    starts = [i for i, l in enumerate(lines) if QHEAD.match(l)]
    if not starts:
        return None
    shared, consumed = find_shared_stems(lines)
    questions = []
    for n, i in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        for j in range(i + 1, end):           # a following '##' heading ends the region too
            if lines[j].startswith("## "):
                end = j
                break
        ordinal = int(QHEAD.match(lines[i]).group(1))
        block = [l for k, l in enumerate(lines[i + 1:end], start=i + 1) if k not in consumed]
        stem, options, answer, expl, extra = split_block(block)
        span, shared_text = shared_for(shared, ordinal)
        if shared_text:
            stem = fold_shared(span, shared_text, stem)
        questions.append(Question(
            qkey=qkey_for(stem, options),     # folding happens first: identity covers the preamble
            ordinal=ordinal,
            type="multi" if answer and len(answer) > 1 else "single",
            stem_md=stem,
            options=options,
            answer=answer,
            explanation_md=expl,
            explanation_origin="authored" if expl else None,
            shared_span=span,
            declared_defect=bool(DECLARED.search(stem)),
            unattributed=extra,
        ))
    return Bank(path=path, title=title, shape="exam", questions=questions)
