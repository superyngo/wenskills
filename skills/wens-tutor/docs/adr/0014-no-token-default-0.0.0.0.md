# No token; bind 0.0.0.0 by default

Supersedes ADR 0010. The token gate — a shared secret passed once in the URL and held in a
cookie — is removed entirely. `serve` binds `0.0.0.0` by default, not loopback, and the
engine no longer mints, stores, or checks a token.

The token existed so that another device on the same virtual network could not read the
owner's study state by guessing a port. In practice this was friction without security: the
trust boundary is the private network itself (Tailscale/ZeroTier), already device-authenticated
at the transport layer, and plain HTTP over it is not a secure origin regardless. The token
made the first URL ugly, required a cookie round-trip, and gave a false sense of auth on a
non-TLS transport.

The touch-host adaptation decisions from ADR 0010 stand (bottom action bar, slide-over lookup,
drawer columns, ≥44 px hit targets); only the token is gone.
