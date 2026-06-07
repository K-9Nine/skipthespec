---
name: prototype-first
description: "Turn a high-level product idea into a working, shippable prototype FAST — instead of writing a PRD or spec. Use when the user says 'skip the spec', 'just build a prototype', 'I have an idea', 'make something I can try', 'rough version', or hands over a one-line feature goal. Replaces detailed requirements with a reasonable-assumption protocol, a thin-slice build, and an immediate internal-ship handoff. Pairs with autonomous-build (execution), dogfood-loop (shipping + data), and eval-loops (safety net). Load autonomous-dev first for governance."
license: MIT
metadata:
  author: nathan
  version: '1.0'
---

# Prototype-First

Model: Anthropic's Claude Code team — *Idea → Prototype (skip the spec) → Internal launch → Watch & listen → Data-driven prioritization.* Code is the canvas for product discovery, not the output of a finished spec.

## When to Use This Skill

When you have a high-level goal and the instinct is to write requirements first. Don't. Build the smallest working thing that lets real users generate signal.

> Prerequisite: `autonomous-dev` loaded and `references/constitution.md` read. Honor the priority hierarchy — skipping the spec never means skipping safety.

## The Loop

```
Idea ──► Reasonable-assumption brief ──► Thinnest working slice ──► Ship internally (flag) ──► hand to dogfood-loop
                  ▲                                                                                    │
                  └──────────────────── iterate on real signal ◄──────────────────────────────────────┘
```

## Step 1 — Capture the goal in one sentence

Write the mission as a single sentence: **what** it does and **why it matters**. Not a paragraph, not a feature list.

- Good: "Let a user preview Excel/CSV/TSV files inline so they never download to inspect data."
- Bad: a 2-page requirements doc.

If the human gave you the sentence, use it. If they gave you a vague idea, compress it to one sentence and confirm in-line (don't block).

## Step 2 — Run the Reasonable-Assumption Protocol (replaces the PRD)

For every ambiguity that a PRD would normally resolve, make a **reasonable, functional assumption** and record it. Do not wait for answers. Produce a short `PROTOTYPE.md` instead of a spec:

```markdown
# Prototype: <one-sentence mission>

## Vision input (human-owned)
- Why this should exist: ...
- Boundaries / do-not-touch: ...
- Success metric: <the one number/behavior that says "promote it">
- Rollback metric: <the condition that says "kill or revert">

## Assumptions I'm making (so I don't wait on a spec)
- A1: ... (chosen because ...)
- A2: ...
(Each assumption is cheap to reverse later. Flag any that are NOT cheap to reverse.)

## Thinnest slice that produces signal
- In scope for v0: ...
- Explicitly deferred: ...
```

Rules for assumptions:
- Prefer the assumption that is **cheapest to reverse** after real usage.
- Any assumption that is expensive to reverse (schema migrations, public API shape, pricing) is **not** a prototype assumption — surface it to the human before building (epistemic autonomy, constitution §2).
- Never assume past a Hard Constraint (constitution §4).

## Step 3 — Build the thinnest slice that produces signal

The prototype's only job is to generate real usage signal. Optimize for that, not for completeness.

- **Ship rough.** Brand it as a research preview internally so users calibrate expectations. Unpolished is fine; broken-and-misleading is not.
- **Real path over fake path.** A prototype that books a fake flight teaches nothing. Make the core action actually do the thing (constitution: grade outcomes, not theater).
- **Behind a flag, never a replacement.** v0 ships behind a feature flag so it can be killed instantly (corrigibility + dogfood-loop staging).
- Hand the actual implementation to `autonomous-build` — that skill owns the plan→write→self-review loop. This skill owns *what* the slice is and *that it's shippable*.

### What "shippable prototype" means (the bar)
- The core user journey works end to end on representative data.
- It is reachable by internal users behind a flag.
- It emits at least one usage signal (see `references/signal-design.md`).
- It cannot corrupt production data or cross a Hard Constraint if it breaks.

## Step 4 — Minimal instrumentation, then ship

Add only enough instrumentation to answer "did people use it and did it help?" Premature analytics is an anti-pattern — ship to real users first, instrument the one or two signals that map to your success metric. Detailed signal design: `references/signal-design.md`.

Then hand off to **`dogfood-loop`** to ship to staff/beta customers and collect data.

## Step 5 — Iterate on signal, not opinion

When the data comes back from `dogfood-loop`:
- High usage + positive signal → recommend promotion (human decides — constitution §3).
- Low engagement or friction → return to Step 2, revise the assumptions that the data invalidated, rebuild the slice.
- The feedback and usage data are now your spec sheet. Update `PROTOTYPE.md` assumptions to record what real behavior taught you.

## Anti-Patterns

- Writing a PRD "just to be safe." If you're writing requirements instead of code, stop.
- Polishing v0. Polish is for features that earned promotion via data.
- Building the complete feature before any user touches it.
- Instrumenting twenty metrics before launch. Instrument one or two that map to the success metric.
- Faking the core action to "demo faster." A fake prototype produces fake signal.

## Hand-off

End by stating: the `PROTOTYPE.md`, the flag name, the one success metric, and "ready for dogfood-loop." Return to `autonomous-dev`.

## References

- `references/signal-design.md` — how to pick the one or two usage signals a prototype must emit, and how to avoid premature instrumentation.
