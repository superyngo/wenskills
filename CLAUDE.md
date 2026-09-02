# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

A collection of AI assistant skills for Claude and GitHub Copilot CLI. Each skill is a self-contained directory under `skills/` that defines a specialized AI behavior.

## Skill Structure

```
skills/<skill-name>/
  SKILL.md           # YAML frontmatter + instruction prose
  scripts/           # Python helper scripts (stdlib only — no third-party deps)
  references/        # Markdown modules included by the skill
```

**`SKILL.md` frontmatter fields:** `name`, `description`, `argument-hint` (optional), `allowed-tools`

## Key Conventions

- **Python scripts**: Standard library only. Invoked via `Bash` tool as `python3 scripts/<script>.py`.
- **Planning docs**: Go in `docs/plans/` with filename `YYYY-MM-DD-<topic>.md`.
- **Distributable bundles**: `.skill` files at repo root are ZIP-packaged bundles of a skill directory — not source.

## Migrated Skills

`wens-dev-principles`, `vscode-dev-experience-pack`, `rust-crossplatform-app`,
`publishing-platform-stores`, `github-init`, `dev-prompt`, `create-release-workflow`, and
`git-release` moved to `~/repos/wensdev` (2026-09-02). See that repo for their docs.

## Adding a New Skill

1. Create `skills/<skill-name>/SKILL.md` with YAML frontmatter.
2. Add Python stdlib-only helper scripts to `skills/<skill-name>/scripts/`.
3. Add reference markdown to `skills/<skill-name>/references/` if needed.
4. Optionally package into a `.skill` ZIP bundle at the repo root.
