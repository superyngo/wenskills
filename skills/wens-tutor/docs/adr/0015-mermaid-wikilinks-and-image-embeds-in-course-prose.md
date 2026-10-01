# Mermaid, wikilinks, and image embeds render client-side; resolution stays in `reader.js`

Course prose in the corpus now uses three Obsidian conventions that `render.js` previously
passed through as literal text or silently dropped: ` ```mermaid ` fenced flowcharts,
`[[#heading|alias]]` intra-file wikilinks, and `![[file|width]]` image embeds.

**Mermaid** is rendered client-side with a vendored `mermaid.min.js` (same pattern as
`vendor/katex/`), not pre-rendered to a static image at authoring time. The corpus already
treats Markdown as the single source of truth that the engine renders live (ADR-worthy
precedent: KaTeX for `$…$`) — a pre-rendered SVG would silently go stale the next time the
diagram's source changes, with no signal that it had. The cost is real: `mermaid.min.js` is
roughly 3.5 MB unminified-download / ~700 KB gzipped, an order of magnitude past
`katex.min.js` (277 KB). It is loaded only on `reader.html`; `exam.html` never renders Course
prose and does not pay for it.

**Wikilinks and embeds are extracted before `markdown-it` sees the source**, using the same
placeholder-token technique as the existing LaTeX math extraction. This is not just
consistency: several wikilinks in the real corpus sit inside table cells
(`| … | [[#③ 模型選擇與架構設計|③ 模型選擇]] | … |`), and the `|` inside `[[target|alias]]`
would otherwise be read as a table-cell delimiter by markdown-it's table parser, corrupting
the row.

**Resolution is deliberately split from parsing.** `render.js` emits inert
`<a class="wikilink" data-target="…">`/`<img class="embed" data-embed="…">` markup only —
it has no section list and no file path, because it also renders Question stems in `exam.js`,
which carry neither. `reader.js` (which has `meta.sections` and knows its own `relpath`) wires
the actual jump target and embed `src` afterward. A wikilink target is matched against
`Section.title` verbatim — `tutorlib/parser.py` already stores the raw heading text there, so
no new identity scheme was introduced. An embed path resolves relative to the Material File's
own directory, matching how the corpus's images sit beside their `.md` file on disk; if that
404s, `reader.js` retries once under that directory's `assets/` subfolder (some notes keep
images there). Obsidian's vault-wide basename lookup is deliberately not replicated.

**Unresolved targets are visibly broken, not silently swallowed or hard errors** — a
mistyped wikilink target or a missing/renamed image gets the same dashed-underline treatment
as an Orphan Annotation, discoverable by reading, not hidden and not a build failure.

This stays entirely inside the web layer. `tutorlib/parser.py`, `check`, and the Bank/Defect
vocabulary are untouched — none of the three conventions occur in Bank content in the current
corpus, and if one ever does, it renders inertly there exactly as it did before this change.

## Server-side prerequisite

`safe_material_path` (`server.py`) rejected every non-`.md` path outright, so `/raw/` could
not serve an image at all before this change — a correctness bug independent of the render
work, fixed by taking an `exts` allow-list (default unchanged at `(".md",)`) and passing an
image-extension allow-list from the `/raw/` handler, which now also sets the real
`Content-Type` via `mimetypes.guess_type` instead of a hardcoded `text/markdown`.
