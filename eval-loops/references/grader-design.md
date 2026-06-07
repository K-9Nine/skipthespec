# Grader Design — choosing, building, and calibrating graders

"An essential component of effective evaluation design is to choose the right graders for the job." This is where evals succeed or fail.

## The selection rule

> Deterministic graders where possible, LLM graders where necessary or for flexibility, human graders judiciously for validation.

Default to code. Reach for an LLM judge only when the thing you're grading is genuinely open-ended (quality, tone, reasoning). Use humans only to calibrate the LLM judge or for irreducibly subjective output.

## Deterministic / code-based graders

| Grader | Use for |
|---|---|
| String match (exact / regex / fuzzy) | Known correct answers, format conformance |
| Binary tests (fail-to-pass, pass-to-pass) | Coding tasks — new behavior works, old behavior unbroken |
| Static analysis (lint, type, security) | Code quality floor, no regressions in safety |
| Outcome verification | The real end state — DB row exists, file written, config changed |
| Tool-call verification | Whether a required tool was used (sparingly — see below) |
| Transcript analysis | Turns taken, token usage, cost |

**Strengths:** fast, cheap, objective, reproducible, easy to debug.
**Weaknesses:** brittle to valid variations; lacks nuance; weak on subjective tasks.

### Grade the outcome, not the path
There is a strong instinct to assert "the agent called tool A then B then C." Resist it — it's too rigid, brittle, and punishes valid creativity. Check the **final state in the environment**. A flight-booking agent passes because a reservation exists in the DB, not because the transcript says "booked." For computer/browser agents this means checking file-system state, DB contents, DOM/URL state, or app config — not the click sequence.

### Outcome-check examples
- Coding: run the project's test suite against the produced code; lint + type-check pass.
- Data task: assert the output file's contents/schema, not the code that made it.
- Workflow: query the backend for the record the workflow was supposed to create.

## LLM-as-judge graders

| Grader | Use for |
|---|---|
| Rubric-based scoring | Multi-dimensional quality (correctness, clarity, completeness) |
| Natural-language assertions | "Does the answer cite a source for each claim?" |
| Pairwise comparison | A/B between two versions |
| Reference-based | Compare against a known-good reference answer |
| Multi-judge consensus | Reduce single-judge variance on high-stakes calls |

**Strengths:** flexible, scalable, captures nuance, handles freeform/open-ended output.
**Weaknesses:** non-deterministic, more expensive than code, requires calibration.

### Rules for trustworthy LLM judges
1. **Calibrate against human experts.** Periodically have a human grade the same trials; confirm low divergence. An uncalibrated judge is a guess with a confident voice.
2. **Give it an out.** Instruct it to return "Unknown" when it lacks enough information — prevents hallucinated verdicts.
3. **One dimension, one judge.** Use a structured rubric and grade each dimension with an isolated judge, rather than one judge scoring everything at once.
4. **Make it hack-resistant.** The judge should not be fooled by output that asserts its own correctness. Grade evidence, not self-claims.
5. **Recalibrate for subjective domains** (research quality, writing) frequently — drift is real.

## Partial credit

For multi-component tasks, build partial credit into the grader rather than all-or-nothing. It gives a smoother optimization signal and avoids hiding progress.

## The honesty enforcement angle (constitution §2)

A well-built grader is the mechanical enforcement of "no faking results." Because the grader checks the real outcome and resists bypasses, the only way to make it pass is to actually fix the code. If you ever find yourself editing the grader to make a build pass, you are faking results — fix the code, or fix the eval only if a transcript proves the grader was genuinely unfair.

## Calibration loop (quick recipe)

1. Pick ~20 trials spanning pass and fail.
2. Have a human grade them blind.
3. Run your graders on the same trials.
4. Measure agreement. Disagreements → either the grader is wrong (fix it) or the human spec was ambiguous (sharpen the task).
5. Repeat until agreement is high, then let the automated graders run; sample human review occasionally thereafter.
