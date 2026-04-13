#!/bin/bash
# =============================================================================
# Install git hooks for autorefine.
# Run once after cloning: bash scripts/install-hooks.sh
# =============================================================================

set -e

HOOKS_DIR="$(git rev-parse --show-toplevel)/.git/hooks"

# --- Pre-commit hook ---
cat > "$HOOKS_DIR/pre-commit" << 'HOOK'
#!/bin/bash
# Block sensitive content from being committed
STAGED_CONTENT=$(git diff --cached --diff-filter=d -U0 2>/dev/null)
STAGED_FILES=$(git diff --cached --name-only --diff-filter=d 2>/dev/null)

# Block .env files
if echo "$STAGED_FILES" | grep -qE '\.env$'; then
    echo "BLOCKED: .env file staged. Never commit credentials."
    exit 1
fi

# Block API keys
if echo "$STAGED_CONTENT" | grep -qE 'sk-[a-zA-Z0-9]{20,}'; then
    echo "BLOCKED: Possible API key in staged changes."
    exit 1
fi
if echo "$STAGED_CONTENT" | grep -qE '(API_KEY|api_key)\s*=\s*["\x27]?[A-Za-z0-9+/]{30,}'; then
    echo "BLOCKED: Hardcoded credential in staged changes."
    exit 1
fi

# Block custom terms from .audit-blocklist
BLOCKLIST="$(git rev-parse --show-toplevel)/.audit-blocklist"
if [ -f "$BLOCKLIST" ]; then
    while IFS= read -r pattern || [ -n "$pattern" ]; do
        pattern=$(echo "$pattern" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        [ -z "$pattern" ] && continue
        [[ "$pattern" == \#* ]] && continue
        if echo "$STAGED_CONTENT" | grep -qE "$pattern"; then
            echo "BLOCKED: Custom blocked term '$pattern' in staged changes."
            exit 1
        fi
    done < "$BLOCKLIST"
fi

exit 0
HOOK

chmod +x "$HOOKS_DIR/pre-commit"
echo "Installed pre-commit hook."

# --- Pre-push hook ---
cat > "$HOOKS_DIR/pre-push" << 'HOOK'
#!/bin/bash
# Scan all tracked files before push
echo "Running pre-push security scan..."
REPO_ROOT=$(git rev-parse --show-toplevel)
if bash "$REPO_ROOT/scripts/audit.sh"; then
    exit 0
else
    echo "Push blocked. Run 'bash scripts/audit.sh' for details."
    exit 1
fi
HOOK

chmod +x "$HOOKS_DIR/pre-push"
echo "Installed pre-push hook."

echo ""
echo "Done. Hooks will block sensitive content from commits and pushes."
if [ ! -f "$(git rev-parse --show-toplevel)/.audit-blocklist" ]; then
    echo ""
    echo "TIP: Create .audit-blocklist with your proprietary terms."
    echo "See .audit-blocklist.example for the format."
fi
