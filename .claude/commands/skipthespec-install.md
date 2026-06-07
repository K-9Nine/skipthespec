---
description: Install the Skip-the-Spec autonomous developer skill set from GitHub into this project.
---

Install the Skip-the-Spec skill set from git into the current project.

Run these steps with the Bash tool. Report what happened after each.

1. Determine scope. Default to **project scope** (`.claude/skills/`) so this set is isolated to
   skip-the-spec repos and never leaks into PRD-led projects. Only use personal scope
   (`~/.claude/skills/`) if the user explicitly asks.

2. Clone or update the source repo into a temp location and copy the five skills in:

   ```bash
   set -e
   REPO="https://github.com/K-9Nine/skipthespec.git"
   TMP="$(mktemp -d)"
   git clone --depth 1 "$REPO" "$TMP"
   DEST=".claude/skills"            # project scope (default)
   mkdir -p "$DEST"
   for s in autonomous-dev prototype-first dogfood-loop autonomous-build eval-loops; do
     rm -rf "$DEST/$s"
     cp -r "$TMP/$s" "$DEST/$s"
   done
   # also install the slash commands + mode toggle
   mkdir -p .claude/commands
   cp "$TMP/.claude/commands/"*.md .claude/commands/
   cp "$TMP/install/skipthespec-mode.sh" .claude/ 2>/dev/null || true
   chmod +x .claude/skipthespec-mode.sh 2>/dev/null || true
   rm -rf "$TMP"
   echo "Installed: $(ls "$DEST")"
   ```

3. Confirm the skills are visible: list `.claude/skills/` and read the `name:` line of each
   `SKILL.md` so the user can see all five are present.

4. Tell the user to run **/skipthespec-mode on** to make this the primary skill set (suppressing
   PRD-led skills) before starting an autonomous build cycle, and point them at
   `autonomous-dev/KICKOFF-PROMPT.md` (or the repo README) to run the first loop.
