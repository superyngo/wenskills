# Defective Questions are detected, excluded from Papers by default, and repaired in content

26 of the 200 Questions in the first Materials Root cannot honestly be sat as published:
3 carry no answer (PDF extraction lost the field) and 23 refer to a figure, table, or code
listing that is not in the Markdown at all — the corpus contains zero images. Most of the
23 are the Python code-reading Questions that the issuing body added from 114年第二梯次
onward, which are roughly a quarter of the 機器學習 paper. The tooling detects both Defect
kinds heuristically, excludes defective Questions from composed Papers unless explicitly
included, and reports them; repair happens by Backfilling the content from the original PDFs
that sit beside the Markdown in `source/`.

Without this, the mock Paper looks complete while systematically skipping an entire
Question type, and 8 of the 23 are silently degraded — their stem says "下圖" with no note
that anything is missing, so nothing on screen would reveal the omission.

## Consequences

The `figure_missing` heuristic (a reference such as 下圖/上表/程式碼中 with no fenced block,
table, or image anywhere in the Question) is conservative and will occasionally accuse a
Question that reads fine; the report is advisory and inclusion is one flag away. Defect
counts are expected to fall to zero as Backfill proceeds, which makes them a usable progress
signal for content repair.
