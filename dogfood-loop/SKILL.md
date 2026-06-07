---
name: dogfood-loop
description: "Ship a prototype immediately to internal staff and beta customers behind a feature flag, instrument minimal usage signals, and turn real usage data + feedback into the de-facto spec. Use when the user says 'ship it internally', 'dogfood this', 'let users try it', 'roll it out behind a flag', or asks how to decide whether a feature graduates. Owns the staged rollout ladder and the promote/iterate/kill decision — with the final verdict reserved for the human (constitution §3). Pairs with prototype-first (what to ship) and eval-loops (quality gate). Load autonomous-dev first."
license: MIT
metadata:
  author: nathan
  version: '1.0'
---

# Dogfood Loop

Model: Anthropic's *Internal launch → watch & listen → data-driven prioritization.* Ship the prototype to everyone internally with no polish required, track usage religiously, and let real behavior — not opinion — guide the roadmap. "Dogfooding their own tool to build their own tool."

## When to Use This Skill

After `prototype-first` produces a shippable slice, or any time you need to get a flagged build in front of real users and convert their behavior into the spec.

> Prerequisite: `autonomous-dev` loaded, constitution read. The rollout ladder is also your corrigibility mechanism — every stage must be instantly killable.

## The Loop

```
flagged prototype ──► roll out one rung ──► watch usage + feedback ──► decision
                          ▲                                              │
                          │                              promote (next rung) / iterate / kill
                          └──────────── iterate: back to prototype-first ◄┘
```

## Step 1 — Confirm it's shippable, not polished

The bar is functionality, not polish (that's `prototype-first` Step 3). Confirm:
- Core journey works on representative data.
- It's behind a flag with a working kill switch.
- It emits the two signals from `references/` of prototype-first (adoption + helpfulness).
- It cannot corrupt production data or cross a Hard Constraint if it breaks.

Brand it internally as a research preview so users calibrate expectations.

## Step 2 — Roll out one rung at a time

Use the staged ladder. Each rung has an explicit gate that must pass before the next. Never jump straight to "default on."

| Stage | Audience | Gate to advance |
|---|---|---|
| 0 | Local / dev only | Works on representative data? |
| 1 | Internal staff (your whole team) | Is the new workflow clearer/faster than the old one? |
| 2 | One friendly beta customer | Are the errors and confusion acceptable? |
| 3 | Small controlled customer cohort | Are success metrics better than baseline? |
| 4 | Default on | Keep kill switch briefly, then remove the flag. |

Stage 1 (all internal staff) is the heart of dogfooding — your team uses it in real work and generates honest signal fast.

## Step 3 — Watch & listen (usage is the spec)

Collect both streams. Detail and templates: `references/feedback-synthesis.md` and `templates/rollout-log.md`.

- **Quantitative:** adoption (invoked / eligible) and helpfulness (success / invoked) from the two prototype signals. Track against the success metric and the rollback metric.
- **Qualitative:** the friction channel (Slack thread, thumbs, inline report). Capture verbatim friction, not summarized sentiment.

Record everything in a rollout log so the decision is evidence-based, not vibe-based.

## Step 4 — Make the data-driven decision

This is the core of the method. Apply the rule, then route:

| Signal pattern | Decision |
|---|---|
| High usage **and** positive helpfulness / feedback | **Promote** — advance one rung (human approves the final default-on). |
| Low engagement **or** recurring friction/complaints | **Iterate** — back to `prototype-first` Step 2; revise the assumptions the data invalidated. |
| Crosses the rollback metric, or breaks badly | **Kill** — flip the kill switch immediately, then diagnose. |

Guardrails:
- **Data over enthusiasm.** A loud advocate is not adoption. Promote on the metric, not on opinion.
- **The human owns the final verdict** on ultimate success and on default-on (constitution §3). You supply the evidence and a recommendation; you do not unilaterally make a feature the new default.
- **Every reported failure becomes an eval task.** Hand recurring failures to `eval-loops` so they can't regress.

## Step 5 — Close the loop

- Promote → re-run Step 2 at the next rung; tighten evals via `eval-loops` before widening blast radius.
- Iterate → `prototype-first` with updated assumptions.
- Kill → write a short post-mortem of what the data showed; feed lessons back to the project boundaries.

## Anti-Patterns

- **Skipping rungs.** Going from internal to default-on without a customer cohort hides failure until it's expensive.
- **Polishing before shipping.** Polish a feature that earned promotion, not a prototype seeking signal.
- **Promoting on opinion.** If you can't point to the adoption/helpfulness numbers, you're guessing.
- **No kill switch.** A rollout you can't instantly revert violates corrigibility.
- **Losing failures.** Friction that isn't logged and converted to an eval task will recur.

## Hand-off

End by stating: current rung, the adoption + helpfulness numbers, the decision (promote/iterate/kill), and the next skill (`prototype-first` to iterate, `eval-loops` to harden, or back to `autonomous-dev`).

## References & Templates

- `references/feedback-synthesis.md` — turning raw usage + feedback into a defensible decision and into eval tasks.
- `templates/rollout-log.md` — the per-rung evidence log.
