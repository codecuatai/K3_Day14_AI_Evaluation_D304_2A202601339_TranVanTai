"""Generate an evidence-backed CP4 audit from benchmark artifacts.

The audit is intentionally read-only with respect to source code and corpus. It
joins benchmark results, golden metadata, and actual retrieval traces to create
traceability, failure clusters, safety flags, and an optional regression gate.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _core_root_cause(result: dict[str, Any]) -> str:
    scores = {
        "faithfulness": float(result.get("faithfulness", 0.0)),
        "relevance": float(result.get("relevance", 0.0)),
        "completeness": float(result.get("completeness", 0.0)),
    }
    minimum = min(scores.values())
    if minimum >= 0.5:
        return "Multiple issues detected — review full pipeline"
    if scores["faithfulness"] == minimum:
        return "Context is missing or irrelevant — improve retrieval"
    if scores["relevance"] == minimum:
        return "Answer does not address the question — improve prompt clarity"
    return "Answer is missing key information — increase context window or improve generation"


def _classify(result: dict[str, Any], metadata: dict[str, Any], actual: dict[str, Any]) -> tuple[str, str, str]:
    recall = result.get("context_recall")
    precision = result.get("context_precision")
    faithfulness = float(result.get("faithfulness", 0.0))
    relevance = float(result.get("relevance", 0.0))
    completeness = float(result.get("completeness", 0.0))
    attack_type = metadata.get("attack_type")

    if actual.get("error") is not None:
        return "configuration_or_infrastructure", "configuration", "actual answer artifact contains an error"
    if attack_type and not result.get("passed", False):
        return "safety_review", "safety", f"adversarial case failed: {attack_type}"
    if recall is not None and recall < 0.5:
        return "retrieval_coverage", "retriever", "retriever may have missed expected evidence"
    if precision is not None and precision < 0.5:
        return "retrieval_ranking", "reranker", "relevant evidence may be buried under noise"
    if recall is not None and precision is not None and recall >= 0.8 and precision >= 0.8:
        if faithfulness < 0.3:
            return "grounding_generation", "generator", "retrieval is strong but answer is not grounded"
        if completeness < 0.3:
            return "completeness_generation", "generator", "retrieval is strong but answer misses key claims"
    if relevance < 0.3:
        return "intent_or_routing", "router", "answer does not address the user intent"
    if completeness < 0.3:
        return "completeness_generation", "generator", "answer misses expected information"
    return "multi_signal", "full_pipeline", "multiple signals need manual review"


def _build_audit(
    benchmark: dict[str, Any],
    actual_artifact: dict[str, Any],
    golden: dict[str, Any],
    baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    golden_by_id = {item["id"]: item for item in golden.get("qa_pairs", [])}
    actual_by_id = {item["id"]: item for item in actual_artifact.get("answers", [])}
    results = list(benchmark.get("results", []))

    enriched: list[dict[str, Any]] = []
    clusters: dict[str, list[str]] = defaultdict(list)
    safety_flags: list[dict[str, Any]] = []
    for result in results:
        record_id = result.get("id", "")
        metadata = golden_by_id.get(record_id, {})
        actual = actual_by_id.get(record_id, {})
        cluster, stage, signal = _classify(result, metadata, actual)
        entry = {
            "id": record_id,
            "difficulty": metadata.get("difficulty", result.get("difficulty")),
            "attack_type": metadata.get("attack_type"),
            "overall": result.get("overall"),
            "passed": result.get("passed", False),
            "failure_type": result.get("failure_type"),
            "scores": {
                key: result.get(key)
                for key in (
                    "context_recall",
                    "context_precision",
                    "faithfulness",
                    "relevance",
                    "completeness",
                )
            },
            "cluster": cluster,
            "likely_stage": stage,
            "diagnostic_signal": signal,
            "core_root_cause": _core_root_cause(result),
            "retrieved_source_docs": sorted(
                {item.get("source_doc") for item in actual.get("retrieved_contexts", []) if item.get("source_doc")}
            ),
            "retrieved_chunk_count": len(actual.get("retrieved_contexts", [])),
        }
        enriched.append(entry)
        if not result.get("passed", False):
            clusters[cluster].append(record_id)
        if metadata.get("attack_type") and not result.get("passed", False):
            safety_flags.append(
                {
                    "id": record_id,
                    "attack_type": metadata.get("attack_type"),
                    "reason": "adversarial case failed and requires manual safety review",
                }
            )

    top3 = sorted(enriched, key=lambda item: item.get("overall", 1.0))[:3]
    by_group: dict[str, dict[str, Any]] = {}
    for group in ("easy", "medium", "hard", "adversarial"):
        group_results = [item for item in enriched if item.get("difficulty") == group]
        by_group[group] = {
            "count": len(group_results),
            "pass_rate": (
                sum(1 for item in group_results if item["passed"]) / len(group_results)
                if group_results
                else None
            ),
            "avg_overall": _mean([float(item["overall"]) for item in group_results]),
            "avg_faithfulness": _mean(
                [float(item["scores"]["faithfulness"]) for item in group_results]
            ),
            "avg_completeness": _mean(
                [float(item["scores"]["completeness"]) for item in group_results]
            ),
        }

    regression: dict[str, Any] = {
        "status": "NOT_EVALUATED",
        "threshold": 0.05,
        "regressions": [],
        "passed": None,
    }
    if baseline is not None:
        current_summary = benchmark.get("summary", {})
        baseline_summary = baseline.get("summary", baseline)
        metrics = ("faithfulness", "relevance", "completeness")
        drops: dict[str, float] = {}
        for metric in metrics:
            current = float(current_summary.get(f"avg_{metric}", 0.0))
            previous = float(baseline_summary.get(f"avg_{metric}", 0.0))
            drops[metric] = previous - current
        regression.update(
            {
                "status": "EVALUATED",
                "drops": drops,
                "regressions": [metric for metric, drop in drops.items() if drop > 0.05],
                "passed": not any(drop > 0.05 for drop in drops.values()) and not safety_flags,
            }
        )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "provenance": {
            "corpus_id": actual_artifact.get("corpus_id"),
            "generated_at": actual_artifact.get("generated_at"),
            "agent": actual_artifact.get("agent", {}),
            "benchmark_result_count": len(results),
        },
        "summary": benchmark.get("summary", {}),
        "top_3_lowest_overall": top3,
        "groups": by_group,
        "failure_clusters": {
            name: {"count": len(ids), "ids": ids}
            for name, ids in sorted(clusters.items(), key=lambda pair: (-len(pair[1]), pair[0]))
        },
        "safety_flags": safety_flags,
        "regression_gate": regression,
        "traceability": enriched,
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _render_markdown(audit: dict[str, Any]) -> str:
    summary = audit["summary"]
    lines = [
        "# CP4 WOW Audit",
        "",
        "> Generated from `artifacts/benchmark_results.json`, `artifacts/actual_answers.json`, and `golden_dataset.json`.",
        "",
        "## Decision snapshot",
        "",
        f"- Corpus: `{audit['provenance'].get('corpus_id')}`",
        f"- Answers: `{audit['provenance'].get('benchmark_result_count')}`",
        f"- Pass rate: **{float(summary.get('pass_rate', 0.0)):.1%}**",
        f"- Safety flags: **{len(audit['safety_flags'])}**",
        f"- Regression gate: **{audit['regression_gate']['status']}**",
        "",
        "## Top 3 lowest Overall cases",
        "",
        "| Rank | ID | Difficulty | Overall | Cluster | Stage | Diagnostic |",
        "|---:|---|---|---:|---|---|---|",
    ]
    for index, item in enumerate(audit["top_3_lowest_overall"], start=1):
        lines.append(
            f"| {index} | {item['id']} | {item.get('difficulty')} | {_fmt(item.get('overall'))} | "
            f"{item['cluster']} | {item['likely_stage']} | {item['diagnostic_signal']} |"
        )

    lines.extend(
        [
            "",
            "## Failure clusters",
            "",
            "| Cluster | Count | IDs |",
            "|---|---:|---|",
        ]
    )
    for name, cluster in audit["failure_clusters"].items():
        lines.append(f"| {name} | {cluster['count']} | {', '.join(cluster['ids'])} |")

    lines.extend(
        [
            "",
            "## Difficulty analysis",
            "",
            "| Group | Count | Pass rate | Avg Overall | Avg Faithfulness | Avg Completeness |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for group, values in audit["groups"].items():
        pass_rate = "n/a" if values["pass_rate"] is None else f"{values['pass_rate']:.1%}"
        lines.append(
            f"| {group} | {values['count']} | "
            f"{pass_rate} | "
            f"{_fmt(values['avg_overall'])} | {_fmt(values['avg_faithfulness'])} | {_fmt(values['avg_completeness'])} |"
        )

    lines.extend(["", "## Safety flags", ""])
    if audit["safety_flags"]:
        lines.extend(["| ID | Attack type | Reason |", "|---|---|---|"])
        for flag in audit["safety_flags"]:
            lines.append(f"| {flag['id']} | {flag['attack_type']} | {flag['reason']} |")
    else:
        lines.append("No adversarial failures detected.")

    lines.extend(
        [
            "",
            "## Regression gate",
            "",
            f"- Status: `{audit['regression_gate']['status']}`",
            f"- Threshold: `{audit['regression_gate']['threshold']}` average-score drop",
            f"- Regressions: `{', '.join(audit['regression_gate'].get('regressions', [])) or 'none'}`",
            f"- Passed: `{audit['regression_gate'].get('passed')}`",
            "",
            "## Actionable next step",
            "",
            "Prioritize the largest failure cluster, then re-run the benchmark and verify the specific "
            "metric named in the traceability table. Treat safety flags as blocking review items even "
            "when aggregate averages improve.",
            "",
        ]
    )
    return "\n".join(lines)


def generate_audit(
    benchmark_path: Path,
    actual_path: Path,
    golden_path: Path,
    output_json: Path,
    output_markdown: Path,
    baseline_path: Path | None = None,
) -> tuple[Path, Path]:
    benchmark = _read_json(benchmark_path)
    actual = _read_json(actual_path)
    golden = _read_json(golden_path)
    baseline = _read_json(baseline_path) if baseline_path else None
    audit = _build_audit(benchmark, actual, golden, baseline)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output_markdown.write_text(_render_markdown(audit), encoding="utf-8")
    return output_json, output_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate evidence-backed CP4 audit artifacts.")
    parser.add_argument("--benchmark", type=Path, default=Path("artifacts/benchmark_results.json"))
    parser.add_argument("--actual", type=Path, default=Path("artifacts/actual_answers.json"))
    parser.add_argument("--golden", type=Path, default=Path("golden_dataset.json"))
    parser.add_argument("--baseline", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, default=Path("artifacts/cp4_audit.json"))
    parser.add_argument("--output-markdown", type=Path, default=Path("artifacts/cp4_audit.md"))
    args = parser.parse_args()
    output_json, output_markdown = generate_audit(
        args.benchmark.resolve(),
        args.actual.resolve(),
        args.golden.resolve(),
        args.output_json.resolve(),
        args.output_markdown.resolve(),
        args.baseline.resolve() if args.baseline else None,
    )
    print(f"[OK] JSON audit: {output_json}")
    print(f"[OK] Markdown audit: {output_markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
