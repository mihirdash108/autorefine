You are making ONE targeted edit to improve a document's quality on a specific dimension.

## Your task

- **Directory:** {project_root}
- **Artifact to edit:** {artifact_name}
- **Weakest dimension:** {dimension_name}
- **Current score/verdict:** {score}
- **Judge's rationale:** {rationale}
- **Iteration number:** {iteration} {bold_note}

## Previously tried strategies

DO NOT repeat any strategy marked DISCARD — it was already tried and didn't work. Try a completely different approach.

{tried_strategies}

## Instructions

1. Read the artifact file:
   ```
   Read("{project_root}/artifacts/{artifact_name}")
   ```

2. Read the rubric dimension to understand exactly what the judge evaluates:
   ```
   Read("{project_root}/rubric.yaml")
   ```
   Find the dimension `{dimension_name}` and read its pass/fail criteria or score anchors.

3. Make **ONE focused edit** to improve the `{dimension_name}` dimension. Examples of good edits:
   - Reframe a section to better fit the target audience
   - Add a missing transition between sections
   - Restructure a paragraph for clarity
   - Replace vague claims with specific evidence
   - Improve a table's readability

4. Rules:
   - Do NOT modify evaluate.py, rubric.yaml, or program.md
   - Preserve ALL `{{PLACEHOLDER}}` values exactly as they are (e.g., `{{FAITH}}`, `{{ENT_RET}}`)
   - Do NOT add boilerplate sections (Executive Summary, Glossary, About This Document)
   - Do NOT rewrite in generic corporate voice — maintain the document's authentic tone
   - Keep the edit focused — one change, not a full rewrite

5. Commit your change:
   ```
   Bash("cd {project_root} && git add artifacts/ && git commit -m 'brief description of what you changed'")
   ```

6. Report what you changed in 1-2 sentences. This will be logged to tried_strategies.log.
