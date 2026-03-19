#!/usr/bin/env bash
# orchestrate.sh — Master agent orchestrator for camara-ca
#
# Purpose: Run all agents in the correct sequence for a feature build.
# Token Watcher runs before and after every agent to track usage.
# If any agent produces blockers, pipeline halts immediately.
#
# Usage:
#   ./scripts/orchestrate.sh build   # Full feature pipeline from feature-request.json
#   ./scripts/orchestrate.sh review  # Review-only pipeline (PR review)
#   ./scripts/orchestrate.sh docs    # Post-merge docs + dashboard update
#
# Callers can rely on: exit code 0 = all agents approved, exit code 1 = blocked.
# Callers must NOT assume: which agent blocked — check .agent-bus/review.json.

set -euo pipefail

MODE="${1:-build}"
BUS=".agent-bus"
LOG="$BUS/orchestration.log"

mkdir -p "$BUS"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) orchestrate.sh started mode=$MODE" >> "$LOG"

# ─── Helpers ─────────────────────────────────────────────────────────────────

run_agent() {
  local agent="$1"
  local task="${2:-}"
  echo "→ Running agent: $agent ${task:+(task: $task)}"
  ./scripts/run-agent.sh "$agent" "$task" 2>&1 | tee -a "$LOG"
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) agent=$agent task=$task completed" >> "$LOG"
}

check_review() {
  # Parse review.json — halt if not approved
  local approved
  approved=$(python3 -c "import json,sys; d=json.load(open('$BUS/review.json')); print(str(d.get('approved',False)).lower())")
  if [ "$approved" != "true" ]; then
    echo "✗ Reviewer blocked the PR. Check $BUS/review.json for blockers."
    cat "$BUS/review.json"
    exit 1
  fi
  echo "✓ Reviewer approved"
}

check_qa() {
  local passed
  passed=$(python3 -c "import json,sys; d=json.load(open('$BUS/qa-report.json')); print(str(d.get('passed',False)).lower())")
  if [ "$passed" != "true" ]; then
    echo "✗ QA conformance failed. Check $BUS/qa-report.json"
    cat "$BUS/qa-report.json"
    exit 1
  fi
  echo "✓ QA conformance passed"
}

# ─── Pipeline modes ───────────────────────────────────────────────────────────

if [ "$MODE" = "build" ]; then
  echo "=== CAMARA-CA AGENT PIPELINE: BUILD MODE ==="

  # 1. Token Watcher pre-run baseline
  run_agent token-watcher pre-build

  # 2. Architect reads feature-request.json → produces ADR
  run_agent architect

  # 3. Developer reads ADR → writes implementation (one file at a time)
  run_agent developer

  # 4. Tester reads function signature → writes tests (before seeing implementation)
  run_agent tester

  # 5. Run actual tests — fail fast
  echo "→ Running test suite..."
  python3 -m pytest tests/ -x -q 2>&1 | tee -a "$LOG"

  # 6. QA conformance — CAMARA spec validation
  run_agent qa
  check_qa

  # 7. Personas run in parallel (background)
  run_agent user-persona &
  run_agent operator-persona &
  wait
  echo "✓ Both personas completed"

  # 8. Reviewer does final check
  run_agent reviewer
  check_review

  # 9. Token Watcher post-run report
  run_agent token-watcher post-build

  echo "=== PIPELINE COMPLETE: All agents approved ==="

elif [ "$MODE" = "review" ]; then
  echo "=== CAMARA-CA AGENT PIPELINE: REVIEW MODE ==="
  run_agent token-watcher pre-review
  run_agent qa
  check_qa
  run_agent user-persona &
  run_agent operator-persona &
  wait
  run_agent reviewer
  check_review
  run_agent token-watcher post-review
  echo "=== REVIEW COMPLETE ==="

elif [ "$MODE" = "docs" ]; then
  echo "=== CAMARA-CA AGENT PIPELINE: DOCS MODE ==="
  run_agent docs-dashboard
  run_agent layman
  echo "✓ docs/ and index.html updated"

else
  echo "Unknown mode: $MODE. Use: build | review | docs"
  exit 1
fi
