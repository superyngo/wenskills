---
name: wens-skill-creater
description: Use when creating, editing, or improving an agent skill. Triggers on requests like "write a skill for X", "turn this workflow into a skill", "improve this skill's description", or when capturing a repeated technique into reusable form.
---

# Wen's Skill Creater

Synthesis of three approaches: TDD-style skill testing, lean drafting template, and eval-driven iteration. Use the loop below — adapt depth to the user's appetite (full eval loop vs. "just vibe with me").

## Core Loop

```
1. Capture intent      → know what & when the skill triggers
2. Draft SKILL.md      → minimal frontmatter + body
3. Test                → subagent pressure scenarios OR eval prompts
4. Iterate             → close loopholes / improve based on feedback
5. (Optional) Optimize → tune description for triggering accuracy
```

The order is flexible. If the user already has a draft, jump to step 3. If they say "just write it, no testing", honor that — but warn that untested skills usually have gaps.

## 1. Capture Intent

Before writing, get clear answers (extract from conversation history first; ask user only for gaps):

- **What** should the skill enable the agent to do?
- **When** should it trigger? (user phrases, file types, symptoms, contexts)
- **Output format** expected?
- **Type** of skill — which determines testing approach:
  - **Discipline-enforcing** (rules under pressure): TDD, verification-before-completion
  - **Technique** (how-to): condition-based-waiting, root-cause-tracing
  - **Pattern** (mental model): reducing-complexity
  - **Reference** (API/syntax docs): library guides

If the task is broad, present 2-3 interpretations and let the user pick — don't silently choose.

## 2. Draft SKILL.md

### Frontmatter (YAML, ≤1024 chars)

```yaml
---
name: kebab-case-name
description: Use when [specific triggers, symptoms, contexts]
argument-hint: <optional>
allowed-tools: <optional>
---
```

**Rules for `description`** (this is the ONLY thing the agent sees before deciding to load the skill):

- Start with **"Use when..."** — focus on triggering conditions.
- Third person. Keep under ~500 chars when possible.
- Include concrete symptoms, error messages, file types, user phrasings.
- **Do NOT summarize the skill's workflow.** Agents who see a workflow summary will follow that summary instead of reading the body. Bad: `Use when executing plans — dispatches subagent per task with code review between`. Good: `Use when executing implementation plans with independent tasks`.
- Be a little "pushy" against under-triggering: `...Make sure to use this skill whenever the user mentions X, Y, or Z, even if they don't explicitly ask for it.`

### Body Template

```markdown
# Skill Name

## Overview
Core principle in 1-2 sentences. What problem does this solve?

## When to Use
Symptoms / situations. When NOT to use.

## Quick Reference / Core Pattern
Table or before-after snippet for scanning.

## Workflow
Numbered steps, or a small flowchart only if the decision is non-obvious.

## Examples
ONE excellent, real example. Not multi-language. Not fill-in-the-blank.

## Common Mistakes
What goes wrong + how to fix.

## Red Flags (for discipline skills)
Self-check list of "I'm about to violate this rule" symptoms.
```

### Body Rules

- **Token efficiency**: target <500 lines, <200 words for frequently-loaded skills. Move heavy reference to `references/*.md`. Move deterministic logic to `scripts/*.py` (stdlib only per this repo's convention).
- **Explain the *why***. Smart agents follow reasoning further than rote `MUST`/`NEVER`. Reserve all-caps for genuinely critical invariants.
- **Imperative voice** in instructions.
- **No narrative** ("In session 2025-…, we found…"). Skills are reusable references, not war stories.
- **Cross-reference other skills by name**, not `@` path (that force-loads and burns context): `**REQUIRED BACKGROUND:** Use superpowers:test-driven-development`.

### Directory Structure

```
skills/<skill-name>/
  SKILL.md              # required
  references/*.md       # heavy reference (>100 lines) loaded on demand
  scripts/*.py          # deterministic helpers (stdlib only)
  assets/               # templates/icons used in output
```

Flat namespace. Split files only when content is heavy reference or reusable code — keep everything else inline.

## 3. Test the Skill

Two complementary modes — pick based on skill type and user appetite.

### Mode A — Subagent pressure scenarios (for discipline / technique skills)

Adapts TDD: **RED → GREEN → REFACTOR**.

1. **RED**: Run 1-3 realistic scenarios with a fresh subagent *without* the skill. Record exact behavior and rationalizations verbatim. This is your failing test.
2. **GREEN**: Write the skill that addresses *those specific* rationalizations. Re-run; agent should now comply.
3. **REFACTOR**: Find new rationalizations under combined pressures (time, sunk cost, authority, exhaustion). Add explicit counters. Repeat until bulletproof.

Build a **rationalization table** in the skill body capturing every excuse you saw and a one-line counter.

### Mode B — Eval prompts (for skills with verifiable outputs)

For skills producing files, data, code, or fixed workflows.

1. Write 2-3 realistic prompts a real user would type (concrete, with file paths, names, context — not abstract).
2. Run with-skill and baseline (without-skill) subagents in parallel.
3. Grade against assertions where possible; qualitative review for subjective output.
4. Iterate based on user feedback and any patterns in transcripts.

If the user wants the full eval-viewer loop (workspace dirs, benchmark.json, HTML viewer), use Anthropic's `skill-creator` scripts directly — this skill summarizes the methodology, not the tooling.

### The Iron Law

**Don't claim a skill is done before watching an agent use it.** Reading ≠ using. Confidence ≠ correctness. 15 minutes of testing saves hours of debugging in production.

## 4. Iterate

When you get feedback:

- **Generalize.** The skill must work for cases beyond your test prompts. Avoid fiddly overfits and oppressive `MUST`s. Try different framings if a problem is stubborn.
- **Keep it lean.** Remove instructions that aren't pulling their weight. Read transcripts — if the skill is sending the agent down unproductive paths, cut those parts.
- **Spot repeated work across runs.** If every test run reinvents the same helper, bundle that helper in `scripts/`.
- **Explain *why*** rather than tightening rules. A reasoned instruction transfers; a brittle command doesn't.

## 5. Description Optimization (Optional)

After the body is good, the description still decides whether the skill ever triggers. To tune it:

- Generate ~20 realistic eval queries (8-10 should-trigger, 8-10 should-not-trigger). Include near-misses for should-not — the easy negatives test nothing.
- Run the description against the queries (manually or via a loop script), measure trigger accuracy, propose alternatives, re-test.
- Pick the variant that wins on a held-out subset, not the one with best overall score (avoids overfitting).

See [references/anthropic-patterns.md](references/anthropic-patterns.md) for the deeper eval/viewer methodology if needed.

## Anti-Patterns

| Anti-pattern | Why bad |
|---|---|
| Description summarizes workflow | Agent follows summary instead of body |
| Description in first person | Frontmatter is injected as system prompt context |
| Narrative storytelling in body | Specific, not reusable |
| Multi-language examples | Mediocre quality, maintenance burden |
| Code rendered inside flowcharts | Can't copy-paste; hard to read |
| `@path/to/other-skill` cross-refs | Force-loads 200k+ context immediately |
| Skill deployed without ever being run by a fresh agent | Untested = unknown |

## Checklist Before Deploying

- [ ] `name` is kebab-case (letters, numbers, hyphens only)
- [ ] `description` starts with "Use when…", third person, includes triggers/symptoms, doesn't summarize workflow
- [ ] Frontmatter ≤1024 chars
- [ ] Body explains *why*, not just *what*
- [ ] One excellent example, not many mediocre ones
- [ ] Heavy reference (>100 lines) moved to `references/`
- [ ] Deterministic logic moved to `scripts/` (stdlib only in this repo)
- [ ] At least one fresh-agent test run completed
- [ ] Common mistakes / red flags section present (if discipline skill)

## Reference

- [references/anthropic-patterns.md](references/anthropic-patterns.md) — Progressive disclosure, eval-viewer workflow, blind comparison, description-optimization loop. Load only when the user wants the full Anthropic skill-creator tooling.
