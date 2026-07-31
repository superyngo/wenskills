# Per-store environments inside one gate run, when selective publishing is needed

ADR-0001 chose one shared `publish-gate` environment because per-store *workflow-level* gates
duplicate the same approval N times and let sibling stores' approval state drift. That
reasoning holds for the common case: "ship this release everywhere, yes/no."

It breaks down when a release legitimately shouldn't reach every configured store — a store's
listing is paused, this release only touches one platform's assets, or a prior submission to
that store is still under review and shouldn't be resubmitted. For that case, split
`publish-gate.yml`'s single job into N jobs (one per store), each gated by its own
`environment: publish-gate-<store>` instead of the one shared `publish-gate`. GitHub's "Review
pending deployments" screen lists every pending environment for **one workflow run** as
individually checkable items — the approver still visits the gate exactly once per release, but
can approve a subset instead of all-or-nothing. This keeps ADR-0001's "one release decision, one
visit" property while adding selection; rejected/unapproved jobs are simply skipped, not failed,
and don't block the jobs that were approved.

Trade-off: N environments to configure once in repo settings (reviewers list duplicated N
times) instead of 1. Default to the single shared environment from ADR-0001; adopt this only
when a project demonstrably needs per-release channel selection. The two are not mutually
exclusive across a project's lifetime — a project with one store today can name that store's
job/environment `publish-gate-<store>` from the start (zero extra cost) so a second store added
later slots into the same selective-gate shape without a rename.

**Status:** proposed — not yet run in production.
