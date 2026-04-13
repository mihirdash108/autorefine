#!/bin/bash
# =============================================================================
# Install git hooks for autorefine OSS repo.
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

# Block proprietary terms
for term in "AntHill" "theanthill-ai" "da-ml-openai" "ANTHILL_" "anthill_context"; do
    if echo "$STAGED_CONTENT" | grep -qF "$term"; then
        echo "BLOCKED: Proprietary term '$term' in staged changes."
        exit 1
    fi
done

exit 0
HOOK

chmod +x "$HOOKS_DIR/pre-commit"
echo "Installed pre-commit hook."

# --- Pre-push hook ---
cat > "$HOOKS_DIR/pre-push" << 'HOOK'
#!/bin/bash
# Scan all tracked files before push
echo "Running pre-push security scan..."
if bash scripts/audit.sh; then
    exit 0
else
    echo "Push blocked. Run 'bash scripts/audit.sh' for details."
    exit 1
fi
HOOK

chmod +x "$HOOKS_DIR/pre-push"
echo "Installed pre-push hook."

echo "Done. Hooks will block sensitive content from commits and pushes."
