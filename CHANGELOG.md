# Changelog

## Unreleased — harness hardening + scope honesty (v1.1)

A quality pass on the runnable eval harness and the docs around it. The five skills'
core methodology is unchanged; this makes the executable parts solid and the claims honest.

### eval-loops/scripts/run_evals.py
- **Security — no more `eval()`.** Grader `check` expressions run through a restricted AST
  evaluator (`safe_eval`): comparisons, boolean/arithmetic ops, literals, indexing, and a small
  allow-list of functions only. Attribute access and arbitrary calls are refused, closing the
  classic `().__class__.__bases__[0].__subclasses__()` escape — a malicious community task pack
  can no longer run code through a grader. A bad check degrades to a failed grade, never a crash.
- **Robustness.** A crashing or hung trial no longer aborts the suite. Each trial is wrapped with
  a per-trial `--timeout`; crashes/timeouts are recorded as failed trials with the error captured
  in the transcript for inspection.
- **Provenance.** `report.json` now carries a `meta` block: harness version, git commit, UTC
  timestamp, python/platform, k, timeout, optional `STS_MODEL`/`STS_AGENT_VERSION`, and class balance.
- **`expectation` wired in.** The harness reports the positive/negative split and warns on
  one-sided suites and on negative tasks lacking an absence-asserting outcome grader.
- **Judge abstentions.** An LLM-judge `unknown` verdict is counted separately (never as a pass)
  and surfaced per task and per trial as `needs_review`.

### eval-loops — first-run + self-test
- `demo_tasks/` ships two JSON tasks (one positive, one negative) so the quickstart runs with
  **zero dependencies**. PyYAML is now optional (`requirements.txt`), only for YAML task files.
- `tests/test_run_evals.py` (stdlib `unittest`) is the harness's own self-test: covers the safe
  evaluator including escape refusal, metrics, crash/timeout handling, and suite-design checks.
  Run: `python -m unittest discover -s eval-loops/tests`.

### docs
- `autonomous-dev`: added a **"When NOT to Use This Skill"** section — production-critical /
  regulated / hard-to-reverse work stays spec-first. Mirrored as a short note in the README.
- README + `eval-loops`: documented that **clean-room is state isolation, not a security sandbox**;
  run untrusted task packs in a container with no credentials and egress disabled.
- Reframed the mode toggle accurately as a **soft, session-start nudge** (project scope is the real
  isolation); the constitution gained a "how this is enforced (and how it is not)" section.
- Install one-liner uses `mktemp -d` instead of a predictable, world-readable `/tmp/sts` path.
- `pass@k`/`pass^k` documented as the **empirical** per-task figure, not the unbiased estimator.
