#!/usr/bin/env python3
"""
run_with_claude.py — wire the eval harness to a REAL Claude agent + a calibrated
LLM judge. This is the turnkey counterpart to the stubs in ../scripts/run_evals.py.

What it shows, end to end:
  - `run_agent()`  → a real Claude call. The example agent is a query router: given
    a message, it decides whether answering correctly needs a web search, and answers
    directly when it doesn't. The graded OUTCOME is its decision + answer (grade the
    outcome, not the path).
  - `llm_judge()`  → a real Claude call used as a one-dimension grader that returns
    pass / fail / unknown + a reason, via strict tool use (structured output).
  - `calibrate_judge()` → checks the judge against human-labelled verdicts BEFORE you
    trust it, per references/grader-design.md ("an uncalibrated judge is a guess with
    a confident voice").

It overrides the two stub hooks in run_evals and then runs the normal harness, so you
get the same clean-room trials, pass@k / pass^k, provenance, and transcripts.

Models (override via env):
  - agent  → STS_MODEL        (default claude-opus-4-8 — the capable model)
  - judge  → STS_JUDGE_MODEL  (default claude-haiku-4-5 — small/fast grader)

Run:
  pip install -r requirements.txt
  export ANTHROPIC_API_KEY=...
  python run_with_claude.py --calibrate --k 3
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Import the harness from ../scripts without installing anything.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "scripts"))
import run_evals  # noqa: E402

AGENT_MODEL = os.environ.get("STS_MODEL", "claude-opus-4-8")
JUDGE_MODEL = os.environ.get("STS_JUDGE_MODEL", "claude-haiku-4-5")


# --------------------------------------------------------------------------- #
# Anthropic client (imported lazily so this file is importable/--help-able
# even when the `anthropic` package isn't installed).
# --------------------------------------------------------------------------- #
def _client() -> Any:
    try:
        import anthropic  # noqa: PLC0415
    except ImportError as e:
        raise SystemExit(
            "The `anthropic` package is required for this example.\n"
            "  pip install -r requirements.txt"
        ) from e
    # Resolves ANTHROPIC_API_KEY from the environment.
    return anthropic.Anthropic()


def _tool_input(message: Any, tool_name: str) -> dict:
    """Pull the (validated) input of a forced tool call out of a response."""
    for block in message.content:
        if block.type == "tool_use" and block.name == tool_name:
            return dict(block.input)
    raise RuntimeError(f"model did not call {tool_name!r}")


# --------------------------------------------------------------------------- #
# The agent: a query router. Outcome = its decision + direct answer.
# --------------------------------------------------------------------------- #
ROUTER_SYSTEM = (
    "You are a query router. Decide whether answering the user's message correctly "
    "requires an up-to-date web search — true for recent events, current prices/news, "
    "or version-specific facts; false for greetings, chit-chat, and stable general "
    "knowledge. When no search is needed, answer the message directly. Always respond "
    "by calling the `respond` tool."
)

RESPOND_TOOL = {
    "name": "respond",
    "description": "Return the routing decision and a direct answer.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "needs_search": {
                "type": "boolean",
                "description": "True if answering correctly needs an up-to-date web search.",
            },
            "answer": {
                "type": "string",
                "description": "The direct answer when needs_search is false; empty string otherwise.",
            },
        },
        "required": ["needs_search", "answer"],
        "additionalProperties": False,
    },
}


def claude_run_agent(task: run_evals.Task, workdir: Path) -> dict:
    """Real agent. Replaces run_evals.run_agent. Raises on API failure so the harness
    records the trial as errored (rather than silently passing)."""
    client = _client()
    prompt = task.input.get("prompt", "")
    msg = client.messages.create(
        model=AGENT_MODEL,
        max_tokens=1024,
        system=ROUTER_SYSTEM,
        tools=[RESPOND_TOOL],
        tool_choice={"type": "tool", "name": "respond"},
        messages=[{"role": "user", "content": prompt}],
    )
    decision = _tool_input(msg, "respond")
    outcome = {
        "search_triggered": bool(decision["needs_search"]),
        "answer": decision.get("answer", ""),
    }
    transcript = (
        f"agent_model={AGENT_MODEL}\n"
        f"prompt={prompt!r}\n"
        f"decision={json.dumps(decision)}\n"
        f"request_id={getattr(msg, '_request_id', None)}"
    )
    return {"outcome": outcome, "transcript": transcript}


# --------------------------------------------------------------------------- #
# The judge: one dimension, pass/fail/unknown + reason, via strict tool use.
# --------------------------------------------------------------------------- #
JUDGE_SYSTEM = (
    "You are a strict, fair grader. Grade ONLY the single dimension described, against "
    "the rubric. Judge the evidence in the provided outcome and transcript — never trust "
    "a claim the output makes about itself. If the information given is insufficient to "
    "decide, return verdict 'unknown'. Record your verdict with the `record_verdict` tool."
)

VERDICT_TOOL = {
    "name": "record_verdict",
    "description": "Record the grading verdict for one dimension.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": ["pass", "fail", "unknown"]},
            "reason": {"type": "string", "description": "One sentence justifying the verdict."},
        },
        "required": ["verdict", "reason"],
        "additionalProperties": False,
    },
}


def _judge_prompt(dimension: str, rubric: str, outcome: dict, transcript: str) -> str:
    return (
        f"Dimension to grade: {dimension}\n"
        f"Rubric: {rubric}\n\n"
        f"Outcome (final state):\n{json.dumps(outcome, indent=2)}\n\n"
        f"Transcript:\n{transcript}"
    )


def claude_llm_judge(spec: dict, outcome: dict, transcript: str) -> dict:
    """Real LLM-as-judge. Replaces run_evals.llm_judge. A transient API failure
    becomes verdict='unknown' (surfaced as needs_review) rather than a hard fail."""
    dimension = spec.get("dimension", "quality")
    rubric = spec.get("rubric", "")
    try:
        client = _client()
        msg = client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=512,
            system=JUDGE_SYSTEM,
            tools=[VERDICT_TOOL],
            tool_choice={"type": "tool", "name": "record_verdict"},
            messages=[{"role": "user", "content": _judge_prompt(dimension, rubric, outcome, transcript)}],
        )
        data = _tool_input(msg, "record_verdict")
        verdict = str(data.get("verdict", "unknown")).lower()
        reason = data.get("reason", "")
    except Exception as e:  # noqa: BLE001 — abstain on any judge failure, don't fake a pass
        verdict, reason = "unknown", f"judge error: {type(e).__name__}: {e}"
    return {
        "type": "llm_judge",
        "dimension": dimension,
        "verdict": verdict,
        "passed": verdict == "pass",
        "unknown": verdict == "unknown",
        "reason": reason,
        "calibrated": bool(spec.get("calibrated_against_human")),
    }


# --------------------------------------------------------------------------- #
# Calibration: do not trust the judge until it agrees with humans.
# Each entry is a trial we already know the right verdict for.
# --------------------------------------------------------------------------- #
_GREETING_RUBRIC = (
    "Does `answer` politely respond to the user's greeting without asking for "
    "clarification? Return 'unknown' if there is no answer text to judge."
)

CALIBRATION_SET = [
    {
        "dimension": "greeting_answer",
        "rubric": _GREETING_RUBRIC,
        "outcome": {"search_triggered": False, "answer": "Good morning! How can I help you today?"},
        "transcript": "prompt='Good morning!'",
        "human": "pass",
    },
    {
        "dimension": "greeting_answer",
        "rubric": _GREETING_RUBRIC,
        "outcome": {"search_triggered": False, "answer": "Hi there — hope you're having a great day!"},
        "transcript": "prompt='hello'",
        "human": "pass",
    },
    {
        "dimension": "greeting_answer",
        "rubric": _GREETING_RUBRIC,
        "outcome": {"search_triggered": False, "answer": "I can only help with technical questions."},
        "transcript": "prompt='good afternoon'",
        "human": "fail",
    },
    {
        "dimension": "greeting_answer",
        "rubric": _GREETING_RUBRIC,
        "outcome": {"search_triggered": False, "answer": ""},
        "transcript": "prompt='hey'",
        "human": "unknown",
    },
]


def calibrate_judge(threshold: float = 0.75) -> float:
    """Run the judge on the labelled set, report agreement, warn if it's too low."""
    print(f"\nCalibrating judge ({JUDGE_MODEL}) against {len(CALIBRATION_SET)} human-labelled trials:")
    agree = 0
    for ex in CALIBRATION_SET:
        g = claude_llm_judge({"dimension": ex["dimension"], "rubric": ex["rubric"]}, ex["outcome"], ex["transcript"])
        ok = g["verdict"] == ex["human"]
        agree += ok
        mark = "✓" if ok else "✗"
        print(f"  {mark} human={ex['human']:<8} judge={g['verdict']:<8} {('' if ok else '<- disagreement: ' + g['reason'])}")
    rate = agree / len(CALIBRATION_SET)
    print(f"  agreement: {agree}/{len(CALIBRATION_SET)} = {rate:.0%}")
    if rate < threshold:
        print(f"  ⚠ below {threshold:.0%} — sharpen the rubric or the labelled set before trusting this judge.")
    else:
        print("  ✓ calibrated — safe to use this judge for these tasks.")
    return rate


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the eval harness against a real Claude agent + judge.")
    ap.add_argument("--tasks", default=str(_HERE / "example_tasks"), help="task directory")
    ap.add_argument("--k", type=int, default=3, help="trials per task")
    ap.add_argument("--timeout", type=float, default=120.0, help="per-trial timeout (s)")
    ap.add_argument("--out", default=str(_HERE / "eval_runs"), help="output dir")
    ap.add_argument("--calibrate", action="store_true", help="calibrate the judge before running")
    args = ap.parse_args(argv)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY to run this example.", file=sys.stderr)
        return 2

    # Record which models produced the run in report.json provenance.
    os.environ.setdefault("STS_MODEL", AGENT_MODEL)
    os.environ.setdefault("STS_AGENT_VERSION", f"judge={JUDGE_MODEL}")

    if args.calibrate:
        calibrate_judge()

    # Swap the stubs for the real thing, then run the ordinary harness.
    run_evals.run_agent = claude_run_agent
    run_evals.GRADERS["llm_judge"] = claude_llm_judge

    print(f"\nRunning suite with agent={AGENT_MODEL}, judge={JUDGE_MODEL} ...")
    return run_evals.main(
        ["--tasks", args.tasks, "--k", str(args.k), "--timeout", str(args.timeout), "--out", args.out]
    )


if __name__ == "__main__":
    raise SystemExit(main())
