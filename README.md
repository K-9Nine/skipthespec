# Autonomous Developer — Claude Code skill set

A five-skill system that operationalizes how Anthropic builds: **prototype-first decisions,
usage data as the spec, Claude authoring the majority of code, and automated test/eval
loops** — bounded by a constitution that keeps humans in structural control.

## The five skills

| Skill | Principle it implements | Job |
|---|---|---|
| **autonomous-dev** | Overall philosophy + governance | Router. Loads the constitution, routes to the right phase, enforces the priority hierarchy. **Load this first.** |
| **prototype-first** | #1 Skip the Spec | Goal → working, shippable prototype via a reasonable-assumption protocol (no PRD). |
| **dogfood-loop** | #2 Internal Dogfooding | Ship behind a flag to staff/beta users; turn usage + feedback into the spec; promote/iterate/kill. |
| **autonomous-build** | #3 AI Autonomy | Claude plans, writes, tests, self-reviews, optimizes — under honesty rules and instant corrigibility. |
| **eval-loops** | #4 Automated test & eval | Build/run the eval harness; deterministic + LLM graders; pass@k/pass^k; regression graduation. |

The **Autonomous Developer Constitution** lives once at
`autonomous-dev/references/constitution.md` and governs all four phase skills:
priority hierarchy **Safety > Corrigibility > Velocity > Quality**, the Hard Constraints,
and the human-vs-AI decision boundaries.

## Quick install (from GitHub)

This repo IS the source. Two slash commands handle install and isolation:

```bash
# one-time, inside a project repo where you want skip-the-spec available:
git clone --depth 1 https://github.com/K-9Nine/skipthespec.git /tmp/sts \
  && mkdir -p .claude/skills .claude/commands \
  && cp -r /tmp/sts/{autonomous-dev,prototype-first,dogfood-loop,autonomous-build,eval-loops} .claude/skills/ \
  && cp /tmp/sts/.claude/commands/*.md .claude/commands/ \
  && cp /tmp/sts/install/skipthespec-mode.sh .claude/ && chmod +x .claude/skipthespec-mode.sh
```

After that first copy, the slash commands are available in Claude Code:

- **`/skipthespec-install`** — clone/pull this repo and (re)install the five skills + commands into the current project. Use it to install in new repos or update to the latest version.
- **`/skipthespec-mode on|off|status`** — toggle this set as the **primary / only** skill set. `on` writes an enforcement block into `CLAUDE.md` instructing Claude to use only these five skills and ignore PRD-led skills; `off` removes it. Start a fresh session after toggling so Claude re-reads `CLAUDE.md`.

### Isolating from your PRD-led skills (the on/off switch)

There is no native "use only this set" switch in Claude Code, so isolation is achieved two ways, both included here:

1. **Project scope.** Install into `.claude/skills/` (not `~/.claude/skills/`). PRD-led repos simply don't contain these skills, so they can never trigger there.
2. **Mode flag.** Even in a shared environment, `/skipthespec-mode on` adds a CLAUDE.md directive telling Claude this set is primary and PRD-led skills are suppressed for the session. `/skipthespec-mode off` restores normal behavior. The toggle is idempotent and preserves the rest of your CLAUDE.md.

## Manual install in Claude Code

Personal (all projects):
```bash
mkdir -p ~/.claude/skills
unzip 'autonomous-*.zip' 'prototype-first.zip' 'dogfood-loop.zip' 'eval-loops.zip' -d ~/.claude/skills/
# each zip expands to its own <skill-name>/ directory containing SKILL.md
```
Project-scoped (commit with the repo):
```bash
mkdir -p .claude/skills && unzip '*.zip' -d .claude/skills/
```
Verify Claude sees them: start Claude Code and run `/autonomous-dev` (or just describe a
build goal — the router should trigger on phrases like "build a prototype", "ship it
internally", "let Claude drive", "set up evals").

## Run the first cycle

See **KICKOFF-PROMPT.md** — paste it into Claude Code with your goal filled in to run one full
idea → prototype → build → eval → dogfood → decision loop.

## How the skills compose

```
                       autonomous-dev (router + constitution)
                                     │ routes to
        ┌───────────────┬───────────────────────┬──────────────────┐
   prototype-first → autonomous-build → eval-loops (net) → dogfood-loop → decision
        ▲                                                                  │
        └──────────────────── iterate on real usage data ◄────────────────┘
```

## Design provenance

Built directly from Anthropic primary sources:
- Prototype-first product process (Claude Code team / Catherine Wu) — idea → prototype →
  internal launch → watch → data-driven prioritization.
- "Equipping agents for the real world with Agent Skills" — progressive disclosure,
  evaluation-first, think-from-Claude's-perspective.
- "Demystifying evals for AI agents" — 20-50 tasks from real failures, deterministic +
  LLM-judge graders, grade outcomes not paths, isolated trials, pass@k vs pass^k, read the
  transcripts.
- Anthropic reporting that Claude authors 80%+ of merged code with an automated reviewer
  gating every change.

## Customize

- Put project-specific boundaries/compliance rules in your repo's `CLAUDE.md` — they extend,
  never override, the constitution's Hard Constraints.
- Wire `eval-loops/scripts/run_evals.py` `run_agent()` and `llm_judge()` to your real harness.
- All five skills validate against the agentskills.io spec.
```
```
