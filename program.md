# autorefine

Autonomous document refinement using an LLM-as-judge evaluation loop.
Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch).

## Setup

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `apr13`). The branch `autorefine/<tag>` must not already exist.
2. **Create the branch**: `git checkout -b autorefine/<tag>` from current main.
3. **Read the in-scope files**:
   - `program.md` — this file. Your instructions.
   - `rubric.yaml` — evaluation criteria. Read to understand what the judge values. DO NOT modify.
   - `evaluate.py` — fixed evaluation engine. DO NOT modify.
   - All files in `artifacts/` — the documents you will refine.
4. **Run baseline**: `uv run evaluate.py --baseline > eval.log 2>&1`
5. **Read results**: `tail -25 eval.log`
6. **Confirm and go**: Confirm setup with the user.

## What You Can and Cannot Do

**CAN:** Modify any file in `artifacts/`. Restructure, rewrite, improve, reorganize.

**CANNOT:**
- Modify `evaluate.py`, `rubric.yaml`, `program.md`
- Install packages or add dependencies
- Modify `results.tsv` or `eval_state.json` (managed by evaluate.py)
- Remove `{PLACEHOLDER}` values (mechanically validated)

## The Goal

**Get the highest combined_score.** The evaluation engine handles scoring, comparison, and verdicts. You read the verdict and act on it.

## The Loop

The evaluation engine enforces git discipline mechanically:
- It **refuses to run** if you have uncommitted artifact changes (forces you to commit first).
- It **auto-reverts** on DISCARD or CONVERGED (you never need to run `git reset` yourself).

Your job is just: **edit → commit → evaluate → read verdict → repeat.**

LOOP FOREVER:

1. Read the last evaluation: `tail -25 eval.log`
2. Identify the **weakest dimension** (the lowest-scoring or failing dimension across all artifacts).
3. Make **ONE targeted refinement** to improve that dimension.
4. Commit: `git add artifacts/ && git commit -m "brief description"`
5. Evaluate: `uv run evaluate.py > eval.log 2>&1`
6. Read verdict: `grep "^verdict:" eval.log`
7. Act on verdict:
   - **KEEP** — Change improved the score. Next iteration.
   - **DISCARD** — Auto-reverted. Your change was undone. Try a different approach.
   - **INVALID** — Auto-reverted. A placeholder was removed or artifact is broken. Fix the issue.
   - **CONVERGED** — Auto-reverted. Scores have plateaued. **Stop** and report final results.
   - **BASELINE** — First run recorded. Begin refining.
8. If exit code 2 — infrastructure error (API timeout). Wait 30s, retry step 5. Your change is still committed.
9. Repeat from step 1.

## Strategy

**Target the weakest dimension.** Look at per-dimension results. Focus on the lowest-scoring or failing dimension.

**Alternate between artifacts.** Never make >3 consecutive changes to the same artifact.

**One change per iteration.** One focused edit — rewrite a section, sharpen an argument, restructure a table. Small changes are easier to evaluate.

**Every 10th iteration, try something bold.** Reorder sections, merge content, restructure the flow. Radical changes escape local optima.

**Preserve content, improve presentation.** Never delete nuanced arguments, honest limitations, or specific data. Move content — don't delete it.

**Maintain cross-document consistency.** When you change a claim in one document, verify it's consistent with the others.

## Rules

- **Placeholders are sacred.** Every `{PLACEHOLDER}` must be preserved exactly. The evaluator validates this mechanically.
- **No padding.** Don't add boilerplate to game scores.
- **No corporate voice.** Write like the person who built it — direct, specific, opinionated.
- **Don't game the rubric.** Write for the actual human reader, not the judge prompt.
- **Git discipline.** Always commit before evaluating (evaluate.py enforces this). Reverts are automatic — never run `git reset` or `git clean` yourself.

**NEVER STOP** unless the verdict is CONVERGED. Do not pause to ask the human. They may be away. If you run out of ideas, use `--verbose` to get per-dimension rationales, then try new angles.
