// skills/wens-tutor/web/app/render.js — markdown-it + data-line stamping + text-quote anchoring
const md = window.markdownit({ html: false, linkify: false });
const stamp = (tokens, idx, options, env, self) => {
  const t = tokens[idx];
  if (t.map) t.attrSet("data-line", String(t.map[0] + 1));
  return self.renderToken(tokens, idx, options);
};
for (const rule of ["paragraph_open", "heading_open", "table_open", "blockquote_open",
                    "bullet_list_open", "ordered_list_open"]) {
  md.renderer.rules[rule] = stamp;
}

export function renderInto(el, source) {
  el.innerHTML = md.render(source);
  return el;
}

export function blocks(el) {
  return Array.from(el.querySelectorAll("[data-line]"));
}

/** Wrap `ann.exact` in a mark; returns true when anchored, false when orphaned. */
export function anchor(el, ann) {
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
      if (wrapTextRange(block, start, ann.exact.length, ann)) return true;
    }
  }
  return false;
}

function wrapTextRange(block, start, length, ann) {
  const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT);
  let seen = 0, node, range = document.createRange(), set = false;
  while ((node = walker.nextNode())) {
    const next = seen + node.nodeValue.length;
    if (!set && next > start) { range.setStart(node, start - seen); set = true; }
    if (set && next >= start + length) { range.setEnd(node, start + length - seen); break; }
    seen = next;
  }
  if (!set) return false;
  const mark = document.createElement("mark");
  mark.className = "ann ann--" + (ann.color || "yellow");
  mark.dataset.annId = ann.id;
  if (ann.note_md) mark.dataset.note = ann.note_md;
  try { range.surroundContents(mark); } catch (_) { return false; }
  return true;
}

/** {block_line, exact, prefix, suffix} for the current selection, or null. */
export function quoteFromSelection(el) {
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed) return null;
  const exact = sel.toString().trim();
  if (!exact) return null;
  let node = sel.anchorNode;
  while (node && node !== el && !(node.dataset && node.dataset.line)) node = node.parentNode;
  if (!node || node === el) return null;
  const text = node.textContent;
  const at = text.indexOf(exact);
  return {
    block_line: Number(node.dataset.line),
    exact,
    prefix: at > 0 ? text.slice(Math.max(0, at - 32), at) : "",
    suffix: at >= 0 ? text.slice(at + exact.length, at + exact.length + 32) : "",
  };
}
