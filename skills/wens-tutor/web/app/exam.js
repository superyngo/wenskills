// skills/wens-tutor/web/app/exam.js
import S from "/strings.js";
import * as api from "/app/api.js";
import * as render from "/app/render.js";
import { openLookupResult } from "/app/host.js";

const params = new URLSearchParams(location.search);
const root = document.getElementById("root");
const clock = document.getElementById("clock");
let attempt = null, index = 0, shownAt = Date.now(), ticker = null, deadline = null;

async function main() {
  document.getElementById("keys").textContent =
    [S.keys.digits, S.keys.arrows, S.keys.enter, S.keys.esc].join("　");
  if (params.get("attempt")) return openAttempt(Number(params.get("attempt")));
  if (params.get("q")) return startPaper({ qkeys: [params.get("q")], timed: false });
  if (params.get("drill")) return startPaper({ drill: true });
  renderComposeForm();
}

function renderComposeForm() {
  document.getElementById("phase").textContent = S.exam.compose;
  const form = document.createElement("form");
  const fields = [
    ["cap", S.exam.cap, "number", 50],
    ["shuffle", S.exam.shuffle, "checkbox", true],
    ["timed", S.exam.timed, "checkbox", true],
    ["include_defective", S.exam.includeDefective, "checkbox", false],
  ];
  const bank = document.createElement("select");
  bank.multiple = true;
  bank.name = "bkeys";
  api.get("/api/portal").then((data) => {
    for (const s of data.subjects) {
      for (const f of s.files) {
        for (const b of f.banks) {
          const opt = document.createElement("option");
          opt.value = b.bkey;
          opt.selected = params.get("bkey") ? params.get("bkey") === b.bkey : true;
          opt.textContent = `${s.subject} · ${f.title} — ${b.title} (${b.n_questions})`;
          bank.append(opt);
        }
      }
    }
  });
  form.append(Object.assign(document.createElement("label"), { textContent: S.exam.banks }), bank);
  for (const [name, label, type, value] of fields) {
    const wrap = document.createElement("label");
    wrap.textContent = label;
    const input = document.createElement("input");
    input.name = name; input.type = type;
    if (type === "checkbox") input.checked = value; else input.value = value;
    wrap.append(input);
    form.append(wrap);
  }
  const go = document.createElement("button");
  go.type = "submit"; go.textContent = S.exam.start;
  form.append(go);
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    startPaper({
      bkeys: Array.from(bank.selectedOptions).map((o) => o.value),
      cap: Number(fd.get("cap")),
      shuffle: fd.get("shuffle") === "on",
      timed: fd.get("timed") === "on",
      include_defective: fd.get("include_defective") === "on",
    });
  });
  root.textContent = "";
  root.append(form);
}

/** The deadline is derived exactly once per Attempt open (ADR: never on re-paint). */
function adoptAttempt(payload, id) {
  attempt = payload;
  attempt.attempt_id = id ?? payload.attempt_id;
  deadline = payload.remaining_ms == null ? null : Date.now() + payload.remaining_ms;
  startClock();
}

async function startPaper(criteria) {
  adoptAttempt(await api.post("/api/paper", criteria));
  index = 0;
  paint();
}

async function openAttempt(id) {
  adoptAttempt(await api.get(`/api/attempt/${id}`), id);
  index = attempt.questions.findIndex((q) => !q.given);
  if (index < 0) index = 0;
  paint();
}

function paint() {
  document.getElementById("phase").textContent = `${index + 1}/${attempt.questions.length}`;
  if (attempt.questions.length === 0) {
    root.textContent = "";
    root.append(Object.assign(document.createElement("p"), { textContent: S.exam.empty }));
    const home = document.createElement("a");
    home.href = "/";
    home.textContent = S.exam.backHome;
    root.append(home);
    return;
  }
  const q = attempt.questions[index];
  shownAt = Date.now();
  root.textContent = "";

  const stem = document.createElement("div");
  render.renderInto(stem, q.stem_md);
  root.append(stem);

  for (const [letter, text] of q.options) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "option" + (q.given === letter ? " focus" : "");
    btn.textContent = `(${letter}) ${text}`;
    btn.addEventListener("click", () => choose(letter));
    root.append(btn);
  }

  const star = document.createElement("button");
  star.type = "button";
  star.textContent = (q.starred ? "★ " : "☆ ") + S.exam.star;
  star.addEventListener("click", async () => {
    const res = await api.post("/api/star", { qkey: q.qkey });
    q.starred = res.starred;
    paint();
  });

  const look = document.createElement("button");
  look.type = "button";
  look.textContent = S.reader.lookup;
  look.addEventListener("click", () => lookupSelection(q.qkey));

  const submit = document.createElement("button");
  submit.type = "button";
  submit.textContent = S.exam.submit;
  submit.addEventListener("click", finish);

  const map = document.createElement("nav");
  attempt.questions.forEach((item, i) => {
    const dot = document.createElement("button");
    dot.type = "button";
    dot.textContent = String(i + 1);
    dot.className = item.given ? "answered" : "";
    dot.addEventListener("click", () => { index = i; paint(); });
    map.append(dot);
  });

  root.append(star, look, submit, map);
}

async function choose(letter) {
  const q = attempt.questions[index];
  q.given = letter;
  await api.put(`/api/attempt/${attempt.attempt_id}/answer`, {
    qkey: q.qkey, given: letter, ms: Date.now() - shownAt,
  });
  if (index < attempt.questions.length - 1) index += 1;
  paint();
}

function startClock() {
  clearInterval(ticker);
  if (deadline == null) { clock.textContent = ""; return; }
  const render = () => {
    const left = deadline - Date.now();
    if (left <= 0) { clearInterval(ticker); finish(); return; }
    const s = Math.floor(left / 1000);
    clock.textContent = `${S.exam.remaining} ${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  };
  render();
  ticker = setInterval(render, 500);
}

/** A throttled tab drifts; the server holds the only authority on remaining time. */
document.addEventListener("visibilitychange", async () => {
  if (document.hidden || !attempt || deadline == null) return;
  const fresh = await api.get(`/api/attempt/${attempt.attempt_id}`);
  deadline = fresh.remaining_ms == null ? null : Date.now() + fresh.remaining_ms;
  startClock();
});

async function lookupSelection(excludeQkey) {
  const term = (window.getSelection() || "").toString().trim() || prompt(S.reader.lookup) || "";
  if (!term) return;
  const res = await api.get(`/api/lookup?q=${encodeURIComponent(term)}&exclude=${encodeURIComponent(excludeQkey)}`);
  const panel = document.createElement("div");
  panel.className = "popup";
  panel.append(Object.assign(document.createElement("p"), { textContent: `${S.exam.queryUsed}：${res.query_used}` }));
  const tabs = document.createElement("div");
  const courses = document.createElement("section");
  const questions = document.createElement("section");
  questions.hidden = true;
  for (const [label, section] of [[S.exam.courseTab, courses], [S.exam.bankTab, questions]]) {
    const t = document.createElement("button");
    t.type = "button"; t.textContent = label;
    t.addEventListener("click", () => { courses.hidden = section !== courses; questions.hidden = section !== questions; });
    tabs.append(t);
  }
  for (const hit of res.courses) {
    const a = document.createElement("a");
    a.href = `/reader?p=${encodeURIComponent(hit.relpath)}&path=${encodeURIComponent(hit.path)}&q=${encodeURIComponent(res.query_used)}`;
    a.textContent = `${hit.subject} · ${hit.title}`;
    a.addEventListener("click", (e) => { e.preventDefault(); openLookupResult(a.href); });
    courses.append(a);
  }
  for (const hit of res.questions) {
    questions.append(Object.assign(document.createElement("p"),
      { textContent: `${hit.bank_title} 第${hit.ordinal}題 — ${hit.snippet}` }));
  }
  const close = document.createElement("button");
  close.type = "button"; close.textContent = "×";
  close.addEventListener("click", () => panel.remove());
  panel.append(close, tabs, courses, questions);
  document.body.append(panel);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") panel.remove(); }, { once: true });
}

/** Everything shown here comes from the submit response - the exam never held the key. */
async function finish() {
  clearInterval(ticker);
  deadline = null;
  clock.textContent = "";
  const result = await api.post(`/api/attempt/${attempt.attempt_id}/submit`, {});
  root.textContent = "";
  document.getElementById("phase").textContent = S.exam.score;
  root.append(Object.assign(document.createElement("h2"), {
    textContent: `${result.score} ${result.passed ? "✓ " + S.exam.pass : ""} ${result.expired ? S.exam.expired : ""}`,
  }));
  for (const item of result.wrong) {
    const box = document.createElement("article");
    const stem = document.createElement("div");
    render.renderInto(stem, item.stem_md);
    box.append(stem);
    box.append(Object.assign(document.createElement("p"), {
      textContent: `✗ ${item.given || S.exam.blank} → ✓ ${item.answer}`,
    }));
    if (item.explanation_md) {
      const ex = document.createElement("div");
      const originLabel = S.exam.origin[item.explanation_origin] || item.explanation_origin;
      render.renderInto(ex, `**${S.exam.explanation}（${originLabel}）**\n\n${item.explanation_md}`);
      box.append(ex);
    }
    const note = document.createElement("textarea");
    note.placeholder = S.exam.myNote;
    note.value = item.note_md || "";
    note.addEventListener("change", () => api.post("/api/note", { qkey: item.qkey, note_md: note.value }));
    box.append(note);
    const star = document.createElement("button");
    star.type = "button";
    star.textContent = "★ " + S.exam.star;
    star.addEventListener("click", () => api.post("/api/star", { qkey: item.qkey }));
    box.append(star);
    root.append(box);
  }
}

document.addEventListener("keydown", (e) => {
  if (!attempt || !attempt.questions) return;
  const q = attempt.questions[index];
  if (!q) return;
  const digit = "1234".indexOf(e.key);
  const letter = "ABCD".indexOf(e.key.toUpperCase());
  if (digit >= 0 && q.options[digit]) choose(q.options[digit][0]);
  else if (letter >= 0 && q.options[letter]) choose(q.options[letter][0]);
  else if (e.key === "ArrowRight" && index < attempt.questions.length - 1) { index += 1; paint(); }
  else if (e.key === "ArrowLeft" && index > 0) { index -= 1; paint(); }
  else if (e.key === " ") {
    const cur = q.options.findIndex(([l]) => l === q.given);
    choose(q.options[(cur + 1) % q.options.length][0]);
    e.preventDefault();
  }
});

main();
