// skills/wens-tutor/web/app/reader.js
import S from "/strings.js";
import * as api from "/app/api.js";
import * as render from "/app/render.js";
import { isTouch, mountSelectionBar, openLookupResult } from "/app/host.js";

const params = new URLSearchParams(location.search);
const relpath = params.get("p");
const doc = document.getElementById("doc");
const COLORS = ["yellow", "green", "blue", "pink"];
let meta = null;

async function load() {
  meta = await api.get(`/api/file?p=${encodeURIComponent(relpath)}`);
  document.getElementById("title").textContent = meta.title;
  document.getElementById("keys").textContent = [S.keys.esc, S.reader.read].join("　");
  const source = await (await fetch(`/raw/${encodeURIComponent(relpath)}`)).text();
  render.renderInto(doc, source);
  buildToc();
  await restoreAnnotations();
  jumpToTarget();
  trackReadingPos();
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
    if (s.is_leaf) {
      const box = document.createElement("input");
      box.type = "checkbox";
      box.checked = s.read;
      box.title = S.reader.read;
      box.addEventListener("change", () =>
        api.post("/api/progress", { relpath, path: s.path, read: box.checked }));
      row.prepend(box);
    }
    toc.append(row);
  }
}

function scrollToLine(line) {
  const blocks = render.blocks(doc);
  const target = blocks.reduce((best, b) =>
    Number(b.dataset.line) <= line && (!best || Number(b.dataset.line) > Number(best.dataset.line)) ? b : best, null);
  (target || doc).scrollIntoView({ block: "start" });
}

async function restoreAnnotations() {
  const { annotations } = await api.get(`/api/annotations?p=${encodeURIComponent(relpath)}`);
  const list = document.getElementById("anns");
  list.textContent = "";
  const orphans = [];
  for (const ann of annotations) {
    const ok = render.anchor(doc, ann);
    if (!ok) orphans.push(ann);
    if (Boolean(ann.orphan) !== !ok) await api.patch(`/api/annotation/${ann.id}`, { orphan: ok ? 0 : 1 });
    const row = document.createElement("div");
    row.className = ok ? "ann-row" : "ann-row orphan";
    row.textContent = (ann.note_md ? `📝 ${ann.note_md} — ` : "") + `「${ann.exact}」`;
    const del = document.createElement("button");
    del.type = "button";
    del.textContent = S.reader.del;
    del.addEventListener("click", async () => { await api.del(`/api/annotation/${ann.id}`); location.reload(); });
    row.append(del);
    list.append(row);
  }
  if (orphans.length) list.prepend(Object.assign(document.createElement("h3"),
    { textContent: `${S.reader.orphanList} (${orphans.length})` }));
}

function setupSelectionBar() {
  const bar = mountSelectionBar(document.getElementById("selbar"));
  const rebuild = (quote) => {
    bar.textContent = "";
    for (const color of COLORS) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = `swatch swatch--${color}`;
      b.title = S.reader.highlight;
      b.addEventListener("click", async () => {
        await api.post("/api/annotation", { relpath, ...quote, color, note_md: "" });
        location.reload();
      });
      bar.append(b);
    }
    const note = document.createElement("button");
    note.type = "button";
    note.textContent = S.reader.note;
    note.addEventListener("click", async () => {
      const text = prompt(S.reader.note);
      if (text === null) return;
      await api.post("/api/annotation", { relpath, ...quote, color: "yellow", note_md: text });
      location.reload();
    });
    const look = document.createElement("button");
    look.type = "button";
    look.textContent = S.reader.lookup;
    look.addEventListener("click", () => showLookup(quote.exact));
    bar.append(note, look);
  };

  document.addEventListener("selectionchange", () => {
    const quote = render.quoteFromSelection(doc);
    if (!quote) { bar.hidden = true; return; }
    rebuild(quote);
    bar.hidden = false;
    if (!isTouch) {
      const rect = window.getSelection().getRangeAt(0).getBoundingClientRect();
      bar.style.top = `${window.scrollY + rect.top - 40}px`;
      bar.style.left = `${rect.left}px`;
    }
  });
}

async function showLookup(term) {
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
}

function jumpToTarget() {
  const path = params.get("path");
  const term = params.get("q");
  if (path) {
    const sec = meta.sections.find((s) => s.path === path);
    if (sec) scrollToLine(sec.line_start);
  } else if (meta.reading_pos) {
    scrollToLine(meta.reading_pos);
  }
  if (term) {
    for (const b of render.blocks(doc)) {
      if (b.textContent.includes(term)) { b.classList.add("focus"); b.scrollIntoView({ block: "center" }); break; }
    }
  }
}

function trackReadingPos() {
  let timer = null;
  window.addEventListener("scroll", () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      const mid = window.innerHeight / 2;
      const block = render.blocks(doc).find((b) => b.getBoundingClientRect().bottom > mid);
      if (block) api.post("/api/reading-pos", { relpath, line: Number(block.dataset.line) });
    }, 800);
  });
}

for (const [btn, panel] of [["toc-toggle", "toc"], ["ann-toggle", "anns"]]) {
  document.getElementById(btn).addEventListener("click", () =>
    document.getElementById(panel).classList.toggle("open"));
}
setupSelectionBar();
load();
