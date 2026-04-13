# Refinement Program: Claude Code Skills

## Strategy

Claude Code skills are behavioral specifications — they tell an AI agent *what to do*, *when to do it*, and *how to handle problems*. Refinement focuses on making the skill reliable and predictable, not on making it read well.

### Refinement priorities (in order)

1. **Trigger precision** — A skill that fires when it shouldn't is worse than one that occasionally misses. Tighten the description field so it activates on specific intent, not keyword overlap. Test the description against 3 mental scenarios: one where the skill should fire, one where it should not, and one ambiguous case.

2. **Instruction specificity** — Replace every instance of vague language ("handle as needed", "use appropriate tools") with concrete instructions. If the agent would need to make a judgment call, the skill is underspecified. Provide the decision criteria directly.

3. **Error paths** — For every tool call in the skill, ask: "What if this fails?" If the answer isn't in the skill text, add it. Common failures: file not found, tool returns empty result, permission denied, unexpected format.

4. **Decomposition clarity** — Each step should have exactly one responsibility. If a step says "analyze and then update", split it into two steps. Make dependencies between steps explicit ("Step 3 uses the file list from Step 1").

5. **Minimal permissions** — Remove any allowed-tool that isn't used in the instructions. If the skill only reads files and runs searches, it should not have Write, Edit, or Bash.

### Recommended iterations

- **Iterations 1-2**: Focus on trigger accuracy and instruction completeness. These are the highest-impact dimensions.
- **Iterations 3-4**: Focus on error handling. Walk through each tool call and add failure paths.
- **Iterations 5-6**: Focus on task decomposition and capability scoping. Split overloaded steps, remove unused permissions.
- **Iteration 7**: Final pass across all dimensions. Fix any regressions from earlier changes.

## Anti-patterns

- **Don't make trigger descriptions less specific to match more cases.** Specificity is a feature, not a bug. A skill that fires precisely on 5 valid cases is better than one that fires on 20 cases including 15 false positives. If the skill is missing valid cases, add them explicitly to the description rather than broadening the language.

- **Don't add instructions that assume prior conversation context.** Skills start fresh. They have no access to what the user said before invoking them. Every piece of information the skill needs must come from its arguments, from tool calls it makes, or from explicit file paths. Never reference "the current discussion" or "what was mentioned earlier."

- **Don't use aspirational constraints.** Phrases like "try to be careful", "aim for minimal changes", or "be thoughtful about side effects" are unenforceable. Replace with concrete rules: "Do NOT modify files outside the artifacts/ directory", "Do NOT create new files unless the instruction explicitly requires it."

- **Don't evaluate formatting or style.** Skills are about behavior — do the right tools get called, in the right order, with the right parameters? Whether the skill text uses headers or bullet points is irrelevant to its quality as a behavioral specification.
