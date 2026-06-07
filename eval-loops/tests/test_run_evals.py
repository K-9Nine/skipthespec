#!/usr/bin/env python3
"""Self-test for the eval harness. Stdlib only (unittest) — no dependencies.

Run from the repo root:
    python -m unittest discover -s eval-loops/tests
or directly:
    python eval-loops/tests/test_run_evals.py

An evals tool that grades everything else should be able to grade itself.
"""
import sys
import unittest
from pathlib import Path

# Make scripts/ importable regardless of where the test is invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import run_evals as rv  # noqa: E402


class TestSafeEval(unittest.TestCase):
    def test_allows_comparisons_and_indexing(self):
        outcome = {"download_events": 0, "rendered_table": {"headers": ["id", "name"]}}
        names = {**rv.ALLOWED_FUNCS, **outcome}
        self.assertTrue(rv.safe_eval("download_events == 0", names))
        self.assertTrue(rv.safe_eval("rendered_table['headers'][0] == 'id'", names))
        self.assertFalse(rv.safe_eval("download_events > 0", names))

    def test_allows_allowlisted_functions(self):
        names = {**rv.ALLOWED_FUNCS, **{"rows": [1, 2, 3, 4, 5]}}
        self.assertTrue(rv.safe_eval("len(rows) == 5", names))
        self.assertTrue(rv.safe_eval("max(rows) == 5 and min(rows) == 1", names))
        self.assertTrue(rv.safe_eval("all([1, 1, 1])", names))
        self.assertFalse(rv.safe_eval("any([0, 0])", names))

    def test_allows_boolean_and_arithmetic(self):
        names = {**rv.ALLOWED_FUNCS, "a": 2, "b": 8}
        self.assertTrue(rv.safe_eval("a == 2 and b == 8", names))
        self.assertTrue(rv.safe_eval("a / b == 0.25", names))
        self.assertTrue(rv.safe_eval("not (a > b)", names))

    def test_rejects_attribute_access_escape(self):
        # The classic sandbox-escape vector must be refused, not executed.
        names = {**rv.ALLOWED_FUNCS}
        with self.assertRaises(rv.GraderExprError):
            rv.safe_eval("().__class__.__bases__[0].__subclasses__()", names)

    def test_rejects_disallowed_calls_and_dunders(self):
        names = {**rv.ALLOWED_FUNCS}
        for bad in ["__import__('os')", "open('x')", "eval('1')", "exec('x')",
                    "(lambda: 1)()", "[x for x in range(3)]"]:
            with self.assertRaises(rv.GraderExprError):
                rv.safe_eval(bad, names)

    def test_unknown_name_is_rejected(self):
        with self.assertRaises(rv.GraderExprError):
            rv.safe_eval("mystery_field == 1", {**rv.ALLOWED_FUNCS})

    def test_grade_outcome_reports_error_not_crash(self):
        # A malicious/broken check must degrade to a failed grade, never raise.
        grade = rv.grade_outcome({"check": "().__class__"}, {})
        self.assertFalse(grade["passed"])
        self.assertIn("error", grade)


class TestGradingAndMetrics(unittest.TestCase):
    def test_trial_passed_semantics(self):
        self.assertTrue(rv.trial_passed([{"passed": True}, {"passed": True}]))
        self.assertFalse(rv.trial_passed([{"passed": True}, {"passed": False}]))
        self.assertFalse(rv.trial_passed([]))  # nothing asserted => not a pass

    def test_metrics(self):
        self.assertEqual(rv.pass_at_k(0), 0.0)
        self.assertEqual(rv.pass_at_k(1), 1.0)
        self.assertEqual(rv.pass_pow_k(5, 5), 1.0)
        self.assertEqual(rv.pass_pow_k(4, 5), 0.0)
        self.assertEqual(rv.pass_pow_k(0, 0), 0.0)
        self.assertAlmostEqual(rv.per_trial_rate(3, 4), 0.75)

    def test_judge_unknown_is_not_a_pass(self):
        grade = rv.llm_judge({"dimension": "readability"}, {}, "transcript")
        self.assertIn(grade["verdict"], {"pass", "fail", "unknown"})
        if grade["verdict"] == "unknown":
            self.assertFalse(grade["passed"])


class TestRunnerRobustness(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(rv.tempfile.mkdtemp(prefix="eval_selftest_"))
        self._orig_agent = rv.run_agent

    def tearDown(self):
        rv.run_agent = self._orig_agent
        rv.shutil.rmtree(self.tmp, ignore_errors=True)

    def _task(self, **kw):
        defaults = dict(id="t", input={}, graders=[{"type": "outcome", "check": "ok == True"}])
        defaults.update(kw)
        return rv.Task(**defaults)

    def test_happy_path_writes_transcript(self):
        rv.run_agent = lambda task, wd: {"outcome": {"ok": True}, "transcript": "did it"}
        summary = rv.run_task(self._task(), k=3, out_dir=self.tmp, timeout=10)
        self.assertEqual(summary["successes"], 3)
        self.assertEqual(summary["pass^k"], 1.0)
        self.assertTrue(Path(summary["trials"][0]["transcript_path"]).exists())

    def test_crashing_agent_does_not_abort_suite(self):
        def boom(task, wd):
            raise RuntimeError("agent exploded")
        rv.run_agent = boom
        summary = rv.run_task(self._task(), k=2, out_dir=self.tmp, timeout=10)
        self.assertEqual(summary["successes"], 0)
        self.assertEqual(summary["errors"], 2)
        # transcript should capture the error for inspection
        self.assertIn("agent exploded", Path(summary["trials"][0]["transcript_path"]).read_text())

    def test_timeout_is_recorded_as_error(self):
        def slow(task, wd):
            rv.time.sleep(0.5)
            return {"outcome": {"ok": True}, "transcript": "slow"}
        rv.run_agent = slow
        summary = rv.run_task(self._task(), k=1, out_dir=self.tmp, timeout=0.05)
        self.assertEqual(summary["errors"], 1)
        self.assertEqual(summary["successes"], 0)


class TestSuiteDesignChecks(unittest.TestCase):
    def test_one_sided_suite_warns(self):
        tasks = [rv.Task(id="p", input={}, expectation="positive",
                         graders=[{"type": "outcome", "check": "ok == True"}])]
        warns = rv.balance_warnings(tasks)
        self.assertTrue(any("one-sided" in w for w in warns))

    def test_negative_without_outcome_grader_warns(self):
        tasks = [
            rv.Task(id="p", input={}, expectation="positive",
                    graders=[{"type": "outcome", "check": "ok == True"}]),
            rv.Task(id="n", input={}, expectation="negative",
                    graders=[{"type": "llm_judge", "dimension": "x"}]),
        ]
        warns = rv.balance_warnings(tasks)
        self.assertTrue(any("negative but has no outcome grader" in w for w in warns))


if __name__ == "__main__":
    unittest.main(verbosity=2)
