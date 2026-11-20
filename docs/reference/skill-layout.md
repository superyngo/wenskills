# Skill layout

Each **Skill** is a self-contained directory under `skills/`:

```
skills/<skill-name>/
  SKILL.md           # YAML frontmatter + instruction prose
  scripts/           # helper scripts (Python: standard library only)
  references/        # Markdown reference modules the skill loads on demand
  templates/         # dispatch templates (dispatching skills only)
```

**`SKILL.md` frontmatter fields:**

- `name` — skill identifier, matches the directory name
- `description` — shown in the skill picker; used for auto-invocation matching
- `argument-hint` — optional, describes positional args (e.g. `[version]`)
- `allowed-tools` — the tools the skill may use

Python helper scripts are invoked from the skill's instructions through the shell, e.g.
`python3 scripts/<script>.py`.

## Skills in this repo

| Skill | Purpose |
|---|---|
| `agd-dispatch` | Render one dispatch template and send it to a third-party agent via `agd` |
| `agent-dispatcher` | Install and configure the `agd` CLI; tier-based fallback dispatch |
| `gpinstall` | Write README install sections using the gpinstall release-installer scripts |
| `wens-plan-creator` | Brainstorm → spec → external review loop → plan → handoff prompt |
| `wens-plan-implementer` | Execute a plan with every implement/review subtask dispatched via `agd` |
| `wens-skill-creater` | Create, edit, or improve an agent skill |
| `wens-tutor` | Turn a Markdown courseware tree into a study site (own glossary and ADRs) |
| `wenswiki-notes` | Capture session insights into, and query, the wenswiki vault |
| `yt-channel-dl` | Download audio or video from a YouTube channel or playlist |

Skills that moved to `~/repos/wensdev` (2026-09-02): `wens-dev-principles`,
`vscode-dev-experience-pack`, `rust-crossplatform-app`, `publishing-platform-stores`,
`github-init`, `dev-prompt`, `create-release-workflow`, `git-release`.

## Adding a new skill

1. Create `skills/<skill-name>/SKILL.md` with YAML frontmatter.
2. Add standard-library-only Python helper scripts to `skills/<skill-name>/scripts/`.
3. Add reference Markdown to `skills/<skill-name>/references/` if needed.
4. Add a row to the table above.
