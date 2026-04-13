# Deferred Issues

Known limitations and potential fixes that are parked for later.

## Background agent cannot ask user questions

**Status:** Deferred — low priority until testing shows frequent stuck states.

**Problem:** Claude Code background agents cannot use `AskUserQuestion` — it's explicitly unavailable in subagents. If the refinement agent gets stuck on something it could resolve with a single clarification (e.g., "this section references a product feature that doesn't appear elsewhere — should I add context or remove the reference?"), it has no way to ask. It either makes its best judgment or stops via convergence.

**Potential fix:** File-based question channel.

1. Agent writes question to `.autorefine-question` file and polls for `.autorefine-answer`
2. Dashboard shows the question prominently in the activity feed
3. User answers via `/autorefine answer "do X"` which writes the answer file
4. Agent reads answer, deletes both files, continues the loop

**Why deferred:** With a good rubric and `tried_strategies.log`, the agent rarely needs to ask. The `CONVERGED` verdict handles the "genuinely stuck" case. Revisit if real-world testing shows the agent frequently hitting situations where one question would unblock multiple iterations.

**Implementation notes:**
- Add `check_for_question()` poll at the start of each iteration in supervisor prompt
- Add `/autorefine answer` subcommand to SKILL.md
- Dashboard needs a "Question pending" banner with input field
- Timeout: if no answer within 10 minutes, agent makes its best judgment and logs it

## Split evaluate.py into modules

**Status:** Deferred — cosmetic/maintainability. No functional impact.

**Problem:** evaluate.py is 996 lines with ~8 responsibilities: backend detection, rubric loading, placeholder handling, binary eval, scale eval, cross-doc eval, state management, and the main loop. Works fine but is hard for contributors to navigate.

**Potential fix:** Split into `autorefine/backends.py`, `autorefine/scoring.py`, `autorefine/state.py`, `autorefine/placeholders.py`, `autorefine/rubric.py`. evaluate.py becomes a thin orchestrator (~200 lines) importing from the package.

**Why deferred:** Users never edit evaluate.py (it's read-only for the agent). The monolith works. Split when contributions increase or the file grows past ~1500 lines.

## Parallel API calls for dimension evaluation

**Status:** Deferred — performance optimization, not correctness.

**Problem:** Each dimension is evaluated N=3 times sequentially. With 5 dimensions, that's 15 serial API calls per iteration (1-3s each = 30-60s). The calls are fully independent and could be parallelized with `concurrent.futures.ThreadPoolExecutor`.

**Potential fix:** Add `eval_all_dimensions()` wrapper that submits all dimension evals to a thread pool. Would cut iteration time from 30-60s to 5-10s.

**Why deferred:** Iterations still complete in under a minute. The bottleneck is the LLM synthesis, not the parallelism. Fix when users report iteration time as a pain point.

## Cost tracking accuracy gaps

**Status:** Deferred — low impact for most users.

**Problem:** `COST_PROFILES` hardcodes prices for a handful of models (gpt-4o, gpt-4o-mini, claude-sonnet-4-6, claude-haiku-4-5) and falls back to GPT-4o pricing for everything else. Users running gpt-4-turbo, claude-opus, or Gemini models get silently wrong cost estimates. A user running a tight `--budget-cap` could overspend.

**Potential fix:** Add a disclaimer in output when using fallback pricing. Or make cost profiles configurable in rubric.yaml.

## Convergence thresholds not configurable

**Status:** Deferred — minor usability issue.

**Problem:** `SCALE_IMPROVEMENT_THRESHOLD` (0.2), `HIGH_SCORE_CONVERGENCE` (0.95), and `MAX_CONSECUTIVE_DISCARDS` (5) are hardcoded in evaluate.py. Users can't tune these from rubric.yaml.

**Potential fix:** Expose as optional fields in rubric.yaml: `improvement_threshold`, `convergence_score`, `max_consecutive_discards`.

## Claude Code skill directory underdocumented

**Status:** Deferred — only affects users who want to understand skill internals.

**Problem:** README mentions `/autorefine` subcommands but doesn't explain the skill file structure (SKILL.md, supervisor-prompt.md, iteration-subagent-prompt.md).

**Potential fix:** Add a "Skill internals" section to README or a separate SKILL-ARCHITECTURE.md.

## Anthropic model default will go stale

**Status:** Deferred — minor.

**Problem:** Default Anthropic model is hardcoded as `claude-sonnet-4-6`. Model names change with new releases.

**Potential fix:** Note in .env.example to always set the model explicitly.

## calibrate.py import side effects

**Status:** Deferred — minor technical debt.

**Problem:** calibrate.py imports from evaluate.py, which triggers `load_dotenv` and other top-level side effects on every import. Works but is architecturally unclean.

**Potential fix:** Resolves automatically when evaluate.py is split into modules (the shared logic moves to a package with no side effects).
