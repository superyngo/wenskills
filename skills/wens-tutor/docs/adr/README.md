# wens-tutor — Architecture Decision Records

Decisions for the `wens-tutor` skill. They live inside the skill because `SKILL.md` loads them
by relative path (root [ADR 0002](../../../../docs/adr/0002-skill-local-docs-stay-in-the-skill.md)).
ADRs are never edited; a revisited decision gets a new ADR. Vocabulary:
[`../../CONTEXT.md`](../../CONTEXT.md).

| # | Decision | Status |
|---|---|---|
| [0001](0001-user-state-only-database.md) | The database holds user state only; content facts are parsed at startup | Implemented (2026-08-13) |
| [0002](0002-content-addressed-question-identity.md) | User state is keyed on content, not on file paths | Implemented (2026-08-13) |
| [0003](0003-device-local-root-registry.md) | Device settings live in a local registry; the Materials Root carries only user state | Implemented (2026-08-13) |
| [0004](0004-defective-questions-excluded-by-default.md) | Defective Questions are detected, excluded from Papers by default, and repaired in content | Implemented (2026-08-13) |
| [0005](0005-explanations-live-in-content.md) | Explanations are content in the Bank; Notes are user state | Implemented (2026-08-13) |
| [0006](0006-bank-is-a-region-not-a-file.md) | A Bank is a region of a Material File, not a file | Implemented (2026-08-13) |
| [0007](0007-sections-identified-by-ancestor-path.md) | Sections are identified by their ancestor path | Implemented (2026-08-13) |
| [0008](0008-no-service-worker.md) | Installable, but deliberately no service worker | Implemented (2026-08-13) |
| [0009](0009-json-export-beside-the-database.md) | User state is exported to JSON beside the database | Implemented (2026-08-13) |
| [0010](0010-touch-hosts-over-a-private-network.md) | Touch hosts are supported over a private virtual network | Superseded by 0014 |
| [0011](0011-shared-stems-are-folded-into-every-member-question.md) | Shared stems are folded into every member Question | Implemented (2026-08-13) |
| [0012](0012-the-parser-attributes-every-line-or-reports-it.md) | The parser attributes every line, or reports it as a Defect | Implemented (2026-08-13) |
| [0013](0013-answers-reach-the-client-only-at-submission.md) | Answers reach the client only at submission | Implemented (2026-08-13) |
| [0014](0014-no-token-default-0.0.0.0.md) | No token; bind 0.0.0.0 by default | Implemented (2026-08-20) |
| [0015](0015-mermaid-wikilinks-and-image-embeds-in-course-prose.md) | Mermaid, wikilinks, and image embeds render client-side; resolution stays in `reader.js` | Implemented (2026-09-16) |
