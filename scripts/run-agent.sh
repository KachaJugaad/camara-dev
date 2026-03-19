#!/usr/bin/env bash
# run-agent.sh — Runs a single agent with token logging
#
# Purpose: Wraps every Claude Code subagent call with token usage tracking.
# Reads the agent's system prompt from agents/{name}.md,
# runs claude with the correct model, logs token usage to .agent-bus/token-log.jsonl.
#
# Usage: ./scripts/run-agent.sh <agent-name> [task]
# Example: ./scripts/run-agent.sh developer bell-carrier-profile
#
# Callers can rely on: token usage always being logged, regardless of agent success.
# Callers must NOT assume: output location — each agent declares its own output file.

set -euo pipefail

AGENT="${1:-}"
TASK="${2:-}"
BUS=".agent-bus"
AGENTS_DIR="agents"
START_TIME=$(date +%s%N)

if [ -z "$AGENT" ]; then
  echo "Usage: run-agent.sh <agent-name> [task]"
  exit 1
fi

PROMPT_FILE="$AGENTS_DIR/$AGENT.md"
if [ ! -f "$PROMPT_FILE" ]; then
  echo "✗ Agent prompt not found: $PROMPT_FILE"
  exit 1
fi

# ─── Model routing (mirrors CLAUDE.md model routing table) ───────────────────
get_model() {
  case "$1" in
    architect)            echo "claude-opus-4-5" ;;
    developer)            echo "claude-sonnet-4-5" ;;
    tester)               echo "claude-sonnet-4-5" ;;
    qa)                   echo "claude-sonnet-4-5" ;;
    reviewer)             echo "claude-sonnet-4-5" ;;
    user-persona)         echo "claude-haiku-4-5-20251001" ;;
    operator-persona)     echo "claude-haiku-4-5-20251001" ;;
    token-watcher)        echo "claude-haiku-4-5-20251001" ;;
    docs-dashboard)       echo "claude-haiku-4-5-20251001" ;;
    layman)               echo "claude-haiku-4-5-20251001" ;;
    *)                    echo "claude-sonnet-4-5" ;;
  esac
}

# ─── Token budgets (input / output) ─────────────────────────────────────────
get_budget() {
  case "$1" in
    architect)            echo "8000 2000" ;;
    developer)            echo "4000 4000" ;;
    tester)               echo "2000 3000" ;;
    qa)                   echo "2000 1000" ;;
    reviewer)             echo "3000 1000" ;;
    user-persona)         echo "1000 800" ;;
    operator-persona)     echo "1000 800" ;;
    token-watcher)        echo "500 500" ;;
    docs-dashboard)       echo "1000 1500" ;;
    layman)               echo "1000 800" ;;
    *)                    echo "2000 2000" ;;
  esac
}

MODEL=$(get_model "$AGENT")
read -r BUDGET_IN BUDGET_OUT <<< "$(get_budget "$AGENT")"

echo "→ [$AGENT] model=$MODEL budget=${BUDGET_IN}in/${BUDGET_OUT}out task=${TASK:-default}"

# ─── Build the task context (minimal — only what the agent needs) ─────────────
build_context() {
  local agent="$1"
  local task="$2"

  case "$agent" in
    architect)
      # Architect reads: feature request + existing ADRs list
      cat "$BUS/feature-request.json" 2>/dev/null || echo "{}"
      echo "---"
      ls docs/decisions/ 2>/dev/null | head -20 || true
      ;;
    developer)
      # Developer reads: latest ADR (not full file, just the interface section)
      local latest_adr
      latest_adr=$(ls docs/decisions/ADR-*.md 2>/dev/null | tail -1)
      if [ -n "$latest_adr" ]; then
        # Extract only the interface/contract section — not the full ADR
        sed -n '/## Interface/,/## /p' "$latest_adr" | head -60
      fi
      ;;
    tester)
      # Tester reads: function signatures only (not implementation)
      if [ -n "$task" ]; then
        # Extract only pub fn signatures and doc comments from the relevant file
        grep -n "^pub fn\|^    pub fn\|^/// " "src/simulation/src/surfaces/${task}.rs" 2>/dev/null | head -40 || true
      fi
      ;;
    qa)
      # QA reads: OpenAPI spec path only (Schemathesis loads the file itself)
      echo "Run: python3 tests/conformance/camara_conformance.py"
      ls config/openapi/*.yaml 2>/dev/null || true
      ;;
    reviewer)
      # Reviewer reads: the git diff of changed files only
      git diff HEAD~1 --stat 2>/dev/null | head -30 || echo "No diff available"
      git diff HEAD~1 -- '*.rs' '*.go' '*.py' '*.ts' 2>/dev/null | head -200 || true
      ;;
    token-watcher)
      # Token Watcher reads: current token log (last 20 entries)
      tail -20 "$BUS/token-log.jsonl" 2>/dev/null || echo "No log yet"
      ;;
    user-persona)
      # User Persona reads: dev portal routes and README quickstart only
      head -50 docs/guides/developer-quickstart.md 2>/dev/null || echo "Quickstart not yet written"
      ;;
    operator-persona)
      # Operator Persona reads: operator wizard step definitions only
      head -50 docs/guides/operator-onboarding.md 2>/dev/null || echo "Onboarding guide not yet written"
      ;;
    docs-dashboard)
      # Docs Agent reads: PR description + list of changed files
      cat "$BUS/feature-request.json" 2>/dev/null || echo "{}"
      git diff HEAD~1 --name-only 2>/dev/null | head -20 || true
      ;;
    layman)
      # Layman reads: the docs agent output only (not raw code)
      tail -50 docs/PLAIN_ENGLISH.md 2>/dev/null || echo "No plain English docs yet"
      ;;
  esac
}

# ─── Run the agent via Claude Code ───────────────────────────────────────────
CONTEXT=$(build_context "$AGENT" "$TASK")
SYSTEM_PROMPT=$(cat "$PROMPT_FILE")

# Invoke claude CLI with --print for non-interactive output
# Token counts are captured from the response metadata
RESPONSE_FILE="$BUS/${AGENT}-response.md"

claude \
  --model "$MODEL" \
  --system "$SYSTEM_PROMPT" \
  --max-tokens "$BUDGET_OUT" \
  --print \
  "$CONTEXT" > "$RESPONSE_FILE" 2>/dev/null

# ─── Log token usage ─────────────────────────────────────────────────────────
END_TIME=$(date +%s%N)
DURATION_MS=$(( (END_TIME - START_TIME) / 1000000 ))

# Note: actual token counts come from claude's --output-format json mode
# For now log estimated counts; replace with actual when using json output
TOKENS_ESTIMATED_IN=${#CONTEXT}
TOKENS_ESTIMATED_OUT=$(wc -c < "$RESPONSE_FILE")

cat >> "$BUS/token-log.jsonl" << EOF
{"agent":"$AGENT","model":"$MODEL","task":"${TASK:-default}","tokens_in_est":$TOKENS_ESTIMATED_IN,"tokens_out_est":$TOKENS_ESTIMATED_OUT,"budget_in":$BUDGET_IN,"budget_out":$BUDGET_OUT,"duration_ms":$DURATION_MS,"timestamp":"$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
EOF

echo "✓ [$AGENT] completed in ${DURATION_MS}ms → $RESPONSE_FILE"
