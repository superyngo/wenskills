# Explanations are content in the Bank file; Notes are user state

An Explanation — prose saying why an answer is correct — is written into the Bank Markdown
as an attributed block (`**解析（AI 生成，未經官方確認）：**`), not into the database. A Note,
the human's own private reaction to a Question, stays in the database as user state. The
published Banks contain no explanations at all, so every Explanation is authored, and the
attribution is what keeps the boundary between the issuing body's words and generated prose
visible in a diff.

Explanations belong in content because they must be findable by Lookup, reviewable as a git
diff, and synced across devices as part of the corpus; a Note belongs in user state because
it is personal, edited constantly, and meaningless to anyone else.

## Consequences

Writing an Explanation modifies a Bank file, which changes that Question's stem hash only if
the Explanation is placed inside the stem — so it is placed after the options, where the
parser skips it. The parser must round-trip Explanations: read them, render them in the
result view, and never mistake one for a stem or an option.
