#!/usr/bin/env python3
"""
run_evals.py — minimal, dependency-free evaluation harness.

Implements the core of Anthropic's evals method so Claude can run an automated
test/eval loop autonomously:

  - load tasks (JSON out of the box; YAML if PyYAML is installed) from a directory
  - run k isolated trials per task in a CLEAN-ROOM temp dir (no shared state)
  - apply pluggable graders (deterministic + LLM-as-judge stub)
  - report pass@k and pass^k, plus class balance, errors, and judge-abstentions
  - persist transcripts + a provenance-stamped report so a run is reproducible
    and a human can READ THE TRANSCRIPTS

This is a SKELETON for the harness wiring. Replace `run_agent()` with a call into
your real agent and `llm_judge()` with a real model call. Two rules are baked in
and must not be loosened (constitution §2: no faking results):

  1. Graders never use `eval()`. Grader `check` expressions run through a
     restricted evaluator (`safe_eval`) that allows only comparisons, boolean/
     arithmetic ops, literals, indexing, and a small allow-list of functions.
     Attribute access is forbidden — that closes the classic
     `().__class__.__bases__...` sandbox escape. A malicious community task pack
     therefore cannot run arbitrary code through the grader.
  2. CLEAN-ROOM ≠ SANDBOX. Each trial gets a fresh temp dir so there is no shared
     state between trials. That is NOT a security boundary: `run_agent()` runs
     with this process's full privileges, filesystem, network, and env. If you
     run task packs you did not author, run the whole harness inside a container
     / VM with no credentials in the environment and egress disabled.

Usage:
    python run_evals.py --tasks ./tasks --k 5 --timeout 120 --out ./eval_runs
"""
from __future__ import annotations
import argparse, ast, json, operator, os, platform, shutil, subprocess, sys, tempfile, time, traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

HARNESS_VERSION = "1.1"

# ---- optional YAML support (JSON works with zero dependencies) -------------- #
try:
    import yaml  # type: ignore
    _HAVE_YAML = True
    def _load_task_file(p: Path) -> dict:
        return yaml.safe_load(p.read_text())
except Exception:  # pragma: no cover - exercised only when PyYAML is absent
    _HAVE_YAML = False
    def _load_task_file(p: Path) -> dict:
        if p.suffix.lower() in (".yaml", ".yml"):
            raise RuntimeError(
                f"PyYAML not installed; cannot read {p.name}. "
                f"Use JSON task files or `pip install pyyaml`."
            )
        return json.loads(p.read_text())


# --------------------------------------------------------------------------- #
# Safe expression evaluator for grader `check` strings.
# Allows: literals, names (resolved against the outcome dict + allow-listed
# funcs), comparisons, boolean ops, unary/binary arithmetic, indexing, and
# list/tuple/set literals. Forbids everything else — notably attribute access,
# calls to anything outside ALLOWED_FUNCS, comprehensions, and lambdas.
# --------------------------------------------------------------------------- #
class GraderExprError(ValueError):
    """Raised when a grader `check` expression is malformed or disallowed."""


ALLOWED_FUNCS: dict[str, Callable[..., Any]] = {
    "len": len, "abs": abs, "min": min, "max": max, "sum": sum,
    "all": all, "any": any, "round": round, "sorted": sorted,
    "str": str, "int": int, "float": float, "bool": bool,
}

_BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv,
    ast.Pow: operator.pow,
}
_CMP_OPS = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
    ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b,
    ast.Is: operator.is_, ast.IsNot: operator.is_not,
}
_UNARY_OPS = {
    ast.Not: operator.not_, ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def safe_eval(expr: str, names: dict[str, Any]) -> Any:
    """Evaluate a restricted boolean/arithmetic expression. No code execution."""
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise GraderExprError(f"syntax error in check: {e}") from e
    return _eval_node(tree.body, names)


def _eval_node(node: ast.AST, names: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in names:
            return names[node.id]
        raise GraderExprError(f"unknown name {node.id!r} (not an outcome field or allowed function)")
    if isinstance(node, ast.BoolOp):
        vals = (_eval_node(v, names) for v in node.values)
        if isinstance(node.op, ast.And):
            result: Any = True
            for v in vals:
                result = v
                if not v:
                    break
            return result
        result = False
        for v in vals:
            result = v
            if v:
                break
        return result
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand, names))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval_node(node.left, names), _eval_node(node.right, names))
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, names)
        for op, comp in zip(node.ops, node.comparators):
            if type(op) not in _CMP_OPS:
                raise GraderExprError(f"comparison {type(op).__name__} not allowed")
            right = _eval_node(comp, names)
            if not _CMP_OPS[type(op)](left, right):
                return False
            left = right
        return True
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        elts = [_eval_node(e, names) for e in node.elts]
        return set(elts) if isinstance(node, ast.Set) else (tuple(elts) if isinstance(node, ast.Tuple) else elts)
    if isinstance(node, ast.Subscript):
        value = _eval_node(node.value, names)
        key = _eval_node(node.slice, names)  # py3.9+: slice is the expr directly
        try:
            return value[key]
        except (KeyError, IndexError, TypeError) as e:
            raise GraderExprError(f"bad subscript {key!r}: {e}") from e
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_FUNCS:
            raise GraderExprError("only allow-listed functions may be called")
        if node.keywords:
            raise GraderExprError("keyword arguments are not allowed in checks")
        args = [_eval_node(a, names) for a in node.args]
        return ALLOWED_FUNCS[node.func.id](*args)
    # Attribute access, lambdas, comprehensions, walrus, f-strings, etc.
    raise GraderExprError(f"expression element {type(node).__name__} is not allowed in a grader check")


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
    error: str | None = None          # set if the trial crashed or timed out
    needs_review: bool = False        # set if a judge abstained ("unknown")


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
    # Demo behavior so the harness runs end-to-end out of the box. The outcome is
    # a superset that satisfies both bundled demo tasks (one positive, one negative).
    outcome = {
        "rendered_table": {"headers": ["id"]},
        "download_events": 0,
        "lint_pass": True,
        "type_pass": True,
        "search_triggered": False,
    }
    transcript = f"[demo] task={task.id} produced outcome={json.dumps(outcome)}"
    return {"outcome": outcome, "transcript": transcript}


# --------------------------------------------------------------------------- #
# Graders. Deterministic first; LLM-as-judge only where nuance is needed.
# Grade the OUTCOME, not the path.
# --------------------------------------------------------------------------- #
def grade_outcome(spec: dict, outcome: dict) -> dict:
    """Evaluate a restricted boolean expression against the outcome dict."""
    expr = spec.get("check", "True")
    names = {**ALLOWED_FUNCS, **outcome}
    try:
        passed = bool(safe_eval(expr, names))
    except GraderExprError as e:
        return {"type": "outcome", "check": expr, "passed": False, "error": str(e)}
    return {"type": "outcome", "check": expr, "passed": passed}


def grade_static(spec: dict, outcome: dict) -> dict:
    expr = spec.get("check", "True")
    names = {**ALLOWED_FUNCS, **outcome}
    try:
        passed = bool(safe_eval(expr, names))
    except GraderExprError as e:
        return {"type": "static", "check": expr, "passed": False, "error": str(e)}
    return {"type": "static", "check": expr, "passed": passed}


def llm_judge(spec: dict, outcome: dict, transcript: str) -> dict:
    """STUB LLM-as-judge. Replace with a real model call.

    Rules baked in by contract (see references/grader-design.md):
      - one dimension per judge
      - give it an out: may return "unknown" (counted separately, not as a pass)
      - must be calibrated against human verdicts before trusted
    A real implementation returns {"verdict": "pass"|"fail"|"unknown", "reason": "..."}.
    """
    verdict = "pass"  # demo default — replace with a model call
    return {
        "type": "llm_judge",
        "dimension": spec.get("dimension", "quality"),
        "verdict": verdict,
        "passed": verdict == "pass",
        "unknown": verdict == "unknown",
        "calibrated": bool(spec.get("calibrated_against_human")),
    }


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
    """All graders must pass. Graders encode the CORRECT outcome — for a negative
    task that means asserting the behavior is ABSENT. (Add partial-credit logic
    here for multi-component tasks.) An abstaining judge ("unknown") is not a pass."""
    return len(grades) > 0 and all(g.get("passed") for g in grades)


# --------------------------------------------------------------------------- #
# Metrics  (empirical, per-task — not the unbiased Chen-et-al pass@k estimator)
# --------------------------------------------------------------------------- #
def pass_at_k(successes: int) -> float:
    """≥1 success across the k trials run -> 1.0 else 0.0 (empirical pass@k)."""
    return 1.0 if successes >= 1 else 0.0

def pass_pow_k(successes: int, k: int) -> float:
    """All k trials succeeded -> 1.0 else 0.0 (empirical pass^k)."""
    return 1.0 if k > 0 and successes == k else 0.0

def per_trial_rate(successes: int, k: int) -> float:
    return successes / k if k else 0.0


# --------------------------------------------------------------------------- #
# Trial execution with timeout + crash isolation
# --------------------------------------------------------------------------- #
def _call_with_timeout(fn: Callable[..., Any], timeout: float | None, *args: Any) -> Any:
    """Run fn(*args), raising FutureTimeout if it exceeds `timeout` seconds.

    Note: a timed-out worker thread cannot be force-killed in CPython; it is
    abandoned and the harness moves on. For hard isolation, run trials in
    separate processes/containers.
    """
    if not timeout or timeout <= 0:
        return fn(*args)
    with ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(fn, *args).result(timeout=timeout)


def run_one_trial(task: Task, i: int, out_dir: Path, timeout: float | None) -> TrialResult:
    # Clean-room: fresh temp dir per trial. No shared state between trials.
    # (This isolates state, not privileges — see the module docstring.)
    workdir = Path(tempfile.mkdtemp(prefix=f"eval_{task.id}_{i}_"))
    t0 = time.time()
    error: str | None = None
    grades: list[dict] = []
    transcript = ""
    passed = False
    try:
        run = _call_with_timeout(run_agent, timeout, task, workdir)
        outcome, transcript = run["outcome"], run.get("transcript", "")
        grades = apply_graders(task, outcome, transcript)
        passed = trial_passed(grades)
    except FutureTimeout:
        error = f"timeout after {timeout}s"
        transcript = f"[ERROR] {error}\ntask={task.id} trial={i}"
    except Exception as e:  # a crashing agent must not abort the whole suite
        error = f"{type(e).__name__}: {e}"
        transcript = f"[ERROR] {error}\n\n{traceback.format_exc()}"
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    latency = time.time() - t0

    tdir = out_dir / task.id
    tdir.mkdir(parents=True, exist_ok=True)
    tpath = tdir / f"trial_{i}.txt"
    tpath.write_text(transcript)  # READ THE TRANSCRIPTS

    needs_review = any(g.get("type") == "llm_judge" and g.get("unknown") for g in grades)
    return TrialResult(task.id, i, passed, grades, str(tpath), latency,
                       error=error, needs_review=needs_review)


def run_task(task: Task, k: int, out_dir: Path, timeout: float | None) -> dict:
    results = [run_one_trial(task, i, out_dir, timeout) for i in range(k)]
    successes = sum(1 for r in results if r.passed)
    summary = {
        "task_id": task.id,
        "expectation": task.expectation,
        "k": k,
        "successes": successes,
        "errors": sum(1 for r in results if r.error),
        "judge_unknowns": sum(1 for r in results if r.needs_review),
        "per_trial_rate": round(per_trial_rate(successes, k), 4),
        "pass@k": pass_at_k(successes),
        "pass^k": pass_pow_k(successes, k),
        "reported_metric": task.metric,
        "avg_latency_s": round(sum(r.latency_s for r in results) / k, 4) if k else 0,
        "total_cost_usd": round(sum(r.cost_usd for r in results), 4),
        "trials": [asdict(r) for r in results],
    }
    return summary


# --------------------------------------------------------------------------- #
# Loading + provenance
# --------------------------------------------------------------------------- #
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


def _git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or None
    except Exception:
        return None


def build_meta(tasks: list[Task], k_override: int | None, timeout: float | None) -> dict:
    pos = sum(1 for t in tasks if t.expectation == "positive")
    neg = sum(1 for t in tasks if t.expectation == "negative")
    return {
        "harness_version": HARNESS_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "python": platform.python_version(),
        "platform": platform.system(),
        "k_override": k_override,
        "timeout_s": timeout,
        "model": os.environ.get("STS_MODEL"),
        "agent_version": os.environ.get("STS_AGENT_VERSION"),
        "n_tasks": len(tasks),
        "class_balance": {"positive": pos, "negative": neg},
    }


def balance_warnings(tasks: list[Task]) -> list[str]:
    """Surface the suite-design problems the eval-loops skill warns about."""
    warns: list[str] = []
    pos = sum(1 for t in tasks if t.expectation == "positive")
    neg = sum(1 for t in tasks if t.expectation == "negative")
    if tasks and (pos == 0 or neg == 0):
        warns.append("one-sided suite: add both positive and negative tasks "
                     "(test where the behavior should AND shouldn't occur).")
    for t in tasks:
        if t.expectation == "negative" and not any(g.get("type") == "outcome" for g in t.graders):
            warns.append(f"task {t.id!r} is negative but has no outcome grader asserting the behavior is absent.")
    return warns


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Minimal eval harness (Anthropic evals method).")
    ap.add_argument("--tasks", default="./tasks", help="directory of task files (json; yaml if PyYAML installed)")
    ap.add_argument("--k", type=int, default=None, help="override trials per task")
    ap.add_argument("--timeout", type=float, default=120.0, help="per-trial timeout in seconds (0 = none)")
    ap.add_argument("--out", default="./eval_runs", help="output dir for transcripts + report")
    args = ap.parse_args(argv)

    tasks_dir = Path(args.tasks)
    if not tasks_dir.exists():
        print(f"No tasks dir at {tasks_dir}", file=sys.stderr)
        return 2
    tasks = load_tasks(tasks_dir)
    if not tasks:
        print(f"No tasks found in {tasks_dir}", file=sys.stderr)
        return 2

    out_dir = Path(args.out) / time.strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    for w in balance_warnings(tasks):
        print(f"  ⚠ suite warning: {w}", file=sys.stderr)

    summaries = [run_task(t, args.k or t.k, out_dir, args.timeout) for t in tasks]

    report = {
        "meta": build_meta(tasks, args.k, args.timeout),
        "n_tasks": len(summaries),
        "suite_pass@k_mean": round(sum(s["pass@k"] for s in summaries) / len(summaries), 4),
        "suite_pass^k_mean": round(sum(s["pass^k"] for s in summaries) / len(summaries), 4),
        "total_errors": sum(s["errors"] for s in summaries),
        "total_judge_unknowns": sum(s["judge_unknowns"] for s in summaries),
        "tasks": summaries,
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=2))

    print(f"\nEval report → {out_dir/'report.json'}")
    print(f"  harness {HARNESS_VERSION} | commit {report['meta']['git_commit']} | tasks: {report['n_tasks']}")
    print(f"  suite pass@k (mean): {report['suite_pass@k_mean']}")
    print(f"  suite pass^k (mean): {report['suite_pass^k_mean']}")
    if report["total_errors"]:
        print(f"  ⚠ errored trials: {report['total_errors']}")
    if report["total_judge_unknowns"]:
        print(f"  ⚠ judge abstentions (needs review): {report['total_judge_unknowns']}")
    for s in summaries:
        flag = "" if s[s["reported_metric"]] == 1.0 else "  <-- below bar"
        extra = f" err={s['errors']}" if s["errors"] else ""
        print(f"   - {s['task_id']:<28} per-trial={s['per_trial_rate']:.2f} "
              f"pass@k={s['pass@k']:.0f} pass^k={s['pass^k']:.0f} ({s['reported_metric']}){extra}{flag}")
    print("\nNow READ THE TRANSCRIPTS in", out_dir, "- do not trust scores you haven't inspected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
