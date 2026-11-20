# Glossary

Canonical vocabulary for this repository. Skill-specific domain terms live with the skill that
owns them (for example `skills/wens-tutor/CONTEXT.md`, recorded in
[ADR 0002](../adr/0002-skill-local-docs-stay-in-the-skill.md)).

**Skill**:
A self-contained directory under `skills/<name>/` that defines one specialized agent behavior.
Its entry point is its **SKILL.md**.
_Avoid_: Plugin, prompt pack, command.

**SKILL.md**:
The file an agent loads to run a **Skill**: YAML **Frontmatter** followed by instruction prose.
_Avoid_: Skill file, readme.

**Frontmatter**:
The YAML block at the top of a **SKILL.md**. Fields: `name`, `description`, `argument-hint`
(optional), `allowed-tools`. The `description` decides when an agent triggers the **Skill**.
_Avoid_: Header, metadata block.

**Reference module**:
A Markdown file under `skills/<name>/references/` that a **SKILL.md** loads on demand.
_Avoid_: Include, partial.

**Helper script**:
A script under `skills/<name>/scripts/` that a **Skill** runs through the shell. Python helper
scripts use the standard library only.
_Avoid_: Tool, utility.

**Dispatch**:
Sending one rendered **Dispatch template** to a third-party agent through **agd** and capturing
its output. Done by each skill's own `scripts/dispatch.sh`.
_Avoid_: Offload, delegate, subagent call.

**Dispatch template**:
A prompt file under `skills/<name>/templates/` (`spec-review`, `code-review`, `code-implement`,
`review-implement`) with `{{key}}` placeholders and optional `SKILLS-BLOCK` / `GUIDANCE-BLOCK`
sections.
_Avoid_: Prompt template, recipe.

**agd**:
The external agent-dispatcher CLI (formerly `dispatch-agent`) that runs a prompt on a configured
agent tier. Installed and configured through the `agent-dispatcher` **Skill**.
_Avoid_: dispatch-agent (old name), agent runner.

**Handoff prompt**:
The paste-ready block `wens-plan-creator` prints at the end of planning, which starts
`wens-plan-implementer` in a fresh session.
_Avoid_: Continuation prompt, resume prompt.

**Scratch directory**:
A per-task directory `docs/tmp/<agent>-scratch/YYYY-MM-DD-<slug>/` holding probes, rendered
prompts, and dispatch output. Gitignored by the pattern `docs/tmp/*-scratch/`.
_Avoid_: Temp dir, flat `docs/tmp/` files.
