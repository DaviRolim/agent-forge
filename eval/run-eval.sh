#!/bin/bash
# Agent Forge Eval Suite
# Usage: bash eval/run-eval.sh [task-number]
# Examples:
#   bash eval/run-eval.sh        # Run all tasks
#   bash eval/run-eval.sh 3      # Run only task 03

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FORGE_DIR="$(dirname "$SCRIPT_DIR")"
TASKS_DIR="$SCRIPT_DIR/tasks"
DATE=$(date +%Y-%m-%d_%H%M)
RESULTS_DIR="$SCRIPT_DIR/results/$DATE"

echo "🔨 Agent Forge Eval Suite"
echo "========================"
echo "Date: $DATE"
echo "Results: $RESULTS_DIR"
echo ""

# Filter to specific task if argument provided
FILTER="$1"

for task in "$TASKS_DIR"/*.md; do
  name=$(basename "$task" .md)
  
  # Skip if filter is set and doesn't match
  if [ -n "$FILTER" ] && [[ "$name" != *"$FILTER"* ]]; then
    continue
  fi

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📋 Task: $name"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  
  TASK_DIR="$RESULTS_DIR/$name"
  mkdir -p "$TASK_DIR"
  
  START=$(date +%s)
  
  python3 "$FORGE_DIR/forge.py" \
    --task-file "$task" \
    --dir "$TASK_DIR" \
    --log-file "$TASK_DIR/forge.jsonl" \
    --verbose \
    2>&1 | tee "$TASK_DIR/console.log"
  
  END=$(date +%s)
  ELAPSED=$((END - START))
  
  echo ""
  echo "⏱  Completed in ${ELAPSED}s"
  echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Eval suite complete!"
echo "Results saved to: $RESULTS_DIR"
echo ""
echo "Review artifacts:"
echo "  ls $RESULTS_DIR/*/artifacts/"
echo ""
echo "Review manifests:"
echo "  cat $RESULTS_DIR/*/artifacts/manifests/SUMMARY.json"
