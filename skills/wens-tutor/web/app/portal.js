// skills/wens-tutor/web/app/portal.js
import S from "/strings.js";
import * as api from "/app/api.js";

const make = (tag, props) => Object.assign(document.createElement(tag), props || {});

function courseCard(f) {
  const card = make("article", { className: "card" });
  card.append(
    make("a", { href: `/reader?p=${encodeURIComponent(f.relpath)}`, textContent: f.title }),
    make("span", {
      textContent: ` ${S.portal.annotations} ${f.annotations}` +
        (f.orphans ? ` · ${S.portal.orphans} ${f.orphans}` : ""),
    }),
  );
  return card;
}

function bankCard(f, b) {
  const card = make("article", { className: "card" });
  const links = make("div", { className: "bank-links" });
  links.append(
    make("a", { href: `/exam?bkey=${encodeURIComponent(b.bkey)}`, textContent: `${f.title} — ${b.title}` }),
    make("a", { href: `/reader?p=${encodeURIComponent(f.relpath)}${b.path ? `&path=${encodeURIComponent(b.path)}` : ""}`,
               textContent: S.portal.browse, className: "browse-link" }),
  );
  card.append(
    links,
    make("span", {
      textContent: ` ${b.n_questions} 題 · ${S.portal.stars} ${b.stars}` +
        (b.defects ? ` · ${S.portal.defects} ${b.defects}` : ""),
    }),
  );
  return card;
}

/** One panel, one source: everything in it comes from `/api/version`. */
function mountAbout(meta) {
  const button = document.getElementById("help");
  button.textContent = S.about.help;
  const panel = make("aside", { className: "popup about", hidden: true });
  panel.append(
    make("p", { textContent: `${S.about.version}: ${meta.version}` }),
    make("p", { textContent: `${S.about.root}: ${meta.root}` }),
    make("p", { textContent: `${S.about.project}: ${meta.project}` }),
    make("p", { textContent: `${S.about.license}: ${meta.license}` }),
    make("p", { textContent: [S.keys.esc, S.keys.enter, S.keys.arrows, S.keys.digits].join("　") }),
  );
  document.body.append(panel);
  button.addEventListener("click", () => { panel.hidden = !panel.hidden; });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !panel.hidden) panel.hidden = true;
  });
}

async function main() {
  document.getElementById("appname").textContent = S.app;
  document.getElementById("keys").textContent = [S.keys.esc, S.keys.enter].join("　");
  const [data, meta] = await Promise.all([api.get("/api/portal"), api.get("/api/version")]);
  document.getElementById("version").textContent = meta.version;
  mountAbout(meta);
  const root = document.getElementById("root");

  const actions = make("nav");
  actions.append(
    make("a", { href: "/exam", textContent: S.portal.newPaper }),
    make("a", { href: "/exam?drill=1", textContent: S.portal.drill }),
    make("a", { href: "/stats", textContent: S.portal.stats }),
  );
  root.append(actions);

  for (const a of data.in_flight) {
    const row = make("div", { className: "card in-flight" });
    row.append(make("a", {
      href: `/exam?attempt=${a.attempt_id}`,
      textContent: `${S.portal.inFlight} · attempt #${a.attempt_id}`,
    }));
    const del = make("button", { type: "button", textContent: S.reader.del });
    del.addEventListener("click", async (e) => {
      e.preventDefault();
      await api.del(`/api/attempt/${a.attempt_id}`);
      row.remove();
    });
    row.append(del);
    root.append(row);
  }

  if (data.latest.length) {
    const sec = make("section");
    sec.append(make("h3", { textContent: S.portal.history }));
    for (const a of data.latest) {
      const row = make("div", { className: "card in-flight" });
      row.append(make("a", {
        href: `/exam?review=${a.id}`,
        textContent: `${S.portal.review} · ${a.score}分 (${a.correct}/${a.total})`,
      }));
      const del = make("button", { type: "button", textContent: S.reader.del });
      del.addEventListener("click", async (e) => {
        e.preventDefault();
        await api.del(`/api/attempt/${a.id}`);
        row.remove();
      });
      row.append(del);
      sec.append(row);
    }
    root.append(sec);
  }
  for (const s of data.subjects) {
    const sec = make("section");
    sec.append(make("h2", { textContent: s.subject }));
    // A Material File is Course prose AND Bank regions (ADR 0006): the study guides list twice.
    const courses = s.files.filter((f) => f.leaf_sections > 0);
    const banks = s.files.flatMap((f) => f.banks.map((b) => [f, b]));
    if (courses.length) {
      sec.append(make("h3", { textContent: S.portal.courses }));
      for (const f of courses) sec.append(courseCard(f));
    }
    if (banks.length) {
      sec.append(make("h3", { textContent: S.portal.banks }));
      for (const [f, b] of banks) sec.append(bankCard(f, b));
    }
    root.append(sec);
  }
}
main();
