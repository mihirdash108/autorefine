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

Autonomous document refinement. One command runs baseline, opens dashboard, and loops in the background until convergence.

## Subcommands

- `/autorefine` or `/autorefine run` — Full run: setup + baseline + background loop
- `/autorefine status` — Show current iteration, scores, cost
- `/autorefine stop` — Kill background agent + dashboard, clean up
- `/autorefine resume` — Resume a stopped/crashed run

## Handler: /autorefine run

Execute these steps in order. Do NOT skip any step.

### Step 1: Find project root

Walk up from the current working directory looking for a directory that contains `evaluate.py` AND `rubric.yaml` AND `artifacts/`. Check cwd first, then parent, then grandparent (max 3 levels). If not found:

> "No autorefine project found. Run from a directory containing evaluate.py, rubric.yaml, and artifacts/."

Store the found path as `PROJECT_ROOT`.

### Step 2: Check lock file

Check if `PROJECT_ROOT/.autorefine.lock` exists. If it does, read it and report:

> "autorefine is already running (started {time}, branch {branch}). Use `/autorefine stop` to terminate or `/autorefine status` to check progress."

### Step 3: Verify setup

Run `bash` to check prerequisites:

```
[ -f "$PROJECT_ROOT/.env" ] && [ -d "$PROJECT_ROOT/artifacts" ] && ls "$PROJECT_ROOT/artifacts/" | grep -v example.md | head -1
```

If .env is missing: "Missing .env — copy .env.example and add your API key."
If no artifacts (other than example.md): "No artifacts in artifacts/. Add your documents first."

### Step 4: Create git branch + worktree

Generate a branch tag from today's date (e.g., `autorefine/apr13`). If the branch exists, try `autorefine/apr13-2`, `-3`, etc.

Create the branch and a git worktree so the background agent works in an isolated copy — the user's working tree stays untouched:

```bash
cd PROJECT_ROOT && git branch autorefine/<tag>
cd PROJECT_ROOT && git worktree add .autorefine-worktree autorefine/<tag>
```

Copy the .env file to the worktree (it's gitignored so it won't be in the branch):

```bash
cp PROJECT_ROOT/.env PROJECT_ROOT/.autorefine-worktree/.env
```

All subsequent commands (baseline, evaluate, dashboard) run in `.autorefine-worktree/`, NOT in PROJECT_ROOT. Store `WORKTREE_PATH = PROJECT_ROOT/.autorefine-worktree`.

### Step 5: Git tag for rollback

```bash
cd PROJECT_ROOT && git tag pre-autorefine/<tag>
```

### Step 6: Start dashboard

Kill any existing dashboard on port 8501, then start a new one (from the worktree):

```bash
lsof -ti:8501 | xargs kill 2>/dev/null; cd WORKTREE_PATH && uv run dashboard.py --no-open &
```

Open the browser:

```bash
open http://localhost:8501
```

### Step 7: Run baseline

Run baseline in the worktree:

```bash
cd WORKTREE_PATH && uv run evaluate.py --baseline > eval.log 2>&1
```

Read `eval.log` (tail -25) and show the baseline scores to the user.

### Step 8: Cost estimate

Count the number of dimensions in rubric.yaml and artifacts. Estimate:
- Judge cost: ~$0.10-0.30 per iteration × 30 iterations = $3-9
- Refiner cost (Claude Code): ~$0.50-2.00 per iteration × 30 iterations = $15-60
- Total estimate: $18-69

Tell the user: "Estimated cost for 30 iterations: ~$20-70 total (judge + refiner). Adjust max iterations if needed."

### Step 9: Create lock file

Write `.autorefine.lock`:

```json
{"started": "<timestamp>", "branch": "autorefine/<tag>", "dashboard_port": 8501, "project_root": "<path>", "worktree_path": "<worktree_path>"}
```

### Step 10: Spawn background supervisor

Read the file `references/supervisor-prompt.md` from the skill directory (use the Glob tool to find `~/.claude/skills/autorefine/references/supervisor-prompt.md`). Inject these values into the template:

- `{project_root}` → WORKTREE_PATH absolute path (the worktree, where all work happens)
- `{branch}` → the branch name created in step 4
- `{baseline_scores}` → the baseline scores from step 7 (tail -25 of eval.log)
- `{max_iterations}` → 30 (default)

Then spawn a background Agent:

```
Agent(
  description: "autorefine background loop",
  prompt: <the assembled supervisor prompt>,
  run_in_background: true
)
```

### Step 11: Return to user

Tell the user:

> "autorefine is running in the background on branch `autorefine/<tag>`.
> Dashboard: http://localhost:8501
> To check progress: `/autorefine status`
> To stop: `/autorefine stop`
> I'll notify you when it converges."

## Handler: /autorefine status

1. Find PROJECT_ROOT (same as step 1 above)
2. Read `eval_state.json` — show iteration count, best score, cumulative cost, consecutive discards
3. Read last 5 lines of `tried_strategies.log` — show recent attempts
4. Read last entry of `eval_history.jsonl` — show latest per-dimension scores

## Handler: /autorefine stop

1. Find PROJECT_ROOT
2. Read `.autorefine.lock` for dashboard port and worktree path
3. Kill dashboard: `lsof -ti:<port> | xargs kill 2>/dev/null`
4. Remove `.autorefine.lock`
5. Clean up worktree (optional — ask user): `cd PROJECT_ROOT && git worktree remove .autorefine-worktree`
6. Report: "autorefine stopped. Results in .autorefine-worktree/results.tsv. Branch: <branch>. To merge: `git merge <branch>`"

Note: The background agent will naturally stop when its context ends or on the next iteration when it can't acquire the eval lock.

## Handler: /autorefine resume

1. Find PROJECT_ROOT
2. Check that `eval_state.json` exists (there's state to resume from)
3. Read current state — show iteration count, best score
4. Start dashboard if not running
5. Create new lock file
6. Spawn background supervisor (same as step 10 of /autorefine run)
7. Report: "Resuming from iteration {N}. Dashboard: http://localhost:8501"
