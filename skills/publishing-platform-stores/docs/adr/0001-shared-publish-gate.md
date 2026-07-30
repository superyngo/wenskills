# One shared publish-gate approval, not one gate per store

Publishing to N stores after a tagged build could put a separate manual-approval
`environment:` in front of every `publish-<store>.yml` workflow — the intuitive shape, since
each store submission feels like its own event. This skill instead prescribes **one** shared
gate workflow (triggered by the build workflow's completion) that fans out to every
`publish-<store>.yml` via `workflow_dispatch` after a single approval.

Chosen because per-store gates duplicate the same approval click N times for what is
conceptually one release decision ("ship this build"), and let individual targets' pending-
approval state drift out of sync with each other across reruns — a store re-triggered alone
after a transient failure would otherwise sit in a different approval state than its siblings.
A single gate treats "approve publishing" as one decision, made once per release, independent
of how many stores are wired up.

**Status:** accepted — running in production (confy, since the Microsoft Store + VS
Marketplace/Open VSX targets were both wired up).
