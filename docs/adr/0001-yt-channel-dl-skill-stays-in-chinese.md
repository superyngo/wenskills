# `skills/yt-channel-dl/SKILL.md` stays in Chinese

Date: 2026-11-20

## Context

repo-docs 4 asks for English in every document and skill, and says a repo that chooses another
language records it in an ADR. repo-docs 15 requires an ADR for any deviation. The
`yt-channel-dl` skill (`skills/yt-channel-dl/SKILL.md`, including its frontmatter `description`)
is written in Chinese: its user asks for downloads in Chinese and the skill's prompts to the user
(type confirmation, format choice, status reports) are Chinese. The 2026-11-19 documentation
audit flagged it as the one skill whose prose is not English.

## Decision

`skills/yt-channel-dl/SKILL.md` is kept in Chinese as written. The exception covers that file
only. Every other file in this repo — root files, everything under `docs/`, other skills, and
`yt-channel-dl`'s scripts and tests — follows repo-docs 4 (English; Chinese only where the subject
is the language itself, such as trigger phrases and corpus literals).

## Alternatives rejected

- **Full English translation.** Costs a rewrite of a working skill and changes the language of
  its trigger `description`, which is what the Chinese-speaking user types; no reader of the file
  needs English.
- **English prose with Chinese prompt strings.** Two languages in one file, more to keep in sync,
  no gain for the single user.

## Consequences

- A new or substantially rewritten `yt-channel-dl` skill revisits this ADR.
- Glossary terms (`docs/reference/glossary.md`) stay English; the skill does not introduce
  repo-wide terms.
