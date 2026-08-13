// skills/wens-tutor/web/app/host.js — one host decision, not scattered media queries (ADR 0010)
export const isTouch = window.matchMedia("(pointer: coarse)").matches;

export function openLookupResult(url) {
  if (!isTouch) { window.open(url, "_blank", "noopener"); return null; }
  const panel = document.createElement("aside");
  panel.className = "slideover";
  panel.innerHTML = `<iframe src="${url}" title="lookup"></iframe>`;
  panel.addEventListener("click", (e) => { if (e.target === panel) panel.remove(); });
  document.body.appendChild(panel);
  return panel;
}

export function mountSelectionBar(el) {
  el.classList.toggle("selection-bar--bottom", isTouch);
  el.classList.toggle("selection-bar--float", !isTouch);
  return el;
}
