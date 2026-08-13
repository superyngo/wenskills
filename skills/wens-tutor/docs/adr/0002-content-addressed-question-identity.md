# User state is keyed on content, not on file paths

A Question's identity is `qkey = sha256(NFKC-normalised stem + options)[:12]`, and a file's
identity is a minted `fid` reconciled to its current path at startup — not the path itself.
Stars, Attempts, Annotations, and Progress therefore survive a file being renamed or moved.
When a stem is edited (so its hash changes), the tooling relinks the old key to the new one
by `(fid, ordinal)` and reports the relink; ambiguous cases are reported for an explicit
`relink` instead of being guessed.

The Materials Root proved this necessary before any code existed: its four-commit history
already contains a mass rename, moving six source PDFs into `source/`. A path-keyed design
would have silently dropped every Star and Annotation on that commit. Content-hash keys
alone are not enough either, because fixing an OCR typo in a stem is a frequent, expected
edit in PDF-derived material and must not cost the human their review history.

## Consequences

`qkey` is opaque, so debugging needs a lookup rather than reading the key. Two Questions
with byte-identical stems and options collapse to one identity; in this corpus there are
none, and if a Bank ever repeats a Question verbatim, treating them as the same Question is
the desired behaviour anyway.

A generated Bank skeleton must give every placeholder Question a distinct stem
(`（第 N 題題幹）`): identical placeholder text produces identical keys, and `INSERT OR IGNORE`
then silently collapses ten Questions into one.

Relinking after a stem edit needs a **Slot** record — `question_slot(qkey, bkey, ordinal, ts)`
written at every parse. Without it the only available fallback is "exactly one free slot in
the Bank", which resolves in a one-Question fixture and fails at 270.
