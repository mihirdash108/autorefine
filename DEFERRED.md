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
