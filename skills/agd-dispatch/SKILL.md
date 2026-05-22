---
name: agd-dispatch
description: "Use when you need to package a single task (spec review, code review, code implementation, or review-feedback implementation) and dispatch it to a third-party agent via `agd`. Provides ready-made prompt templates with a `skills` field so the dispatched agent loads matching skills instead of re-explaining everything in the prompt. Use whenever the user says 'dispatch this to agd', 'have codex review X', 'offload this task to another agent', or similar."
argument-hint: "<template> [--var k=v ...] [--skills a,b,c]"
allowed-tools: Bash, Read, Write
---

# agd-dispatch

Thin task-packager for `agd`. Pick a template, fill its placeholders, optionally list skills the dispatched agent should load, and dispatch.

This skill does **not** orchestrate a workflow.

## Templates

| Template | Use for |
|---|---|
| `spec-review` | Have an external agent review a spec/PRD/design doc for completeness, consistency, implementability. |
| `code-review` | Have an external agent review committed changes / a diff for correctness and quality. |
| `code-implement` | Have an external agent implement one well-scoped task (writes files in the workspace). |
| `review-implement` | Have an external agent take a review report and implement its fixes. |

All templates live in `templates/<name>.md`.

## Usage

Single script does both: render template, then dispatch.

```bash
sh skills/agd-dispatch/scripts/dispatch.sh \
    --template spec-review \
    --var spec_path=docs/specs/foo.md \
    --var stage="round 1" \
    --skills systematic-debugging,verification-before-completion \
    --guidance "Pay special attention to the env-var contract — that's where the prior round failed."
```

### Flags

| Flag | Meaning |
|---|---|
| `--template <name>` | Required. Picks `templates/<name>.md`. |
| `--var k=v` | Substitutes `{{k}}` with `v`. Repeatable. Values must not contain newlines. |
| `--skills a,b,c` | Comma-list of skills the dispatched agent should load. Keeps the template's `SKILLS-BLOCK`; omit → block removed. |
| `--guidance <text>` | Free-form paragraph injected at the top of the prompt as caller guidance. Keeps the template's `GUIDANCE-BLOCK`; omit → block removed. |
| `--prompt <path>` | Where to write the rendered prompt. Default: `docs/tmp/<ts>-<template>.md`. |
| `--out <path>` | Where to write agd's stdout+stderr. Default: `docs/tmp/<ts>-<template>.out.md`. |
| `--timeout <sec>` | Overrides the template's default tier timeout. |

Tier defaults: `spec-review` 900s · `code-review` 900s · `code-implement` 1800s · `review-implement` 1800s.

Unresolved `{{placeholders}}` are left in the file and warned to stderr. Emits `prompt=`, `out=`, `tier=`, `timeout=`, `exit=` on stderr. Exit code mirrors `agd` (127 if `agd` missing, 2 if argv malformed).

Ensure `docs/tmp/` is in `.gitignore` before first use — the script does not check.

## Per-template `--var` parameters

Pass each placeholder via `--var key=value`. Any omitted variable stays as `{{name}}` in the rendered prompt and is warned to stderr.

**`spec-review`**
- `spec_path` — path to the spec/PRD being reviewed
- `stage` — short label (e.g. `"round 1"`, `"pre-implementation"`)

**`code-review`**
- `repo_root` — absolute repo path
- `diff_scope` — diff range / branch / PR ref the reviewer should look at
- `files_changed` — newline- or comma-separated list (single line — no real newlines)
- `spec_path` — optional, for spec-aware review
- `stage` — short label

**`code-implement`**
- `repo_root` — absolute repo path; the dispatched agent writes here
- `task_body` — the full task description to implement (use a short value; long bodies belong in a file the spec/plan points to)
- `spec_path` — optional, for context
- `plan_path` — optional, for context
- `stage` — short label

**`review-implement`**
- `repo_root` — absolute repo path
- `review_report_path` — path to the review output (e.g. an earlier `docs/tmp/*.out.md`)
- `spec_path` — optional, for context
- `stage` — short label

In addition, every template supports the two block-toggled inputs:
- `--skills a,b,c` → substitutes `{{skills}}` inside `<!-- SKILLS-BLOCK -->`; block removed if flag omitted.
- `--guidance <text>` → substitutes `{{guidance}}` inside `<!-- GUIDANCE-BLOCK -->`; block removed if flag omitted.

Use `--skills` to delegate the *how* to existing skills (e.g. `test-driven-development`, `verification-before-completion`, `receiving-code-review`) instead of inflating the prompt. Use `--guidance` for one-off context specific to *this* dispatch (e.g. "focus on the auth path", "round 2 — verify R1 findings only").

## Output contract

Every template tells the dispatched agent to begin its response with a YAML frontmatter block containing at minimum `status: PASS | ISSUES_FOUND` (review templates) or `status: COMPLETED | BLOCKED` (implement templates). Parse this to decide next steps; loop or escalate as the caller's workflow requires.

## Non-goals

- No orchestration, no round-tracking, no auto-iterate. Caller drives.
- No installation guidance for `agd` — see `agent-dispatcher`.
- No mode-a/mode-b distinction — caller decides whether the dispatched agent is allowed to write files based on their `agd` config.
