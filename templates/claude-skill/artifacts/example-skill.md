---
name: code-review
description: >
  Use when the user asks to review code, check code, look at changes,
  or wants feedback on their work.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Edit
  - Write
---

# Code Review Skill

Review code changes and provide feedback.

## Steps

1. Run `git diff` to see what changed.
2. Read through the changed files and identify issues.
3. Look for common problems like:
   - Security vulnerabilities
   - Performance issues
   - Missing error handling
   - Code style violations
   - Logic errors
4. Provide feedback on each file, organized by severity.
5. If there are critical issues, suggest fixes.
6. Handle any problems appropriately.

## Output Format

Provide a summary of findings organized by file, with severity levels (critical, warning, info).
