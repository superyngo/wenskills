# Device settings live in a local registry; the Materials Root carries only user state

Materials Roots are registered in `~/.config/wens-tutor/roots.json` (device-local, never
committed), which is also where the serve port and the default root live. Inside the
Materials Root there is exactly one tooling file, `.tutor/tutor.db`, and it contains only
user state. The root's own location is never written down inside itself — it is the parent
of `.tutor/`.

The Materials Root is a git repo that exists to sync across devices, so anything
device-specific stored inside it is wrong on the other device: an absolute root path
recorded in a committed config file is guaranteed to be stale after the first sync. The
registry also solves discovery, which walking up from the working directory cannot: an agent
session usually runs in the skill's own repo, from which no amount of walking upward will
ever find a Materials Root.

## Consequences

`init` must be run once per device. A root moved on disk needs re-registering; the tooling
reports a registered-but-missing root rather than silently creating a new database.
