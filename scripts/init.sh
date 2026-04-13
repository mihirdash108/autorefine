#!/bin/bash
# =============================================================================
# autorefine init — scaffold a project from a template
#
# Usage:
#   bash scripts/init.sh                              # interactive
#   bash scripts/init.sh --template llm-skill --artifact my-prompt.md  # CLI
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATES_DIR="$REPO_ROOT/templates"

# --- Check prerequisites ---
if ! command -v uv &>/dev/null; then
    echo -e "${RED}uv not found.${NC} Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
if [ "$(echo "$PYTHON_VERSION < 3.12" | bc -l 2>/dev/null || echo 1)" = "1" ] && [ "$PYTHON_VERSION" != "0.0" ]; then
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 12 ]); then
        echo -e "${RED}Python 3.12+ required.${NC} Found: $PYTHON_VERSION"
        exit 1
    fi
fi

# --- Parse arguments ---
TEMPLATE=""
ARTIFACT=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --template) TEMPLATE="$2"; shift 2 ;;
        --artifact) ARTIFACT="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# --- Available templates ---
AVAILABLE=$(ls -1 "$TEMPLATES_DIR" 2>/dev/null | grep -v '__')
if [ -z "$AVAILABLE" ]; then
    echo "No templates found in $TEMPLATES_DIR"
    exit 1
fi

# --- Interactive mode if no template specified ---
if [ -z "$TEMPLATE" ]; then
    echo -e "${CYAN}=== autorefine init ===${NC}"
    echo ""
    echo "Available templates:"
    i=1
    for t in $AVAILABLE; do
        echo "  $i) $t"
        i=$((i+1))
    done
    echo ""
    read -p "Pick a template (number or name): " CHOICE

    # Handle numeric choice
    if [[ "$CHOICE" =~ ^[0-9]+$ ]]; then
        TEMPLATE=$(echo "$AVAILABLE" | sed -n "${CHOICE}p")
    else
        TEMPLATE="$CHOICE"
    fi

    if [ ! -d "$TEMPLATES_DIR/$TEMPLATE" ]; then
        echo -e "${RED}Template '$TEMPLATE' not found.${NC}"
        exit 1
    fi
fi

# --- Validate template ---
if [ ! -f "$TEMPLATES_DIR/$TEMPLATE/rubric.yaml" ]; then
    echo -e "${RED}Template '$TEMPLATE' missing rubric.yaml${NC}"
    exit 1
fi

# --- Get artifact path ---
if [ -z "$ARTIFACT" ]; then
    echo ""
    read -p "Path to your artifact (e.g., my-prompt.md): " ARTIFACT
fi

if [ ! -f "$ARTIFACT" ]; then
    echo -e "${RED}File not found: $ARTIFACT${NC}"
    exit 1
fi

ARTIFACT_NAME=$(basename "$ARTIFACT")

# --- Copy template ---
echo ""
echo "Setting up with template: $TEMPLATE"
cp "$TEMPLATES_DIR/$TEMPLATE/rubric.yaml" "$REPO_ROOT/rubric.yaml"
cp "$TEMPLATES_DIR/$TEMPLATE/program.md" "$REPO_ROOT/program.md"
echo "  Copied rubric.yaml and program.md"

# --- Copy artifact ---
cp "$ARTIFACT" "$REPO_ROOT/artifacts/$ARTIFACT_NAME"
# Remove the old example if it exists
rm -f "$REPO_ROOT/artifacts/example.md" 2>/dev/null
echo "  Copied $ARTIFACT_NAME to artifacts/"

# --- Update rubric.yaml with correct artifact name ---
# Find the example artifact name in the template rubric and replace with user's
TEMPLATE_ARTIFACT=$(grep -E "^  [a-zA-Z0-9_-]+\.(md|txt|yaml):" "$REPO_ROOT/rubric.yaml" | head -1 | sed 's/://;s/^  //')
if [ -n "$TEMPLATE_ARTIFACT" ] && [ "$TEMPLATE_ARTIFACT" != "$ARTIFACT_NAME" ]; then
    sed -i.bak "s/  $TEMPLATE_ARTIFACT:/  $ARTIFACT_NAME:/" "$REPO_ROOT/rubric.yaml"
    rm -f "$REPO_ROOT/rubric.yaml.bak"
    echo "  Updated rubric.yaml artifact reference: $TEMPLATE_ARTIFACT → $ARTIFACT_NAME"
fi

# --- Validate ---
echo ""
if command -v uv &>/dev/null; then
    echo "Validating setup..."
    uv run evaluate.py --dry-run 2>&1 | tail -5
fi

echo ""
echo -e "${GREEN}=== Ready ===${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API key (if not done already)"
echo "  2. Review rubric.yaml — adjust dimensions for your artifact"
echo "  3. Run baseline: uv run evaluate.py --baseline --verbose"
echo "  4. Start refinement: open claude and say 'Read program.md and let's go'"
