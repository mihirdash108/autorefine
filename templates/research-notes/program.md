# autorefine — research notes

Autonomous refinement of research documents, literature reviews, and competitive analyses.

## Setup

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `apr13`). The branch `autorefine/<tag>` must not already exist.
2. **Create the branch**: `git checkout -b autorefine/<tag>` from current main.
3. **Read the in-scope files**:
   - `program.md` — this file. Your instructions.
   - `rubric.yaml` — evaluation criteria. Read to understand what the judge values. DO NOT modify.
   - `evaluate.py` — fixed evaluation engine. DO NOT modify.
   - All files in `artifacts/` — the research documents you will refine.
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

LOOP FOREVER:

1. Read the last evaluation: `tail -25 eval.log`
2. Identify the **weakest dimension** (the lowest-scoring or failing dimension across all artifacts).
3. Make **ONE targeted refinement** to improve that dimension.
4. Commit: `git add artifacts/ && git commit -m "brief description"`
5. Evaluate: `uv run evaluate.py > eval.log 2>&1`
6. Read verdict: `grep "^verdict:" eval.log`
7. Act on verdict:
   - **KEEP** — Change improved the score. Next iteration.
   - **DISCARD** — Didn't help. Revert: `git reset --hard HEAD~1`
   - **INVALID** — Placeholder removed or artifact broken. Revert and fix.
   - **CONVERGED** — Scores plateaued. **Stop** and report final results.
   - **BASELINE** — First run recorded. Begin refining.
8. If exit code 2 — infrastructure error (API timeout). Wait 30s, retry step 5. Do NOT discard.
9. Repeat from step 1.

## Strategy — Research Documents

**Target the weakest dimension.** Look at per-dimension results. Focus on the lowest-scoring or failing dimension.

**Fix accuracy before everything else.** If `accuracy` fails, nothing else matters. A research document with errors destroys trust. Verify every claim: is it precise? Is it current? Are similar-but-distinct concepts properly separated? Flag anything you cannot verify with "unverified" or "as of [date]."

**Close coverage gaps explicitly.** If `coverage` fails, either add the missing perspective or explicitly state that it is out of scope and why. "We did not evaluate X because Y" is better than silence. A reader who notices a gap will assume incompetence; a reader who sees a justified exclusion assumes rigor.

**Attribute everything.** For every claim, the reader should be able to answer: "Where did this come from?" Separate sourced facts, author analysis, and author opinion. Make sources specific enough to check — "v2.3 documentation, pricing page as of March 2024" beats "according to their website."

**Synthesize, don't list.** The difference between a useful research document and a Wikipedia article is cross-cutting analysis. After laying out facts, ask: "What pattern do I see across these sources? Where do they contradict each other? What structural difference explains why approach A and approach B make different trade-offs?" Write those insights down. They are the document's primary value.

**Make it actionable.** Every section should move the reader closer to a decision. After each major finding, ask: "So what? What should the reader do with this information?" Tie recommendations directly to the evidence that supports them. "Consider X because finding Y shows Z" beats "consider X."

**Preserve nuance and uncertainty.** Never flatten a complex finding into a simple recommendation. If the evidence is mixed, say so. If a claim depends on context, specify the context. Research that oversimplifies is worse than research that acknowledges complexity.

**One change per iteration.** Add one missing perspective, attribute one section's claims, or synthesize one comparison. Small changes are easier to evaluate.

**Every 10th iteration, try something bold.** Restructure the document around decision criteria instead of topics, merge redundant sections, or rewrite the synthesis from scratch. Radical changes escape local optima.

## Rules

- **Placeholders are sacred.** Every `{PLACEHOLDER}` must be preserved exactly. The evaluator validates this mechanically.
- **No padding.** Don't add boilerplate ("Research Overview", "Methodology Note", "Disclaimer") to game scores.
- **No false precision.** Don't invent specific numbers or dates to appear more rigorous. If you don't know something, say so.
- **Don't game the rubric.** Write for the actual decision-maker, not the judge prompt.
- **Git discipline.** Always commit before evaluating. On DISCARD: `git reset --hard HEAD~1`. Never `git clean`.

**NEVER STOP** unless the verdict is CONVERGED. Do not pause to ask the human. They may be away. If you run out of ideas, use `--verbose` to get per-dimension rationales, then try new angles.
