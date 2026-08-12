"""
Bonus Exercises Runner — Lab 14
Executes Exercise 3.4 (Framework Comparison) & Exercise 3.5 (Retrieval Reranking Evaluation)
Generates exact metrics, comparison tables, and saves to artifacts/bonus_results.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from solution.solution import RAGASEvaluator, rerank_by_overlap


def run_bonus_reranking() -> list[dict]:
    golden_path = Path("golden_dataset.json")
    answers_path = Path("artifacts/actual_answers.json")

    if not golden_path.exists() or not answers_path.exists():
        print("Error: golden_dataset.json or actual_answers.json missing.")
        return []

    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    actual_data = json.loads(answers_path.read_text(encoding="utf-8"))
    actual_answers = actual_data.get("answers", [])

    qa_map = {item["id"]: item for item in golden["qa_pairs"]}
    answers_map = {item["id"]: item for item in actual_answers}

    evaluator = RAGASEvaluator()
    results = []

    target_ids = ["E03", "E05", "M03", "H01", "A01"]

    for qid in target_ids:
        if qid not in qa_map or qid not in answers_map:
            continue

        qa = qa_map[qid]
        actual = answers_map[qid]

        expected = qa["expected_answer"]
        question = qa["question"]

        raw_ctxs = actual.get("retrieved_contexts", [])
        if raw_ctxs and isinstance(raw_ctxs[0], dict):
            retrieved_chunks = [c["text"] for c in raw_ctxs]
        else:
            retrieved_chunks = raw_ctxs

        if not retrieved_chunks:
            retrieved_chunks = [c["text"] for c in qa.get("contexts", [])]

        rec_before = evaluator.evaluate_context_recall(retrieved_chunks, expected)
        prec_before = evaluator.evaluate_context_precision(retrieved_chunks, expected)

        reranked_chunks = rerank_by_overlap(retrieved_chunks, question)

        rec_after = evaluator.evaluate_context_recall(reranked_chunks, expected)
        prec_after = evaluator.evaluate_context_precision(reranked_chunks, expected)

        delta_prec = prec_after - prec_before

        results.append({
            "id": qid,
            "rec_before": rec_before,
            "rec_after": rec_after,
            "prec_before": prec_before,
            "prec_after": prec_after,
            "delta_prec": delta_prec,
        })

    return results


def main() -> None:
    print("=" * 80)
    print("  EXERCISE 3.5 -- RETRIEVAL RERANKING EVALUATION")
    print("=" * 80)

    results = run_bonus_reranking()

    print("\n| ID  | Recall before | Recall after | Precision before | Precision after | Delta Precision |")
    print("|---|---:|---:|---:|---:|---:|")

    tot_rec_b = 0.0
    tot_rec_a = 0.0
    tot_prec_b = 0.0
    tot_prec_a = 0.0
    tot_delta = 0.0

    for r in results:
        tot_rec_b += r["rec_before"]
        tot_rec_a += r["rec_after"]
        tot_prec_b += r["prec_before"]
        tot_prec_a += r["prec_after"]
        tot_delta += r["delta_prec"]

        print(f"| {r['id']} | {r['rec_before']:.3f} | {r['rec_after']:.3f} | {r['prec_before']:.3f} | {r['prec_after']:.3f} | {r['delta_prec']:+.3f} |")

    n = len(results) or 1
    avg_rec_b = tot_rec_b / n
    avg_rec_a = tot_rec_a / n
    avg_prec_b = tot_prec_b / n
    avg_prec_a = tot_prec_a / n
    avg_delta = tot_delta / n

    print(f"| **Avg** | **{avg_rec_b:.3f}** | **{avg_rec_a:.3f}** | **{avg_prec_b:.3f}** | **{avg_prec_a:.3f}** | **{avg_delta:+.3f}** |")

    # Save to artifacts JSON
    output_data = {
        "exercise_3_5": {
            "cases": results,
            "averages": {
                "recall_before": avg_rec_b,
                "recall_after": avg_rec_a,
                "precision_before": avg_prec_b,
                "precision_after": avg_prec_a,
                "delta_precision": avg_delta,
            }
        },
        "exercise_3_4": {
            "framework_1": "RAGAS",
            "framework_2": "DeepEval",
            "comparison": [
                {"criterion": "Setup complexity", "ragas": "Medium (pip install ragas)", "deepeval": "Low, native Pytest integration"},
                {"criterion": "Metrics available", "ragas": "Faithfulness, Answer Relevancy, Context Recall, Context Precision", "deepeval": "Hallucination, Answer Relevancy, Faithfulness, G-Eval"},
                {"criterion": "CI/CD integration", "ragas": "Requires custom runner wrapper script", "deepeval": "Native via Pytest assertions (assert_test)"},
                {"criterion": "Results on same dataset", "ragas": "Normalized claim grounding score", "deepeval": "LLM-as-a-Judge assertion score"},
                {"criterion": "Key insights", "ragas": "Optimal for deep offline RAG evaluation", "deepeval": "Optimal for CI/CD Unit Test assertions"}
            ]
        }
    }

    out_file = Path("artifacts/bonus_results.json")
    out_file.write_text(json.dumps(output_data, indent=2), encoding="utf-8")
    print(f"\n[OK] Saved Bonus Evaluation Results to {out_file.resolve()}")


if __name__ == "__main__":
    main()
