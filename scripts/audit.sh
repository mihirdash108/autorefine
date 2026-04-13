#!/bin/bash
# =============================================================================
# autorefine — Security audit script
# Scans tracked files for API keys, credentials, and custom blocked terms.
# Usage: bash scripts/audit.sh
#
# Custom blocklist: create .audit-blocklist with one regex pattern per line.
# These are YOUR proprietary terms that should never appear in the repo.
# Example .audit-blocklist:
#   MyCompanyName
#   internal-api\.mycompany\.com
#   MYCOMPANY_
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
    matches=$(grep -rlE "$pattern" $ALL_FILES 2>/dev/null | grep -v 'scripts/audit.sh' | grep -v 'scripts/install-hooks.sh' | grep -v '.audit-blocklist' || true)
    if [ -n "$matches" ]; then
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

# --- Built-in patterns (always checked) ---
scan_pattern "API key (sk-*)"        'sk-[a-zA-Z0-9]{20,}'
scan_pattern "Hardcoded credential"  '(API_KEY|api_key)\s*=\s*["'"'"']?[A-Za-z0-9+/]{30,}'

# --- Custom blocklist (your proprietary terms) ---
BLOCKLIST=".audit-blocklist"
if [ -f "$BLOCKLIST" ]; then
    echo "Reading custom blocklist from $BLOCKLIST"
    while IFS= read -r pattern || [ -n "$pattern" ]; do
        pattern=$(echo "$pattern" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        [ -z "$pattern" ] && continue
        [[ "$pattern" == \#* ]] && continue
        scan_pattern "Blocked term: $pattern" "$pattern"
    done < "$BLOCKLIST"
else
    echo -e "${YELLOW}No .audit-blocklist found. Only checking API keys and credentials.${NC}"
    echo "Create .audit-blocklist with your proprietary terms (one regex per line)."
    echo ""
fi

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
