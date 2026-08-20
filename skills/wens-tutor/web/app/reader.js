// skills/wens-tutor/web/app/reader.js
import S from "/strings.js";
import * as api from "/app/api.js";
import * as render from "/app/render.js";
import { openLookupResult } from "/app/host.js";

const params = new URLSearchParams(location.search);
const relpath = params.get("p");
const doc = document.getElementById("doc");
const COLORS = ["yellow", "green", "blue", "pink"];
let meta = null;
let activeColor = COLORS[0];
let cachedSel = null; // {block_line, start_offset, length, exact} — captured at selectionchange

// --- Annotation panel helpers (incremental, no reload) ------------------------

function addAnnRow(ann, ok) {
  const list = document.getElementById("anns");
  const empty = list.querySelector("p[style]");
  if (empty) empty.remove();
  const row = document.createElement("div");
  row.className = ok ? "ann-row" : "ann-row orphan";
  row.dataset.annId = ann.id;
  const label = document.createElement(ok ? "a" : "span");
  label.textContent = `「${ann.exact}」`;
  if (ok) {
    label.href = "#";
    label.title = S.reader.jumpHint;
    label.addEventListener("click", (e) => { e.preventDefault(); jumpToAnnotation(ann.id); });
  }
  row.append(label);
  const del = document.createElement("button");
  del.type = "button";
  del.textContent = S.reader.del;
  del.addEventListener("click", () => deleteAnnotation(ann.id));
  row.append(del);
  list.append(row);
  return row;
}

async function deleteAnnotation(annId) {
  await api.del(`/api/annotation/${annId}`);
  const mark = doc.querySelector(`mark.ann[data-ann-id="${annId}"]`);
  if (mark) render.unwrapMark(mark);
  const row = document.querySelector(`#anns [data-ann-id="${annId}"]`);
  if (row) row.remove();
}

// --- Load ---------------------------------------------------------------------

async function load() {
  meta = await api.get(`/api/file?p=${encodeURIComponent(relpath)}`);
  document.getElementById("title").textContent = meta.title;
  document.getElementById("keys").textContent = `${S.keys.esc}　l ${S.reader.highlight}/${S.reader.clear}`;
  const source = await (await fetch(`/raw/${encodeURIComponent(relpath)}`)).text();
  render.renderInto(doc, source);
  hideAnswers();
  buildToc();
  await restoreAnnotations();
  jumpToTarget();
  // Restore saved scroll position when not arriving via lookup params
  if (!params.get("path") && !params.get("q")) {
    const saved = localStorage.getItem(`scroll:${relpath}`);
    if (saved) window.scrollTo(0, Number(saved));
}
}

function buildToc() {
  const toc = document.getElementById("toc");
  toc.textContent = "";
  for (const s of meta.sections) {
    const row = document.createElement("div");
    row.style.paddingInlineStart = `${(s.level - 1) * 0.75}rem`;
    const link = document.createElement("a");
    link.href = `#L${s.line_start}`;
    link.textContent = s.title;
    link.addEventListener("click", (e) => {
      e.preventDefault();
      scrollToLine(s.line_start);
    });
    row.append(link);
    toc.append(row);
  }
}

function scrollToLine(line) {
  const blocks = render.blocks(doc);
  const target = blocks.reduce((best, b) =>
    Number(b.dataset.line) <= line && (!best || Number(b.dataset.line) > Number(best.dataset.line)) ? b : best, null);
  (target || doc).scrollIntoView({ block: "start" });
}

function jumpToAnnotation(annId) {
  const mark = doc.querySelector(`mark.ann[data-ann-id="${annId}"]`);
  if (!mark) return;
  mark.scrollIntoView({ behavior: "smooth", block: "center" });
  mark.classList.add("flash");
  setTimeout(() => mark.classList.remove("flash"), 1500);
}

function hideAnswers() {
  for (const p of doc.querySelectorAll("p")) {
    if (/答案[：:]/.test(p.textContent)) {
      p.classList.add("answer-hidden");
      p.title = S.reader.revealAnswer;
      p.addEventListener("click", () => p.classList.replace("answer-hidden", "answer-shown"));
    }
  }
}

async function restoreAnnotations() {
  const { annotations } = await api.get(`/api/annotations?p=${encodeURIComponent(relpath)}`);
  const list = document.getElementById("anns");
  list.textContent = "";
  const orphans = [];
  for (const ann of annotations) {
    const ok = render.anchor(doc, ann);
    if (!ok) orphans.push(ann);
    if (Boolean(ann.orphan) !== !ok) api.patch(`/api/annotation/${ann.id}`, { orphan: ok ? 0 : 1 });
    addAnnRow(ann, ok);
  }
  if (!annotations.length) list.append(Object.assign(document.createElement("p"),
    { textContent: S.reader.empty, style: "color:#999" }));
  if (orphans.length) list.prepend(Object.assign(document.createElement("h3"),
    { textContent: `${S.reader.orphanList} (${orphans.length})` }));
}

// --- Header-based highlight toolbar -------------------------------------------

const btnApply = document.getElementById("hl-apply");
const btnColor = document.getElementById("hl-color");
const btnClear = document.getElementById("hl-clear");
const lookBtn = Object.assign(document.createElement("button"),
  { type: "button", textContent: S.reader.lookup, disabled: true });
lookBtn.addEventListener("click", () => { if (cachedSel) showLookup(cachedSel.exact); });
document.querySelector(".toolbar").append(lookBtn);

function syncButtons() {
  cachedSel = render.selectionToOffset(doc);
  const has = Boolean(cachedSel);
  btnApply.disabled = !has;
  btnClear.disabled = !has;
  lookBtn.disabled = !has;
}

btnApply.textContent = S.reader.highlight;
btnColor.textContent = S.reader.color;
btnClear.textContent = S.reader.clear;

btnColor.addEventListener("click", () => {
  activeColor = COLORS[(COLORS.indexOf(activeColor) + 1) % COLORS.length];
  btnColor.className = `swatch swatch--${activeColor}`;
});

btnApply.addEventListener("click", async () => {
  if (!cachedSel) return;
  const { block_line, start_offset, length, exact } = cachedSel;
  const res = await api.post("/api/annotation", { relpath, block_line, start_offset, length, exact, color: activeColor });
  const ann = { id: res.id, block_line, start_offset, length, exact, color: activeColor };
  // Incremental DOM update: wrap in-place, add panel row
  const block = render.blocks(doc).find((b) => Number(b.dataset.line) === block_line);
  if (block && !render.wrapRange(block, start_offset, length, ann)) return; // cross-boundary edge case
  addAnnRow(ann, true);
  window.getSelection().removeAllRanges();
  cachedSel = null;
  syncButtons();
});

btnClear.addEventListener("click", async () => {
  if (!cachedSel) return;
  const { block_line, start_offset, length } = cachedSel;
  const selEnd = start_offset + length;
  const block = render.blocks(doc).find((b) => Number(b.dataset.line) === block_line);
  if (!block) return;
  // Offset intersection: find marks in the same block whose range overlaps the selection
  const marks = Array.from(block.querySelectorAll("mark.ann")).filter((mark) => {
    const mStart = render.markOffsetInBlock(block, mark);
    const mEnd = mStart + mark.textContent.length;
    return mStart < selEnd && start_offset < mEnd;
  });
  for (const mark of marks) {
    const annId = mark.dataset.annId;
    api.del(`/api/annotation/${annId}`);
    render.unwrapMark(mark);
    const row = document.querySelector(`#anns [data-ann-id="${annId}"]`);
    if (row) row.remove();
  }
  window.getSelection().removeAllRanges();
  cachedSel = null;
  syncButtons();
});

// `l` = toggle highlight: apply if clean, clear if already marked
document.addEventListener("keydown", (e) => {
  if (e.key !== "l" || (e.target instanceof Element && e.target.matches("textarea, input"))) return;
  if (!cachedSel) return;
  e.preventDefault();
  const { block_line, start_offset, length } = cachedSel;
  const selEnd = start_offset + length;
  const block = render.blocks(doc).find((b) => Number(b.dataset.line) === block_line);
  if (!block) return;
  const hasMark = Array.from(block.querySelectorAll("mark.ann")).some((mark) => {
    const mStart = render.markOffsetInBlock(block, mark);
    return mStart < selEnd && start_offset < mStart + mark.textContent.length;
  });
  (hasMark ? btnClear : btnApply).click();
});

document.addEventListener("selectionchange", syncButtons);

// --- Lookup -------------------------------------------------------------------

function showLookup(term) {
  return (async () => {
    const res = await api.get(`/api/lookup?q=${encodeURIComponent(term)}`);
    const panel = document.createElement("div");
    panel.className = "popup";
    panel.append(Object.assign(document.createElement("p"),
      { textContent: `${S.exam.queryUsed}：${res.query_used}` }));
    for (const hit of res.courses) {
      const a = document.createElement("a");
      a.href = `/reader?p=${encodeURIComponent(hit.relpath)}&path=${encodeURIComponent(hit.path)}&q=${encodeURIComponent(res.query_used)}`;
      a.textContent = `${hit.subject} · ${hit.title} — ${hit.snippet.slice(0, 60)}`;
      a.addEventListener("click", (e) => { e.preventDefault(); openLookupResult(a.href); });
      panel.append(a);
    }
    const close = document.createElement("button");
    close.type = "button";
    close.textContent = "×";
    close.addEventListener("click", () => panel.remove());
    panel.prepend(close);
    document.body.append(panel);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") panel.remove(); }, { once: true });
  })();
}


// --- Navigation ---------------------------------------------------------------

function jumpToTarget() {
  const path = params.get("path");
  const term = params.get("q");
  if (path) {
    const sec = meta.sections.find((s) => s.path === path);
    if (sec) scrollToLine(sec.line_start);
  }
  if (term) {
    for (const b of render.blocks(doc)) {
      if (b.textContent.includes(term)) { b.classList.add("focus"); b.scrollIntoView({ block: "center" }); break; }
    }
  }
}


// --- Init ---------------------------------------------------------------------

document.getElementById("toc-toggle").textContent = S.reader.toc;
document.getElementById("ann-toggle").textContent = S.reader.annotations;
for (const [btn, panel] of [["toc-toggle", "toc"], ["ann-toggle", "anns"]]) {
  document.getElementById(btn).addEventListener("click", () =>
    document.getElementById(panel).classList.toggle("open"));
}

// Save scroll position (debounced) for restore on next load
let scrollTimer;
window.addEventListener("scroll", () => {
  clearTimeout(scrollTimer);
  scrollTimer = setTimeout(() => localStorage.setItem(`scroll:${relpath}`, String(window.scrollY)), 300);
});
btnColor.className = `swatch swatch--${activeColor}`;
load();
