# Publishing to Platform Stores — Domain

Vocabulary for describing how a project ships built artifacts to third-party platforms via CI.

## Language

**Store**:
A third-party marketplace or distribution platform that requires a manually-created listing,
its own credentials, and (usually) a review process before a build reaches users. Examples:
Microsoft Store, VS Marketplace, Chrome Web Store. This skill's entire scope.
_Avoid_: Target, platform

**Channel**:
Any distribution outlet for a build at all, store or not — the broader umbrella term. Includes
every Store, but also non-store outlets with no listing/review step (a raw GitHub Release
binary, a web deploy). Use "channel" only when deliberately including non-store outlets;
otherwise say "store."

**Extension**:
A build that installs into a specific host application — an editor, a note-taking app, or a
browser — rather than running standalone. Covers marketplace-API-backed hosts (VS Marketplace,
Open VSX, Chrome Web Store, Edge Add-ons, Firefox AMO) and API-less hosts (Obsidian, which ships
via GitHub Releases only, no store API). A browser is a host application like any other — it is
not a separate top-level category from Extension, just another kind of host.
_Avoid_: IDE extension, browser extension (as a top-level category), plugin

**Release**:
The GitHub Release object/event produced by the build+tag workflow. Reserved exclusively for
this GitHub-specific artifact — never used to mean "shipped to a Store."
_Avoid_: Publish (when referring to the GitHub Release itself), ship

**Publish**:
The umbrella verb for the whole act of shipping a build to a Store, end to end — what a
`publish-<store>.yml` workflow does, regardless of whether that Store has a review step.
_Avoid_: Release (reserved for the GitHub object), deploy

**Submit**:
The sub-step, within publishing, of making a build store-visible — either by handing it to a
Store's review queue (a network call, for Stores with a real API: Apple, Google Play
closed/production, Chrome listed, Firefox listed) or, for Stores with no API at all, by minting
the Store's own canonical distribution artifact that its client polls directly (Obsidian: a
correctly-tagged GitHub Release — no third party involved, but still the action that makes the
build visible, not just transferred). Stores that go live the instant a build is uploaded, with
no separate visibility step (Steam), skip this word entirely.
_Avoid_: Upload (the mechanical transfer only, never the visibility-making action)
