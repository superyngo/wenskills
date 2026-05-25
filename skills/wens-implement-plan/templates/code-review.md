# Code Review

<!-- GUIDANCE-BLOCK -->
## Caller guidance

{{guidance}}
<!-- /GUIDANCE-BLOCK -->

You are reviewing a code change for correctness and engineering quality.

- **Repo:** `{{repo_root}}`
- **Scope (diff / range / branch):** `{{diff_scope}}`
- **Files changed:** {{files_changed}}
- **Spec (optional):** `{{spec_path}}`
- **Stage:** {{stage}}

<!-- SKILLS-BLOCK -->
**Load these skills before starting the task** (via your `Skill` tool if running inside Claude Code; otherwise read `~/.claude/skills/<name>/SKILL.md` and follow them): {{skills}}.
<!-- /SKILLS-BLOCK -->

## Scope guard

Review ONLY the listed changes. Do not flag pre-existing code, style nits in untouched files, or work that other tasks/PRs will handle.

## What to evaluate

1. **Correctness** — does it do what it claims? Edge cases the change called for?
2. **Tests** — assert behavior, not implementation. Runnable as-written. TDD where applicable.
3. **Clarity** — naming, structure, comments that explain *why* for non-obvious code.
4. **Surgical** — only what the task required; no drive-by "improvements".
5. **Idioms** — matches surrounding codebase style.

Spot-check 3-5 load-bearing claims. Grep to verify symbols/lines before citing them.

## Severity (closed vocabulary)

`blocker` · `major` · `minor`. Do not invent others.

## Output contract

Your response MUST begin with this YAML frontmatter block:

```yaml
---
status: PASS | ISSUES_FOUND
issues:
  - severity: blocker | major | minor
    location: "<file:line>"
    description: "<what's wrong>"
    suggestion: "<concrete fix>"
---
```

`status: PASS` only when zero blockers and zero majors. Minor-only is acceptable.
