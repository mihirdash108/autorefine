"""
Rubric calibration script for autorefine.

Validates that your rubric ranks known-quality variants correctly.
Provide 2-3 document variants of known relative quality, and this
script checks whether the rubric scores them in the expected order.

Usage:
    uv run calibrate.py best.md baseline.md worst.md
    uv run calibrate.py --rubric rubric.yaml good.md bad.md
    uv run calibrate.py --verbose best.md baseline.md worst.md

Arguments are document paths in DESCENDING quality order (best first).
The script evaluates each and checks if scores match the expected ranking.

Inspired by Hamel Husain's eval calibration workflow.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Reuse evaluate.py infrastructure
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from evaluate import (
    create_client, get_model, load_rubric, parse_json_response, judge_call,
    eval_dimension_binary, eval_dimension_scale, preprocess_placeholders,
    EVAL_REPEATS,
)


def score_document(client, backend, model, text, rubric, eval_mode, scale_max):
    """Score a single document against all dimensions of the first artifact config."""
    artifact_configs = rubric.get("artifacts", {})
    # Use the first artifact's config as the rubric template
    if artifact_configs:
        config = next(iter(artifact_configs.values()))
    else:
        print("ERROR: No artifact dimensions defined in rubric.yaml")
        sys.exit(1)

    context = config.get("context", "Document under evaluation")
    dimensions = config.get("dimensions", {})
    placeholder_mocks = rubric.get("placeholder_mocks", {})
    judge_text = preprocess_placeholders(text, placeholder_mocks)

    dim_results = {}
    for dim_name, dim_config in dimensions.items():
        if eval_mode == "binary":
            passed, rationale, _, _ = eval_dimension_binary(
                client, backend, model, judge_text, context, dim_name, dim_config
            )
            dim_results[dim_name] = {"passed": passed, "rationale": rationale}
        else:
            score, rationale, _, _ = eval_dimension_scale(
                client, backend, model, judge_text, context, dim_name, dim_config, scale_max
            )
            dim_results[dim_name] = {"score": score, "rationale": rationale, "weight": dim_config.get("weight", 1.0)}

    # Compute combined score
    if eval_mode == "binary":
        n_pass = sum(1 for d in dim_results.values() if d["passed"])
        n_total = len(dim_results)
        combined = n_pass / n_total if n_total > 0 else 0
    else:
        w_sum = sum(d["weight"] for d in dim_results.values())
        combined = sum(d["score"] * d["weight"] for d in dim_results.values()) / w_sum if w_sum > 0 else 0

    return combined, dim_results


def main():
    parser = argparse.ArgumentParser(
        description="Calibrate your rubric against known-quality document variants"
    )
    parser.add_argument("variants", nargs="+", help="Document paths in DESCENDING quality order (best first)")
    parser.add_argument("--rubric", default="rubric.yaml", help="Path to rubric YAML")
    parser.add_argument("--verbose", action="store_true", help="Show per-dimension results")
    args = parser.parse_args()

    # Load rubric from specified path
    rubric_path = Path(args.rubric)
    if not rubric_path.is_absolute():
        rubric_path = ROOT_DIR / rubric_path
    try:
        with open(rubric_path) as f:
            rubric = yaml.safe_load(f)
    except Exception as e:
        print(f"ERROR: Cannot load rubric: {e}")
        sys.exit(1)

    client, backend = create_client()
    model = get_model(rubric, backend)
    eval_mode = rubric.get("eval_mode", "binary")
    scale_max = rubric.get("scale_range", 5)

    print(f"Backend: {backend} | Model: {model} | Mode: {eval_mode}")
    print(f"Evaluating {len(args.variants)} variants (expected order: best -> worst)")
    print("---")

    # Score each variant
    results = []
    for i, path in enumerate(args.variants):
        p = Path(path)
        if not p.exists():
            print(f"ERROR: File not found: {path}")
            sys.exit(1)

        text = p.read_text()
        rank_label = ["best", "middle", "worst"][min(i, 2)] if len(args.variants) <= 3 else f"rank-{i+1}"
        print(f"Scoring: {p.name} (expected: {rank_label})...")

        combined, dim_results = score_document(client, backend, model, text, rubric, eval_mode, scale_max)
        results.append({"path": p.name, "score": combined, "dims": dim_results})

        if eval_mode == "binary":
            n_pass = sum(1 for d in dim_results.values() if d["passed"])
            print(f"  Score: {n_pass}/{len(dim_results)} ({combined:.0%})")
        else:
            print(f"  Score: {combined:.2f} / {scale_max}")

        if args.verbose:
            for dn, dr in dim_results.items():
                if eval_mode == "binary":
                    print(f"    {dn:20s} {'PASS' if dr['passed'] else 'FAIL'}")
                else:
                    print(f"    {dn:20s} {dr['score']:.1f}")
                print(f"      {dr['rationale']}")
        print()

    # Check ranking
    print("=" * 60)
    print("CALIBRATION RESULTS")
    print("=" * 60)

    scores = [r["score"] for r in results]
    expected_order = list(range(len(scores)))  # 0, 1, 2 (best to worst)

    # Check if scores are in descending order
    is_correct = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
    # Check for strict ordering (no ties)
    is_strict = all(scores[i] > scores[i+1] for i in range(len(scores)-1))

    for i, r in enumerate(results):
        rank = sorted(range(len(scores)), key=lambda x: -scores[x]).index(i) + 1
        expected = i + 1
        match = "OK" if rank == expected else "MISMATCH"
        if eval_mode == "binary":
            n_pass = sum(1 for d in r["dims"].values() if d["passed"])
            print(f"  {r['path']:30s}  {n_pass}/{len(r['dims'])} ({r['score']:.0%})  expected #{expected}  actual #{rank}  {match}")
        else:
            print(f"  {r['path']:30s}  {r['score']:.2f}/{scale_max}  expected #{expected}  actual #{rank}  {match}")

    print()
    if is_strict:
        print("PASS: Rubric correctly ranks all variants in strict order.")
        print("Your rubric is well-calibrated for this document type.")
    elif is_correct:
        print("PARTIAL PASS: Ranking is correct but some variants tied.")
        print("Consider making dimensions more discriminating or adding dimensions.")
    else:
        print("FAIL: Rubric does NOT rank variants correctly.")
        print("Review your dimension definitions and anchors.")
        print("Common fixes:")
        print("  - Make pass/fail criteria more specific")
        print("  - Add dimensions that distinguish the variants")
        print("  - Check for correlated dimensions that double-weight one aspect")

    # Compute Kendall's tau (rank correlation)
    actual_ranks = sorted(range(len(scores)), key=lambda x: -scores[x])
    concordant = sum(
        1 for i in range(len(actual_ranks))
        for j in range(i+1, len(actual_ranks))
        if (actual_ranks[i] - actual_ranks[j]) * (expected_order[i] - expected_order[j]) > 0
    )
    discordant = sum(
        1 for i in range(len(actual_ranks))
        for j in range(i+1, len(actual_ranks))
        if (actual_ranks[i] - actual_ranks[j]) * (expected_order[i] - expected_order[j]) < 0
    )
    n_pairs = len(scores) * (len(scores) - 1) / 2
    tau = (concordant - discordant) / n_pairs if n_pairs > 0 else 0
    print(f"\nKendall's tau: {tau:.2f} (1.0 = perfect agreement, -1.0 = inverted)")


if __name__ == "__main__":
    main()
