"""
autorefine evaluation engine — the fixed scoring function.
Scores text artifacts against a YAML rubric using an LLM judge.

This file is READ-ONLY for the refiner agent. Do not modify.

Supports multiple LLM backends:
  - OpenAI (OPENAI_API_KEY)
  - Azure OpenAI (AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY)
  - Anthropic (ANTHROPIC_API_KEY)
  - Ollama (OLLAMA_BASE_URL)
  - Or explicit: AUTOREFINE_BACKEND=openai|azure|anthropic|ollama

Supports two evaluation modes (set in rubric.yaml):
  - binary (default): pass/fail per dimension, majority vote, recommended
  - scale: 1-5 per dimension, median of N

Usage:
    uv run evaluate.py                  # evaluate all artifacts
    uv run evaluate.py --baseline       # record baseline (no comparison)
    uv run evaluate.py --verbose        # show per-dimension rationales
    uv run evaluate.py --budget-cap 50  # max USD to spend (default: $30)

Inspired by karpathy/autoresearch (MIT License).
"""

import argparse
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).parent
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
CHECKPOINTS_DIR = ROOT_DIR / "checkpoints"
RUBRIC_PATH = ROOT_DIR / "rubric.yaml"
STATE_PATH = ROOT_DIR / "eval_state.json"
RESULTS_PATH = ROOT_DIR / "results.tsv"
BASELINE_SNAPSHOTS_PATH = ROOT_DIR / ".baseline_placeholders.json"

MIN_ARTIFACT_BYTES = 100
DEFAULT_BUDGET_CAP = 30.0
EVAL_REPEATS = 3  # N=3 for majority vote (binary) or median (scale)

# Binary mode: KEEP if at least 1 more dimension passes
# Scale mode: KEEP if combined_score improves by >= this threshold
SCALE_IMPROVEMENT_THRESHOLD = 0.2  # on a 1-5 scale
MAX_CONSECUTIVE_DISCARDS = 5
HIGH_SCORE_CONVERGENCE = 0.95  # 95% pass rate (binary) or 4.75/5 (scale)
HIGH_SCORE_CONSECUTIVE_DISCARDS = 3

# Approximate pricing per 1M tokens (for cost tracking)
COST_PROFILES = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
    "default": {"input": 2.50, "output": 10.00},
}

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv(ROOT_DIR / ".env")


def detect_backend():
    """Auto-detect LLM backend from environment variables."""
    explicit = os.getenv("AUTOREFINE_BACKEND", "").lower()
    if explicit:
        return explicit

    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY"):
        return "azure"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("OLLAMA_BASE_URL"):
        return "ollama"

    return None


def create_client():
    """Create the appropriate LLM client based on backend detection."""
    backend = detect_backend()

    if backend == "openai":
        from openai import OpenAI
        return OpenAI(api_key=os.getenv("OPENAI_API_KEY"), max_retries=5, timeout=120), backend

    if backend == "azure":
        from openai import AzureOpenAI
        return AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
            max_retries=5, timeout=120,
        ), backend

    if backend == "ollama":
        from openai import OpenAI
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434") + "/v1"
        return OpenAI(base_url=base_url, api_key="ollama", max_retries=3, timeout=300), backend

    if backend == "anthropic":
        try:
            from anthropic import Anthropic
            return Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"), max_retries=5), backend
        except ImportError:
            print("ERROR: anthropic package not installed. Run: uv add anthropic")
            sys.exit(2)

    print("ERROR: No LLM backend configured.")
    print("Set one of: OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT+AZURE_OPENAI_API_KEY,")
    print("ANTHROPIC_API_KEY, OLLAMA_BASE_URL, or AUTOREFINE_BACKEND explicitly.")
    print("See .env.example for details.")
    sys.exit(2)


def get_model(rubric, backend):
    """Determine the model name to use."""
    explicit = os.getenv("AUTOREFINE_MODEL")
    if explicit:
        return explicit
    if backend == "azure":
        return os.getenv("AZURE_OPENAI_MODEL", rubric.get("judge_model", "gpt-4o"))
    if backend == "anthropic":
        return os.getenv("ANTHROPIC_MODEL", rubric.get("judge_model", "claude-sonnet-4-6"))
    return rubric.get("judge_model", "gpt-4o")


def load_rubric():
    try:
        with open(RUBRIC_PATH) as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"ERROR: rubric.yaml parse error: {e}")
        sys.exit(2)
    except FileNotFoundError:
        print("ERROR: rubric.yaml not found")
        sys.exit(2)


# ---------------------------------------------------------------------------
# LLM call abstraction
# ---------------------------------------------------------------------------

def judge_call(client, backend, model, system_prompt, user_prompt):
    """Make a single LLM judge call. Returns (content_str, input_tokens, output_tokens)."""
    if backend == "anthropic":
        response = client.messages.create(
            model=model,
            max_tokens=500,
            temperature=0.0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        content = response.content[0].text
        return content, response.usage.input_tokens, response.usage.output_tokens

    # OpenAI-compatible (openai, azure, ollama)
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 500,
    }
    if backend != "ollama":
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content
    return content, response.usage.prompt_tokens, response.usage.completion_tokens


def parse_json_response(raw):
    """Extract JSON from a response that might contain markdown fences."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        json_lines = [l for l in lines if not l.strip().startswith("```")]
        raw = "\n".join(json_lines)
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Placeholder handling
# ---------------------------------------------------------------------------

PLACEHOLDER_RE = re.compile(r"\{([A-Z][A-Z0-9_]*)\}")


def find_placeholders(text):
    return set(PLACEHOLDER_RE.findall(text))


def load_baseline_placeholders():
    if BASELINE_SNAPSHOTS_PATH.exists():
        with open(BASELINE_SNAPSHOTS_PATH) as f:
            return json.load(f)
    return {}


def save_baseline_placeholders(snapshot):
    with open(BASELINE_SNAPSHOTS_PATH, "w") as f:
        json.dump(snapshot, f, indent=2)


def validate_placeholders(artifact_name, current_text, baseline_snapshot):
    if artifact_name not in baseline_snapshot:
        return []
    return sorted(set(baseline_snapshot[artifact_name]) - find_placeholders(current_text))


def preprocess_placeholders(text, mocks):
    def replacer(match):
        key = match.group(1)
        return str(mocks[key]) if key in mocks else match.group(0)
    return PLACEHOLDER_RE.sub(replacer, text)


# ---------------------------------------------------------------------------
# Evaluation — Binary mode
# ---------------------------------------------------------------------------

def build_binary_prompt(artifact_text, artifact_context, dim_name, dim_config):
    pass_desc = dim_config.get("pass", dim_config.get("description", ""))
    fail_desc = dim_config.get("fail", "")
    criteria = f"**Pass criteria:** {pass_desc}"
    if fail_desc:
        criteria += f"\n**Fail criteria:** {fail_desc}"

    return f"""Evaluate the following document on the dimension: **{dim_name}**

{criteria}

**Document context:** {artifact_context}

---
DOCUMENT:
{artifact_text}
---

First, analyze the document against the criteria step by step. Then give your verdict.

Respond with JSON:
{{
  "analysis": "<2-3 sentence step-by-step analysis with specific evidence from the document>",
  "verdict": "pass" or "fail",
  "rationale": "<1 sentence summary>"
}}"""


def eval_dimension_binary(client, backend, model, artifact_text, context, dim_name, dim_config, verbose=False):
    system_prompt = (
        "You are an expert document quality evaluator. You make binary pass/fail "
        "judgments on specific quality dimensions. Be strict and evidence-based. "
        "A 'pass' means the document clearly meets the criteria. "
        "Document length should NOT influence your judgment. "
        "Respond with valid JSON only."
    )
    user_prompt = build_binary_prompt(artifact_text, context, dim_name, dim_config)

    verdicts = []
    rationales = []
    total_inp, total_out = 0, 0

    for _ in range(EVAL_REPEATS):
        try:
            raw, inp, out = judge_call(client, backend, model, system_prompt, user_prompt)
            total_inp += inp
            total_out += out
            parsed = parse_json_response(raw)
            v = str(parsed.get("verdict", "fail")).lower().strip()
            verdicts.append(v == "pass")
            rationales.append(parsed.get("rationale", parsed.get("analysis", "No rationale.")))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            if verbose:
                print(f"  WARN: Parse error for {dim_name}: {e}")
            verdicts.append(False)
            rationales.append("(parse error)")
        except Exception as e:
            print(f"ERROR: API failure scoring {dim_name}: {e}")
            sys.exit(2)

    passed = sum(verdicts) > len(verdicts) / 2
    for i, v in enumerate(verdicts):
        if v == passed:
            return passed, rationales[i], total_inp, total_out
    return passed, rationales[0], total_inp, total_out


# ---------------------------------------------------------------------------
# Evaluation — Scale mode
# ---------------------------------------------------------------------------

def build_scale_prompt(artifact_text, artifact_context, dim_name, dim_config, scale_max):
    anchors_text = ""
    if "anchors" in dim_config:
        for level, desc in sorted(dim_config["anchors"].items()):
            anchors_text += f"  Score {level}: {desc}\n"

    return f"""Evaluate the following document on the dimension: **{dim_name}**

**Dimension definition:** {dim_config['description']}

**Scoring anchors (1-{scale_max} scale):**
{anchors_text if anchors_text else f"  (Use your judgment on a 1-{scale_max} scale)"}

**Document context:** {artifact_context}

---
DOCUMENT:
{artifact_text}
---

First, analyze the document against the criteria step by step. Then give your score.

Respond with JSON:
{{
  "analysis": "<2-3 sentence step-by-step analysis with specific evidence from the document>",
  "score": <integer 1-{scale_max}>,
  "rationale": "<1 sentence summary>"
}}"""


def eval_dimension_scale(client, backend, model, artifact_text, context, dim_name, dim_config, scale_max, verbose=False):
    system_prompt = (
        f"You are an expert document quality evaluator. You score documents on specific "
        f"quality dimensions using a 1-{scale_max} scale. Be precise and calibrated. "
        f"Document length should NOT influence scoring. "
        f"Respond with valid JSON only."
    )
    user_prompt = build_scale_prompt(artifact_text, context, dim_name, dim_config, scale_max)

    scores = []
    rationales = []
    total_inp, total_out = 0, 0

    for _ in range(EVAL_REPEATS):
        try:
            raw, inp, out = judge_call(client, backend, model, system_prompt, user_prompt)
            total_inp += inp
            total_out += out
            parsed = parse_json_response(raw)
            score = max(1, min(scale_max, int(round(parsed.get("score", scale_max // 2)))))
            scores.append(score)
            rationales.append(parsed.get("rationale", parsed.get("analysis", "No rationale.")))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            if verbose:
                print(f"  WARN: Parse error for {dim_name}: {e}")
            scores.append(scale_max // 2)
            rationales.append("(parse error)")
        except Exception as e:
            print(f"ERROR: API failure scoring {dim_name}: {e}")
            sys.exit(2)

    median_score = statistics.median(scores)
    best_idx = min(range(len(scores)), key=lambda i: abs(scores[i] - median_score))
    return median_score, rationales[best_idx], total_inp, total_out


# ---------------------------------------------------------------------------
# Cross-document consistency
# ---------------------------------------------------------------------------

def eval_cross_doc(client, backend, model, artifact_texts, eval_mode, scale_max, verbose=False):
    system_prompt = (
        "You are an expert document quality evaluator. You check whether multiple "
        "documents that reference each other are internally consistent. "
        "Respond with valid JSON only."
    )

    docs_block = ""
    for name, text in artifact_texts.items():
        docs_block += f"\n--- DOCUMENT: {name} ---\n{text}\n"

    if eval_mode == "binary":
        user_prompt = f"""Evaluate cross-document consistency between the following documents.

Check for:
- Claims in one document that are contradicted by another
- Data or numbers that don't match across documents
- Cross-references that are valid and accurate

**Pass:** All claims across documents are consistent. No contradictions.
**Fail:** At least one claim is contradicted or unsupported by another document.

{docs_block}

First analyze for inconsistencies, then give your verdict.

Respond with JSON:
{{
  "analysis": "<step-by-step consistency check>",
  "verdict": "pass" or "fail",
  "rationale": "<1 sentence summary>"
}}"""
    else:
        user_prompt = f"""Evaluate cross-document consistency between the following documents.

Check for:
- Claims in one document that are contradicted by another
- Data or numbers that don't match across documents
- Cross-references that are valid and accurate

Score 1-{scale_max}:
  Score 1: Major contradictions between documents.
  Score {scale_max // 2}: Minor inconsistencies. Most claims align.
  Score {scale_max}: Fully consistent. Every claim supported across docs.

{docs_block}

First analyze for inconsistencies, then give your score.

Respond with JSON:
{{
  "analysis": "<step-by-step consistency check>",
  "score": <integer 1-{scale_max}>,
  "rationale": "<1 sentence summary>"
}}"""

    verdicts_or_scores = []
    rationales = []
    total_inp, total_out = 0, 0

    for _ in range(EVAL_REPEATS):
        try:
            raw, inp, out = judge_call(client, backend, model, system_prompt, user_prompt)
            total_inp += inp
            total_out += out
            parsed = parse_json_response(raw)
            if eval_mode == "binary":
                v = str(parsed.get("verdict", "fail")).lower().strip()
                verdicts_or_scores.append(v == "pass")
            else:
                s = max(1, min(scale_max, int(round(parsed.get("score", scale_max // 2)))))
                verdicts_or_scores.append(s)
            rationales.append(parsed.get("rationale", parsed.get("analysis", "")))
        except (json.JSONDecodeError, KeyError, TypeError):
            verdicts_or_scores.append(False if eval_mode == "binary" else scale_max // 2)
            rationales.append("(parse error)")
        except Exception as e:
            print(f"ERROR: API failure scoring cross-doc consistency: {e}")
            sys.exit(2)

    if eval_mode == "binary":
        passed = sum(verdicts_or_scores) > len(verdicts_or_scores) / 2
        for i, v in enumerate(verdicts_or_scores):
            if v == passed:
                return passed, rationales[i], total_inp, total_out
        return passed, rationales[0], total_inp, total_out
    else:
        median_s = statistics.median(verdicts_or_scores)
        best_idx = min(range(len(verdicts_or_scores)), key=lambda i: abs(verdicts_or_scores[i] - median_s))
        return median_s, rationales[best_idx], total_inp, total_out


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def load_state():
    if STATE_PATH.exists():
        with open(STATE_PATH) as f:
            return json.load(f)
    return {
        "best_combined_score": None,
        "iteration": 0,
        "cumulative_cost_usd": 0.0,
        "consecutive_discards": 0,
        "history": [],
    }


def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def get_git_commit():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=ROOT_DIR,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except FileNotFoundError:
        return "unknown"


def create_checkpoint_tag(iteration, combined_score):
    try:
        subprocess.run(
            ["git", "tag", f"checkpoint-{iteration}", "-m", f"combined: {combined_score:.3f}"],
            capture_output=True, text=True, cwd=ROOT_DIR,
        )
    except FileNotFoundError:
        pass


def save_checkpoint_snapshot(iteration, verdict):
    """Copy artifact files to checkpoints/iteration-NNN-status/ for diffing."""
    label = f"iteration-{iteration:03d}-{verdict.lower()}"
    dest = CHECKPOINTS_DIR / label
    dest.mkdir(parents=True, exist_ok=True)
    for af in sorted(ARTIFACTS_DIR.glob("*")):
        if af.is_file():
            shutil.copy2(af, dest / af.name)


def append_results_tsv(row):
    write_header = not RESULTS_PATH.exists()
    with open(RESULTS_PATH, "a") as f:
        if write_header:
            f.write("commit\tcombined_score\tcross_doc\tstatus\titeration\tdescription\n")
        f.write(
            f"{row['commit']}\t{row['combined_score']:.3f}\t"
            f"{row['cross_doc']:.3f}\t{row['status']}\t"
            f"{row['iteration']}\t{row.get('description', '')}\n"
        )


def compute_cost(model, input_tokens, output_tokens):
    profile = COST_PROFILES.get(model, COST_PROFILES["default"])
    return (input_tokens / 1_000_000) * profile["input"] + (output_tokens / 1_000_000) * profile["output"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="autorefine evaluation engine")
    parser.add_argument("--baseline", action="store_true", help="Record baseline (no comparison)")
    parser.add_argument("--verbose", action="store_true", help="Show per-dimension rationales")
    parser.add_argument("--budget-cap", type=float, default=DEFAULT_BUDGET_CAP, help="Max USD budget")
    args = parser.parse_args()

    rubric = load_rubric()
    client, backend = create_client()
    model = get_model(rubric, backend)
    state = load_state()
    placeholder_mocks = rubric.get("placeholder_mocks", {})
    eval_mode = rubric.get("eval_mode", "binary")
    scale_max = rubric.get("scale_range", 5)
    cross_doc_weight = rubric.get("cross_doc_weight", 0.15)

    print(f"Backend: {backend} | Model: {model} | Mode: {eval_mode}")

    if state["cumulative_cost_usd"] >= args.budget_cap:
        print(f"ERROR: Budget cap ${args.budget_cap:.2f} reached (spent: ${state['cumulative_cost_usd']:.2f})")
        sys.exit(2)

    # --- Discover artifacts ---
    artifact_configs = rubric.get("artifacts", {})
    artifact_files = sorted(f for f in ARTIFACTS_DIR.glob("*") if f.is_file() and not f.name.startswith("."))
    if not artifact_files:
        print("ERROR: No files found in artifacts/")
        sys.exit(1)

    # --- Baseline placeholder snapshot ---
    baseline_snapshot = load_baseline_placeholders()
    if args.baseline:
        snapshot = {af.name: sorted(find_placeholders(af.read_text())) for af in artifact_files}
        save_baseline_placeholders(snapshot)
        baseline_snapshot = snapshot

    # --- Validate artifacts ---
    for af in artifact_files:
        content = af.read_text()
        if len(content.encode()) < MIN_ARTIFACT_BYTES:
            print(f"INVALID: {af.name} is only {len(content.encode())} bytes")
            print("verdict:             INVALID")
            sys.exit(1)
        missing = validate_placeholders(af.name, content, baseline_snapshot)
        if missing:
            print(f"INVALID: placeholder(s) {', '.join('{' + p + '}' for p in missing)} removed from {af.name}")
            print("verdict:             INVALID")
            sys.exit(1)

    # --- Evaluate each artifact ---
    total_inp, total_out = 0, 0
    artifact_results = {}

    print("---")

    for af in artifact_files:
        raw_text = af.read_text()
        word_count = len(raw_text.split())
        judge_text = preprocess_placeholders(raw_text, placeholder_mocks)

        config = artifact_configs.get(af.name, {})
        context = config.get("context", f"Document: {af.name}")
        dimensions = config.get("dimensions", {})

        dim_results = {}
        for dim_name, dim_config in dimensions.items():
            if eval_mode == "binary":
                passed, rationale, inp, out = eval_dimension_binary(
                    client, backend, model, judge_text, context, dim_name, dim_config, args.verbose
                )
                dim_results[dim_name] = {"passed": passed, "rationale": rationale}
            else:
                score, rationale, inp, out = eval_dimension_scale(
                    client, backend, model, judge_text, context, dim_name, dim_config, scale_max, args.verbose
                )
                dim_results[dim_name] = {"score": score, "rationale": rationale, "weight": dim_config.get("weight", 1.0)}
            total_inp += inp
            total_out += out

        if eval_mode == "binary":
            n_pass = sum(1 for d in dim_results.values() if d["passed"])
            n_total = len(dim_results) if dim_results else 1
            artifact_score = n_pass / n_total
        else:
            w_sum = sum(d["weight"] for d in dim_results.values())
            artifact_score = sum(d["score"] * d["weight"] for d in dim_results.values()) / w_sum if w_sum > 0 else 0

        artifact_results[af.name] = {"score": artifact_score, "dims": dim_results, "word_count": word_count}

        print(f"artifact:            {af.name}")
        if eval_mode == "binary":
            print(f"score:               {n_pass}/{n_total} passing ({artifact_score:.0%})")
            for dn, dr in dim_results.items():
                print(f"  {dn:20s} {'PASS' if dr['passed'] else 'FAIL'}")
                if args.verbose:
                    print(f"    -> {dr['rationale']}")
        else:
            print(f"score:               {artifact_score:.2f} / {scale_max}")
            for dn, dr in dim_results.items():
                print(f"  {dn:20s} {dr['score']:.1f}")
                if args.verbose:
                    print(f"    -> {dr['rationale']}")
        print(f"word_count:          {word_count}")
        print("---")

    # --- Cross-document consistency ---
    cross_doc_result = None
    has_cross_doc = len(artifact_files) > 1
    if has_cross_doc:
        judge_texts = {af.name: preprocess_placeholders(af.read_text(), placeholder_mocks) for af in artifact_files}
        cd_value, cd_rationale, inp, out = eval_cross_doc(
            client, backend, model, judge_texts, eval_mode, scale_max, args.verbose
        )
        total_inp += inp
        total_out += out
        cross_doc_result = {"value": cd_value, "rationale": cd_rationale}
        if eval_mode == "binary":
            print(f"cross_doc_consistency: {'PASS' if cd_value else 'FAIL'}")
        else:
            print(f"cross_doc_consistency: {cd_value:.1f} / {scale_max}")
        if args.verbose:
            print(f"  -> {cd_rationale}")

    # --- Combined score ---
    if eval_mode == "binary":
        all_passes = sum(sum(1 for d in ar["dims"].values() if d["passed"]) for ar in artifact_results.values())
        all_total = sum(len(ar["dims"]) for ar in artifact_results.values())
        if has_cross_doc:
            all_passes += 1 if cross_doc_result["value"] else 0
            all_total += 1
        combined_score = all_passes / all_total if all_total > 0 else 0
    else:
        actual_cross_weight = cross_doc_weight if has_cross_doc else 0.0
        artifact_total_weight = 1.0 - actual_cross_weight
        aw = {af.name: artifact_configs.get(af.name, {}).get("weight", 1.0) for af in artifact_files}
        aw_sum = sum(aw.values())
        combined_score = sum(
            artifact_results[af.name]["score"] * (aw[af.name] / aw_sum) * artifact_total_weight
            for af in artifact_files
        )
        if has_cross_doc:
            combined_score += cross_doc_result["value"] * actual_cross_weight

    # --- Cost ---
    eval_cost = compute_cost(model, total_inp, total_out)
    state["cumulative_cost_usd"] += eval_cost
    state["iteration"] += 1
    iteration = state["iteration"]

    # --- Verdict ---
    previous_best = state["best_combined_score"]
    delta = combined_score - previous_best if previous_best is not None else 0.0

    if args.baseline or previous_best is None:
        verdict = "BASELINE"
        state["best_combined_score"] = combined_score
        state["consecutive_discards"] = 0
    elif eval_mode == "binary":
        min_improvement = 1.0 / (all_total if all_total > 0 else 1)
        if delta >= min_improvement - 0.001:
            verdict = "KEEP"
            state["best_combined_score"] = combined_score
            state["consecutive_discards"] = 0
        else:
            verdict = "DISCARD"
            state["consecutive_discards"] += 1
    else:
        if delta >= SCALE_IMPROVEMENT_THRESHOLD:
            verdict = "KEEP"
            state["best_combined_score"] = combined_score
            state["consecutive_discards"] = 0
        else:
            verdict = "DISCARD"
            state["consecutive_discards"] += 1

    if verdict == "DISCARD":
        if state["consecutive_discards"] >= MAX_CONSECUTIVE_DISCARDS:
            verdict = "CONVERGED"
        elif (previous_best is not None and previous_best >= HIGH_SCORE_CONVERGENCE
              and state["consecutive_discards"] >= HIGH_SCORE_CONSECUTIVE_DISCARDS):
            verdict = "CONVERGED"

    # --- Print summary ---
    if eval_mode == "binary":
        print(f"combined_score:      {all_passes}/{all_total} ({combined_score:.0%})")
    else:
        print(f"combined_score:      {combined_score:.3f}")
    prev_str = f"{previous_best:.3f}" if previous_best is not None else "(none)"
    print(f"previous_best:       {prev_str}")
    print(f"delta:               {'+' if delta >= 0 else ''}{delta:.3f}")
    print(f"verdict:             {verdict}")
    print(f"eval_cost_usd:       {eval_cost:.3f}")
    print(f"cumulative_cost_usd: {state['cumulative_cost_usd']:.3f}")
    print(f"iteration:           {iteration}")
    print("---")

    # --- Word count warnings ---
    baseline_wc = state.get("baseline_word_counts", {})
    for af_name, ar in artifact_results.items():
        bwc = baseline_wc.get(af_name)
        if bwc and ar["word_count"] > bwc * 1.3:
            pct = ((ar["word_count"] / bwc) - 1) * 100
            print(f"WARNING: {af_name} grew {pct:.0f}% from baseline ({bwc} -> {ar['word_count']} words)")

    if args.baseline:
        state["baseline_word_counts"] = {n: ar["word_count"] for n, ar in artifact_results.items()}

    state["history"].append(verdict)
    save_state(state)

    if verdict in ("KEEP", "BASELINE"):
        save_checkpoint_snapshot(iteration, verdict)

    cross_doc_score = 0.0
    if cross_doc_result:
        cross_doc_score = (1.0 if cross_doc_result["value"] else 0.0) if eval_mode == "binary" else cross_doc_result["value"]
    append_results_tsv({
        "commit": get_git_commit(),
        "combined_score": combined_score,
        "cross_doc": cross_doc_score,
        "status": verdict.lower(),
        "iteration": iteration,
        "description": "baseline" if verdict == "BASELINE" else "",
    })

    if iteration > 0 and iteration % 10 == 0:
        create_checkpoint_tag(iteration, combined_score)
        print(f"Created checkpoint tag: checkpoint-{iteration}")

    sys.exit(0)


if __name__ == "__main__":
    main()
