# User state is exported to JSON beside the database

`tutor.py export` writes all user state — Annotations, Progress, Stars, Notes, Papers, Attempts
— into a single human-readable JSON file committed next to `tutor.db`, and `tutor.py import`
rebuilds the database from it. Both representations of the same data are committed on purpose.

`tutor.db` is committed so study state syncs across devices (ADR 0001), but SQLite is binary:
git cannot merge it, so two devices that both study before syncing can only keep one side and
silently discard the other's Attempts, and a corrupted or deleted file takes every Star,
Annotation and Attempt with it. The JSON is diffable and mergeable, which turns "pick a side"
into a real merge and "total loss" into "restore from the last commit". Roughly 60 lines of code
buys both.

## Consequences

The two can drift if `export` is skipped, so the JSON is authoritative only as a recovery and
merge artifact, never as the live store: `SKILL.md` runs `export` before any commit of the
Materials Root, and `check` reports a JSON older than the database's newest row.
