# Skill-local glossary and ADRs stay inside the skill bundle

Date: 2026-11-20

## Context

repo-docs 1, 2, and 6 put the documentation entry point in root `CONTEXT.md`, the decision
records in root `docs/adr/`, and the glossary in root `docs/reference/glossary.md`. repo-docs 15
requires an ADR for a deviation from a `MUST`.

`skills/wens-tutor/` carries its own `CONTEXT.md` (a domain glossary: Materials Root, Course,
Bank, Section, Question, …) and `docs/adr/0001…0015`. `skills/wens-tutor/SKILL.md` loads both by
relative path, and the skill is installed by copying or linking its directory, so anything
hoisted to the repo root would be missing wherever the skill is installed.

## Decision

Documentation a skill loads at run time stays inside that skill's directory:

- `skills/wens-tutor/CONTEXT.md` stays at that path and keeps its name, because `SKILL.md`,
  the frozen spec `docs/spec/2026-08-13-wens-tutor.md`, and the skill's ADRs cite it. It is a
  skill-local glossary, not a second documentation entry point.
- `skills/wens-tutor/docs/adr/` stays in the skill and carries its own
  [`README.md`](../../skills/wens-tutor/docs/adr/README.md) status table, held to repo-docs 17.
- Root `CONTEXT.md`, `docs/reference/README.md`, and `docs/adr/README.md` link to both, so
  they remain reachable from the root entry point.

The exception applies to files a skill bundle loads at run time. Repo-level records about a
skill — its spec, plan, debug and audit records — live in root `docs/`.

## Alternatives rejected

- **Hoist to root `docs/adr/` and the root glossary, link out from the skill.** Breaks the
  skill wherever it is installed outside this repo.
- **Rename `skills/wens-tutor/CONTEXT.md` to `glossary.md` in place.** Rewrites citations in
  the skill, the frozen spec and the ADRs for a name change only; the root-entry ambiguity is
  already resolved by this ADR and the root links.

## Consequences

- Another skill that grows its own glossary or ADRs follows the same shape: in the skill, an
  `adr/README.md` status table, and a link from the root indexes.
