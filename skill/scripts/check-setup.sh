#!/bin/bash
# Verify autorefine prerequisites
# Usage: bash check-setup.sh [project_root]

DIR="${1:-.}"
ERRORS=0

[ ! -f "$DIR/evaluate.py" ] && echo "Missing: evaluate.py" && ERRORS=$((ERRORS+1))
[ ! -f "$DIR/rubric.yaml" ] && echo "Missing: rubric.yaml" && ERRORS=$((ERRORS+1))
[ ! -f "$DIR/.env" ] && echo "Missing: .env (copy .env.example and add your API key)" && ERRORS=$((ERRORS+1))
[ ! -d "$DIR/artifacts" ] && echo "Missing: artifacts/ directory" && ERRORS=$((ERRORS+1))

if [ -d "$DIR/artifacts" ]; then
    ARTIFACT_COUNT=$(find "$DIR/artifacts" -type f ! -name '.*' ! -name 'example.md' 2>/dev/null | wc -l | tr -d ' ')
    [ "$ARTIFACT_COUNT" -eq 0 ] && echo "No artifacts in artifacts/ (only example.md found)" && ERRORS=$((ERRORS+1))
fi

if [ $ERRORS -eq 0 ]; then
    echo "OK"
fi

exit $ERRORS
