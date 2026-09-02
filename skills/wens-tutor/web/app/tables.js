// skills/wens-tutor/web/app/tables.js — drag-to-resize table columns, ratios persisted per (relpath, table line)
const MIN_PX = 48; // ~3em at 16px base

function storageKey(relpath, line) {
  return `colw:${relpath}:${line}`;
}

function applyRatios(colgroup, widths) {
  const cols = colgroup.querySelectorAll("col");
  cols.forEach((col, i) => { col.style.width = `${widths[i]}%`; });
}

function setupTable(table, relpath) {
  const line = table.getAttribute("data-line");
  const headRow = table.querySelector("tr");
  if (!headRow) return;
  const cellCount = headRow.children.length;
  if (cellCount < 2) return;

  const colgroup = document.createElement("colgroup");
  for (let i = 0; i < cellCount; i++) colgroup.append(document.createElement("col"));
  table.prepend(colgroup);

  const key = storageKey(relpath, line);
  const saved = line ? localStorage.getItem(key) : null;
  let ratios;
  try {
    ratios = saved ? JSON.parse(saved) : null;
  } catch {
    ratios = null;
  }
  if (!Array.isArray(ratios) || ratios.length !== cellCount) {
    ratios = Array(cellCount).fill(100 / cellCount);
  }
  applyRatios(colgroup, ratios);

  // Wrap the table so resize handles can span its FULL height (not just the header
  // row): a handle parented to <th> is clipped to that row's height, which is too
  // short a target to reliably hit on touch.
  const wrap = document.createElement("div");
  wrap.className = "table-wrap";
  table.replaceWith(wrap);
  wrap.append(table);

  const handles = [];
  for (let i = 0; i < cellCount - 1; i++) {
    const handle = document.createElement("span");
    handle.className = "col-resizer";
    wrap.append(handle);
    handles.push(handle);
  }

  const headCells = Array.from(headRow.children);
  const positionHandles = () => {
    const wrapRect = wrap.getBoundingClientRect();
    for (let i = 0; i < handles.length; i++) {
      const cellRect = headCells[i].getBoundingClientRect();
      handles[i].style.left = `${cellRect.right - wrapRect.left}px`;
    }
  };
  positionHandles();
  window.addEventListener("resize", positionHandles);

  handles.forEach((handle, i) => {
    handle.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      const tableWidth = table.getBoundingClientRect().width;
      const startPx = ratios.map((r) => (r / 100) * tableWidth);
      const startX = e.clientX;
      handle.setPointerCapture(e.pointerId);
      document.body.classList.add("resizing-col");

      const onMove = (ev) => {
        const delta = ev.clientX - startX;
        let left = startPx[i] + delta;
        let right = startPx[i + 1] - delta;
        if (left < MIN_PX) { right -= (MIN_PX - left); left = MIN_PX; }
        if (right < MIN_PX) { left -= (MIN_PX - right); right = MIN_PX; }
        const px = startPx.slice();
        px[i] = left;
        px[i + 1] = right;
        const total = px.reduce((a, b) => a + b, 0);
        ratios = px.map((v) => (v / total) * 100);
        applyRatios(colgroup, ratios);
        positionHandles();
      };
      const onUp = () => {
        handle.removeEventListener("pointermove", onMove);
        handle.removeEventListener("pointerup", onUp);
        document.body.classList.remove("resizing-col");
        if (line) localStorage.setItem(key, JSON.stringify(ratios));
      };
      handle.addEventListener("pointermove", onMove);
      handle.addEventListener("pointerup", onUp);
    });
  });
}

export function enhanceTables(doc, relpath) {
  doc.querySelectorAll("table[data-line]").forEach((table) => setupTable(table, relpath));
}
