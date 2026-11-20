# Backlog
Status: In progress

The one living record of open work. Rows move to Done with the commit that closed them and are
never deleted. Evidence is file + symbol, never a line number. `Verified` is the date the row was
last checked against the tree — not when it was opened.

## Open

| ID | Opened | Verified | Pri | Finding | Evidence | Effort | Acceptance |
|---|---|---|---|---|---|---|---|
| B1 | 2026-09-23 | 2026-11-20 | P2 | `wens-tutor` corpus tests hard-code counts of the live Materials Root, which has since grown: 11 tests fail (54 pass) | `skills/wens-tutor/tests/test_parser.py` `TestCorpusTotals`; `skills/wens-tutor/tests/test_rules.py` `TestCatalogue` (both read `ROOT` under `~/repos/wenswiki/…/2026_AI應用規劃師`) | M | `pytest skills/wens-tutor/tests` passes; counts asserted against a fixture corpus or derived, not hard-coded |
| B2 | 2026-09-23 | 2026-11-20 | P2 | `wens-tutor` reader: a plain-text answer paragraph (`答案：B` directly in `<p>`) cannot be hidden — the hide rule only hides element children, so the paragraph's text nodes stay visible | `skills/wens-tutor/web/style.css` `.answer-hidden > *:not(.reveal-btn)`; `skills/wens-tutor/web/app/reader.js` `hideAnswers()` / `makeToggle()` | S | A Bank with plain-text `答案：X` paragraphs shows only the reveal button until clicked; reveal state persists across reload |

## Pending verification

Landed, but the check needs a platform or pipeline not available locally.

| Item | Closed by | Verifies when | Fallback |
|---|---|---|---|

## Awaiting external

Blocked on a person or third party. **Not counted as open** — no amount of local work closes it.

| Item | Blocked on | Ready when |
|---|---|---|

## Watching

Known, deliberately not scheduled — each with the reason it is not a defect *yet*, the **trigger**
that would promote it to Open, and the date it was last re-read.

| Item | Why not now | Trigger | Re-read |
|---|---|---|---|

## Done

| ID | Finding | Closed by |
|---|---|---|
