#!/bin/bash
# =============================================================================
# autorefine — start a refinement run
#
# Usage:
#   bash start.sh              # baseline + dashboard + instructions
#   bash start.sh --skip-baseline  # skip baseline (already recorded)
# =============================================================================

set -e

SKIP_BASELINE=false
if [ "$1" = "--skip-baseline" ]; then
    SKIP_BASELINE=true
fi

echo "=== autorefine ==="
echo ""

# Check for artifacts
ARTIFACT_COUNT=$(find artifacts/ -type f ! -name '.*' 2>/dev/null | wc -l | tr -d ' ')
if [ "$ARTIFACT_COUNT" -eq 0 ]; then
    echo "ERROR: No artifacts found in artifacts/"
    echo "Add your documents: cp your-doc.md artifacts/"
    exit 1
fi
echo "Found $ARTIFACT_COUNT artifact(s) in artifacts/"

# Check for .env
if [ ! -f .env ]; then
    echo "ERROR: .env not found. Copy .env.example to .env and add your API key."
    exit 1
fi

# Install dependencies if needed
if [ ! -d .venv ]; then
    echo "Installing dependencies..."
    uv sync 2>&1 | tail -1
fi

# Run baseline if needed
if [ "$SKIP_BASELINE" = false ]; then
    if [ -f eval_state.json ]; then
        echo "Baseline already recorded. Use --skip-baseline to skip, or delete eval_state.json to re-run."
        read -p "Re-run baseline? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            SKIP_BASELINE=true
        else
            rm -f eval_state.json eval_history.jsonl results.tsv .baseline_placeholders.json
        fi
    fi

    if [ "$SKIP_BASELINE" = false ]; then
        echo ""
        echo "Running baseline evaluation..."
        uv run evaluate.py --baseline --verbose 2>&1 | tee eval.log
        echo ""
    fi
fi

# Start dashboard in background
echo "Starting dashboard..."
uv run dashboard.py --no-open &
DASH_PID=$!
sleep 1
echo "Dashboard running at http://localhost:8501 (PID: $DASH_PID)"

# Open browser
if command -v open &>/dev/null; then
    open http://localhost:8501
elif command -v xdg-open &>/dev/null; then
    xdg-open http://localhost:8501
fi

echo ""
echo "=== Ready ==="
echo ""
echo "Dashboard: http://localhost:8501"
echo ""
echo "To start the refinement loop, open a new terminal and run:"
echo ""
echo "  cd $(pwd)"
echo "  claude"
echo ""
echo "Then say: \"Read program.md and let's kick off a refinement run.\""
echo ""
echo "To stop the dashboard: kill $DASH_PID"
