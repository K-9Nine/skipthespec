---
description: Toggle Skip-the-Spec as the primary/only skill set (suppress PRD-led skills). Usage: /skipthespec-mode on|off|status
argument-hint: on | off | status
---

Toggle Skip-the-Spec mode. Argument: `$ARGUMENTS` (one of: on, off, status).

Skip-the-Spec mode makes the five autonomous-dev skills the **only** active set and tells you
to ignore PRD-led / spec-first skills, so the two workflows don't get confused.

Run the toggle script and act on the result:

```bash
SCRIPT=".claude/skipthespec-mode.sh"
[ -f "$SCRIPT" ] || SCRIPT="./skipthespec-mode.sh"
bash "$SCRIPT" ${ARGUMENTS:-status}
```

Then:

- If the argument was **on**: confirm the mode directive is now in `CLAUDE.md`. This is a
  **soft, session-start nudge**, not a hard runtime lock — Claude Code reads `CLAUDE.md` when a
  session begins, so the user should start a fresh session (or re-read CLAUDE.md) for the
  suppression to take effect. From then until they run `off`, use ONLY: `autonomous-dev`,
  `prototype-first`, `dogfood-loop`, `autonomous-build`, `eval-loops`. Load `autonomous-dev` first.
- If the argument was **off**: confirm the block was removed and normal skill selection is back.
- If the argument was **status** (or empty): report whether mode is ON or OFF.

Do not modify any skill files — this command only flips the mode marker in CLAUDE.md.
