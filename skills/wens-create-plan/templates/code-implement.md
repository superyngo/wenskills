# Implement Task

<!-- GUIDANCE-BLOCK -->
## Caller guidance

{{guidance}}
<!-- /GUIDANCE-BLOCK -->

You are implementing one well-scoped task. The caller has delegated to you via `agd`. You may write files in `{{repo_root}}` (the operator has enabled the required bypass flags in your `agd` config).

- **Repo:** `{{repo_root}}`
- **Spec (optional):** `{{spec_path}}`
- **Plan (optional):** `{{plan_path}}`
- **Stage:** {{stage}}

<!-- SKILLS-BLOCK -->
**Load these skills before starting the task** (via your `Skill` tool if running inside Claude Code; otherwise read `~/.claude/skills/<name>/SKILL.md` and follow them): {{skills}}.
<!-- /SKILLS-BLOCK -->

## Task

{{task_body}}

## Rules

1. Work in `{{repo_root}}`. Do not modify files outside what the task lists unless the task says to.
2. Follow any TDD steps the task names exactly: failing test → run → implement → run → commit.
3. Use the commit message the task specifies verbatim, if any.
4. If a step is ambiguous or the task contradicts the spec, STOP and return `status: BLOCKED` with notes.
5. Inspect-only commands are fine; do not let them mutate workspace state.

## Output contract

Your response MUST **end with** this YAML block (delimited by `---`, after any progress notes):

```yaml
---
status: COMPLETED | BLOCKED
files_changed:
  - <path relative to {{repo_root}}>
notes: |
  <free-text summary; required even when COMPLETED>
---
```

- `COMPLETED`: all steps run, tests pass, commit created.
- `BLOCKED`: explain in `notes` (missing context, plan conflict, environment).
- `files_changed`: if unsure, paste `git diff --name-only HEAD`.
