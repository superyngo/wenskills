# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
