# autorefine — technical evaluation papers

Autonomous refinement of technical papers and whitepapers for due-diligence reviewers.

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

LOOP FOREVER:

1. Read the last evaluation: `tail -25 eval.log`
2. Identify the **weakest dimension** (the lowest-scoring or failing dimension across all artifacts).
3. Make **ONE targeted refinement** to improve that dimension.
4. Commit: `git add artifacts/ && git commit -m "brief description"`
5. Evaluate: `uv run evaluate.py > eval.log 2>&1`
6. Read verdict: `grep "^verdict:" eval.log`
7. Act on verdict:
   - **KEEP** — Change improved the score. Next iteration.
   - **DISCARD** — Didn't help. evaluate.py handles reverts automatically on DISCARD. Never run git reset yourself.
   - **INVALID** — Placeholder removed or artifact broken. evaluate.py handles reverts automatically on DISCARD. Never run git reset yourself. Fix the issue in a new commit.
   - **CONVERGED** — Scores plateaued. **Stop** and report final results.
   - **BASELINE** — First run recorded. Begin refining.
8. If exit code 2 — infrastructure error (API timeout). Wait 30s, retry step 5. Do NOT discard.
9. Repeat from step 1.

## Strategy — Technical Papers

**Target the weakest dimension.** Look at per-dimension results. Focus on the lowest-scoring or failing dimension.

**Methodology first.** If `methodology_rigor` fails, fix it before touching anything else. A technical reader who cannot assess the methodology will discount everything that follows. State what was measured, how, with what tools, in what environment, and why the approach was chosen over alternatives.

**Add context to every number.** Every quantitative claim needs: sample size or dataset description, baseline or comparison point, and qualification of uncertainty. "Latency improved 40%" means nothing without "from X to Y, measured over N requests, p95, under Z load conditions."

**Make it reproducible.** For every procedure described, ask: "Could someone outside my team follow this?" If not, add the missing configuration, environment, or dataset details. Where exact reproduction is impossible (proprietary data, specific infrastructure), say so explicitly and describe what an approximation would look like.

**Disclose limitations aggressively.** Technical reviewers respect honesty and distrust papers that only show wins. For every positive claim, ask: "Under what conditions does this NOT hold?" State those conditions. This is not weakness — it is precision.

**Structure as a logical chain.** Each section should establish something the next section depends on. If a reader could skip a section without losing the thread, that section is misplaced. Reorder to create a dependency chain: context, methodology, results, analysis, limitations.

**Figures must earn their space.** Every figure or table should convey information that text alone cannot. Reference each figure in the body text and explain what the reader should take away from it. Remove decorative visuals.

**One change per iteration.** Rewrite one methodology section, add context to one set of numbers, restructure one logical dependency. Small changes are easier to evaluate.

**Every 3rd iteration, try something bold.** Restructure the entire argument flow, merge redundant sections, or split an overloaded section. Radical changes escape local optima.

**Preserve nuance.** Never delete hedged claims, honest limitations, caveats about generalizability, or negative results. These are features, not bugs. Move them to better locations — don't remove them.

## Rules

- **Placeholders are sacred.** Every `{PLACEHOLDER}` must be preserved exactly. The evaluator validates this mechanically.
- **No padding.** Don't add boilerplate ("About This Document", "Executive Summary", "Glossary") to game scores.
- **No corporate voice.** Write like an engineer presenting findings — direct, precise, evidence-based.
- **Don't game the rubric.** Write for the actual technical reviewer, not the judge prompt.
- **Git discipline.** Always commit before evaluating. evaluate.py handles reverts automatically on DISCARD. Never run git reset yourself.

## Anti-patterns

- Don't remove statistical caveats to simplify the narrative
- Don't add methodology details that weren't actually used
- Don't abstract the reproduction section so much that claims become unverifiable
- Don't overclaim -- "achieves state-of-the-art" requires evidence

**NEVER STOP** unless the verdict is CONVERGED. Do not pause to ask the human. They may be away. If you run out of ideas, use `--verbose` to get per-dimension rationales, then try new angles.
