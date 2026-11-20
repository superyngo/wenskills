---
name: wens-plan-creator
description: "Use when starting a new feature/project and you want Wen's full plan-creation flow — brainstorm → spec → external review loop → implementation plan — with spec review offloaded via agd to save main-session context. Use whenever the user says 'wens-plan-creator', 'wens create plan', 'wens plan', 'start a wens plan flow', or asks for a planning workflow that ends with a paste-ready handoff prompt for the implement skill."
allowed-tools: Bash, Read, Write, Edit, Skill
---

# Wen's Create-Plan Flow

End-to-end planning workflow that produces a reviewed spec **and** an implementation plan, ending with a paste-ready prompt the user can drop into a fresh session to start `wens-plan-implementer`.

External spec review runs via `agd` (this skill embeds its own copy of `dispatch.sh` + templates — no need to load `agd-dispatch`).

## Assumptions

All referenced skills are installed. Don't validate them.

- `brainstorming`, `grill-with-docs`, `writing-plans`, `feature-planning`
- `agd` is on `PATH` and configured

## Workflow

```
1. brainstorming                       (interactive)
2. Spec Self-Review + grill-with-docs  (forced pairing inside step 1's review gate)
3. Loop: dispatch spec-review via agd  (until zero blockers)
4. writing-plans + feature-planning    (produce plan doc)
5. Emit handoff prompt                 (user pastes into next session)
```

### Step 1 — Brainstorm

Invoke the `brainstorming` skill and run it to completion. Follow its flow verbatim — clarifying questions, approach exploration, design presentation, write spec, commit — except for where the spec goes. Override brainstorming's default path and write the spec as a repo-docs working record:

- Path: `docs/spec/YYYY-MM-DD-<kebab-title>.md` — dated the day it is written, no `-design` suffix. The plan in Step 4 reuses `<kebab-title>` so the two pair by name.
- Line 1 is the H1; line 2 is exactly `Status: Draft`.
- Add the spec to the `## In progress` list in `docs/spec/README.md` (`- [<file>](<file>) — Draft`) in the same commit. If `docs/spec/README.md` does not exist, create it with an `## In progress` section and a `## Landed` table (`| Date | Document | Status |`).

### Step 2 — Spec Self-Review (paired with grill-with-docs)

When `brainstorming` reaches its **Spec Self-Review** gate, **also** invoke `grill-with-docs` in the same step. Run both back-to-back against the freshly-written spec, fix issues inline, then re-loop if either flags something material.

Order: brainstorming's self-review scan first (placeholders, internal consistency, scope, ambiguity), then `grill-with-docs` (challenge against domain model and existing CONTEXT.md / ADRs). Apply both sets of fixes inline.

### Step 3 — External Review Loop via `agd`

Loop the spec through external review until zero blockers remain. Each round:

```bash
sh skills/wens-plan-creator/scripts/dispatch.sh \
    --template spec-review \
    --var spec_path=<path-to-spec> \
    --var stage="round <N>" \
    --slug <kebab-title> \
    --skills systematic-debugging,verification-before-completion \
    --guidance "<optional: focus areas, prior-round followups>"
```

`--slug` (the spec's kebab title) keeps every round in one task directory. The script writes the rendered prompt and `agd` output under `docs/tmp/claude-scratch/YYYY-MM-DD-<kebab-title>/`. Read the `out` file; its YAML frontmatter has `status: PASS | ISSUES_FOUND` and an `issues:` list with `severity: blocker | major | minor`.

**Loop rules:**

- If any `blocker` exists: fix the spec inline (you, in main session — small edits don't need offload), commit, increment `stage`, dispatch again.
- If no blockers remain: set the spec's line 2 to `Status: Approved`, update its row in `docs/spec/README.md`, commit, exit the loop and proceed. `major` and `minor` items are advisory at this stage — note them and move on; they can be revisited during planning or implementation.
- Pass `--guidance` on follow-up rounds to point the reviewer at "verify R<N-1> blockers only" so each round stays cheap.
- No round cap — loop until blockers reach zero. If rounds aren't converging (same blocker keeps re-appearing after a fix attempt), surface to the user; that's a structural problem the loop can't resolve.

Ensure `docs/tmp/*-scratch/` is in `.gitignore` before the first dispatch — ignore only the scratch directories, not all of `docs/tmp/`.

### Step 4 — Write the Plan

Invoke `writing-plans` to drive the plan structure. Pair it with `feature-planning` for task decomposition. Override `writing-plans`' default path:

- Path: `docs/plan/YYYY-MM-DD-<kebab-title>.md` — the same `<kebab-title>` as the spec, dated the day the plan is written, no `-plan` suffix.
- Line 1 is the H1; line 2 is exactly `Status: Approved`.
- Add the plan to the `## In progress` list in `docs/plan/README.md` in the same commit (create the README as in Step 1 if missing).

Commit.

### Step 5 — Emit Handoff Prompt

Print a prompt block the user can copy-paste into a new session to start implementation. Format:

```
=== PASTE INTO NEW SESSION ===
/wens-plan-implementer

Spec: <absolute path to spec>
Plan: <absolute path to plan>
Repo: <absolute repo root>
Branch: <current branch>

Notes (optional):
- <any caller context the implement flow should know>
==============================
```

End your turn after printing this block. Do **not** auto-invoke `wens-plan-implementer` — the handoff is intentional context reset.

## Dispatch Template Reference

`scripts/dispatch.sh` (copied from `agd-dispatch`) — flags this skill uses:

| Flag | Used for |
|---|---|
| `--template spec-review` | Only template this skill calls |
| `--var spec_path=<path>` | Required |
| `--var stage="round N"` | Required, for traceability |
| `--slug <kebab-title>` | Scratch task directory `docs/tmp/claude-scratch/YYYY-MM-DD-<kebab-title>/` |
| `--skills a,b,c` | Comma-list reviewer should load |
| `--guidance <text>` | Per-round focus (e.g. "verify R1 fixes only") |

Default timeout 900s; override with `--timeout <sec>` if the spec is large.

## Red Flags

- Skipping the brainstorming flow because "the user already described it" — run it anyway; the gates catch hidden assumptions.
- Skipping `grill-with-docs` at the self-review gate because the spec "looks clean" — pair is mandatory.
- Treating `status: ISSUES_FOUND` with only `major`/`minor` items as a reason to keep looping — only blockers gate the loop; majors/minors are advisory.
- Auto-invoking `wens-plan-implementer` at the end. The handoff prompt is the deliverable; the user starts the next session.
- Forgetting to commit between rounds — reviewer needs the latest spec on disk.
- Writing the spec or plan to `docs/superpowers/` or with a `-design` / `-plan` suffix — they go in `docs/spec/` and `docs/plan/` under one shared kebab title, with `Status:` on line 2 and a folder `README.md` row.
