"""Offline smoke tests for the Vietnamese demo backend."""

from serve_demo import _state, run_query, run_reranking


def test_demo_state_loads_real_artifacts() -> None:
    state = _state()
    assert state["validation"]["status"] == "PASS"
    assert len(state["golden"]) == 20
    assert len(state["results"]) == 20


def test_live_demo_query_returns_trace_and_case_evaluation() -> None:
    response = run_query(
        {
            "question": "When does the standard add/drop period end for Fall 2026?",
            "case_id": "E01",
            "provider": "offline",
            "top_k": 5,
        }
    )
    assert response["model"] == "demo-offline-grounded"
    assert response["chunks"]
    assert response["evaluation"]["id"] == "E01"
    assert response["evaluation"]["context_recall"] == 1.0


def test_demo_reranking_preserves_union_coverage() -> None:
    result = run_reranking({})
    assert len(result["rows"]) == 5
    assert all(row["union_unchanged"] for row in result["rows"])
    assert all(row["recall_before"] == row["recall_after"] for row in result["rows"])
