# Signal Design for Prototypes

A prototype exists to produce signal. Bad signal design is the most common reason a prototype-first cycle stalls: you ship, nobody can tell if it worked, and you fall back to opinion.

## The one rule

Instrument the **minimum** signal that lets you answer two questions:
1. **Did they use it?** (adoption / engagement)
2. **Did it help?** (the success metric from `PROTOTYPE.md`)

Everything else is premature instrumentation — add it only after the feature earns promotion.

## Pick signals that map to the success metric

| Success metric type | Signal to emit | Avoid |
|---|---|---|
| "People preview files instead of downloading" | count of preview opens vs. downloads per user | tracking every scroll, hover, pixel |
| "Triage is faster" | time-to-first-action; actions-per-session | vanity pageviews |
| "Fewer support tickets" | tickets tagged to the workflow, before/after | generic NPS surveys at this stage |
| "Users return" | day-2 / day-7 return rate among internal cohort | global DAU dashboards |

## Two-signal default

For most prototypes, emit exactly two events:
- `prototype.<name>.invoked` — fired when a user enters the new path.
- `prototype.<name>.completed_success` — fired when the user reaches the outcome the success metric cares about (the real outcome, not a "thank you" screen).

Adoption = invoked / eligible users. Helpfulness = completed_success / invoked. That's enough to make the promote/iterate/kill call in `dogfood-loop`.

## Qualitative signal counts too

Usage data answers "did they use it." A lightweight feedback channel answers "why / why not." Provide one friction-free way for dogfooders to react (a thumbs control, a Slack thread, an inline "this is wrong" button). Treat reported failures as future eval tasks — hand them to `eval-loops`.

## Anti-patterns

- **Analytics before users.** Don't build a metrics pipeline before anyone has touched the prototype.
- **Outcome theater.** Firing `completed_success` on a screen render rather than the real outcome inflates helpfulness and poisons the decision.
- **Twenty events.** More events = more noise = slower decision. Two good signals beat twenty mediocre ones.
- **No kill signal.** Always be able to see the rollback metric, not just the success metric.
