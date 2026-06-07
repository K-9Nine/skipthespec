---
name: eval-loops
description: "Design, build, run, and maintain automated test and evaluation loops so Claude can verify its own work without deploying to users. Use when the user says 'eval loop', 'set up evals', 'test harness', 'automated testing', 'how do I know it works', 'regression suite', 'grade the agent', or when a build needs a verification net. Implements Anthropic's evals method: 20-50 tasks from real failures, deterministic graders + LLM-as-judge, grade outcomes not paths, isolated trials, pass@k vs pass^k, read the transcripts. The safety net under autonomous-build and the quality gate before dogfood-loop promotion. Load autonomous-dev first."
license: MIT
metadata:
  author: nathan
  version: '1.0'
---

# Eval Loops

Model: Anthropic's evals method. "Good evaluations help teams ship AI agents more confidently. Evals make problems and behavioral changes visible before they affect users." This is the automated test/eval loop that lets Claude run autonomously without flying blind, and the gate that protects every dogfood promotion.

## When to Use This Skill

Whenever a build needs verification: before calling an `autonomous-build` slice done, before promoting a feature in `dogfood-loop`, when converting dogfood failures into protected tests, or when standing up a harness for a project.

> Prerequisite: `autonomous-dev` loaded, constitution read. Evals are how the honesty rule is enforced mechanically — a real grader can't be talked into passing.

## Vocabulary (use these terms precisely)

- **task** — one test: defined inputs + success criteria. **trial** — one attempt at a task. **grader** — logic that scores output. **transcript** — full record of a trial. **outcome** — final environment state at trial end. **suite** — a collection of tasks. **harness** — infra that runs it all.

## The Loop

```
real failures ──► write tasks (+reference solution) ──► run trials ──► grade ──► read transcripts
      ▲                                                                    │            │
      │                                              fix code (autonomous-build) ◄──────┘
      └──── feed new failures back as tasks ──────────────────────────────┘   (bound repair at 3)
```

## Step 0 — Start early, start small

Do not wait for a perfect suite. **20-50 simple tasks drawn from real failures is a great start.** In early development each change has a large, visible effect, so small samples suffice. Evals get harder to build the longer you wait.

## Step 1 — Source tasks from real failures

- Start with the manual checks you already run before a release, and the common things users try.
- Mine the bug tracker, support queue, and the dogfood friction log (`dogfood-loop`). Converting user-reported failures into tasks makes the suite reflect actual usage.
- Prioritize by user impact.

## Step 2 — Write unambiguous tasks with reference solutions

- A good task: **two domain experts would independently reach the same pass/fail verdict.** Ambiguity becomes noise in metrics.
- Each task must be passable by an agent that follows instructions correctly.
- Create a **reference solution** per task — a known-good output that passes all graders. This proves the task is solvable and that the graders are wired correctly. (A 0% pass@100 usually means a broken task, not an incapable agent.)
- Use the task template: `templates/eval-task.yaml`.

## Step 3 — Build balanced problem sets

- Test where a behavior **should** occur **and** where it **shouldn't**. One-sided evals create one-sided optimization.
- Avoid class imbalance. Example: include both "queries that should trigger a search" and "queries to answer from existing knowledge."

## Step 4 — Build a robust, isolated harness

- The eval agent must function roughly the same as production; the environment must not add noise.
- **Each trial starts from a clean environment.** No leftover files, cached data, or shared state — these cause correlated failures (flakiness) or artificially inflate scores.
- Use `scripts/run_evals.py` as the harness skeleton (deterministic + LLM-judge graders, clean-room per trial, pass@k / pass^k reporting).

## Step 5 — Design graders thoughtfully

Choose **deterministic graders where possible, LLM graders where necessary, human graders judiciously.** Full guidance: `references/grader-design.md`.

- **Grade the outcome, not the path.** Don't assert an exact tool-call sequence — too brittle, punishes valid creativity. Check the final state. (A booking agent passes if the reservation exists in the DB, not because it said "booked".)
- **Code graders:** string/regex/fuzzy match, fail-to-pass + pass-to-pass binary tests, static analysis (lint/type/security), outcome verification. Fast, cheap, objective, reproducible.
- **LLM-as-judge:** rubric scoring, natural-language assertions, pairwise, reference-based. Flexible, handles open-ended output. Must be **calibrated against human experts**. Give it an out ("return Unknown if insufficient info") to avoid hallucination. Use **structured rubrics, one isolated judge per dimension**, not one judge for everything.
- **Partial credit** for multi-component tasks.
- Make graders resistant to bypasses/hacks — this is how the no-faking rule is enforced.

## Step 6 — Read the transcripts (do not skip)

- You won't know your graders work until you read transcripts + grades across many trials.
- When a task fails, the transcript tells you whether the **agent** erred or the **grader** wrongly rejected a valid solution.
- **Failures should seem fair.** If grading is unfair, tasks ambiguous, or valid solutions penalized → revise the eval, not the code.
- Rule: do not take an eval score at face value until someone has read some transcripts.

## Step 7 — Use the right metric

- **pass@k** — probability of ≥1 success in k attempts. Use where **one success matters** (e.g. a tool that just needs to work once).
- **pass^k** — probability **all** k trials succeed. Use where **consistency is essential** (agents users rely on every time). Note: 75% per-trial over 3 trials = (0.75)³ ≈ 42% pass^3.
- Also track for free: latency, token usage, cost/task, error rate on a static task bank.

## Step 8 — Graduate and maintain

- **Eval-driven development:** write capability evals that define a planned behavior *before* the agent can do it, then iterate until it passes. Low starting pass rates make progress visible.
- When a capability eval reaches a high pass rate, **graduate it to the regression suite** — run continuously to catch drift. "Can we do this at all?" becomes "Can we still do this reliably?"
- Watch for **saturation**: an eval at 100% tracks regressions but gives no improvement signal — add harder tasks.
- An eval suite is a living artifact. Treat owning/iterating evals as routine as unit tests.

## How this gates the other skills

- **autonomous-build** runs this loop as its self-test/repair net (repair bounded at 3).
- **dogfood-loop** must not promote a feature past its current rung until the relevant capability evals pass and the regression suite stays green.
- **dogfood friction** flows back here as new tasks so nothing regresses.

## Anti-Patterns

- Waiting for a perfect suite before writing any eval.
- Grading the path (exact tool-call order) instead of the outcome.
- Shared state between trials (flaky, correlated failures).
- Trusting an LLM judge without calibrating it against human verdicts.
- Taking eval scores at face value without reading transcripts.
- "Fixing" a failing eval by weakening the grader — that is faking results (constitution §2).
- One-sided suites that only test the positive case.

## Hand-off

Report: tasks count, pass@k / pass^k, what's in the regression suite, any unfair-grader findings, and whether the gate for the next `dogfood-loop` rung is met. Return to `autonomous-dev`.

## References, Scripts & Templates

- `references/grader-design.md` — choosing and calibrating graders; deterministic vs. LLM-as-judge in depth.
- `scripts/run_evals.py` — runnable harness skeleton: clean-room trials, pluggable graders, pass@k / pass^k.
- `templates/eval-task.yaml` — the per-task definition (inputs, success criteria, reference solution, graders).
