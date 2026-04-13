#!/bin/bash
# =============================================================================
# autorefine — Security audit script
# Run before any push to verify no sensitive content exists in tracked files.
# Usage: bash scripts/audit.sh
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=== autorefine security audit ==="
echo ""

ISSUES=0
ALL_FILES=$(git ls-files)

# Helper: scan for a pattern, report if found
scan_pattern() {
    local desc="$1"
    local pattern="$2"
    local matches
    matches=$(grep -rlE "$pattern" $ALL_FILES 2>/dev/null | grep -v 'scripts/audit.sh' | grep -v 'scripts/install-hooks.sh' || true)
    if [ -n "$matches" ]; then
        # Filter out commented lines in .env.example
        local real_matches=""
        for f in $matches; do
            if [ "$f" = ".env.example" ]; then
                if grep -E "$pattern" "$f" | grep -qv '^\s*#'; then
                    real_matches="$real_matches $f"
                fi
            else
                real_matches="$real_matches $f"
            fi
        done
        if [ -n "$real_matches" ]; then
            echo -e "${RED}ISSUE: $desc found in:${NC}$real_matches"
            ISSUES=$((ISSUES + 1))
        fi
    fi
}

# --- Scan for sensitive patterns ---
scan_pattern "API key (sk-*)"        'sk-[a-zA-Z0-9]{20,}'
scan_pattern "Hardcoded credential"  '(API_KEY|api_key)\s*=\s*["'"'"']?[A-Za-z0-9+/]{30,}'
scan_pattern "AntHill reference"     'AntHill'
scan_pattern "Internal org"          'theanthill-ai'
scan_pattern "Internal endpoint"     'da-ml-openai'
scan_pattern "Internal env prefix"   'ANTHILL_'
scan_pattern "Internal DB ref"       'anthill_context'
scan_pattern "Internal repo"         'context-graph-v[0-9]'
scan_pattern "BFSI reference"        'BFSI'
scan_pattern "Internal ticket ID"    'MOBAST-'

# --- Check .env not tracked ---
if git ls-files --error-unmatch .env >/dev/null 2>&1; then
    echo -e "${RED}ISSUE: .env is tracked by git!${NC}"
    ISSUES=$((ISSUES + 1))
fi

# --- Check .gitignore covers essentials ---
for ignore in ".env" "eval_state.json" "results.tsv" "checkpoints/" ".baseline_placeholders.json"; do
    if ! grep -qF "$ignore" .gitignore 2>/dev/null; then
        echo -e "${YELLOW}WARNING: $ignore not in .gitignore${NC}"
        ISSUES=$((ISSUES + 1))
    fi
done

# --- Result ---
echo ""
if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}PASSED: No sensitive content found. Safe to push.${NC}"
    exit 0
else
    echo -e "${RED}FAILED: $ISSUES issue(s) found. Fix before pushing.${NC}"
    exit 1
fi
