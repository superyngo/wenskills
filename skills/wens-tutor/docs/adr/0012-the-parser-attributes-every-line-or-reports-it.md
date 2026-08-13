# The parser attributes every line, or reports it as a Defect

Every non-blank line inside a Question's region must land somewhere nameable: the stem, an
option, the answer, an Explanation, or a recognised Shared Stem. A line that fits none of those
becomes an `unattributed_lines` Defect on that Question. Only `---` and `《以下空白》` are
whitelisted as trailers.

The alternative — tolerate stray prose, keep whatever the patterns matched — is what the first
draft did, and it lost content in silence: 14 Questions were dropping lines, including all ten
of the transcriber's `> ※ 本題附有程式碼圖，請對照原始 PDF。` declarations and every
`> 以下第42~43 題共用題幹：` group marker. Nothing failed. The parse looked clean, the counts
looked plausible, and the two decisions recorded in ADR 0011 and the declared-Defect rule were
invisible until the dropped lines were printed.

A parser over someone else's Markdown will always meet shapes it does not know. The choice is
whether it says so. Reporting costs one list per Question and one `check` finding; not
reporting costs the human content they cannot tell is gone.

## Consequences

The corpus reaches 0 unattributed lines only *after* declared markers and shared stems are
recognised. That ordering is the point: the count is a to-do list for the parser, and it went
14 → 0 by learning two real conventions rather than by widening a tolerance.

`unattributed_lines` is a Defect kind, so it flows through the existing machinery — excluded
from Papers by default, counted by `check`, shown in the portal — instead of needing a second
reporting path.

Text that a future corpus attributes wrongly is now visible as a wrong stem rather than as an
absence, which is a better failure: a stem with a stray line in it is obviously broken, while a
stem missing its figure note reads as complete.
