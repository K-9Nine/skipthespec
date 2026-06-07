<div align="center">

# 🚀 Skip the Spec

### Build software the way Anthropic does — *skip the PRD, ship the prototype, let the data decide.*

**A set of [Claude Code](https://www.claude.com/product/claude-code) skills that hands the dev lifecycle to the AI under a safety‑bounded constitution: prototype‑first decisions, internal dogfooding as the spec, autonomous build + test, and automated eval loops.**

[![Claude Code](https://img.shields.io/badge/Claude_Code-Skills-D97757?logo=anthropic&logoColor=white)](https://www.claude.com/product/claude-code)
[![Agent Skills](https://img.shields.io/badge/Agent_Skills-spec_valid-22c55e)](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#-contributing)
![Skills](https://img.shields.io/badge/skills-5-8b5cf6)

⭐ **If this changes how you build with AI, star the repo — it’s the fastest way to help others find it.**

</div>

---

## 💡 What is this?

Anthropic doesn’t write a dense PRD and then build to it. Their Claude Code team **builds a working prototype first, ships it internally the same day, watches real usage, and lets the data choose the roadmap** — while Claude now authors **80%+ of merged production code** behind an automated reviewer.

**Skip the Spec** turns that playbook into five composable Claude Code skills you can drop into any repo. You give the high‑level goal and the boundaries; Claude plans, writes, tests, evaluates, and ships behind a flag — and a built‑in **Autonomous Developer Constitution** keeps you in the loop at every decision boundary: a priority hierarchy Claude carries through every choice, deterministic graders that can't be talked into passing, and human sign‑off on the calls that matter.

> No PRDs. Prototypes are the spec. Usage data is the roadmap. Evals are the safety net. You hold the kill switch.

## ✨ Highlights

- 🧭 **One router skill** loads everything and enforces a strict priority order: **Safety → Corrigibility → Velocity → Quality**.
- ⚡ **Skip the spec, not the thinking** — a reasonable‑assumption protocol replaces requirements docs with shippable prototypes.
- 🐕 **Dogfood loop** — staged feature‑flag rollout (dev → internal → beta → cohort → default‑on) with a data‑driven *promote / iterate / kill* rule.
- 🤖 **High AI autonomy, hard honesty rules** — Claude drives execution but can never fake a green test, hide reasoning, or resist a human override.
- 🧪 **Runnable eval harness** — Anthropic’s evals method in code: tasks from real failures, deterministic + LLM‑judge graders, `pass@k` / `pass^k`, *read the transcripts*.
- 🔀 **On/off mode switch** — isolate this set so it never collides with your PRD‑led skills.
- ✅ **Spec‑valid** — all five skills pass the [agentskills.io](https://agentskills.io) validator.

## ⏱️ Install in one command

Run inside any project repo where you want the skill set (installs at **project scope**, so it stays isolated):

```bash
STS="$(mktemp -d)" && git clone --depth 1 https://github.com/K-9Nine/skipthespec.git "$STS" \
  && mkdir -p .claude/skills .claude/commands \
  && cp -r "$STS"/{autonomous-dev,prototype-first,dogfood-loop,autonomous-build,eval-loops} .claude/skills/ \
  && cp "$STS"/.claude/commands/*.md .claude/commands/ \
  && cp "$STS"/install/skipthespec-mode.sh .claude/ && chmod +x .claude/skipthespec-mode.sh \
  && rm -rf "$STS"
```

Then in Claude Code:

```text
/skipthespec-mode on        # make this the primary skill set (suppress PRD-led skills)
/skipthespec-install        # re-install / update in any repo, anytime
```

…and describe a goal — e.g. *“Let users preview Excel/CSV files inline.”* Claude loads `autonomous-dev` and runs the loop. See **[KICKOFF-PROMPT.md](KICKOFF-PROMPT.md)** for a fill‑in‑the‑blanks first run.

## 🧩 The five skills

| Skill | Principle | What it does |
|---|---|---|
| 🧭 **autonomous-dev** | Governance | Router. Loads the **Constitution**, routes to the right phase, enforces the priority hierarchy. **Load first.** |
| ⚡ **prototype-first** | Skip the Spec | Goal → working, shippable prototype via a reasonable‑assumption protocol. No PRD. |
| 🐕 **dogfood-loop** | Dogfooding | Ship behind a flag to staff/beta users; turn usage + feedback into the spec; promote / iterate / kill. |
| 🤖 **autonomous-build** | AI Autonomy | Claude plans, writes, tests, self‑reviews, optimizes — under honesty rules + instant corrigibility. |
| 🧪 **eval-loops** | Automated Evals | Build/run the eval harness; deterministic + LLM graders; `pass@k`/`pass^k`; regression graduation. |

## 🔁 How it flows

```
                 autonomous-dev  (router + constitution)
                          │ routes to
   prototype-first → autonomous-build → eval-loops (net) → dogfood-loop → decision
          ▲                                                                  │
          └────────────────── iterate on real usage data ◄──────────────────┘
```

A normal feature touches all four phases: **prototype → build (evals run as the net) → dogfood → promote / iterate / kill.**

## 📜 The Autonomous Developer Constitution

High AI autonomy only works with hard boundaries. Every skill inherits one constitution ([`autonomous-dev/references/constitution.md`](autonomous-dev/references/constitution.md)):

| # | Priority | Core metric |
|---|---|---|
| 1 | **System Safety** | Total adherence to Hard Constraints; zero infrastructure risk |
| 2 | **Corrigibility** | Instant compliance with human halt / rollback / pivot |
| 3 | **Velocity** | Rapid prototyping, immediate shipping, automated loops |
| 4 | **Code Quality** | Clean, honest, maintainable architecture |

- **Humans own** the vision, the boundaries, and the final “did it work” verdict.
- **Claude owns** planning, writing, testing, optimizing, and sub‑experiments — *inside* those boundaries.
- **Bright lines** (never crossed, even on request): malicious artifacts, infrastructure sabotage, covert execution, circumventing org/security/legal controls.

## 🔀 Isolating it from your PRD‑led skills

Claude Code has no native “use only this set” switch, so isolation comes from two layers:

1. **Project scope** — installed in `.claude/skills/`, so PRD‑led repos never see these skills. This is the real isolation.
2. **Mode flag** — `/skipthespec-mode on` writes a `CLAUDE.md` directive telling Claude to use *only* these five skills and ignore PRD‑led ones; `/skipthespec-mode off` removes it. It's a **soft, session‑start nudge**, not a hard runtime lock — Claude reads `CLAUDE.md` when a session begins, so start a fresh session for it to take hold. Idempotent, and it preserves the rest of your `CLAUDE.md`.

## 🧪 Try the eval harness now

Zero dependencies — two example tasks (one positive, one negative) ship ready to run:

```bash
python3 eval-loops/scripts/run_evals.py --tasks eval-loops/demo_tasks --k 5 --out ./eval_runs
python3 -m unittest discover -s eval-loops/tests      # the harness's own self-test
```

The harness runs **k isolated, clean‑room trials per task**, applies deterministic + LLM‑judge graders, reports `pass@k` / `pass^k`, and saves transcripts — because you don’t trust a score you haven’t read. JSON tasks need nothing installed; for YAML task files, `pip install -r eval-loops/requirements.txt`. The provenance‑stamped `report.json` also carries class balance, errored trials, and judge abstentions. Task format: [`eval-loops/templates/eval-task.yaml`](eval-loops/templates/eval-task.yaml).

> ⚠ Grader `check` strings run through a restricted evaluator (no attribute access, no arbitrary calls), so a task file can't execute code — but a *trial* runs your agent with full privileges. **Clean‑room is not a sandbox:** run task packs you didn't author inside a container with no credentials and egress disabled.

Want it wired to a real model? **[`eval-loops/examples/run_with_claude.py`](eval-loops/examples/run_with_claude.py)** runs the harness against a live Claude agent + a small/fast **calibrated** judge. A GitHub Action ([`.github/workflows/evals-selftest.yml`](.github/workflows/evals-selftest.yml)) runs the harness self-test on every PR.

## 📚 Built from primary sources

- Anthropic — *[prototype‑first product process](https://www.anthropic.com/engineering)* (Claude Code team): idea → prototype → internal launch → watch → data‑driven prioritization.
- Anthropic — *[Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)*: progressive disclosure, evaluation‑first, think from Claude’s perspective.
- Anthropic — *[Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)*: tasks from real failures, deterministic + LLM‑judge graders, grade outcomes not paths, `pass@k` vs `pass^k`, read the transcripts.
- Reporting that **Claude authors 80%+ of merged code** at Anthropic with an automated reviewer gating every change.

## 🗺️ Repo layout

```
skipthespec/
├── autonomous-dev/      # router + constitution (load first)
├── prototype-first/     # skip the spec → shippable prototype
├── dogfood-loop/        # flagged rollout + data-driven decision
├── autonomous-build/    # Claude drives plan→write→test→review
├── eval-loops/          # runnable eval harness + graders
├── .claude/commands/    # /skipthespec-install, /skipthespec-mode
├── install/             # mode toggle script
└── KICKOFF-PROMPT.md     # paste-and-go first cycle
```

## 🧭 When (not) to use it

Reach for it on **greenfield, low-stakes, reversible** work — internal tools, new features behind a flag, prototypes. Stay **spec-first** for production-critical or regulated paths (billing, payments, auth, PII, compliance) and hard-to-reverse changes (schema migrations, public APIs, data deletion). The constitution ranks Velocity above Quality *on purpose*; that's the right call for discovery and the wrong call when a mistake is expensive. `autonomous-dev` spells out the boundary.

## 🤝 Contributing

Issues and PRs welcome — new skills, better graders, real‑world eval task packs, or workflow refinements. If you ship something with it, open a Discussion and tell us how it went.

## ⭐ Like it?

Star the repo and share it with someone drowning in PRDs. That’s the whole ask.

## 📄 License

[MIT](LICENSE) © K9
