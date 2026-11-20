# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

A collection of AI assistant skills for Claude and GitHub Copilot CLI. Documentation starts at
[`CONTEXT.md`](CONTEXT.md); skill layout and the skill list are in
[`docs/reference/skill-layout.md`](docs/reference/skill-layout.md).

## Conventions

- **Python scripts**: Standard library only. Invoked via `Bash` tool as `python3 scripts/<script>.py`.
- **Docs**: follow the repo-docs layout in `CONTEXT.md` — specs in `docs/spec/`, plans in
  `docs/plan/` (`YYYY-MM-DD-<kebab-title>.md`, a spec and its plan share the title, `Status:` on
  line 2, row in the folder `README.md`); open work in `docs/plan/BACKLOG.md`.
- **Scratch**: `docs/tmp/<agent>-scratch/YYYY-MM-DD-<slug>/`, gitignored by `docs/tmp/*-scratch/`.
- **Changelog**: every change gets an entry under `## [Unreleased]` → `### YYYY-MM-DD`.
