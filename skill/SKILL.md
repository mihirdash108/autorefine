---
name: autorefine
description: >
  Autonomous document refinement using LLM-as-judge evaluation.
  Use when the user asks to "refine docs", "run autorefine", "improve
  document quality", "start refinement loop", or "autorefine these docs".
  Runs entirely in the background — the user continues working while
  documents are iteratively improved. Requires an autorefine project
  directory with evaluate.py, rubric.yaml, and artifacts/.
allowed-tools: Agent, Bash, Read, Write, Edit, Glob, Grep
argument-hint: "[subcommand: run (default) | status | stop | resume]"
effort: high
---

# autorefine skill

## /autorefine run (default)

Determine the autorefine project root: walk up from cwd looking for `evaluate.py` + `rubric.yaml` + `artifacts/`. If not found within 3 levels, error out.

Check if `.autorefine.lock` exists. If yes, report it's already running and suggest `/autorefine status` or `/autorefine stop`.

If clear, spawn a SINGLE background agent that handles EVERYTHING — setup, baseline, dashboard, and the full refinement loop. Do NOT execute any steps yourself. Read `references/supervisor-prompt.md` from this skill's directory, replace `{project_root}` with the found path and `{max_iterations}` with 30, then:

```
Agent(
  description: "autorefine full run",
  prompt: <contents of references/supervisor-prompt.md with values injected>,
  run_in_background: true
)
```

Then immediately tell the user:

> "autorefine spawned in background. Dashboard will be at http://localhost:8501 once setup completes. Use `/autorefine status` to check progress, `/autorefine stop` to terminate. I'll notify you when it converges."

That's it. Return control to the user. Do NOT wait for the agent. Do NOT run baseline yourself. Do NOT start the dashboard yourself.

## /autorefine status

Find project root. Read `eval_state.json` and `tried_strategies.log` from the worktree (check `.autorefine.lock` for worktree path). Show iteration count, best score, cumulative cost, consecutive discards, last 5 tried strategies.

## /autorefine stop

Find project root. Read `.autorefine.lock`. Kill dashboard: `lsof -ti:<port> | xargs kill 2>/dev/null`. Remove lock file. Report branch name and how to merge.

## /autorefine resume

Find project root. Verify `eval_state.json` exists in worktree. Spawn background agent same as `/autorefine run` but with `--skip-setup` note in the prompt so the agent skips branch/worktree/baseline creation and goes straight to the loop.
