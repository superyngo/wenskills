# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### 2026-08-13 — docs(wens-tutor): third grilling round — measured render, install baseline, JSON export

- `skills/wens-tutor/docs/adr/0008-no-service-worker.md`: New — the site installs (manifest,
  standalone display) but deliberately ships **no service worker**, a recorded deviation from
  `ui-design-principles` 23: all content comes from the local server, so an offline shell would
  load a UI with no courses, no questions and no way to persist an answer — a screen that looks
  usable and is not.
- `skills/wens-tutor/docs/adr/0009-json-export-beside-the-database.md`: New — `export`/`import`
  keep a diffable JSON copy of user state committed beside the binary `tutor.db`, turning git's
  inability to merge SQLite from "pick a side and discard the other device's attempts" into a real
  merge, and DB loss from total to recoverable.
- `docs/superpowers/specs/2026-08-13-wens-tutor-design.md`: Client render cost is now **measured,
  not assumed** — headless Chromium with vendored markdown-it renders the largest file (292 KB,
  1330 blocks, 3777 DOM nodes) in 82 ms cold / 26 ms warm, and restoring 200 annotations by naive
  scan costs 18 ms, so chunked rendering, TOC virtualisation, `content-visibility` and any anchor
  index are all struck from the design. Adds the composition form (6 fixed fields; defaults 50
  questions / all banks / shuffled / timed / defects off), shuffle policy (questions yes, options
  never — shuffled options would invalidate all 70 official explanations that name `Ans（B）`),
  countdown computed from `started` so a throttled tab cannot gain time, `tests/test_rules.py`
  covering the five silently-failing rules at the pure-function layer, `export`/`import`
  subcommands, and the chrome/layout contract (build-stamped version, Help/About panel, fluid
  resize-aware columns, desktop-only target while the server binds 127.0.0.1).

### 2026-08-13 — docs(wens-tutor): second grilling round — banks are regions, +70 official questions

- `skills/wens-tutor/docs/adr/0006-bank-is-a-region-not-a-file.md`: New — a Bank is a region of a
  Material File, not a file. Measuring heading structure surfaced **70 official practice
  questions hiding inside the two study guides** (7 `選擇題` regions of exactly 10, every one
  with 4 options, an official answer, an official 解析, and zero defects) — 26% more questions
  than the four exam papers hold, and the only official explanations in the corpus. The
  file-typed model discarded all of it silently.
- `skills/wens-tutor/docs/adr/0007-sections-identified-by-ancestor-path.md`: New — Sections are
  keyed by ancestor path, not by a counter-deduplicated slug: `1. 前言與章節導覽` occurs 9 times
  in the 科目1 guide and 12 times in 科目3, so a counter makes identity depend on how many
  identical headings precede it and inserting one chapter moves the human's read-ticks onto
  different sections. Ancestor paths are collision-free across all eight files.
- `skills/wens-tutor/docs/adr/0005-explanations-live-in-content.md`: Corrected — its premise
  ("the published banks contain no explanations at all") was false for the study guides. Now
  distinguishes official explanations (parsed, never rewritten) from authored ones (exam papers
  only, attributed).
- `skills/wens-tutor/CONTEXT.md`: Course and Bank redefined as regions; new term Material File;
  Annotation widened to any Material File; Progress pinned to leaf sections; Lookup widened to
  cover banks as well as courses; Attempt gains resumability and wall-clock semantics.
- `docs/superpowers/specs/2026-08-13-wens-tutor-design.md`: Rewritten again for the second round.
  Corpus is now **270 questions in 11 banks**. Adds the second question shape and its parser
  tolerances, resumable attempts with a wall-clock countdown and auto-submit, the statistics page
  (five panels ordered score → pace → most-missed → per-bank → star/defect trend), dual-tab
  Lookup (課程 + 考古題) with right-shortening queries that state the query actually used, the
  keyboard/key-hint contract from `ui-design-principles`, an externalised string catalogue, and a
  three-level `check` exit contract (0 clean / 1 content findings / 2 tool failure).

### 2026-08-13 — docs(wens-tutor): grill the design, pin the domain, record five ADRs

- `skills/wens-tutor/CONTEXT.md`: New — domain glossary pinning 18 terms across content
  (Materials Root, Subject, Course, Bank, Section, Question, Defect), sitting (Paper,
  Attempt, Drill, Star), reading (Annotation/Highlight/Note, Orphan, Progress, Lookup) and
  repair (Backfill, Explanation), each with an `_Avoid_` list. Retires the overloaded
  "material" and separates Paper (a composed question set) from Attempt (one sitting).
- `skills/wens-tutor/docs/adr/0001…0005`: New — user-state-only database with the content
  catalogue parsed into memory at startup (deletes the `index` command, the cache and its
  invalidation); content-addressed question identity (`qkey = sha256(stem+options)[:12]`)
  after the materials repo was found to have already done a mass rename in its four-commit
  history; device-local root registry instead of an absolute path committed inside a synced
  repo; defective questions detected and excluded from papers by default; explanations as
  attributed content in the bank file, notes as user state.
- `docs/superpowers/specs/2026-08-13-wens-tutor-design.md`: Rewritten against eight decisions
  from the grilling session. New ground-truth measurements: strict bank detection is required
  (the loose `### 第` pattern misclassifies 58 cheatsheet chapter headings as questions),
  stems contain fenced code so the option scanner must skip fenced regions, and **23 of 200
  questions (11.5%) reference a figure/table/code listing that is absent — the corpus holds
  zero images** — clustered in the Python code-reading questions the issuing body added from
  114年第二梯次. Adds official exam conditions (90 min / 50 questions / 60-point pass line,
  scaled per paper size, auto-submit at zero), the star lifecycle (two consecutive corrects
  clears a `wrong` star; `manual` stars never auto-clear), and the agent backfill workflows
  that repair defects from the original PDFs already sitting in `source/`.

### 2026-08-13 — docs(wens-tutor): design spec for courseware review skill + site

- `docs/superpowers/specs/2026-08-13-wens-tutor-design.md`: New design for `wens-tutor`, a
  skill that indexes a Markdown courseware root into a SQLite metadata DB and serves a
  dynamically generated study site (portal, reader with persistent highlights/notes, mock
  exam with per-attempt statistics, starred-question drilling, selection-driven lookup from
  exam into course material). Architecture is one stdlib Python process mounting two static
  roots — the engine from inside the skill, the content from the courseware repo — which is
  how the engine/content path split is resolved without symlinks (forbidden by the wenswiki
  vault's `CLAUDE.md` §2). Three measured findings shaped the design: SQLite FTS5 cannot
  tokenize CJK (`unicode61` and `trigram` both miss a two-character query), a whole-corpus
  substring scan costs 0.33 ms, and course/bank classification by content sniffing is 8/8
  correct on the real material — so no search engine is built. First materials root is the
  `ipas-ai-planner-2026` submodule (200 questions, 4 course files).

### 2026-08-07 — feat(skills): add wenswiki-notes

- `skills/wenswiki-notes/`: New skill for capturing session insights into, and querying,
  the user's personal wenswiki vault (`~/repos/wenswiki/wenswiki`), fully compliant with
  that vault's own `CLAUDE.md` governance. Three branches: quick capture to `inbox/`
  (no ceremony, per that folder's format exemption), structured capture into
  `notes/`/`projects/`/`runbooks/`/`reference/`/`work/` (search-first, live-schema-read,
  always draft-then-confirm — never an auto-write fast path), and read-only cross-note
  query/synthesis (scoped search, cited answers). `references/vault-rules.md` is a
  pre-write self-check checklist. Design at
  `docs/superpowers/specs/2026-08-07-wenswiki-notes-design.md`.

### 2026-07-30 — refactor(publishing-platform-stores): grill and sharpen domain vocabulary

- `skills/publishing-platform-stores/CONTEXT.md`: New — pins five terms surfaced by a grilling session: **Store** (third-party marketplace, credentials + listing required) vs. **Channel** (any distribution outlet, store or not); **Extension** as one category covering editor plugins, app plugins, and browser extensions alike (a browser is just another kind of host application, not a sibling category); and **Release**/**Publish**/**Submit** as three distinct pipeline stages (Submit generalized to include minting a store's canonical artifact for API-less stores like Obsidian, not just review-queue network calls).
- `skills/publishing-platform-stores/docs/adr/0001-shared-publish-gate.md`: New ADR recording why the skill prescribes one shared `publish-gate` approval fanning out to every `publish-*.yml`, instead of a separate approval per store.
- `skills/publishing-platform-stores/SKILL.md`: Retired "target" in favor of "store" throughout; collapsed the platform table from 4 categories to 3 (Desktop/Mobile/Extension, folding "IDE extension" and "Browser extension" into one); checklist step 5 now covers API-less stores explicitly; corrected a Common Mistakes row that conflated Obsidian's one-time directory-admission review with routine per-release review latency (ordinary Obsidian releases are unthrottled).
- `skills/publishing-platform-stores/references/extension-obsidian.md`: Added the `workflow_dispatch(tag, run_id)` adaptation of Obsidian's official standalone template, for when Obsidian is one store among several in a multi-store pipeline rather than a lone plugin repo.

### 2026-07-30 — feat(skills): add publishing-platform-stores

- `skills/publishing-platform-stores/`: New reference skill for wiring GitHub Actions store-publishing workflows, generalized from a real production pipeline (build/tag → shared approval gate → per-store `publish-*.yml` fan-out). SKILL.md stays lightweight (pattern, platform table, wiring checklist, common mistakes); ten `references/*.md` cover the actual mechanics per store across four categories — desktop (Microsoft Store, Mac App Store, Steam), mobile (Google Play, Apple App Store/TestFlight), IDE extensions (VS Marketplace + Open VSX, Obsidian), and browser extensions (Chrome Web Store, Edge Add-ons, Firefox AMO). Microsoft Store and VS Marketplace/Open VSX references are sourced from a verified live workflow; the rest are sourced from official docs and flagged unverified-in-production. Extensible: new stores add one `references/<category>-<store>.md` file plus one table row.

### 2026-07-28 — refactor(github-init): fully translate to English, add PRIVACY.md skeleton, and enable workflow caching

- `skills/github-init/SKILL.md`: Translated all content into clear technical English. Added `PRIVACY.md` to the standard required skeleton files with a default privacy policy template. Modernized the `.github/workflows/release.yml` skeleton workflow with comprehensive caching (`Swatinem/rust-cache@v2`, `actions/cache@v4` for cross binaries, `CARGO_INCREMENTAL: 0`), and upgraded release action to `softprops/action-gh-release@v2`. Added pre-flight health checks (`gh auth status`, `git config user.name`/`user.email`, `git branch -M main`) and dual-platform installation snippets (`PowerShell` & `curl | bash`).

### 2026-07-18 — feat(skills): expand ui-design-principles text-input contract (selection + clipboard)

- `skills/ui-design-principles/references/text-editing-contract.md`: New reference covering the full text-field editing contract beyond cursor movement — Shift+move selection with a committed-anchor model (mirrors the list-selection two-set principle), word/line/document jumps, delete char/word/line, cut/copy/paste, undo/redo. Includes per-platform key tables (macOS Cmd / Win-Linux Ctrl / TUI Emacs-style `Ctrl+A/E/K/U/W/Y`), the `Ctrl+A` (select-all vs line-start) and `Ctrl+C`/`Ctrl+Z` (SIGINT/SIGTSTP) conflict resolution, TUI fallbacks for Shift+arrow selection (Emacs mark mode, mouse drag, kill/yank), grapheme-cluster-based offsets for CJK/emoji, IME composition handling, and atomic-cut / failed-paste-preserve invariants tying back to principles 8 and 9.
- `skills/ui-design-principles/SKILL.md`: Principle 10 expanded from the bare "arrows + Home/End" baseline to the full editing contract (move + select + edit + clipboard), with the platform-modifier split and a link to the new reference. Common Mistakes gains three text-editing entries (Ctrl+C binding and Shift+arrow-only selection in a TUI; byte/codepoint cursor movement in CJK/emoji; non-atomic cut on a locked clipboard).

### 2026-06-23 — refactor(skills): condense git-release + branch handling

- `skills/git-release/SKILL.md`: Moderately condensed prose to save tokens (kept all steps + bash). Added explicit uncommitted-change detection (ask → commit). Enhanced non-main branch handling: "Switch to main" now merges the feature branch into `main`, continues the release there, and a new Step 6 removes the merged local feature branch with `git branch -d` (safe; refuses if unmerged) after a successful release.

### 2026-05-26 — feat(skills): add ui-design-principles

- `skills/ui-design-principles/`: New reference skill capturing high-level, implementation-agnostic UI conventions (TUI-first). 12 principles: shared interface for identical operations; Home/End/arrow keys in text fields; PgUp/PgDn for multi-line input; keyboard navigation for all scrollable elements; sticky-cursor list scrolling; top-right version display; resize-aware layout; consistent global keys + key-hint footer; destructive-action confirmation + state preservation; graceful degradation (NO_COLOR/ASCII/color semantics); UI-safe logging (no stdout/stderr pollution); upfront i18n planning.
- `skills/ui-design-principles/references/scrollable-list-viewport.md`: Full sticky-cursor scrolling spec for principle 5 — separated `selected_index`/`scroll_offset` state, minimal-scroll rules, edge cases, and required test scenarios.

### 2026-05-25 — feat(skills): add wens-plan-creator and wens-plan-implementer

- `skills/wens-plan-creator/`: New skill orchestrating brainstorming → spec self-review (paired with grill-with-docs) → external agd spec-review loop (until zero blockers) → writing-plans + feature-planning → handoff prompt for next session. Embeds own copy of `dispatch.sh` + templates so runtime does not need to load `agd-dispatch`.
- `skills/wens-plan-implementer/`: New skill that runs `subagent-driven-development`'s loop with every implement / two-stage review subtask dispatched via embedded `agd-dispatch` script; review-feedback fixes stay in main session. Embeds own copy of `dispatch.sh` + templates.

### 2026-05-10 — test(rust): add insta snapshot tests and implement golden fixtures

- `skills/dispatch-agent/rust/tests/snapshots_test.rs`: Three `insta::assert_snapshot!` tests for `format_list`, `format_show_config`, and `format_list_detect` display functions. Snapshot files committed in `tests/snapshots/`.
- `skills/dispatch-agent/rust/src/lib.rs`: Minimal library interface to expose modules for integration testing.
- `skills/dispatch-agent/rust/scripts/regen_golden.sh`: Fully implemented — builds release binary, runs `detect` and `init` on fixture inputs, saves outputs to `tests/fixtures/golden/`.
- `skills/dispatch-agent/rust/scripts/parity_check.sh`: Fully implemented — compares binary output against golden files, reports pass/fail.
- `skills/dispatch-agent/rust/tests/fixtures/golden/detect_output.json` and `init_output.toml`: Generated golden fixture files.
- `skills/dispatch-agent/rust/tests/fixtures/inputs/init_canonical.json`: Changed `save_location` from `"user"` to `"project"` to prevent scripts from touching `~/.config/dispatch-agent.toml`.

### 2026-05-10 — test(rust): complete integration test suite (dispatch, init, detect, config_cmd)

- `skills/dispatch-agent/rust/tests/dispatch.rs`: 10 integration tests covering dry-run, --list, --show-config, --agent/--tier not found, recursion guard, and fake_agent exit code propagation. Uses TempDir HOME isolation and DISPATCH_AGENT_TEMPLATES to avoid touching real user config.
- `skills/dispatch-agent/rust/tests/init.rs`: 3 tests — canonical JSON→TOML with 0600 mode check (unix), invalid JSON rejection, and stderr hint containing "config edit".
- `skills/dispatch-agent/rust/tests/detect.rs`: JSON output assertion with HOME isolation.
- `skills/dispatch-agent/rust/tests/config_cmd.rs`: 2 tests for `config path` and `config show` error paths with HOME isolation.
- Fixed proptest `prompt_appears_at_most_once` invariant to use a sentinel prefix, avoiding collisions with generated binary names and extra_args.

### 2026-05-10 — feat(rust): implement rr_state.rs (load_rr_state, store_rr_state)

- `skills/dispatch-agent/rust/src/rr_state.rs`: Implements round-robin state persistence with file-based locking (fs2 sidecar lock), JSON serialization via IndexMap, and graceful error handling (NotFound → empty, PermissionDenied/parse errors → warn stderr). Includes roundtrip, NotFound, and concurrent load+store tests.

### 2026-05-10 — feat(dispatch-agent): Rust crate scaffold and cli-templates.toml rewrite

- `skills/dispatch-agent/rust/`: New Rust crate for the dispatch-agent binary rewrite (PR 1, layer a). Implements `types.rs`, `fsutil.rs`, `config.rs`, `templates.rs` with full unit tests. Python scripts remain the active entry point; Rust source is dark in production (see docs/plans/2026-05-10-dispatch-agent-rust-rewrite.md for rollout plan).
- `skills/dispatch-agent/data/cli-templates.toml`: Rewritten as a fully-commented field reference document.

### 2026-05-08 — feat(dispatch-agent): add type=source env entries for shell env file sourcing

- Added `type=source` as a valid env entry type in dispatch-agent config
- At dispatch time, source files are loaded via `bash -c "set -a; source <file>; set +a; exec ..."` — no Python-side parsing needed
- Updated `init-guide.md` to include the new "Source env file (type=source)" option
- Updated `init.py` TOML serialization to omit `name` field for source entries
- Updated `--show-config` display to label source entries correctly

### 2026-04-28 — feat(yt-channel-dl): background execution with status file

- Added `--status-file` to `download_channel.py` — writes compact JSON progress at each video boundary
- SKILL.md step 3 now runs the download script in background via `nohup`, redirecting output to a log file
- Agent polls a tiny status.json instead of streaming all stdout, drastically reducing token consumption
- Users can monitor progress via `tail -f download.log` in another terminal

### 2026-04-28 — feat(yt-channel-dl): add playlist URL support

- SKILL.md now accepts YouTube playlist URLs (e.g. `?list=PLxxxxxx`) alongside channel URLs
- Updated prompts, parameter descriptions, and script metadata to reflect channel + playlist support
- Summary output changed from "Total in channel" to generic "Total"

### 2026-03-04 — feat: add github-init skill

Add `github-init` skill for initialising a new GitHub repository or Gist from the current directory. Handles git init, skeleton file generation (README, CHANGELOG, LICENSE, .gitignore, release workflow), remote creation via `gh repo create`, and initial push.
