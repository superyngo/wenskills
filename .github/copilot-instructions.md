# Copilot Instructions

This repository is a collection of AI assistant skills for GitHub Copilot CLI and Claude.
Documentation starts at [`CONTEXT.md`](../CONTEXT.md); skill layout, frontmatter fields, the skill
list, and how to add a skill are in
[`docs/reference/skill-layout.md`](../docs/reference/skill-layout.md).

## Conventions

- Python helper scripts use **standard library only** (no third-party dependencies).
- Specs go in `docs/spec/`, plans in `docs/plan/`, as `YYYY-MM-DD-<kebab-title>.md` with
  `Status:` on line 2; open work goes in `docs/plan/BACKLOG.md`.
