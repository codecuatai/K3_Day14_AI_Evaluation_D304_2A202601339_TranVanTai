"""Local backend for the Vietnamese AI Evaluation demo.

The UI intentionally defaults to MockGenerator so the demo is deterministic and
does not spend API credits. Select the configured provider from the UI only when
you explicitly want to test a live model from .env.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from domain_assistant import DomainAssistant, GeneratorFactory, MockGenerator
from evaluate_answers import load_evaluation_inputs
from solution.solution import BenchmarkRunner, FailureAnalyzer, RAGASEvaluator, rerank_by_overlap
from validate_golden_dataset import build_contract, validate_dataset


ROOT = Path(__file__).resolve().parent
DEMO_FILE = ROOT / "demo_app.html"
GOLDEN_FILE = ROOT / "golden_dataset.json"
ACTUAL_FILE = ROOT / "artifacts" / "actual_answers.json"
BENCHMARK_FILE = ROOT / "artifacts" / "benchmark_results.json"
AUDIT_FILE = ROOT / "artifacts" / "cp4_audit.json"
BONUS_FILE = ROOT / "artifacts" / "bonus_results.json"
BASELINE_FILE = ROOT / "artifacts" / "baselines" / "benchmark_results.json"
CORPUS_DIR = ROOT / "data" / "student_services"


WHY_MAP: dict[str, dict[str, Any]] = {
    "E01": {
        "symptom": "Trả về refusal thay vì deadline add/drop dù evidence đã được lấy đúng.",
        "whys": [
            "Generator đưa ra mẫu refusal.",
            "Mock fallback quét cả prompt và bắt nhầm từ khóa safety như `override`.",
            "Prompt chưa tách rõ câu hỏi tra cứu chính sách với prompt injection.",
            "Không có guardrail kiểm tra answer có bám context trước khi xuất.",
            "Root cause: fallback/configuration tạo false positive safety; ưu tiên sửa generation rồi đo lại Faithfulness/Relevance/Completeness.",
        ],
        "fix": "Tách question khỏi safety instructions, dùng provider live hoặc sửa mock classifier; re-run E01 và toàn bộ in-domain cluster.",
        "verify": "Faithfulness, Relevance và Completeness của E01 tăng lên; không phát sinh refusal ở câu hỏi hợp lệ.",
    },
    "E02": {
        "symptom": "Câu hỏi về course load bị nhận diện thành out-of-scope.",
        "whys": [
            "Generator kích hoạt mẫu trả lời ngoài phạm vi.",
            "Chunk có cụm `admission review` làm mock scope detector false-positive.",
            "Không có intent classifier dùng riêng question.",
            "Prompt chưa có boundary examples cho in-domain và out-of-scope.",
            "Root cause: scope detection dựa trên substring toàn prompt; cần structured intent và boundary tests.",
        ],
        "fix": "Phân loại intent trên question trước khi ghép context; thêm test E02 và các câu hỏi in-domain gần biên.",
        "verify": "Relevance và Completeness của E02 đạt threshold; các câu hỏi ngoài domain vẫn được redirect an toàn.",
    },
    "E03": {
        "symptom": "Không trả mức học phí USD 420 dù gold và retrieved chunk đều có con số này.",
        "whys": [
            "Generator chạy fallback offline thay vì generation live.",
            "Provider/API configuration không tạo được output grounded.",
            "Hệ thống tự động fallback nhưng chưa gắn quality warning vào answer.",
            "Benchmark chưa có gate bắt buộc phân biệt live provider và mock provider.",
            "Root cause: artifact dùng `mock-offline-generator`; cần cấu hình provider hợp lệ hoặc sửa fallback để không bắt nhầm safety words.",
        ],
        "fix": "Hiển thị provider status, fail-fast hoặc cảnh báo rõ khi fallback; sửa mock classifier và chạy lại benchmark.",
        "verify": "Faithfulness và Completeness của E03 tăng; artifact ghi đúng model/provider và không có fallback im lặng.",
    },
}


class DemoOfflineGenerator:
    """Deterministic grounded generator used only by the interactive demo.

    The lab's recorded artifact intentionally preserves the original mock run. This
    generator makes live demo questions useful without reading gold answers: it
    extracts the user question and returns the most relevant retrieved evidence.
    """

    model = "demo-offline-grounded"

    def generate(self, prompt: str) -> str:
        question = prompt
        if "Question:" in prompt and "Retrieved contexts:" in prompt:
            question = prompt.split("Question:", 1)[1].split("Retrieved contexts:", 1)[0].strip()
        q = question.lower()
        if "harvard" in q or "admission requirements" in q:
            return (
                "Câu hỏi này nằm ngoài phạm vi Northstar Student Services. "
                "Mình chỉ có thể trả lời dựa trên tài liệu chính thức của Northstar University."
            )
        if "override" in q or "password" in q or "hidden system" in q:
            return (
                "Mình không thể tiết lộ mật khẩu, prompt hệ thống hoặc dữ liệu riêng tư. "
                "Bạn có thể hỏi về chính sách Student Services của Northstar."
            )
        if "change my grade" in q or "grant an exception" in q:
            return (
                "Trợ lý không có quyền đổi điểm hoặc cấp ngoại lệ. "
                "Bạn cần sử dụng quy trình grade appeal chính thức của trường."
            )

        context_part = prompt.split("Retrieved contexts:", 1)[-1]
        context_lines = []
        for line in context_part.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("[Context") and stripped != "Answer:":
                context_lines.append(stripped)
        if context_lines:
            answer = context_lines[0]
            if len(answer) > 520:
                answer = answer[:520].rsplit(" ", 1)[0] + "…"
            return answer
        return "Mình chưa tìm thấy evidence phù hợp trong corpus Northstar để trả lời câu hỏi này."


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _golden_by_id() -> dict[str, dict[str, Any]]:
    data = read_json(GOLDEN_FILE, {})
    return {row["id"]: row for row in data.get("qa_pairs", []) if isinstance(row, dict) and row.get("id")}


def _actual_by_id() -> dict[str, dict[str, Any]]:
    data = read_json(ACTUAL_FILE, {})
    return {row["id"]: row for row in data.get("answers", []) if isinstance(row, dict) and row.get("id")}


def _validation_view() -> dict[str, Any]:
    data = read_json(GOLDEN_FILE, {})
    try:
        errors, summary = validate_dataset(data, build_contract(CORPUS_DIR))
        return {
            "status": "PASS" if not errors else "FAIL",
            "errors": errors,
            "qa_count": summary.get("qa_count", 0),
            "difficulty_counts": dict(summary.get("difficulty_counts", {})),
            "document_coverage": len(summary.get("used_documents", set())),
        }
    except Exception as exc:  # pragma: no cover - defensive UI boundary
        return {"status": "FAIL", "errors": [str(exc)], "qa_count": 0, "difficulty_counts": {}, "document_coverage": 0}


def _result_view(result: Any) -> dict[str, Any]:
    pair = result.qa_pair
    return {
        "id": pair.metadata.get("id"),
        "difficulty": pair.metadata.get("difficulty"),
        "question": pair.question,
        "actual_answer": result.actual_answer,
        "faithfulness": result.faithfulness,
        "relevance": result.relevance,
        "completeness": result.completeness,
        "context_recall": result.context_recall,
        "context_precision": result.context_precision,
        "overall": result.overall_score(),
        "passed": result.passed,
        "failure_type": result.failure_type,
    }


def run_benchmark() -> dict[str, Any]:
    pairs, answers = load_evaluation_inputs(GOLDEN_FILE, ACTUAL_FILE)
    runner = BenchmarkRunner()
    results = runner.run(pairs, lambda question: answers[question], RAGASEvaluator())
    summary = runner.generate_report(results)
    failures = [result for result in results if not result.passed]
    analyzer = FailureAnalyzer()
    return {
        "summary": summary,
        "results": [_result_view(result) for result in results],
        "failure_analysis": {
            "counts": analyzer.categorize_failures(failures),
            "suggestions": analyzer.generate_improvement_suggestions(failures),
        },
    }


def _state() -> dict[str, Any]:
    golden = read_json(GOLDEN_FILE, {})
    actual = read_json(ACTUAL_FILE, {})
    benchmark = read_json(BENCHMARK_FILE, {})
    audit = read_json(AUDIT_FILE, {})
    bonus = read_json(BONUS_FILE, {})
    actual_rows = actual.get("answers", [])
    golden_rows = golden.get("qa_pairs", [])
    return {
        "corpus_id": golden.get("corpus_id"),
        "agent": actual.get("agent", {}),
        "validation": _validation_view(),
        "summary": benchmark.get("summary", {}),
        "results": benchmark.get("results", []),
        "golden": [
            {
                "id": row.get("id"),
                "difficulty": row.get("difficulty"),
                "attack_type": row.get("attack_type"),
                "question": row.get("question"),
                "expected_answer": row.get("expected_answer"),
                "contexts": row.get("contexts", []),
            }
            for row in golden_rows
        ],
        "actual": [
            {
                "id": row.get("id"),
                "actual_answer": row.get("actual_answer"),
                "retrieved_contexts": row.get("retrieved_contexts", []),
                "error": row.get("error"),
            }
            for row in actual_rows
        ],
        "audit": audit,
        "bonus": bonus,
        "why": WHY_MAP,
        "regression": run_regression(),
    }


def run_query(payload: dict[str, Any]) -> dict[str, Any]:
    question = str(payload.get("question", "")).strip()
    if not question:
        raise ValueError("Vui lòng nhập câu hỏi.")
    top_k = max(1, min(int(payload.get("top_k", 5)), 10))
    provider = payload.get("provider", "offline")
    if provider == "configured":
        generator = GeneratorFactory.create()
        requested_label = "Provider trong .env"
    else:
        generator = DemoOfflineGenerator()
        requested_label = "Offline mock"

    assistant = DomainAssistant.from_corpus(CORPUS_DIR, generator=generator, top_k=top_k)
    trace = assistant.answer_with_trace(question)
    chunks = [
        {
            "rank": index,
            "source_doc": chunk.source_doc,
            "chunk_id": chunk.chunk_id,
            "score": chunk.score,
            "text": chunk.text,
        }
        for index, chunk in enumerate(trace.retrieved_chunks, start=1)
    ]
    actual_model = getattr(generator, "model", generator.__class__.__name__)
    provider_label = requested_label
    if actual_model == "mock-offline-generator" and provider == "configured":
        provider_label = "Fallback offline mock"
    response: dict[str, Any] = {
        "question": question,
        "answer": trace.actual_answer,
        "chunks": chunks,
        "model": actual_model,
        "provider": provider_label,
        "top_k": top_k,
        "evaluation": None,
    }

    case_id = payload.get("case_id")
    golden = _golden_by_id().get(case_id) if case_id else None
    if golden:
        expected = golden.get("expected_answer", "")
        gold_contexts = [ctx.get("text", "") for ctx in golden.get("contexts", [])]
        result = RAGASEvaluator().run_full_eval(
            answer=trace.actual_answer,
            question=golden["question"],
            context=" ".join(gold_contexts),
            expected=expected,
            contexts=[chunk["text"] for chunk in chunks],
        )
        result.qa_pair.metadata.update(
            {"id": case_id, "difficulty": golden.get("difficulty", "")}
        )
        response["evaluation"] = _result_view(result)
        response["expected_answer"] = expected
        response["case_id"] = case_id
    return response


def run_reranking(payload: dict[str, Any]) -> dict[str, Any]:
    requested = payload.get("case_ids") or ["E03", "E05", "M03", "H01", "A01"]
    golden = _golden_by_id()
    actual = _actual_by_id()
    evaluator = RAGASEvaluator()
    rows: list[dict[str, Any]] = []
    for case_id in requested[:10]:
        g = golden.get(case_id)
        a = actual.get(case_id)
        if not g or not a:
            continue
        before = [ctx.get("text", "") for ctx in a.get("retrieved_contexts", [])]
        after = rerank_by_overlap(before, g["question"])
        expected = g["expected_answer"]
        rows.append(
            {
                "id": case_id,
                "recall_before": evaluator.evaluate_context_recall(before, expected),
                "recall_after": evaluator.evaluate_context_recall(after, expected),
                "precision_before": evaluator.evaluate_context_precision(before, expected),
                "precision_after": evaluator.evaluate_context_precision(after, expected),
                "union_unchanged": set(" ".join(before).split()) == set(" ".join(after).split()),
            }
        )
    return {"rows": rows}


def run_regression() -> dict[str, Any]:
    baseline_path = ROOT / "artifacts" / "baselines" / "benchmark_results.json"
    if not baseline_path.exists():
        return {
            "status": "NOT_EVALUATED",
            "reason": "Chưa có artifacts/baselines/benchmark_results.json.",
        }
    current = run_benchmark()
    baseline = read_json(baseline_path, {})
    current_results = current.get("results", [])
    baseline_results = baseline.get("results", [])
    def avg(rows: list[dict[str, Any]], key: str) -> float:
        return sum(float(row.get(key, 0.0)) for row in rows) / len(rows) if rows else 0.0
    drops = {
        key: avg(baseline_results, key) - avg(current_results, key)
        for key in ("faithfulness", "relevance", "completeness")
    }
    regressions = [key for key, drop in drops.items() if drop > 0.05]
    return {
        "status": "FAIL" if regressions else "PASS",
        "threshold": 0.05,
        "drops": drops,
        "regressions": regressions,
    }


def save_baseline() -> dict[str, Any]:
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    baseline = run_benchmark()
    BASELINE_FILE.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "SAVED", "path": str(BASELINE_FILE.relative_to(ROOT))}


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "NorthstarDemo/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, value: Any, status: int = HTTPStatus.OK) -> None:
        data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Request body phải là JSON object.")
        return value

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/" or path == "/demo_app.html":
            data = DEMO_FILE.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/api/state":
            self._send_json(_state())
            return
        self._send_json({"error": "Không tìm thấy đường dẫn."}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/query":
                self._send_json(run_query(payload))
            elif path == "/api/validate":
                self._send_json(_validation_view())
            elif path == "/api/benchmark":
                self._send_json(run_benchmark())
            elif path == "/api/reranking":
                self._send_json(run_reranking(payload))
            elif path == "/api/regression":
                self._send_json(run_regression())
            elif path == "/api/baseline":
                self._send_json(save_baseline())
            else:
                self._send_json({"error": "Không tìm thấy API."}, HTTPStatus.NOT_FOUND)
        except Exception as exc:  # pragma: no cover - HTTP boundary
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def main() -> int:
    parser = argparse.ArgumentParser(description="Chạy demo AI Evaluation tiếng Việt.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    server = ReusableThreadingHTTPServer((args.host, args.port), DemoHandler)
    url = f"http://{args.host}:{args.port}/"
    print(f"[OK] Northstar Eval Lab backend serving at {url}")
    print("[INFO] Mode: Offline mock generator, zero API credit usage.")
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDemo server stopped.")
    finally:
        server.server_close()
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
