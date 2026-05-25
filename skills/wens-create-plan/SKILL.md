---
name: wens-create-plan
description: "Use when starting a new feature/project and you want Wen's full plan-creation flow — brainstorm → spec → external review loop → implementation plan — with spec review offloaded via agd to save main-session context. Use whenever the user says 'wens create plan', 'wens plan', 'start a wens plan flow', or asks for a planning workflow that ends with a paste-ready handoff prompt for the implement skill."
allowed-tools: Bash, Read, Write, Edit, Skill
---

# Wen's Create-Plan Flow

End-to-end planning workflow that produces a reviewed spec **and** an implementation plan, ending with a paste-ready prompt the user can drop into a fresh session to start `wens-implement-plan`.

External spec review runs via `agd` (this skill embeds its own copy of `dispatch.sh` + templates — no need to load `agd-dispatch`).

## Assumptions

All referenced skills are installed. Don't validate them.

- `brainstorming`, `grill-with-docs`, `writing-plans`, `feature-planning`
- `agd` is on `PATH` and configured

## Workflow

```
1. brainstorming                       (interactive)
2. Spec Self-Review + grill-with-docs  (forced pairing inside step 1's review gate)
3. Loop: dispatch spec-review via agd  (until status: PASS)
4. writing-plans + feature-planning    (produce plan doc)
5. Emit handoff prompt                 (user pastes into next session)
```

### Step 1 — Brainstorm

Invoke the `brainstorming` skill and run it to completion. Follow its flow verbatim — clarifying questions, approach exploration, design presentation, write spec to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`, commit.

### Step 2 — Spec Self-Review (paired with grill-with-docs)

When `brainstorming` reaches its **Spec Self-Review** gate, **also** invoke `grill-with-docs` in the same step. Run both back-to-back against the freshly-written spec, fix issues inline, then re-loop if either flags something material.

Order: brainstorming's self-review scan first (placeholders, internal consistency, scope, ambiguity), then `grill-with-docs` (challenge against domain model and existing CONTEXT.md / ADRs). Apply both sets of fixes inline.

### Step 3 — External Review Loop via `agd`

Loop the spec through external review until it returns `status: PASS` (zero blockers, zero majors). Each round:

```bash
sh skills/wens-create-plan/scripts/dispatch.sh \
    --template spec-review \
    --var spec_path=<path-to-spec> \
    --var stage="round <N>" \
    --skills systematic-debugging,verification-before-completion \
    --guidance "<optional: focus areas, prior-round followups>"
```

The script writes the rendered prompt and `agd` output under `docs/tmp/`. Read the `out` file; its YAML frontmatter has `status: PASS | ISSUES_FOUND` and an `issues:` list with `severity: blocker | major | minor`.

**Loop rules:**

- If any `blocker` exists: fix the spec inline (you, in main session — small edits don't need offload), commit, increment `stage`, dispatch again.
- If no blockers remain: exit the loop and proceed. `major` and `minor` items are advisory at this stage — note them and move on; they can be revisited during planning or implementation.
- Pass `--guidance` on follow-up rounds to point the reviewer at "verify R<N-1> blockers only" so each round stays cheap.
- No round cap — loop until blockers reach zero. If rounds aren't converging (same blocker keeps re-appearing after a fix attempt), surface to the user; that's a structural problem the loop can't resolve.

Ensure `docs/tmp/` is in `.gitignore` before the first dispatch.

### Step 4 — Write the Plan

Invoke `writing-plans` to drive the plan structure. Pair it with `feature-planning` for task decomposition. Output goes to `docs/superpowers/plans/YYYY-MM-DD-<topic>-plan.md` (or whatever `writing-plans` chooses). Commit.

### Step 5 — Emit Handoff Prompt

Print a prompt block the user can copy-paste into a new session to start implementation. Format:

```
=== PASTE INTO NEW SESSION ===
/wens-implement-plan

Spec: <absolute path to spec>
Plan: <absolute path to plan>
Repo: <absolute repo root>
Branch: <current branch>

Notes (optional):
- <any caller context the implement flow should know>
==============================
```

End your turn after printing this block. Do **not** auto-invoke `wens-implement-plan` — the handoff is intentional context reset.

## Dispatch Template Reference

`scripts/dispatch.sh` (copied from `agd-dispatch`) — flags this skill uses:

| Flag | Used for |
|---|---|
| `--template spec-review` | Only template this skill calls |
| `--var spec_path=<path>` | Required |
| `--var stage="round N"` | Required, for traceability |
| `--skills a,b,c` | Comma-list reviewer should load |
| `--guidance <text>` | Per-round focus (e.g. "verify R1 fixes only") |

Default timeout 900s; override with `--timeout <sec>` if the spec is large.

## Red Flags

- Skipping the brainstorming flow because "the user already described it" — run it anyway; the gates catch hidden assumptions.
- Skipping `grill-with-docs` at the self-review gate because the spec "looks clean" — pair is mandatory.
- Treating `status: ISSUES_FOUND` with only `minor` items as a blocker — minors are advisory; exit the loop.
- Auto-invoking `wens-implement-plan` at the end. The handoff prompt is the deliverable; the user starts the next session.
- Forgetting to commit between rounds — reviewer needs the latest spec on disk.
