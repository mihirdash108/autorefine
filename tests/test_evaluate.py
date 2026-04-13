"""Tests for evaluate.py core logic — no LLM calls needed."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluate import (
    find_placeholders,
    validate_placeholders,
    preprocess_placeholders,
    parse_json_response,
    validate_rubric,
)


# ---------------------------------------------------------------------------
# Placeholder tests
# ---------------------------------------------------------------------------

class TestPlaceholders:
    def test_find_placeholders_basic(self):
        text = "Score is {FAITH} and retrieval is {ENT_RET}ms"
        assert find_placeholders(text) == {"FAITH", "ENT_RET"}

    def test_find_placeholders_empty(self):
        assert find_placeholders("no placeholders here") == set()

    def test_find_placeholders_ignores_lowercase(self):
        text = "{good} {BAD} {Also_Bad}"
        # Only uppercase with optional digits/underscores
        assert "BAD" in find_placeholders(text)
        assert "good" not in find_placeholders(text)

    def test_validate_placeholders_all_present(self):
        baseline = {"doc.md": ["FAITH", "SCORE"]}
        current = "Values: {FAITH} and {SCORE} and {EXTRA}"
        assert validate_placeholders("doc.md", current, baseline) == []

    def test_validate_placeholders_missing(self):
        baseline = {"doc.md": ["FAITH", "SCORE", "EXTRA"]}
        current = "Value: {FAITH}"
        missing = validate_placeholders("doc.md", current, baseline)
        assert "EXTRA" in missing
        assert "SCORE" in missing

    def test_validate_placeholders_no_baseline(self):
        assert validate_placeholders("doc.md", "text", {}) == []

    def test_preprocess_basic(self):
        text = "Score: {FAITH}, Time: {RET}"
        mocks = {"FAITH": "0.94", "RET": "806"}
        result = preprocess_placeholders(text, mocks)
        assert result == "Score: 0.94, Time: 806"

    def test_preprocess_unknown_kept(self):
        text = "{KNOWN} and {UNKNOWN}"
        result = preprocess_placeholders(text, {"KNOWN": "yes"})
        assert result == "yes and {UNKNOWN}"


# ---------------------------------------------------------------------------
# JSON parsing tests
# ---------------------------------------------------------------------------

class TestJsonParsing:
    def test_parse_clean_json(self):
        raw = '{"score": 8, "rationale": "Good document"}'
        result = parse_json_response(raw)
        assert result["score"] == 8

    def test_parse_with_markdown_fences(self):
        raw = '```json\n{"score": 5, "rationale": "OK"}\n```'
        result = parse_json_response(raw)
        assert result["score"] == 5

    def test_parse_with_whitespace(self):
        raw = '  \n  {"verdict": "pass"}  \n  '
        result = parse_json_response(raw)
        assert result["verdict"] == "pass"

    def test_parse_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_json_response("not json at all")

    def test_parse_truncated_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_json_response('{"score": 8, "ration')


# ---------------------------------------------------------------------------
# Rubric validation tests
# ---------------------------------------------------------------------------

class TestRubricValidation:
    def _make_artifacts(self, tmp_path, names):
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        files = []
        for name in names:
            f = artifacts_dir / name
            f.write_text("test content")
            files.append(f)
        return files

    def test_valid_binary_rubric(self, tmp_path):
        files = self._make_artifacts(tmp_path, ["doc.md"])
        rubric = {
            "artifacts": {
                "doc.md": {
                    "dimensions": {
                        "clarity": {"pass": "Clear", "fail": "Unclear"}
                    }
                }
            }
        }
        # Should not raise
        validate_rubric(rubric, files, "binary")

    def test_missing_artifact_file(self, tmp_path):
        files = self._make_artifacts(tmp_path, ["other.md"])
        rubric = {
            "artifacts": {
                "missing.md": {
                    "dimensions": {"clarity": {"pass": "Clear"}}
                }
            }
        }
        with pytest.raises(SystemExit):
            validate_rubric(rubric, files, "binary")

    def test_missing_pass_in_binary(self, tmp_path):
        files = self._make_artifacts(tmp_path, ["doc.md"])
        rubric = {
            "artifacts": {
                "doc.md": {
                    "dimensions": {
                        "clarity": {"description": "How clear"}  # no pass/fail
                    }
                }
            }
        }
        with pytest.raises(SystemExit):
            validate_rubric(rubric, files, "binary")

    def test_missing_description_in_scale(self, tmp_path):
        files = self._make_artifacts(tmp_path, ["doc.md"])
        rubric = {
            "artifacts": {
                "doc.md": {
                    "dimensions": {
                        "clarity": {"pass": "Clear"}  # no description for scale
                    }
                }
            }
        }
        with pytest.raises(SystemExit):
            validate_rubric(rubric, files, "scale")

    def test_no_artifacts_section(self, tmp_path):
        files = self._make_artifacts(tmp_path, ["doc.md"])
        rubric = {}
        with pytest.raises(SystemExit):
            validate_rubric(rubric, files, "binary")

    def test_empty_dimensions(self, tmp_path):
        files = self._make_artifacts(tmp_path, ["doc.md"])
        rubric = {
            "artifacts": {
                "doc.md": {"dimensions": {}}
            }
        }
        with pytest.raises(SystemExit):
            validate_rubric(rubric, files, "binary")
