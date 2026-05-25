# Implement Review Feedback

<!-- GUIDANCE-BLOCK -->
## Caller guidance

{{guidance}}
<!-- /GUIDANCE-BLOCK -->

You have been handed a review report. Your job is to address the findings in the workspace. The caller has delegated to you via `agd`; you may write files in `{{repo_root}}`.

- **Repo:** `{{repo_root}}`
- **Review report:** `{{review_report_path}}`
- **Spec (optional, for context):** `{{spec_path}}`
- **Stage:** {{stage}}

<!-- SKILLS-BLOCK -->
**Load these skills before starting the task** (via your `Skill` tool if running inside Claude Code; otherwise read `~/.claude/skills/<name>/SKILL.md` and follow them): {{skills}}.
<!-- /SKILLS-BLOCK -->

## Rules

1. Read the review report. Address every `blocker` and every `major`. `minor` issues are optional — fix only if cheap and uncontroversial.
2. For each issue you act on, make the smallest change that resolves it. Do not refactor adjacent code.
3. For each issue you decline to act on (e.g., disagree with reviewer, out of scope), record the reason in `notes` — do not silently skip.
4. Follow TDD where the original change required it (failing test first, then fix).
5. One logical commit per issue is preferred; squash only when the changes are inseparable.
6. If the report is ambiguous or contradicts the spec, STOP and return `status: BLOCKED` with notes.

## Output contract

Your response MUST **end with** this YAML block:

```yaml
---
status: COMPLETED | PARTIAL | BLOCKED
addressed:
  - issue: "<copy issue location/description>"
    action: fixed | declined | deferred
    commit: "<sha or 'pending'>"
    note: "<one line>"
files_changed:
  - <path relative to {{repo_root}}>
notes: |
  <summary; required>
---
```

- `COMPLETED`: every blocker + major addressed (fixed or explicitly declined with reason).
- `PARTIAL`: some addressed, some deferred — list which and why.
- `BLOCKED`: explain what stopped you.
