// skills/wens-tutor/web/app/stats.js — panel order: score, per-bank, most-missed, trend, pace
import S from "/strings.js";
import * as api from "/app/api.js";

const root = document.getElementById("root");

function panel(title) {
  const s = document.createElement("section");
  s.append(Object.assign(document.createElement("h2"), { textContent: title }));
  root.append(s);
  return s;
}

function sparkline(values, passLine) {
  const w = 480, h = 120, max = 100;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svg.setAttribute("width", "100%");
  const line = (points, color, dash) => {
    const el = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
    el.setAttribute("points", points);
    el.setAttribute("fill", "none");
    el.setAttribute("stroke", color);
    if (dash) el.setAttribute("stroke-dasharray", "4 4");
    svg.append(el);
  };
  if (values.length) {
    const step = values.length > 1 ? w / (values.length - 1) : 0;
    line(values.map((v, i) => `${i * step},${h - (v / max) * h}`).join(" "), "#0b5");
  }
  line(`0,${h - (passLine / max) * h} ${w},${h - (passLine / max) * h}`, "#d33", true);
  return svg;
}

function row(text) {
  return Object.assign(document.createElement("p"), { textContent: text });
}

async function main() {
  document.getElementById("title").textContent = S.stats.title;
  const data = await api.get("/api/stats");

  panel(S.stats.scores).append(sparkline(data.scores.map((s) => s.score), 60));

  const banks = panel(S.stats.perBank);
  for (const b of data.per_bank) {
    banks.append(row(
      `${b.title} — ${S.stats.latest} ${b.latest_score ?? "—"} · ${S.stats.best} ${b.best_score ?? "—"}` +
      ` · ${S.stats.attempts} ${b.attempts} · ${b.n_questions} 題` +
      ` · ${S.portal.stars} ${b.stars}${b.defects ? ` · ${S.portal.defects} ${b.defects}` : ""}`,
    ));
  }

  const missed = panel(S.stats.missed);
  if (!data.most_missed.length) missed.append(row(S.stats.none));
  for (const item of data.most_missed) {
    const a = document.createElement("a");
    a.href = `/exam?q=${encodeURIComponent(item.qkey)}`;
    a.textContent = `×${item.wrong_count} · ${item.bank_title} 第${item.ordinal}題 — ${item.snippet}`;
    missed.append(a, document.createElement("br"));
  }

  const trend = panel(S.stats.trend);
  trend.append(row(`${S.portal.stars} ${data.stars} · ${S.portal.defects} ${data.defects}`));

  const pace = panel(S.stats.pace);
  pace.append(row(`${data.pace_seconds_per_question ?? "—"} s / ${data.official_pace_seconds} s`));
}
main();
