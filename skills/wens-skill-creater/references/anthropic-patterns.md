# Anthropic Skill-Creator Patterns (Reference)

Deeper material from Anthropic's `skill-creator` and the superpowers `writing-skills`. Load only when needed.

## Progressive Disclosure (Three Levels)

1. **Metadata** (name + description) — always in context (~100 words). Decides whether to load.
2. **SKILL.md body** — loaded when the skill triggers. Target <500 lines.
3. **Bundled resources** — loaded on demand. Scripts can run *without* being loaded into context.

Reference files should be linked from SKILL.md with explicit guidance on when to read them. For references >300 lines, include a table of contents.

When a skill spans multiple variants (cloud providers, frameworks), put each in its own reference file and let the body select:

```
cloud-deploy/
  SKILL.md            # workflow + selection logic
  references/aws.md
  references/gcp.md
  references/azure.md
```

## Full Eval-Viewer Workflow

For skills with verifiable outputs where the user wants a rigorous comparison.

### Workspace layout

```
<skill-name>-workspace/
  iteration-1/
    eval-0-<descriptive-name>/
      eval_metadata.json
      with_skill/outputs/...
      without_skill/outputs/...
      grading.json
      timing.json
    benchmark.json
    benchmark.md
  iteration-2/
    ...
```

### Steps

1. **Spawn all runs in one turn** — both with-skill and baseline subagents at once so they finish together.
2. **While runs go**, draft assertions for each eval. Good assertions are objectively verifiable with descriptive names. Don't force assertions on subjective output.
3. **Capture timing data** the moment each subagent notification arrives — `total_tokens` and `duration_ms` aren't persisted elsewhere. Save to `timing.json`.
4. **Grade** — spawn a grader subagent reading `agents/grader.md`. Output to `grading.json` with fields `text`, `passed`, `evidence` (viewer depends on these exact names). For programmatic checks, write a script — faster and reusable.
5. **Aggregate**:
   ```bash
   python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>
   ```
6. **Analyst pass** — look beyond the aggregate: assertions that always pass (non-discriminating), high-variance evals (flaky), token/time tradeoffs.
7. **Launch the viewer**:
   ```bash
   nohup python <skill-creator>/eval-viewer/generate_review.py \
     <workspace>/iteration-N \
     --skill-name "my-skill" \
     --benchmark <workspace>/iteration-N/benchmark.json \
     > /dev/null 2>&1 &
   ```
   For iteration 2+, also pass `--previous-workspace <workspace>/iteration-<N-1>`.
   Headless: use `--static <path>` to emit standalone HTML.

### Reading feedback

`feedback.json` has a `reviews` array with `run_id`, `feedback`, `timestamp`. Empty feedback = user thought it was fine; focus improvements where they complained.

## Blind Comparison (Advanced)

When the user asks "is the new version actually better?":

1. Give two outputs to an independent comparator subagent without telling it which is which.
2. Let it judge quality.
3. Analyze why the winner won.

See Anthropic's `agents/comparator.md` and `agents/analyzer.md`.

## Description Optimization Loop

After the body is good:

1. Generate ~20 eval queries (8-10 should-trigger, 8-10 should-not-trigger). Concrete, realistic, with backstory/paths/typos. Mix of phrasings. Negatives must be near-misses — easy negatives test nothing.
2. Review with the user via `assets/eval_review.html` (placeholders `__EVAL_DATA_PLACEHOLDER__`, `__SKILL_NAME_PLACEHOLDER__`, `__SKILL_DESCRIPTION_PLACEHOLDER__`).
3. Run the loop:
   ```bash
   python -m scripts.run_loop \
     --eval-set <path.json> \
     --skill-path <path> \
     --model <current-session-model-id> \
     --max-iterations 5 \
     --verbose
   ```
   Splits 60/40 train/test. Evaluates each query 3× per iteration for stable rates. Picks `best_description` by test score (not train) to avoid overfitting.
4. Apply `best_description` to the skill's frontmatter. Show before/after.

### How triggering actually works

Claude only consults skills for tasks it can't easily handle alone. Simple one-step queries like "read this PDF" may not trigger a skill even with a perfect description, because Claude handles them directly. Your eval queries must be substantive enough that consulting a skill is genuinely useful — simple queries are poor tests regardless of description quality.

## Bulletproofing Discipline Skills

Discipline skills (TDD, verification-before-completion) face agents that will rationalize under pressure. Counter explicitly:

### Forbid specific workarounds

Bad: `Write code before test? Delete it.`

Good:
```
Write code before test? Delete it. Start over.

No exceptions:
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete
```

### Address spirit-vs-letter early

> Violating the letter of the rules is violating the spirit of the rules.

Cuts off an entire class of "I'm following the spirit" rationalizations.

### Build a rationalization table from baseline testing

| Excuse | Reality |
|---|---|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Tests after achieve the same goals" | Tests-after = "what does this do?". Tests-first = "what should this do?". |

### Pressure scenarios

Combine ≥3 pressures: time deadline + sunk cost + authority + exhaustion. A discipline skill that holds under one pressure but fails under three isn't done.

## Communicating with Skill Users

Users range from "first time in a terminal" to senior engineers. Calibrate jargon:

- "evaluation" / "benchmark": borderline, OK in most contexts.
- "JSON" / "assertion": expect signals the user knows these before using without explanation.
- Briefly define unfamiliar terms when in doubt.

## Updating an Existing Skill

- Preserve the original `name` field and directory name.
- Copy to a writeable location before editing if the installed path is read-only (`/tmp/skill-name/`).
- Output filename must match the original (`research-helper.skill`, not `research-helper-v2.skill`).
