#!/usr/bin/env bash
# git-hooks/pre-commit-evaluator.sh
# Claude (haiku) evaluates staged changes before commit is allowed.
#
# Opt-in:    export CLAUDE_PRECOMMIT_EVAL=1
# Threshold: export CLAUDE_PRECOMMIT_THRESHOLD=7  (default: 7, range: 1-10)
# Bypass:    git commit --no-verify
#
# Install: this script is called from .git/hooks/pre-commit
#          See git-hooks/pre-commit-secrets.sh for the combined hook.

set -uo pipefail

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Only run when opted in
[ "${CLAUDE_PRECOMMIT_EVAL:-0}" != "1" ] && exit 0

THRESHOLD="${CLAUDE_PRECOMMIT_THRESHOLD:-7}"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"

# Verify claude CLI is available
if ! command -v "$CLAUDE_BIN" &>/dev/null; then
  echo -e "${YELLOW}  pre-commit-eval: claude CLI not found — skipping evaluation${NC}"
  exit 0
fi

# Get staged diff
DIFF=$(git diff --cached --stat 2>/dev/null)
DIFF_FULL=$(git diff --cached 2>/dev/null)

[ -z "$DIFF_FULL" ] && exit 0

# Truncate very large diffs to avoid token limits (keep first 6000 chars)
if [ "${#DIFF_FULL}" -gt 6000 ]; then
  DIFF_FULL="${DIFF_FULL:0:6000}
... [diff truncated for evaluation]"
fi

FILE_COUNT=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')

echo -e "${CYAN}  pre-commit-eval: evaluating ${FILE_COUNT} file(s) with Claude haiku...${NC}"

# Build evaluation prompt
PROMPT="You are a strict code reviewer evaluating a git commit diff.

Score this diff from 1-10 across 4 dimensions, then give an overall score:
1. Correctness (1-10): Does the code look functionally correct? Any obvious bugs?
2. Completeness (1-10): Are tests included where needed? Is the change whole?
3. Safety (1-10): Any security issues, secret leaks, dangerous patterns?
4. Scope (1-10): Is the diff focused? Or does it mix unrelated changes?

DIFF STATS:
$DIFF

FULL DIFF:
$DIFF_FULL

Respond ONLY in this exact format (no other text):
CORRECTNESS: X
COMPLETENESS: X
SAFETY: X
SCOPE: X
OVERALL: X
VERDICT: APPROVED or BLOCKED
ISSUES:
- issue 1 (if any)
- issue 2 (if any)

Where OVERALL = average of all 4 scores rounded to 1 decimal.
VERDICT = APPROVED if OVERALL >= $THRESHOLD, else BLOCKED.
If no issues, write ISSUES: none"

# Run evaluation (timeout 30s to avoid hanging commits)
EVALUATION=$(timeout 30s "$CLAUDE_BIN" -p "$PROMPT" --model claude-haiku-4-5-20251001 2>/dev/null) || {
  echo -e "${YELLOW}  pre-commit-eval: evaluation timed out or failed — allowing commit${NC}"
  exit 0
}

[ -z "$EVALUATION" ] && { echo -e "${YELLOW}  pre-commit-eval: empty response — allowing commit${NC}"; exit 0; }

# Parse scores
CORRECTNESS=$(echo "$EVALUATION" | grep -i "^CORRECTNESS:" | grep -oE '[0-9]+(\.[0-9]+)?' | head -1) || CORRECTNESS="?"
COMPLETENESS=$(echo "$EVALUATION" | grep -i "^COMPLETENESS:" | grep -oE '[0-9]+(\.[0-9]+)?' | head -1) || COMPLETENESS="?"
SAFETY=$(echo "$EVALUATION" | grep -i "^SAFETY:" | grep -oE '[0-9]+(\.[0-9]+)?' | head -1) || SAFETY="?"
SCOPE=$(echo "$EVALUATION" | grep -i "^SCOPE:" | grep -oE '[0-9]+(\.[0-9]+)?' | head -1) || SCOPE="?"
OVERALL=$(echo "$EVALUATION" | grep -i "^OVERALL:" | grep -oE '[0-9]+(\.[0-9]+)?' | head -1) || OVERALL="0"
VERDICT=$(echo "$EVALUATION" | grep -i "^VERDICT:" | sed 's/VERDICT:[[:space:]]*//' | tr '[:lower:]' '[:upper:]' | tr -d '[:space:]') || VERDICT="UNKNOWN"
ISSUES=$(echo "$EVALUATION" | sed -n '/^ISSUES:/,$ p' | tail -n +2) || ISSUES="none"

# Display result
echo ""
echo -e "  ┌─────────────────────────────────────────┐"
echo -e "  │       Claude Pre-Commit Evaluation       │"
echo -e "  ├─────────────────────────────────────────┤"
printf  "  │  Correctness:   %-24s │\n" "${CORRECTNESS}/10"
printf  "  │  Completeness:  %-24s │\n" "${COMPLETENESS}/10"
printf  "  │  Safety:        %-24s │\n" "${SAFETY}/10"
printf  "  │  Scope:         %-24s │\n" "${SCOPE}/10"
echo -e "  ├─────────────────────────────────────────┤"
printf  "  │  Overall:       %-24s │\n" "${OVERALL}/10  (threshold: ${THRESHOLD}/10)"
echo -e "  └─────────────────────────────────────────┘"

if [ "$ISSUES" != "none" ] && [ -n "$ISSUES" ]; then
  echo ""
  echo -e "${YELLOW}  Issues found:${NC}"
  while IFS= read -r line; do
    [ -n "$line" ] && echo "    $line"
  done <<< "$ISSUES"
fi
echo ""

# Verdict
if [ "$VERDICT" = "APPROVED" ]; then
  echo -e "${GREEN}  ✅ APPROVED (${OVERALL}/10 ≥ ${THRESHOLD}/10) — commit proceeding${NC}"
  echo ""
  exit 0
else
  echo -e "${RED}  ❌ BLOCKED (${OVERALL}/10 < ${THRESHOLD}/10) — commit rejected${NC}"
  echo ""
  echo -e "${YELLOW}  Options:${NC}"
  echo "    1. Fix the issues listed above and re-stage"
  echo "    2. Lower threshold: CLAUDE_PRECOMMIT_THRESHOLD=5 git commit -m \"...\""
  echo "    3. Bypass (emergencies only): git commit --no-verify"
  echo ""
  exit 1
fi
