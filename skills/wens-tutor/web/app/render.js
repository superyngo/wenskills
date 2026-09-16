// skills/wens-tutor/web/app/render.js — markdown-it + data-line stamping + offset anchoring
const md = window.markdownit({ html: false, linkify: false });
const stamp = (tokens, idx, options, env, self) => {
  const t = tokens[idx];
  if (t.map) t.attrSet("data-line", String(t.map[0] + 1));
  return self.renderToken(tokens, idx, options, env);
};
for (const rule of ["paragraph_open", "heading_open", "table_open", "blockquote_open",
                    "bullet_list_open", "ordered_list_open"]) {
  md.renderer.rules[rule] = stamp;
}

if (window.mermaid) window.mermaid.initialize({ startOnLoad: false, theme: "neutral" });

/** Fence rule: render ```mermaid blocks as a container mermaid.run() fills in;
 * every other fence language keeps markdown-it's default <pre><code> output. */
const defaultFence = md.renderer.rules.fence
  || ((tokens, idx, options, env, self) => self.renderToken(tokens, idx, options, env));
md.renderer.rules.fence = (tokens, idx, options, env, self) => {
  const t = tokens[idx];
  if (t.info.trim() === "mermaid") {
    return `<pre class="mermaid">${md.utils.escapeHtml(t.content)}</pre>`;
  }
  return defaultFence(tokens, idx, options, env, self);
};

/** Placeholder delimiters for `[[#heading|alias]]` wikilinks and `![[file|width]]`
 * embeds — extracted before markdown-it for the same reason as math: a `|`
 * inside either construct would otherwise be read as a table-cell delimiter. */
const REF_OPEN = "\uE002", REF_CLOSE = "\uE003";

function extractRefs(source) {
  const store = [];
  const push = (entry) => `${REF_OPEN}${store.push(entry) - 1}${REF_CLOSE}`;
  let out = source.replace(/!\[\[([^|\]]+)(?:\|(\d+))?\]\]/g,
    (_, file, width) => push({ kind: "embed", file: file.trim(), width }));
  out = out.replace(/\[\[#([^|\]]+)(?:\|([^\]]+))?\]\]/g,
    (_, target, alias) => push({ kind: "wikilink", target: target.trim(), alias: (alias || target).trim() }));
  return { text: out, store };
}

/** Replace placeholder tokens with unresolved <a>/<img> markup — resolving
 * a wikilink target or an embed's file path needs the caller's section list
 * and file path, neither of which this module has (it also renders Question
 * stems, which carry no sections). The caller wires resolution afterward. */
function substituteRefs(html, store) {
  if (!store.length) return html;
  const re = new RegExp(`${REF_OPEN}(\\d+)${REF_CLOSE}`, "g");
  return html.replace(re, (_, idx) => {
    const entry = store[Number(idx)];
    if (entry.kind === "wikilink") {
      return `<a class="wikilink" data-target="${md.utils.escapeHtml(entry.target)}">${md.utils.escapeHtml(entry.alias)}</a>`;
    }
    const width = entry.width ? ` width="${Number(entry.width)}"` : "";
    return `<img class="embed" data-embed="${md.utils.escapeHtml(entry.file)}"${width} alt="${md.utils.escapeHtml(entry.file)}">`;
  });
}

/** Placeholder delimiters: Unicode Private-Use-Area chars markdown-it never
 * treats specially, so math spans survive inline parsing (bold/underscore/
 * pipe-in-tables) untouched until substituted back into the rendered HTML. */
const MATH_OPEN = "\uE000", MATH_CLOSE = "\uE001";

/** Pull `$$…$$` (display) and `$…$` (inline) LaTeX out of raw markdown before
 * it reaches markdown-it, replacing each with a placeholder token. Newlines
 * inside a match are preserved in the placeholder so later data-line stamping
 * (block line numbers) stays aligned with the original source. Currency like
 * `$850` or `$5/1M tokens…$15/1M` is excluded: a `$`-span starting with a
 * digit is only treated as math if it also contains a LaTeX command (`\`). */
function extractMath(source) {
  const store = [];
  const push = (tex, display, m) => {
    const idx = store.length;
    store.push({ tex: tex.trim(), display });
    const nl = (m.match(/\n/g) || []).length;
    return `${MATH_OPEN}${idx}${MATH_CLOSE}` + "\n".repeat(nl);
  };
  let out = source.replace(/\$\$([\s\S]+?)\$\$/g, (m, tex) => push(tex, true, m));
  out = out.replace(/\$([^\n$]+?)\$/g, (m, tex) => {
    if (/^\d/.test(tex) && !tex.includes("\\")) return m;
    return push(tex, false, m);
  });
  return { text: out, store };
}

/** Replace placeholder tokens in rendered HTML with KaTeX markup. */
function substituteMath(html, store) {
  if (!store.length) return html;
  const re = new RegExp(`${MATH_OPEN}(\\d+)${MATH_CLOSE}`, "g");
  return html.replace(re, (_, idx) => {
    const { tex, display } = store[Number(idx)];
    try {
      return window.katex.renderToString(tex, { displayMode: display, throwOnError: false });
    } catch {
      return display ? `$$${tex}$$` : `$${tex}$`;
    }
  });
}

export async function renderInto(el, source) {
  const refs = extractRefs(source);
  const { text, store } = extractMath(refs.text);
  el.innerHTML = substituteRefs(substituteMath(md.render(text), store), refs.store);
  if (window.mermaid) {
    const nodes = el.querySelectorAll("pre.mermaid");
    if (nodes.length) await window.mermaid.run({ nodes });
  }
  return el;
}

export function blocks(el) {
  return Array.from(el.querySelectorAll("[data-line]"));
}

/** Wrap a character range within a block in <mark> elements (one per text-node segment).
 * Per-segment wrapping avoids surroundContents throwing on ranges that cross
 * inline-element (<strong>, <a>, <td>, …) boundaries. All marks share ann.id. */
export function wrapRange(block, start, length, ann) {
  const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT);
  let seen = 0, node;
  const segs = [];
  while ((node = walker.nextNode())) {
    const nlen = node.nodeValue.length;
    const next = seen + nlen;
    if (next > start && seen < start + length) {
      // Skip whitespace-only nodes that are direct children of table structure
      // elements (tr/tbody/thead/tfoot/table) — wrapping them creates invalid
      // HTML and breaks table layout.
      const parent = node.parentElement;
      if (/^\s*$/.test(node.nodeValue) && parent && ["TR","THEAD","TBODY","TFOOT","TABLE"].includes(parent.nodeName)) {
        seen = next;
        continue;
      }
      segs.push({ node, s: Math.max(0, start - seen), e: Math.min(nlen, start + length - seen) });
    }
    seen = next;
  }
  if (!segs.length) return false;
  for (const seg of segs) {
    const range = document.createRange();
    range.setStart(seg.node, seg.s);
    range.setEnd(seg.node, seg.e);
    const mark = document.createElement("mark");
    mark.className = "ann ann--" + (ann.color || "yellow");
    mark.dataset.annId = ann.id;
    range.surroundContents(mark);
  }
  return true;
}

/** Unwrap a mark: move children back to parent, remove mark, normalize text nodes. */
export function unwrapMark(mark) {
  const parent = mark.parentNode;
  while (mark.firstChild) parent.insertBefore(mark.firstChild, mark);
  parent.removeChild(mark);
  parent.normalize();
}

/** Character offset of a mark's start within its containing block. */
export function markOffsetInBlock(block, mark) {
  const range = document.createRange();
  range.selectNodeContents(block);
  range.setEndBefore(mark);
  return range.toString().length;
}

/**
 * Anchor an annotation. Tries offset first (fast, deterministic), falls back to
 * text-quote search for legacy rows without offset data or when content shifted.
 */
export function anchor(el, ann) {
  if (ann.start_offset != null && ann.length > 0) {
    const block = blocks(el).find((b) => Number(b.dataset.line) === ann.block_line);
    if (block) {
      const sub = block.textContent.substr(ann.start_offset, ann.length);
      if (ann.exact && sub === ann.exact) {
        if (wrapRange(block, ann.start_offset, ann.length, ann)) return true;
      }
      // Fallback: normalize whitespace for cross-cell annotations where
      // Range.toString() used \t between cells but textContent uses \n.
      // Offsets may be wrong (different whitespace counts), so do a
      // normalized text search and map back to textContent coordinates.
      if (ann.exact) {
        for (const b of [block, ...blocks(el)]) {
          if (_anchorByNorm(b, ann)) return true;
        }
      }
    }
  }
  return _anchorByText(el, ann);
}

/** Legacy text-quote anchoring: search by exact + prefix/suffix + block_line. */
function _anchorByText(el, ann) {
  const all = blocks(el);
  const preferred = all.filter((b) => Number(b.dataset.line) === ann.block_line);
  const attempts = [
    { list: preferred, needle: (ann.prefix || "") + ann.exact + (ann.suffix || "") },
    { list: preferred, needle: ann.exact },
    { list: all, needle: ann.exact },
  ];
  for (const { list, needle } of attempts) {
    for (const block of list) {
      const idx = block.textContent.indexOf(needle);
      if (idx < 0) continue;
      const start = idx + (needle === ann.exact ? 0 : (ann.prefix || "").length);
      if (wrapRange(block, start, ann.exact.length, ann)) return true;
    }
  }
  return false;
}

/** Normalized text search: strip all whitespace from both sides, find match,
 *  then map back to textContent coordinates for wrapRange. Rescues cross-cell
 *  annotations where Range.toString() whitespace diverges from textContent. */
function _anchorByNorm(block, ann) {
  const text = block.textContent;
  const needle = ann.exact.replace(/\s+/g, "");
  if (!needle) return false;
  for (let start = 0; start < text.length; start++) {
    if (/\s/.test(text[start])) continue;
    let ti = start, ni = 0;
    while (ni < needle.length && ti < text.length) {
      if (/\s/.test(text[ti])) { ti++; continue; }
      if (text[ti] !== needle[ni]) break;
      ti++; ni++;
    }
    if (ni === needle.length)
      return wrapRange(block, start, ti - start, ann);
  }
  return false;
}

/**
 * Extract offset data from the current selection within el.
 * Returns {block_line, start_offset, length, exact} or null.
 */
export function selectionToOffset(el) {
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed) return null;
  const range = sel.getRangeAt(0);
  let node = sel.anchorNode;
  while (node && node !== el && !(node.dataset && node.dataset.line)) node = node.parentNode;
  if (!node || node === el) return null;
  const block = node;
  // Walk text nodes in block to find selection boundaries in textContent
  // coordinates — consistent with wrapRange's offset walk and anchor's
  // textContent comparison. Avoids Range.toString() whitespace normalization
  // (e.g. \t between table cells) that diverges from textContent.
  const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT);
  let seen = 0, tn, startOff = -1, endOff = -1;
  while ((tn = walker.nextNode())) {
    const nlen = tn.nodeValue.length;
    if (range.intersectsNode(tn)) {
      if (startOff < 0)
        startOff = (range.startContainer === tn) ? seen + range.startOffset : seen;
      endOff = (range.endContainer === tn) ? seen + range.endOffset : seen + nlen;
    }
    seen += nlen;
  }
  if (startOff < 0) return null;
  const raw = block.textContent.substring(startOff, endOff);
  const exact = raw.trim();
  if (!exact) return null;
  const leadWS = raw.length - raw.trimStart().length;
  return {
    block_line: Number(block.dataset.line),
    start_offset: startOff + leadWS,
    length: exact.length,
    exact,
  };
}
