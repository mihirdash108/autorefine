# Contributing to autorefine

## Setup

```bash
git clone https://github.com/mihirdash108/autorefine.git
cd autorefine
uv sync --dev          # includes pytest
bash scripts/install-hooks.sh  # security hooks
```

## Running tests

```bash
pytest tests/ -v
```

## Before submitting a PR

1. **Security audit must pass:** `bash scripts/audit.sh`
2. **Tests must pass:** `pytest tests/ -v`
3. **No proprietary content:** If you have a custom `.audit-blocklist`, ensure your terms don't appear
4. **Python files compile:** `python -m py_compile evaluate.py calibrate.py dashboard.py`

## Adding a template

Templates live in `templates/<name>/`. Each template needs:

```
templates/<name>/
├── rubric.yaml          # Binary mode dimensions (3-5)
├── program.md           # Refinement strategy + anti-patterns section
└── artifacts/
    └── example-*.md     # Working example artifact with deliberate quality gaps
```

Follow existing templates for conventions. The example artifact should produce meaningful scores — some dimensions should FAIL on baseline to demonstrate value.

## Code style

- No linter configured yet — keep it consistent with existing code
- evaluate.py is the core — changes here need test coverage
- Keep dashboard.py as a single file with no external dependencies beyond stdlib

## Reporting issues

Open an issue with: what you expected, what happened, and your eval.log output (redact any sensitive content).
