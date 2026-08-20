// skills/wens-tutor/web/app/host.js — host detection for touch vs pointer
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
