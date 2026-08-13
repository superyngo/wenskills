---
name: wens-tutor
description: Use when the user wants to 複習 / 開始讀書 / 模擬考 / 出卷 / 重點題 / 複習進度 / 補答案 / 補圖, or their English equivalents (review, start studying, mock exam, compose a paper, drill weak questions, check study progress, fill in a missing answer, fill in a missing figure). Operates on a registered Materials Root of Markdown courseware — a directory tree of Subjects, each holding Course prose and Question Banks — serving it as a local study site with persistent annotations, timed mock papers, and wrong-answer drilling.
---

# Wen's Tutor

A stdlib-only Python engine (`scripts/tutor.py` + `scripts/tutorlib/`) plus a vanilla-JS study
site (`web/`) over a Materials Root of Markdown courseware. Vocabulary — Materials Root,
Subject, Material File, Course, Bank, Section, Question, Shared Stem, Defect, Paper, Slot,
Attempt, Drill, Star, Annotation, Orphan, Progress, Lookup, Backfill, Explanation — is defined
once in `CONTEXT.md`; read it before using unfamiliar terms below.

## Dispatch

| The user wants to… | Do this |
|---|---|
| Start a study session | `tutor.py serve` — see **Serving** below. |
| Sit a Paper (模擬考 / 出卷) | Start the server, open `/exam`, compose there — CLI never composes a Paper on the user's behalf, since composition criteria (Subjects, Banks, count, shuffle, timed, defective) are the user's judgement call. |
| Drill weak Questions (重點題) | Start the server, open `/exam`, choose Drill — it sits every currently-Starred Question, untimed. |
| Check content health (複習進度 / general "is my material OK") | `tutor.py check [--root]` — prints every finding (Defects by kind, unparsed Banks, collapsed skeletons, overlapping shared-stem spans, relinked/unresolved `qkey`s, stale Progress, Orphan Annotations, a stale export) and exits 0 clean / 1 findings-in-content / 2 usage-or-I/O failure. Exit code, not output text, is how to tell "material needs repair" from "the tool is broken." |
| Repair content (補答案 / 補圖 / add an Explanation) | One of the three **Repair workflows** below — always content, never user state. |

## Hard rules

- **The engine never writes to a Material File.** Every write path in `tutorlib` targets
  `.tutor/tutor.db` (user state) or is read-only. Only the agent writes a Material File, and
  only in the three Repair workflows below.
- **The agent writes a Material File only when asked**, and only after running `git status` on
  the Materials Root first — per `~/.claude/CLAUDE.md`, confirm the repo is in a known state
  before editing content that syncs across devices.
- **Run `tutor.py export` before committing the Materials Root.** `tutor.db` is binary; the
  JSON export is the mergeable, diffable half of user state (ADR 0009, `references/db-schema.md`).
  A commit without a fresh export leaves the JSON stale — `check` will flag it as
  `stale_export` on the next run.
- **Never `git push` the wenswiki vault.** The Materials Root lives inside it; pushing is
  outside this skill's authority.

## Serving

Start the server as a supervised background process via `hub` (`op: "start"`), with a port
readiness check — never `bash &`, and never a call that blocks the calling session:

```
hub(op="start", name="wens-tutor", application="uv",
    args=["run", "--python", "3.14", "python3", "scripts/tutor.py", "serve", "--port", "8765"],
    cwd="skills/wens-tutor", ready={"port": 8765, "timeout": 15})
```

Report the tokenised URL the CLI prints (`http://127.0.0.1:<port>/?t=<token>`) to the user —
that query parameter is what authorises the browser; a bare URL without it only works over
loopback with no token configured.

`--bind` defaults to `127.0.0.1` (loopback, no token required). Binding anything else — e.g.
`--bind 0.0.0.0` so a phone on the same private network can reach it — **requires** the token
minted at `init`: the engine refuses to bind a non-loopback address without one (ADR 0010). A
request without a valid `?t=` (first hit) or `tutor_token` cookie (subsequent hits) gets `403`.

## Repair workflows

Each of these edits a Material File and re-runs `tutor.py check` to confirm the Defect count
moved. See `references/material-format.md` for exact syntax.

1. **Backfill a `no_answer` Defect.** Authoritative source: the issuing body's published answer
   key on the web (`ipas.org.tw` / `ipd.nat.gov.tw`), read with the agent's own `read`. Write
   `**答案：X**` in place of the placeholder line, re-run `check`.
2. **Backfill a `figure_missing` Defect.** Authoritative source: the original PDF sitting beside
   the Markdown in `source/`. Transcribe a code listing into a fenced block, a table into a
   Markdown table; for a genuine diagram, describe it in prose and say plainly that it is a
   description, not the figure. Re-run `check` and confirm the count fell by exactly the
   Questions repaired.
3. **Author an Explanation.** On request, for a Question answered wrong in an exam-shape Bank
   (the guides already publish 70 official Explanations; exam papers publish none). Register:
   the register of the 70 official Explanations in the guides. Attribution is mandatory —
   `**解析（AI 生成，未經官方確認）：**` — so the boundary between the issuing body's words and
   generated prose stays visible in a diff (ADR 0005).

Importing new material from the web follows the same shape: fetch with `read`, convert to the
Bank/Course conventions in `references/material-format.md`, write into the Materials Root, run
`check`.

## Reference pointers

- `CONTEXT.md` — domain vocabulary; read before using an unfamiliar term.
- `docs/adr/` — one decision per file, with the rejected alternative and its cost. Load the ADR
  named by whatever you're touching rather than re-deriving the reasoning.
- `references/material-format.md` — both Bank shapes verbatim, the Shared Stem conventions and
  folding rule, the line-attribution rule, the three Defect kinds and their measured counts.
- `references/db-schema.md` — the `main` and `cat` schemas, why every key is natural instead of
  a surrogate, and the export/import contract.
