# Claude Code Kickoff Prompt — run the first prototype-first cycle

Copy everything in the fenced block below into Claude Code, after installing the five skills
(see README). It points Claude at the skill set and runs one full cycle end to end so you can
watch the methodology work on a real goal. Replace `<YOUR GOAL>` and the bracketed inputs.

---

```
Use the autonomous-dev skill set to take a single feature from idea to a data-backed
promote/iterate/kill decision. Do not write a PRD.

Load `autonomous-dev` first and read references/constitution.md. Honor the priority
hierarchy (Safety > Corrigibility > Velocity > Quality) and the Hard Constraints throughout.
If I tell you to halt, roll back, or pivot at any point, comply instantly.

GOAL (one sentence): <YOUR GOAL — e.g. "Let users preview Excel/CSV/TSV files inline so
they never download to inspect data.">

Human-owned inputs (constitution §3 — these are mine to set, yours to respect):
- Why it should exist: <...>
- Boundaries / do-not-touch: <e.g. don't touch auth, billing, or the prod DB schema>
- Success metric + target: <e.g. preview-opens/eligible-user >= 40% in week 1>
- Rollback metric: <e.g. >2% of previews error out, or any prod data corruption>

Now run the loop:

1. prototype-first: compress the goal, run the Reasonable-Assumption Protocol, write
   PROTOTYPE.md (assumptions + thinnest signal-producing slice). Flag any assumption that
   is expensive to reverse instead of guessing. Pick the 2 usage signals to emit.

2. autonomous-build: plan the smallest reversible slice, then implement it behind a feature
   flag. You drive — don't ask me to approve every micro-step. Escalate only at the
   boundaries in autonomous-build/references/autonomy-boundaries.md (schema/API/security/
   irreversible) or after 3 failed repair iterations. Write tests alongside the code, not
   after. Apply the honesty rules: never weaken a test to go green; if a test fails, fix the
   code; flag any architectural issue or better alternative you notice.

3. eval-loops: stand up the harness. Start with 20-50 tasks sourced from likely real
   failures for this feature (use templates/eval-task.yaml). Write a reference solution per
   task to prove it's solvable. Use deterministic graders for outcomes + an LLM judge only
   for the nuanced parts; grade outcomes, not tool-call paths. Run scripts/run_evals.py,
   report pass@k / pass^k, and READ THE TRANSCRIPTS before trusting any score. Bound the
   repair loop at 3.

4. dogfood-loop: confirm the slice is shippable (not polished), ship it behind the flag at
   rung 1 (internal). Fill in templates/rollout-log.md with the adoption + helpfulness
   numbers and verbatim feedback. Convert every recurring failure into a new eval task.

5. Decision: apply the data-driven rule (promote / iterate / kill). Give me a falsifiable
   recommendation with the numbers — but leave the final default-on and ultimate-success
   verdict to me (constitution §3).

Return to me at the end with: PROTOTYPE.md, the diff summary + flagged tradeoffs, the eval
report (pass@k/pass^k + transcript notes), the filled rollout-log, and your recommendation.
```

---

## Tips
- Run step 2 (build), step 3 (eval design), and the dogfood instrumentation as **separate Claude
  Code sessions/tabs** if the feature is large — context stays clean and the lanes don't collide.
- For a tiny fix, a single sequential session is fine.
- Keep the constitution in the repo so every session re-grounds on the same boundaries.
