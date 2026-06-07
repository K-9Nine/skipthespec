# Feedback Synthesis — turning usage + feedback into a defensible decision

The point of dogfooding is to replace the PRD with evidence. This file is how you keep that evidence honest.

## 1. Separate the two streams, then combine them

- **Quantitative (what happened):** adoption = invoked / eligible users; helpfulness = success / invoked; plus the rollback metric. These are not debatable.
- **Qualitative (why it happened):** verbatim friction quotes, bug reports, "I expected X but got Y." These explain the numbers.

A promote decision needs both: a number that cleared the bar **and** an explanation that the number isn't an artifact (e.g. one power user inflating it).

## 2. The decision rule, made concrete

Set the thresholds in `PROTOTYPE.md` up front so you can't move the goalposts after seeing data.

- **Promote** when adoption ≥ target AND helpfulness ≥ target AND no unresolved high-severity friction.
- **Iterate** when adoption is healthy but helpfulness lags (people try it, it doesn't deliver) — the assumptions about the *solution* are wrong.
- **Iterate** when adoption is low but helpfulness is high among the few who used it (discovery/positioning problem, not a value problem).
- **Kill** when the rollback metric trips, or when adoption AND helpfulness are both low after a fair window.

## 3. Guard against the classic biases

- **Vocal-minority bias.** One enthusiastic teammate ≠ adoption. Weight by the distribution, not the loudest voice.
- **Novelty spike.** Day-1 usage is inflated. Look at day-2/day-7 retention before promoting.
- **Survivorship.** People who hit a wall and left don't file feedback. Low completion with low feedback is a red flag, not silence-as-consent.
- **Goalpost drift.** If you find yourself redefining "success" after seeing the numbers, stop — that's opinion sneaking back in.

## 4. Every recurring failure becomes an eval task

This is how dogfood data hardens the product instead of evaporating:
- Cluster the friction reports. Any failure that appears more than once, or any high-severity one-off, gets written as a task for `eval-loops`.
- A good eval task from feedback: a concrete input + the correct outcome two people would agree on. ("When previewing a TSV with a BOM header, the first column must not be mangled.")
- Hand the cluster to `eval-loops` so the fix is verified and protected from regression before you widen the rollout.

## 5. Write the recommendation, not the decision

You produce: the numbers, the synthesis, and a recommendation (promote/iterate/kill with reasoning). The human renders the final verdict on ultimate success and on default-on (constitution §3). Make the recommendation falsifiable — state what evidence would change it.
