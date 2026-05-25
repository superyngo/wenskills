# Spec Review

<!-- GUIDANCE-BLOCK -->
## Caller guidance

{{guidance}}
<!-- /GUIDANCE-BLOCK -->

You are reviewing a design spec / PRD for implementation-readiness.

- **Spec:** `{{spec_path}}`
- **Stage:** {{stage}}

<!-- SKILLS-BLOCK -->
**Load these skills before starting the task** (via your `Skill` tool if running inside Claude Code; otherwise read `~/.claude/skills/<name>/SKILL.md` and follow them): {{skills}}.
<!-- /SKILLS-BLOCK -->

## What to assess

1. **Completeness** — decisions made, no implicit TBDs.
2. **Consistency** — sections agree on behavior, layout, contracts.
3. **Implementability** — a fresh engineer could build it without more clarification.
4. **Scope** — coherent, not bundling independent subsystems.
5. **Risks** — tradeoffs surfaced with mitigations or accepted-risk notes.

Spot-check 3-5 load-bearing claims before raising any finding. Grep to verify referenced files/symbols exist.

## Severity (closed vocabulary)

`blocker` · `major` · `minor`. Do not invent others.

## Output contract

Your response MUST begin with this YAML frontmatter block:

```yaml
---
status: PASS | ISSUES_FOUND
issues:
  - severity: blocker | major | minor
    location: "<section or file:line>"
    description: "<what's wrong>"
    suggestion: "<concrete fix>"
---
```

`status: PASS` only when zero blockers and zero majors. `issues: []` when PASS.
