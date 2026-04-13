# autorefine — product documentation

Autonomous refinement of product documentation and landing pages for enterprise buyers.

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

## Strategy — Product Documentation

**Target the weakest dimension.** Look at per-dimension results. Focus on the lowest-scoring or failing dimension.

**Lead with the value proposition.** The first two paragraphs decide whether a buyer keeps reading. If `value_proposition` fails, rewrite the opening before anything else. State the problem, then the solution, in concrete terms.

**Replace adjectives with evidence.** Every time you find a generic claim ("fast", "scalable", "easy"), replace it with a concrete detail: a number, a benchmark, an architecture fact, or a named integration. Specificity is the difference between a page that sells and a page that gets skimmed.

**Make differentiation structural.** Don't just claim you're better — explain the architectural or methodological reason why. "We use X approach, which means Y benefit" is stronger than "unlike others, we deliver Z."

**Write scannable headers.** Replace generic headers ("Features", "Benefits", "How It Works") with specific ones that carry information even if you never read the body text. "Sub-second queries on 10M-row datasets" beats "Performance."

**Kill marketing voice.** Remove superlatives ("best-in-class", "world-class", "cutting-edge") unless immediately followed by evidence. Remove throat-clearing ("In today's fast-paced world..."). Write like an engineer explaining to another engineer what this thing does and why it's good.

**Preserve honest limitations.** Never delete trade-off statements, honest limitations, or "when not to use this" sections. They build trust. Move them if they're poorly placed — don't remove them.

**One change per iteration.** One focused edit — rewrite the opening, sharpen a section, restructure a comparison table. Small changes are easier to evaluate.

**Every 3rd iteration, try something bold.** Reorder sections, merge content, restructure the information hierarchy. Radical changes escape local optima.

## Rules

- **Placeholders are sacred.** Every `{PLACEHOLDER}` must be preserved exactly. The evaluator validates this mechanically.
- **No padding.** Don't add boilerplate ("About This Document", "Executive Summary", "Glossary") to game scores.
- **No corporate voice.** Write like the person who built it — direct, specific, opinionated. Not like a press release.
- **Don't game the rubric.** Write for the actual human buyer, not the judge prompt.
- **Git discipline.** Always commit before evaluating. evaluate.py handles reverts automatically on DISCARD. Never run git reset yourself.

## Anti-patterns

- Don't add boilerplate sections (Executive Summary, Glossary)
- Don't rewrite in corporate marketing voice
- Don't remove honest limitations -- they build credibility
- Don't add claims without supporting evidence

**NEVER STOP** unless the verdict is CONVERGED. Do not pause to ask the human. They may be away. If you run out of ideas, use `--verbose` to get per-dimension rationales, then try new angles.
