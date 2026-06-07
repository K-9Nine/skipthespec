#!/usr/bin/env python3
"""
run_evals.py — minimal, dependency-free evaluation harness skeleton.

Implements the core of Anthropic's evals method so Claude can run an automated
test/eval loop autonomously:

  - load tasks (YAML/JSON) from a directory
  - run k isolated trials per task in a CLEAN-ROOM temp dir (no shared state)
  - apply pluggable graders (deterministic + LLM-as-judge stub)
  - report pass@k and pass^k, plus latency/cost placeholders
  - persist transcripts so a human can READ THE TRANSCRIPTS

This is a SKELETON. Wire `run_agent()` to your real agent harness and
`llm_judge()` to your model. Keep each trial isolated. Do not weaken a grader
to make a build pass — fix the code (constitution §2: no faking results).

Usage:
    python run_evals.py --tasks ./tasks --k 5 --out ./eval_runs
"""
from __future__ import annotations
import argparse, json, math, os, shutil, sys, tempfile, time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable

# ---- optional YAML support (falls back to JSON-only if PyYAML absent) -------
try:
    import yaml  # type: ignore
    def _load_task_file(p: Path) -> dict:
        return yaml.safe_load(p.read_text())
except Exception:  # pragma: no cover
    def _load_task_file(p: Path) -> dict:
        if p.suffix.lower() in (".yaml", ".yml"):
            raise RuntimeError(f"PyYAML not installed; cannot read {p}. Use JSON or `pip install pyyaml`.")
        return json.loads(p.read_text())


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class Task:
    id: str
    input: dict
    success_criteria: str = ""
    expectation: str = "positive"           # positive | negative
    graders: list[dict] = field(default_factory=list)
    metric: str = "pass@k"                   # pass@k | pass^k
    k: int = 5
    raw: dict = field(default_factory=dict)


@dataclass
class TrialResult:
    task_id: str
    trial: int
    passed: bool
    grades: list[dict]
    transcript_path: str
    latency_s: float
    cost_usd: float = 0.0


# --------------------------------------------------------------------------- #
# Agent harness hook — REPLACE with your real agent.
# Must behave roughly like production and run inside the clean-room `workdir`.
# Returns an "outcome" dict (the final environment state) + a transcript.
# --------------------------------------------------------------------------- #
def run_agent(task: Task, workdir: Path) -> dict:
    """STUB. Replace with a call into your real agent/scaffold.

    Return shape:
        {"outcome": {...arbitrary final-state fields...},
         "transcript": "full text record of the trial"}
    """
    # Demo behavior so the harness runs end-to-end out of the box.
    outcome = {"rendered_table": {"headers": ["id"]}, "download_events": 0,
               "lint_pass": True, "type_pass": True}
    transcript = f"[demo] task={task.id} produced outcome={outcome}"
    return {"outcome": outcome, "transcript": transcript}


# --------------------------------------------------------------------------- #
# Graders. Deterministic first; LLM-as-judge only where nuance is needed.
# Grade the OUTCOME, not the path.
# --------------------------------------------------------------------------- #
def grade_outcome(spec: dict, outcome: dict) -> dict:
    """Evaluate a boolean Python expression against the outcome dict.

    The expression is evaluated with `outcome` keys exposed as locals. This is a
    skeleton; in production prefer explicit comparators over eval() for safety.
    """
    expr = spec.get("check", "True")
    try:
        passed = bool(eval(expr, {"__builtins__": {}}, dict(outcome)))  # noqa: S307 (skeleton)
    except Exception as e:
        return {"type": "outcome", "check": expr, "passed": False, "error": str(e)}
    return {"type": "outcome", "check": expr, "passed": passed}


def grade_static(spec: dict, outcome: dict) -> dict:
    expr = spec.get("check", "True")
    try:
        passed = bool(eval(expr, {"__builtins__": {}}, dict(outcome)))  # noqa: S307
    except Exception as e:
        return {"type": "static", "check": expr, "passed": False, "error": str(e)}
    return {"type": "static", "check": expr, "passed": passed}


def llm_judge(spec: dict, outcome: dict, transcript: str) -> dict:
    """STUB LLM-as-judge. Replace with a real model call.

    Rules baked in by contract (see references/grader-design.md):
      - one dimension per judge
      - give it an out: may return "Unknown"
      - must be calibrated against human verdicts before trusted
    """
    # Demo: pass unless rubric clearly unmet. Replace with model call returning
    # {"verdict": "pass"|"fail"|"unknown", "reason": "..."}.
    verdict = "pass"
    return {"type": "llm_judge", "dimension": spec.get("dimension", "quality"),
            "verdict": verdict, "passed": verdict == "pass",
            "calibrated": bool(spec.get("calibrated_against_human"))}


GRADERS: dict[str, Callable[..., dict]] = {
    "outcome": grade_outcome,
    "static": grade_static,
    "llm_judge": llm_judge,
}


def apply_graders(task: Task, outcome: dict, transcript: str) -> list[dict]:
    grades: list[dict] = []
    for spec in task.graders:
        gtype = spec.get("type")
        fn = GRADERS.get(gtype)
        if fn is None:
            grades.append({"type": gtype, "passed": False, "error": "unknown grader type"})
            continue
        grades.append(fn(spec, outcome, transcript) if gtype == "llm_judge" else fn(spec, outcome))
    return grades


def trial_passed(grades: list[dict]) -> bool:
    # All graders must pass. (Add partial-credit logic here for multi-component tasks.)
    return all(g.get("passed") for g in grades) and len(grades) > 0


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def pass_at_k(successes: int) -> float:
    """≥1 success across the trials -> 1.0 else 0.0 (empirical pass@k for this task)."""
    return 1.0 if successes >= 1 else 0.0

def pass_pow_k(successes: int, k: int) -> float:
    """All k trials succeeded -> 1.0 else 0.0 (empirical pass^k for this task)."""
    return 1.0 if successes == k else 0.0

def per_trial_rate(successes: int, k: int) -> float:
    return successes / k if k else 0.0


# --------------------------------------------------------------------------- #
# Runner — isolated clean-room per trial
# --------------------------------------------------------------------------- #
def run_task(task: Task, k: int, out_dir: Path) -> dict:
    results: list[TrialResult] = []
    for i in range(k):
        # Clean-room: fresh temp dir per trial. No shared state between trials.
        workdir = Path(tempfile.mkdtemp(prefix=f"eval_{task.id}_{i}_"))
        t0 = time.time()
        try:
            run = run_agent(task, workdir)
            outcome, transcript = run["outcome"], run["transcript"]
            grades = apply_graders(task, outcome, transcript)
            passed = trial_passed(grades)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        latency = time.time() - t0

        tdir = out_dir / task.id
        tdir.mkdir(parents=True, exist_ok=True)
        tpath = tdir / f"trial_{i}.txt"
        tpath.write_text(transcript)  # READ THE TRANSCRIPTS

        results.append(TrialResult(task.id, i, passed, grades, str(tpath), latency))

    successes = sum(1 for r in results if r.passed)
    summary = {
        "task_id": task.id,
        "k": k,
        "successes": successes,
        "per_trial_rate": round(per_trial_rate(successes, k), 4),
        "pass@k": pass_at_k(successes),
        "pass^k": pass_pow_k(successes, k),
        "reported_metric": task.metric,
        "avg_latency_s": round(sum(r.latency_s for r in results) / k, 4) if k else 0,
        "total_cost_usd": round(sum(r.cost_usd for r in results), 4),
        "trials": [asdict(r) for r in results],
    }
    return summary


def load_tasks(tasks_dir: Path) -> list[Task]:
    tasks: list[Task] = []
    for p in sorted(list(tasks_dir.glob("*.yaml")) + list(tasks_dir.glob("*.yml")) + list(tasks_dir.glob("*.json"))):
        d = _load_task_file(p)
        tasks.append(Task(
            id=d.get("id", p.stem),
            input=d.get("input", {}),
            success_criteria=d.get("success_criteria", ""),
            expectation=d.get("expectation", "positive"),
            graders=d.get("graders", []),
            metric=d.get("metric", "pass@k"),
            k=int(d.get("k", 5)),
            raw=d,
        ))
    return tasks


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Minimal eval harness (Anthropic evals method).")
    ap.add_argument("--tasks", default="./tasks", help="directory of task files (yaml/json)")
    ap.add_argument("--k", type=int, default=None, help="override trials per task")
    ap.add_argument("--out", default="./eval_runs", help="output dir for transcripts + report")
    args = ap.parse_args(argv)

    tasks_dir = Path(args.tasks)
    if not tasks_dir.exists():
        print(f"No tasks dir at {tasks_dir}", file=sys.stderr)
        return 2
    out_dir = Path(args.out) / time.strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    tasks = load_tasks(tasks_dir)
    if not tasks:
        print(f"No tasks found in {tasks_dir}", file=sys.stderr)
        return 2

    summaries = [run_task(t, args.k or t.k, out_dir) for t in tasks]

    report = {
        "n_tasks": len(summaries),
        "suite_pass@k_mean": round(sum(s["pass@k"] for s in summaries) / len(summaries), 4),
        "suite_pass^k_mean": round(sum(s["pass^k"] for s in summaries) / len(summaries), 4),
        "tasks": summaries,
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=2))

    print(f"\nEval report → {out_dir/'report.json'}")
    print(f"  tasks: {report['n_tasks']}")
    print(f"  suite pass@k (mean): {report['suite_pass@k_mean']}")
    print(f"  suite pass^k (mean): {report['suite_pass^k_mean']}")
    for s in summaries:
        flag = "" if s[s["reported_metric"]] == 1.0 else "  <-- below bar"
        print(f"   - {s['task_id']:<28} per-trial={s['per_trial_rate']:.2f} "
              f"pass@k={s['pass@k']:.0f} pass^k={s['pass^k']:.0f} ({s['reported_metric']}){flag}")
    print("\nNow READ THE TRANSCRIPTS in", out_dir, "- do not trust scores you haven't inspected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
