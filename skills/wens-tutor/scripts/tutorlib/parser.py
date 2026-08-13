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
