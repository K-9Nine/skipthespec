# Worked example — real Claude agent + calibrated judge

`../scripts/run_evals.py` ships with stubbed `run_agent()` / `llm_judge()` so it runs
with zero dependencies. This example replaces both stubs with **real Claude calls** and
wires in **judge calibration**, turning the skeleton into a turnkey harness you can adapt.

## What it does

- **Agent** (`claude_run_agent`) — a query router built on `claude-opus-4-8`. Given a
  message, it decides whether answering correctly needs a web search and answers directly
  when it doesn't. The graded **outcome** is its decision (`search_triggered`) + `answer` —
  we grade the outcome, not the tool-call path.
- **Judge** (`claude_llm_judge`) — a one-dimension grader on `claude-haiku-4-5` (small/fast)
  that returns `pass` / `fail` / `unknown` + a reason via **strict tool use** (structured
  output). An API failure becomes `unknown` (surfaced as `needs_review`), never a fake pass.
- **Calibration** (`calibrate_judge`) — runs the judge against human-labelled trials and
  reports agreement before you trust it. This is the mechanical form of grader-design.md's
  rule: *an uncalibrated judge is a guess with a confident voice.*

It then swaps the stubs into `run_evals` and runs the ordinary harness, so you keep the
clean-room trials, `pass@k` / `pass^k`, provenance, and transcripts.

## Run it

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...

# calibrate the judge, then run the example suite (positive + negative routing tasks)
python run_with_claude.py --calibrate --k 3
```

Models are overridable: `STS_MODEL` for the agent (default `claude-opus-4-8`),
`STS_JUDGE_MODEL` for the judge (default `claude-haiku-4-5`). Both are recorded in
`report.json` provenance.

## Adapt it to your project

1. Point `claude_run_agent` at *your* agent — keep the contract: return
   `{"outcome": {...final state...}, "transcript": "..."}`. Outcome fields are whatever your
   deterministic graders assert against.
2. Write tasks (JSON/YAML) whose `outcome` graders check that final state. See
   `example_tasks/` and `../templates/eval-task.yaml`.
3. Keep deterministic graders for anything you can check in code; reserve the LLM judge for
   genuinely open-ended dimensions — and recalibrate it whenever the rubric changes.
