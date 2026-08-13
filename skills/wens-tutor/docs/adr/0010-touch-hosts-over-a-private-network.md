# Touch hosts are supported over a private virtual network, behind a token

Phones and tablets are first-class hosts: `serve --bind <addr>` may bind beyond loopback so a
device on the same private virtual network (Tailscale, ZeroTier, or an equivalent) can reach the
site. Binding to anything other than a loopback address **requires** a shared token, minted at
`init`, kept in the device-local registry, passed once in the URL and then held in a cookie.
The engine refuses to bind a non-loopback address without one.

The trust boundary is the virtual network, which is already device-authenticated at the
transport layer; the token exists so that *another* device on that network cannot read the
owner's study state by guessing a port. This is not a login: single user, one secret, compared
in constant time.

Touch is not a width — it is a different host, so the adaptation is a shared component with
per-host behaviour (`ui-design-principles` 2), never media-query bolt-ons over desktop chrome:

| Concern | Desktop | Touch |
|---|---|---|
| Selection toolbar | floats at the selection rect | fixed action bar at the bottom edge, clear of the OS selection handles |
| Annotation preview | hover | tap, and a second tap closes it (principle 15) |
| Lookup result | `window.open` in a new window | in-page slide-over panel |
| Reader columns | TOC + content + annotations | content only; TOC and annotations are drawers |
| Hit targets | pointer-sized | ≥44 px |

## Consequences

Plain HTTP on a private address is not a secure origin, so a service worker cannot register
there at all and Chrome will not offer an install prompt — which makes ADR 0008's decision moot
rather than merely deliberate. A home-screen bookmark still works and still honours the
manifest's `standalone` display. Anyone wanting a real secure origin fronts the loopback server
with their tunnel's own HTTPS (`tailscale serve`), which is zero code here; the engine never
implements TLS, because self-signed certificates on a phone are a trust-store fight with no
payoff.

Render cost was measured on an M4 desktop (82 ms cold for the 292 KB guide). A phone is
plausibly 3–5× slower, so ~300–400 ms — acceptable for a one-time render. [INFERENCE] If
real-device smoke shows more than a second, the fallback is chapter-scoped rendering on touch
hosts only, not a rewrite of the anchoring model.
