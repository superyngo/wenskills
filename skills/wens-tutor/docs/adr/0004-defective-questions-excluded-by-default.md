# Defective Questions are detected, excluded from Papers by default, and repaired in content

28 of the corpus's 270 Questions cannot honestly be sat as published: 3 carry no answer (PDF
extraction lost the field) and 25 refer to a figure, table, or code listing that is not in the
Markdown at all — the corpus contains zero images. Most of the 25 are the Python code-reading
Questions that the issuing body added from 114年第二梯次 onward, which are roughly a quarter of
the 機器學習 paper. The tooling detects these Defects, excludes defective Questions from composed
Papers unless explicitly included, and reports them; repair happens by Backfilling the content
from the original PDFs that sit beside the Markdown in `source/`.

Without this, the mock Paper looks complete while systematically skipping an entire Question
7 of the 25 are silently degraded — their stem says "下圖" with no note that anything
is missing, so nothing on screen would reveal the omission.

## Consequences

The `figure_missing` keyword heuristic (a reference such as 下圖/上表/程式碼中 with no fenced
block, table, or image anywhere in the Question) is conservative and will occasionally accuse a
Question that reads fine; the report is advisory and inclusion is one flag away.

Of the 25 `figure_missing`, 18 are **declared** — the transcriber wrote the omission down in
words (one of three conventions: `※ …請對照原始 PDF`, `〔註：…於此省略。〕`, or `見原始 P`) — and the
keyword heuristic fires on 24. The two sets overlap on 17, giving a union of 25 (7 inferred-only,
1 declared-only). The declared form is authoritative, and one Question (114-科3 第45題) is reachable
only through its declaration.

A third kind, `unattributed_lines`, exists so that a line the parser cannot place in a stem,
option, answer, Explanation, or Shared Stem is reported instead of dropped. It is currently 0;
any non-zero value flags a parser gap, not a content flaw.

The counts above — 3 `no_answer`, 25 `figure_missing`, 0 `unattributed_lines`, 28 in total —
are a measurement of this corpus at this commit, asserted by tests and reported by `check`, not
a constant. They are expected to fall to zero as Backfill proceeds, which makes them a usable
progress signal for content repair.
