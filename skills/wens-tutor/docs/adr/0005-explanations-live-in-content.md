# Explanations are content in the Bank; Notes are user state

An Explanation — prose saying why an answer is correct — lives in the Bank Markdown, not in the
database. A Note, the human's own private reaction to a Question, stays in the database as user
state.

Explanations belong in content because they must be findable by Lookup, reviewable as a git
diff, and synced across devices as part of the corpus; a Note belongs in user state because it
is personal, edited constantly, and meaningless to anyone else.

Two provenances exist and must stay distinguishable:

- **Official.** The study guides publish an Explanation for each of their 70 practice
  Questions, as `解析：` inside the `解答與解析` region (ADR 0006). These are parsed, never
  rewritten.
- **Authored.** The four exam papers publish none, so any Explanation added to one is written
  by the agent as `**解析（AI 生成，未經官方確認）：**`. The attribution is what keeps the
  boundary between the issuing body's words and generated prose visible in a diff — and it is
  what stops a future reader from mistaking a plausible invention for an official answer key.

## Consequences

Writing an authored Explanation modifies a Material File, so it goes after the options, outside
the stem, leaving `qkey` (ADR 0002) untouched. The parser reads both provenances, the result
view renders them with their attribution intact, and neither is ever mistaken for a stem or an
option. The official Explanations also serve as the register and depth to imitate when
authoring new ones.
