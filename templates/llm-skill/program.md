# autorefine — LLM skill prompts

Autonomous refinement of system prompts, agent skill definitions, and instruction sets for LLM-based tools.

## Setup

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `apr13`). The branch `autorefine/<tag>` must not already exist.
2. **Create the branch**: `git checkout -b autorefine/<tag>` from current main.
3. **Read the in-scope files**:
   - `program.md` — this file. Your instructions.
   - `rubric.yaml` — evaluation criteria. Read to understand what the judge values. DO NOT modify.
   - `evaluate.py` — fixed evaluation engine. DO NOT modify.
   - All files in `artifacts/` — the skill prompts you will refine.
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

## Strategy — LLM Skill Prompts

**Target the weakest dimension.** Look at per-dimension results. Focus on the lowest-scoring or failing dimension.

**Eliminate ambiguity first.** If `instruction_clarity` fails, fix it before anything else. Every vague verb ("handle", "process", "deal with") should become a specific action ("return a JSON object with...", "refuse the request and explain..."). If two instructions could conflict, add an explicit priority order.

**Think adversarially about edge cases.** For each instruction in the prompt, ask: "What happens if the user sends empty input? Malformed input? A request that violates a constraint? An input in a language the prompt doesn't mention?" Add handling for every case you can think of. You do not need exhaustive coverage — but the obvious failure modes must be addressed.

**Specify output format with examples.** Vague format instructions ("return a structured response") always fail. Show the model exactly what you want: a complete example output for a representative input. For structured formats (JSON, YAML), define every field, its type, and whether it is required or optional.

**Make constraints enforceable.** Replace aspirational guidance ("be careful with X") with concrete rules ("if the input contains X, do Y instead of Z"). Every constraint needs a fallback: what the model should do WHEN the constraint fires, not just what it should avoid.

**Scope tone precisely.** "Be professional" is not tone guidance — it produces inconsistent behavior. Specify: sentence length preference, active vs passive voice, whether hedging language is acceptable, formality level, and whether the model should use first person. If the skill serves multiple contexts, define tone per context.

**Structure prompts hierarchically.** The most important instructions go first. Group related instructions under clear headings. Use numbered rules for sequences and bullet points for unordered sets. A model processes prompts sequentially — put critical constraints before optional preferences.

**One change per iteration.** Rewrite one section of instructions, add handling for one edge case class, or tighten one constraint. Small changes are easier to evaluate.

**Every 10th iteration, try something bold.** Restructure the entire prompt, reorder sections by priority, or reframe the model's role. Radical changes escape local optima.

**Test by simulation.** Before committing a change, mentally simulate: "If I were a model reading this prompt for the first time, with no prior context, what would I do with input X?" If the answer is ambiguous, the prompt needs more work.

## Rules

- **Placeholders are sacred.** Every `{PLACEHOLDER}` must be preserved exactly. The evaluator validates this mechanically.
- **No padding.** Don't add boilerplate ("System Prompt Overview", "About This Skill") to game scores.
- **No meta-commentary.** The prompt should contain instructions, not commentary about the instructions.
- **Don't game the rubric.** Write for the actual model that will execute this prompt, not the judge.
- **Git discipline.** Always commit before evaluating. evaluate.py handles reverts automatically on DISCARD. Never run git reset yourself.

## Anti-patterns

- Don't use aspirational language ("try to be helpful") -- use specific behavioral rules
- Don't evaluate grammar or formatting -- evaluate behavioral compliance
- Don't add output examples that are too rigid -- allow flexibility in phrasing
- Don't remove constraints to improve "instruction clarity" -- constraints are features

**NEVER STOP** unless the verdict is CONVERGED. Do not pause to ask the human. They may be away. If you run out of ideas, use `--verbose` to get per-dimension rationales, then try new angles.
