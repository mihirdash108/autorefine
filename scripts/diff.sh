#!/bin/bash
# =============================================================================
# autorefine diff — compare two checkpoint iterations
#
# Usage:
#   bash scripts/diff.sh                    # baseline vs latest keep
#   bash scripts/diff.sh 1 5               # iteration 1 vs iteration 5
#   bash scripts/diff.sh --list             # list available checkpoints
# =============================================================================

CHECKPOINTS_DIR="checkpoints"

if [ ! -d "$CHECKPOINTS_DIR" ]; then
    echo "No checkpoints directory found. Run at least one evaluation first."
    exit 1
fi

AVAILABLE=$(ls -1d "$CHECKPOINTS_DIR"/iteration-* 2>/dev/null | sort)
if [ -z "$AVAILABLE" ]; then
    echo "No checkpoints found."
    exit 1
fi

# --- List mode ---
if [ "$1" = "--list" ] || [ "$1" = "-l" ]; then
    echo "Available checkpoints:"
    for d in $AVAILABLE; do
        name=$(basename "$d")
        files=$(ls -1 "$d" | wc -l | tr -d ' ')
        echo "  $name ($files files)"
    done
    exit 0
fi

# --- Determine which two checkpoints to diff ---
if [ $# -eq 2 ]; then
    # User specified two iteration numbers
    FROM=$(ls -1d "$CHECKPOINTS_DIR"/iteration-$(printf "%03d" "$1")-* 2>/dev/null | head -1)
    TO=$(ls -1d "$CHECKPOINTS_DIR"/iteration-$(printf "%03d" "$2")-* 2>/dev/null | head -1)
    if [ -z "$FROM" ]; then
        echo "Checkpoint for iteration $1 not found."
        echo "Use --list to see available checkpoints."
        exit 1
    fi
    if [ -z "$TO" ]; then
        echo "Checkpoint for iteration $2 not found."
        echo "Use --list to see available checkpoints."
        exit 1
    fi
else
    # Default: baseline vs latest keep
    FROM=$(echo "$AVAILABLE" | head -1)
    TO=$(echo "$AVAILABLE" | tail -1)
fi

FROM_NAME=$(basename "$FROM")
TO_NAME=$(basename "$TO")

echo "Comparing: $FROM_NAME → $TO_NAME"
echo "================================================"
echo ""

# --- Diff each file ---
for f in "$FROM"/*; do
    filename=$(basename "$f")
    to_file="$TO/$filename"

    if [ ! -f "$to_file" ]; then
        echo "--- $filename: removed ---"
        continue
    fi

    DIFF_OUTPUT=$(diff -u "$f" "$to_file" 2>/dev/null)
    if [ -z "$DIFF_OUTPUT" ]; then
        echo "$filename: no changes"
    else
        echo "$DIFF_OUTPUT"
        echo ""
    fi
done

# Check for new files in TO
for f in "$TO"/*; do
    filename=$(basename "$f")
    if [ ! -f "$FROM/$filename" ]; then
        echo "--- $filename: new file ---"
    fi
done
