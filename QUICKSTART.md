# Quickstart — First Score in 5 Minutes

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`), one LLM API key.

```bash
# 1. Clone and install
git clone https://github.com/mihirdash108/autorefine.git
cd autorefine
uv sync

# 2. Add your API key
cp .env.example .env
# Edit .env — uncomment ONE backend and add your key:
#   OPENAI_API_KEY=sk-...
#   or AZURE_OPENAI_ENDPOINT=... + AZURE_OPENAI_API_KEY=...
#   or ANTHROPIC_API_KEY=sk-ant-... (also run: uv add anthropic)

# 3. Validate setup (zero API calls, zero cost)
uv run evaluate.py --dry-run

# 4. Run baseline on the shipped example
uv run evaluate.py --baseline --verbose
# You'll see 4 dimensions scored on a sample product page.
# "specificity" and "evidence_quality" should FAIL — the example
# has deliberate gaps like "our customers love it" with no evidence.

# 5. (Optional) Start the dashboard
uv run dashboard.py &
open http://localhost:8501
```

That's it. You've seen autorefine score a document.

## Next: use your own document

```bash
# Pick a template that matches your use case
bash scripts/init.sh --template llm-skill --artifact my-prompt.md

# Or manually:
cp templates/llm-skill/rubric.yaml .
cp templates/llm-skill/program.md .
cp my-prompt.md artifacts/
# Edit rubric.yaml: change the artifact name to match your file

# Validate, then run
uv run evaluate.py --dry-run
uv run evaluate.py --baseline --verbose
```

## Start the refinement loop

Open Claude Code (or any coding agent) in the autorefine directory:

```
claude
> Read program.md and let's kick off a refinement run.
```

Or with the Claude Code skill installed (`cp -r skill/ ~/.claude/skills/autorefine/`):

```
/autorefine
```

See [README.md](README.md) for full documentation, rubric writing guide, and LLM-as-judge best practices.
