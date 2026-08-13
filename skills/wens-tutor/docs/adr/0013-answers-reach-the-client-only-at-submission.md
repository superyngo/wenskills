# Answers reach the client only at submission

`GET /api/attempt/<id>` returns each Question's stem, options and Star state. It returns no
`answer` and no `explanation_md`. The correct option and the Explanation arrive in the response
to `POST /api/attempt/<id>/submit`, for wrong Questions only.

The first draft withheld `answer` but shipped `explanation_md` with the in-flight payload, which
is the same leak wearing a hat: all 70 official Explanations open with `Ans(B)`. The exam page
never rendered it, so the UI looked correct while one DevTools tab held the whole key.

## Consequences

This is a self-imposed rule with no attacker: the human owns the server, the database and the
Markdown. It is enforced anyway because the artefact under test is a *mock exam*, and its only
value is the honesty of the score it produces. A cheat that takes one click is not deterred by
its own pointlessness.

The submit response therefore carries per-Question detail, not just a total. That makes the
result view a pure render of one response and removes the second round trip the wrong-answer
list would otherwise need.

The rule is a rule, not an invariant, so it is tested where it can actually regress: an
assertion that the in-flight payload's keys contain neither `answer` nor `explanation_md`. A
future field that happens to embed the answer would pass that test — which is why the rule is
written down here in prose as well.
