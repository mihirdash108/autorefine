# Refinement Program: Project Rules (CLAUDE.md)

## Strategy

CLAUDE.md files are behavioral contracts between a developer and an AI agent. Every rule must be specific enough to follow mechanically and justified enough to apply in unstated situations. Refinement focuses on eliminating ambiguity, resolving conflicts, and adding rationale.

### Refinement priorities (in order)

1. **Rule clarity** — Find every rule that two agents could interpret differently. Replace vague language with specific criteria. "Be careful with" becomes "do not X unless Y." "Handle appropriately" becomes the actual handling instruction.

2. **Actionability** — Find every rule that requires judgment the agent does not have. The agent does not know your project's conventions by instinct — it only knows what the rules say. If a rule says "use good naming conventions," specify what those conventions are.

3. **Internal consistency** — Check all rules that touch the same domain (git, database, file creation, testing). Look for contradictions. If two rules conflict, either merge them with explicit priority ordering or remove one.

4. **Rationale** — For every rule, add a short "because X" clause if one is missing. The rationale enables the agent to handle novel situations the rule did not anticipate. Without rationale, rules are brittle — they work only for the exact case they describe.

5. **Edge cases** — For each rule, ask: "What happens when this rule cannot be followed?" Add the exception handling directly into the rule.

### Recommended iterations

- **Iterations 1-2**: Focus on clarity and actionability. Rewrite vague rules, add decision criteria.
- **Iterations 3-4**: Focus on consistency and rationale. Resolve conflicts, add "because" clauses.
- **Iteration 5**: Focus on edge case coverage. For each rule, define the exception path.

## Anti-patterns

- **Don't evaluate tone or writing style.** Whether rules are written as bullet points, numbered lists, or prose paragraphs does not affect their quality. A terse rule that is unambiguous beats a polished paragraph that leaves room for interpretation.

- **Don't add rules for things the agent already does correctly.** Every rule has a cognitive cost — the agent must parse and remember it. Adding "always check if a file exists before reading it" is wasted space if the agent's tooling already handles missing files gracefully. Only add rules that correct actual failure modes.

- **Don't make rules longer to pass clarity — make them more specific instead.** A vague rule with three paragraphs of elaboration is still vague. A one-line rule with a precise condition and action is clear. Length is not clarity.

- **Don't add catch-all rules.** Rules like "always be careful", "use common sense", or "follow best practices" are unenforceable and provide no actionable guidance. If there is a specific best practice worth following, state the practice explicitly.
