#!/usr/bin/env bash
# skipthespec-mode.sh — toggle the Skip-the-Spec skill set as the PRIMARY / only active
# skill set, isolating it from PRD-led skills.
#
# Mechanism: writes an enforcement block (delimited by markers) into the project CLAUDE.md.
# When ON, Claude is instructed to use ONLY the five autonomous-dev skills and to ignore
# PRD-led skills for this session. When OFF, the block is removed and normal behavior resumes.
#
# Usage:
#   ./skipthespec-mode.sh on      # activate (skip-the-spec is primary, PRD skills suppressed)
#   ./skipthespec-mode.sh off     # deactivate (restore normal skill behavior)
#   ./skipthespec-mode.sh status  # show current state
set -euo pipefail

CLAUDE_MD="${CLAUDE_MD:-CLAUDE.md}"
BEGIN="<!-- SKIPTHESPEC:BEGIN -->"
END="<!-- SKIPTHESPEC:END -->"

BLOCK=$(cat <<'EOF'
<!-- SKIPTHESPEC:BEGIN -->
## ACTIVE MODE: Skip-the-Spec (autonomous developer) — PRIMARY SKILL SET

Skip-the-Spec mode is **ON**. For this project/session:

- The **only** skill set you should use is: `autonomous-dev` (router), `prototype-first`,
  `dogfood-loop`, `autonomous-build`, `eval-loops`.
- **Load `autonomous-dev` first** and read its `references/constitution.md`. Honor the
  priority hierarchy: Safety > Corrigibility > Velocity > Quality.
- **Ignore / do not trigger PRD-led or spec-first skills** while this block is present, even
  if their descriptions seem to match. This is a prototype-first workflow — do not write a PRD.
- If a task genuinely needs a suppressed skill, say so and ask before switching out of mode.

To leave this mode, run `./skipthespec-mode.sh off` (or /skipthespec-mode off), which removes
this block and restores normal skill selection.
<!-- SKIPTHESPEC:END -->
EOF
)

remove_block() {
  [ -f "$CLAUDE_MD" ] || return 0
  # delete everything between markers inclusive
  awk -v b="$BEGIN" -v e="$END" '
    $0==b{skip=1} skip&&$0==e{skip=0;next} !skip{print}
  ' "$CLAUDE_MD" > "$CLAUDE_MD.tmp"
  # trim trailing blank lines
  awk 'NF{p=NR} {a[NR]=$0} END{for(i=1;i<=p;i++)print a[i]}' "$CLAUDE_MD.tmp" > "$CLAUDE_MD"
  rm -f "$CLAUDE_MD.tmp"
}

case "${1:-status}" in
  on)
    touch "$CLAUDE_MD"
    remove_block
    printf '%s\n\n%s\n' "$(cat "$CLAUDE_MD")" "$BLOCK" > "$CLAUDE_MD.tmp" && mv "$CLAUDE_MD.tmp" "$CLAUDE_MD"
    echo "Skip-the-Spec mode: ON  (autonomous-dev set is primary; PRD-led skills suppressed)"
    echo "Enforcement written to $CLAUDE_MD. Start a fresh Claude Code session to pick it up."
    ;;
  off)
    remove_block
    echo "Skip-the-Spec mode: OFF (normal skill selection restored)"
    ;;
  status)
    if [ -f "$CLAUDE_MD" ] && grep -q "$BEGIN" "$CLAUDE_MD"; then
      echo "Skip-the-Spec mode: ON"
    else
      echo "Skip-the-Spec mode: OFF"
    fi
    ;;
  *)
    echo "Usage: $0 {on|off|status}" >&2; exit 2;;
esac
