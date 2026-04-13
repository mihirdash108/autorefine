# Changelog

All notable changes to autorefine are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.0] — 2026-04-13

### Added
- Core evaluation engine (`evaluate.py`) with binary and scale modes
- Multi-backend LLM support: OpenAI, Azure OpenAI, Anthropic, Ollama
- N=3 evaluation with majority vote (binary) or median (scale)
- Rubric schema validation and `--dry-run` flag
- `--max-iterations` support via rubric.yaml
- Placeholder preprocessing and mechanical validation
- Cross-document consistency checking
- Git-based keep/discard with auto-revert (SHA-based, not HEAD~1)
- Atomic state writes (eval_state.json)
- Eval lock file to prevent concurrent evaluations
- Convergence detection (consecutive discards + high score threshold)
- Checkpoint snapshots on every KEEP for version diffing
- Browser dashboard (`dashboard.py`) with 9 charts + live activity feed
- Activity log (`activity_log.jsonl`) for real-time observability
- Rubric calibration tool (`calibrate.py`)
- Claude Code skill (`/autorefine`) with background supervisor + iteration subagents
- Subcommands: `/autorefine run`, `status`, `stop`, `resume`
- Security audit script with configurable blocklist
- Pre-commit and pre-push hooks via `scripts/install-hooks.sh`
- 7 template rubrics: claude-skill, project-rules, mcp-tools, llm-skill, product-doc, technical-paper, research-notes
- Example artifacts with deliberate quality gaps for each template
- `start.sh` launcher and `scripts/init.sh` scaffolding
- QUICKSTART.md, CONTRIBUTING.md

### Inspired by
- [karpathy/autoresearch](https://github.com/karpathy/autoresearch) (MIT License)
