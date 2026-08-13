# Installable, but deliberately no service worker

The web surface ships a manifest and standalone display so it can be installed as its own
window, and its strings live in one catalogue from day one. It ships **no service worker and no
offline shell**, which is a deliberate deviation from `ui-design-principles` 23 ("on the web,
PWA is a baseline, not an afterthought").

Every page's content comes from the local server: the catalogue is parsed in-process (ADR 0001)
and user state lives in a SQLite file the browser cannot reach. An offline shell would therefore
load a UI with no Courses, no Questions, and no way to persist an answer — a screen that looks
usable and is not. "Cannot connect" is the honest failure; a cached empty shell is a misleading
one.

## Consequences

This is recorded precisely because the absence looks like an oversight: a future reader comparing
the skill against principle 23 would otherwise "fix" it.

It is also, since ADR 0010, not merely a choice: touch hosts reach the site over plain HTTP on a
private address, which is not a secure origin, so a service worker cannot register there and
Chrome's install prompt will not appear regardless. A home-screen bookmark still honours the
manifest. If the site is ever fronted by real HTTPS (`tailscale serve`) *and* gains a client-side
store that can survive without the server, the trade-off changes and this decision should be
revisited.

The manifest therefore ships no `icons` key at all. With no secure origin (ADR 0010) and no
service worker, the install prompt cannot fire regardless, so shipping 192/512 icons to satisfy
it would be theatre; the manifest earns its place through the home-screen name and theme colour
only.
