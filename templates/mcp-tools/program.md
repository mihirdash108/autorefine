# Refinement Program: MCP Tool Descriptions

## Strategy

MCP tool descriptions are the interface between an AI agent and external capabilities. The agent reads these descriptions to decide which tool to call, how to call it, and how to interpret the result. Refinement focuses on precision and completeness, not readability.

### Refinement priorities (in order)

1. **Disambiguation** — Compare the tool description against what other tools in a typical registry might do. Add explicit boundary statements: "Use this tool for X. Do NOT use this tool for Y — use [alternative] instead." The agent must be able to pick the right tool from a list of 20+ options based on description alone.

2. **Parameter documentation** — For every parameter, ensure: type is specified, constraints are listed (min/max, allowed values, format patterns), default value is stated or explicitly marked as required, and at least one example value is shown. Parameters without types are the single most common cause of malformed tool calls.

3. **Error documentation** — Document every failure mode the agent might encounter. At minimum: what happens with invalid input, what happens when the backing service is unavailable, what the error response shape looks like. The agent needs this to build retry logic and fallback paths.

4. **Return value documentation** — Document the success response structure with field names, types, and an example. Document the error response structure separately. If the return shape varies by input, document each variant.

5. **Examples** — Include at least two examples: one common case and one edge case (empty results, error, boundary input). Examples are the fastest way for the agent to learn correct usage patterns.

### Recommended iterations

- **Iterations 1-2**: Focus on disambiguation and parameter documentation. These prevent the most common failure mode (wrong tool, wrong parameters).
- **Iteration 3**: Focus on error behavior and return value documentation.
- **Iteration 4**: Focus on example coverage. Add edge case examples.

## Anti-patterns

- **Don't add marketing language to descriptions.** Phrases like "powerful search capabilities" or "seamlessly integrates with" provide zero information to an agent selecting tools. Replace with technical facts: "full-text search with BM25 ranking across indexed documents."

- **Don't make descriptions longer than necessary.** Agents scan many tool descriptions quickly. A 50-word description that covers all five dimensions beats a 500-word description that buries critical information in prose. Use structured formats (parameter tables, example blocks) over narrative paragraphs.

- **Don't add parameters without type specifications.** An untyped parameter is worse than a missing parameter — it invites malformed calls that fail silently or produce wrong results. Every parameter must have an explicit type (string, number, boolean, array, object) and format if applicable.

- **Don't document implementation details.** The agent does not need to know that the tool uses an inverted index internally, or that it connects to a specific database. Describe the interface: what goes in, what comes out, what can go wrong. Implementation details are noise that makes the description harder to scan.
