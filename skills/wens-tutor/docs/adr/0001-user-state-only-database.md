# The database holds user state only; content facts are parsed at startup

Courses and Banks are parsed into an in-memory catalogue on every process start
(`ATTACH ':memory:' AS cat`), and the on-disk SQLite file in the Materials Root holds
nothing but user state — Annotations, Progress, Stars, Attempts. There is deliberately no
`index` subcommand, no content cache, and no `sha256`/`mtime` invalidation logic.

The corpus is 660 KB and 200 Questions; parsing it costs tens of milliseconds, which is
cheaper than owning a cache and its staleness bugs. It also means the database can never
disagree with the Markdown, and that the file committed to the Materials Root is small and
semantically pure: every row in it is something the human did.

## Considered Options

- **One database holding both content facts and user state** (the original design). Forced
  an invariant — "re-indexing must never touch user state" — to protect user data from a
  destructive rebuild, plus cache-invalidation bookkeeping, and put a full second copy of
  the corpus into a binary blob that is committed on every re-index.
- **Two files: committed state database plus a gitignored content cache.** Removes the
  blob problem but keeps the cache, its invalidation, and the `index` step.

## Consequences

Cross-database joins (`main.star` against `cat.question`) are used freely; SQLite handles
these natively. The server keeps one connection guarded by a lock rather than one per
thread, because the catalogue lives on that connection.
