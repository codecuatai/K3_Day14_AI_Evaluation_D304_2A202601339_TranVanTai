# Plan — Checkpoint CP2: Part 2 Core Coding

> **Lab:** Day 14 — AI Evaluation & Benchmarking Pipeline
> **File chính cần hoàn thiện:** `template.py`
> **Bản nộp/test ưu tiên:** `solution/solution.py`
> **Thời gian:** 09:45–10:40 (55 phút)
> **Mục tiêu:** hoàn thành 5 Task bắt buộc và đạt tối thiểu `41 passed, 1 skipped`.

---

## Nguyên tắc thực hiện

1. Làm đúng thứ tự Task 1 → Task 5.
2. Hoàn thành một Task thì chạy targeted test ngay, không đợi đến cuối.
3. Không đổi tên class/function/signature và không sửa tests.
4. Retrieval metrics chỉ là diagnostics; không được đưa vào `overall_score()` hoặc pass rule gốc.
5. `rerank_by_overlap()` là bonus, có thể để `NotImplementedError` và chấp nhận 1 test skipped.

## Agent Brief — đọc trước khi bắt đầu

**Nhiệm vụ duy nhất:** hoàn thiện phần core evaluation trong `template.py`, sau đó xác nhận bằng
targeted tests và full suite. Không mở rộng sang Part 3, không tối ưu dataset riêng và không sửa
test để làm pass.

**Thứ tự bắt buộc:**

```text
Task 1 models
  → test Task 1
Task 2 metrics + full eval
  → test Task 2
Task 3 LLM judge
  → test Task 3
Task 4 benchmark runner
  → test Task 4
Task 5 failure analyzer
  → test Task 5
copy solution/solution.py
  → pytest tests/ -v
```

**Nếu một targeted test fail:** đọc assertion và traceback, sửa đúng function đang fail, chạy lại
chính targeted test đó. Không nhảy sang Task tiếp theo khi Task hiện tại chưa xanh.

**Definition of Done:** chỉ báo CP2 hoàn thành khi tất cả targeted tests đạt và full suite đạt tối
thiểu `41 passed, 1 skipped`. Nếu còn test fail, phải báo rõ test nào fail và nguyên nhân; không
đánh dấu hoàn thành chỉ vì `python template.py` chạy được.

### Phân bổ thời gian gợi ý

| Thời gian | Việc cần làm |
|---:|---|
| 0–5 phút | Đọc TODO, xác nhận file test đang load và chạy targeted baseline |
| 5–12 phút | Task 1 + test |
| 12–27 phút | Task 2 + test |
| 27–34 phút | Task 3 + test |
| 34–45 phút | Task 4 + test |
| 45–52 phút | Task 5 + test |
| 52–55 phút | Copy solution, full suite, ghi nhận kết quả |

Nếu thiếu thời gian, bỏ bonus reranking trước; không bỏ targeted test và không bỏ wiring retrieval.

### Bốn bẫy cần kiểm tra trước khi kết luận fail

1. **Tests có thể đang load file khác:** nếu `solution/solution.py` tồn tại, sửa `template.py` thôi
   sẽ không làm kết quả test thay đổi. Copy lại solution trước khi kết luận code chưa chạy.
2. **`contexts=None` khác `contexts=[]`:** `None` nghĩa là không yêu cầu retrieval metrics;
   list rỗng vẫn là contexts được truyền vào và phải tính hai retrieval scores.
3. **Thứ tự dataclass quan trọng:** tests có positional constructor; thêm field ở sai vị trí sẽ gây
   lỗi không liên quan trực tiếp đến logic đang sửa.
4. **Retrieval metrics không phải answer metrics:** không dùng chúng trong `passed`,
   `identify_failures()` hoặc `overall_score()`.

### Quy tắc chỉnh sửa an toàn

- Chỉ sửa phần TODO bắt buộc và các dòng hỗ trợ trực tiếp cho TODO.
- Giữ nguyên public signatures, tên key trong dict và wording được nêu rõ trong docstring.
- Không thêm dependency mới, không gọi API thật, không thay đổi `tests/`.
- Ưu tiên code đơn giản, dễ đọc; mỗi edge case quan trọng nên được xử lý ngay tại function đó.

### Lưu ý về file được test

`tests/test_solution.py` ưu tiên load `solution/solution.py` nếu file này tồn tại; nếu chưa có thì
test `template.py`. Vì vậy nên làm việc trên `template.py`, sau khi hoàn thiện thì copy sang
`solution/solution.py`, rồi chạy lại toàn bộ targeted tests và full suite.

PowerShell:

```powershell
Select-String -Path template.py -Pattern "# TODO"
pytest tests/test_solution.py::TestEvalResultOverallScore -v
```

---

## Task 1 — Data Models

### Phạm vi cần làm

Hoàn thiện `QAPair`, `EvalResult` và `EvalResult.overall_score()`.

### Thiết kế field

`QAPair` cần có đúng các field chính:

```text
question: str
expected_answer: str
context: str = ""
metadata: dict = field(default_factory=dict)
retrieved_contexts: list = field(default_factory=list)
```

`metadata` và `retrieved_contexts` phải dùng `default_factory`, không dùng mutable default trực tiếp.
Giữ đúng thứ tự field để các test đang khởi tạo positional không bị vỡ.

`EvalResult` nên giữ thứ tự tương thích với constructor hiện có:

```text
qa_pair
actual_answer
faithfulness
relevance
completeness
passed
failure_type = None
context_precision = None
context_recall = None
```

`overall_score()` chỉ tính:

```text
(faithfulness + relevance + completeness) / 3.0
```

Không tính `context_recall` hoặc `context_precision` vào điểm này.

### Kiểm tra sau Task 1

```powershell
pytest tests/test_solution.py::TestEvalResultOverallScore -v
```

Kỳ vọng: `3 passed`.

---

## Task 2 — RAGASEvaluator

### 2a. Ba answer-side metrics

Dùng `_tokenize()` đã có sẵn, không tự thay đổi công thức:

| Function | Công thức | Trường hợp mẫu số rỗng |
|---|---|---|
| `evaluate_faithfulness(answer, context)` | `|answer ∩ context| / |answer|` | answer rỗng → `1.0` |
| `evaluate_relevance(answer, question)` | `|answer ∩ question| / |question|` | question rỗng → `1.0` |
| `evaluate_completeness(answer, expected)` | `|answer ∩ expected| / |expected|` | expected rỗng → `1.0` |

Mọi kết quả phải nằm trong `[0.0, 1.0]`. Không để xảy ra `ZeroDivisionError`.

### 2b. Hai retrieval-side metrics

#### `evaluate_context_recall(contexts, expected)`

- Tokenize từng chunk rồi lấy **union** của tất cả chunks.
- Tính coverage của `expected_tokens` trên union đó.
- Thứ tự chunks không ảnh hưởng recall.
- `expected` rỗng → `1.0`; contexts rỗng với expected không rỗng → `0.0`.

#### `evaluate_context_precision(contexts, expected, relevance_threshold=0.1)`

Triển khai rank-aware Average Precision:

1. Một chunk relevant nếu
   `len(chunk_tokens ∩ expected_tokens) / len(expected_tokens) >= relevance_threshold`.
2. Với mỗi rank `k`, tính `Precision@k = relevant_so_far / k`.
3. Chỉ cộng `Precision@k` tại các rank relevant.
4. Chia tổng cho tổng số relevant chunks.

Quy tắc biên:

- expected rỗng → `1.0`.
- contexts rỗng hoặc không có chunk relevant → `0.0`.
- Chunk relevant đứng sớm phải cho điểm cao hơn cùng chunk đứng muộn.

### 2c. `run_full_eval()` và wiring

Luôn chạy ba answer metrics trước. Sau đó:

- `contexts is None` → `context_recall=None`, `context_precision=None`.
- `contexts` là list, kể cả list rỗng → tính và lưu cả hai retrieval metrics.
- `passed=True` chỉ khi cả Faithfulness, Relevance và Completeness `>= 0.5`.
- `failure_type` theo first-match order trong docstring:
  - Faithfulness `< 0.3` → `hallucination`
  - Relevance `< 0.3` → `irrelevant`
  - Completeness `< 0.3` → `incomplete`
  - Nếu failed nhưng không rơi vào ba trường hợp trên → `off_topic`
- Retrieval scores không thay đổi `passed`, `failure_type` hoặc `overall_score()`.

### Kiểm tra sau Task 2

```powershell
pytest tests/test_solution.py::TestRAGASEvaluator tests/test_solution.py::TestContextMetrics tests/test_solution.py::TestRetrievalMetricWiring::test_run_full_eval_connects_optional_retrieval_metrics -v
```

Kỳ vọng: `14 passed, 1 skipped`. Test skipped là bonus reranking và không phải blocker của CP2.

---

## Task 3 — LLMJudge

### `__init__`

Lưu callable nhận vào, ví dụ `self.judge_llm_fn = judge_llm_fn`. Không gọi API khi khởi tạo.

### `score_response()`

Thứ tự xử lý:

1. Build prompt có đủ `question`, `answer` và nội dung `rubric`.
2. Gọi `self.judge_llm_fn(prompt)` đúng một lần.
3. Parse response JSON thành mapping criterion → score.
4. Trả về:

```python
{
    "scores": {"criterion": 0.0_to_1.0},
    "reasoning": "raw judge response or explanation",
}
```

Nếu response không parse được JSON scores, trả score mặc định `0.5` cho từng criterion trong
rubric, đồng thời vẫn giữ reasoning dạng string. Không gọi LLM thật trong unit test.

### `detect_bias()`

Luôn trả đủ ba key boolean:

```python
{
    "positional_bias": bool,
    "leniency_bias": bool,
    "severity_bias": bool,
}
```

- `leniency_bias`: average score toàn batch `> 0.8`.
- `severity_bias`: average score toàn batch `< 0.3`.
- `positional_bias`: chỉ kết luận khi batch có thông tin vị trí/điểm theo vị trí và score vị trí đầu
  cao một cách nhất quán; nếu không có dữ liệu vị trí thì trả `False`, không suy đoán.

### Kiểm tra sau Task 3

```powershell
pytest tests/test_solution.py::TestLLMJudge -v
```

Kỳ vọng: `4 passed`.

---

## Task 4 — BenchmarkRunner

### `run()`

Với từng `QAPair`:

1. Gọi `agent_fn(pair.question)` đúng một lần.
2. Gọi `evaluator.run_full_eval()` với question, expected answer, source context và answer vừa nhận.
3. Truyền `pair.retrieved_contexts` vào tham số `contexts` — kể cả list rỗng.
4. Bảo đảm `EvalResult.qa_pair` giữ lại đúng pair gốc.
5. Trả về đúng một `EvalResult` cho mỗi input pair.

### `generate_report()`

Trả về các key:

```text
total, passed, pass_rate,
avg_faithfulness, avg_relevance, avg_completeness,
avg_context_recall, avg_context_precision, failure_types
```

- Average answer metrics trên toàn bộ results.
- Average retrieval metrics chỉ trên các result có giá trị khác `None`.
- Nếu không result nào có retrieval score, average retrieval tương ứng là `None`.
- `failure_types` là bảng đếm theo `failure_type`.
- Có guard cho danh sách rỗng để không chia cho 0.

### `run_regression()`

- Tính average Faithfulness, Relevance và Completeness của new/baseline.
- Regression khi new average thấp hơn baseline **quá `0.05`**.
- Trả đủ các average fields, `regressions` và `passed`.
- `passed=True` khi không có metric nào regression.

### `identify_failures()`

Lọc các `EvalResult` có **bất kỳ answer-side score** nào thấp hơn threshold. Không dùng retrieval
metrics để thay đổi rule này.

### Kiểm tra sau Task 4

```powershell
pytest tests/test_solution.py::TestBenchmarkRunner tests/test_solution.py::TestRunRegression tests/test_solution.py::TestRetrievalMetricWiring::test_runner_forwards_retrieved_contexts tests/test_solution.py::TestRetrievalMetricWiring::test_report_includes_retrieval_averages -v
```

Kỳ vọng: `11 passed`.

---

## Task 5 — FailureAnalyzer

### `categorize_failures()`

Đếm số failure theo `failure_type`, trả về dict. Danh sách rỗng phải trả dict rỗng, không lỗi.

### `find_root_cause()`

So sánh ba answer-side scores và trả một trong các chuỗi đã nêu trong docstring:

- Faithfulness thấp nhất → `Context is missing or irrelevant — improve retrieval`
- Relevance thấp nhất → `Answer does not address the question — improve prompt clarity`
- Completeness thấp nhất → `Answer is missing key information — increase context window or improve generation`
- Không xác định được một lỗi nổi trội → `Multiple issues detected — review full pipeline`

Giữ nguyên wording của docstring để tránh fail các kiểm tra theo chuỗi.

### `generate_improvement_suggestions()`

- Phân tích failure categories và metric thấp.
- Trả về các suggestion dạng string, cụ thể và có thể hành động.
- Khi có failures, mục tiêu tối thiểu là 3 suggestions.
- Khi failures rỗng, có thể trả list rỗng.

Ví dụ hướng suggestion:

- tăng chunk size hoặc cải thiện retrieval khi incomplete/retrieval failure;
- thêm grounding guardrail/hallucination checker khi faithfulness thấp;
- làm rõ prompt hoặc intent routing khi relevance thấp.

### `generate_improvement_log()`

Tạo Markdown table có header và một row cho mỗi failure:

```text
| Failure ID | Type | Root Cause | Suggested Fix | Status |
|------------|------|------------|---------------|--------|
| F001       | ...  | ...        | ...           | Open   |
```

Status luôn là `Open`; ghép suggestion theo index và không lỗi nếu số suggestions ít hơn số failures.

### Kiểm tra sau Task 5

```powershell
pytest tests/test_solution.py::TestFailureAnalyzer tests/test_solution.py::TestGenerateImprovementLog -v
```

Kỳ vọng: `9 passed`.

---

## Quy trình xác nhận cuối CP2

Sau khi 5 targeted tests đều đạt:

```powershell
Copy-Item -LiteralPath template.py -Destination solution/solution.py -Force
pytest tests/ -v
```

Kỳ vọng bắt buộc: **`41 passed, 1 skipped`**.

Nếu đã triển khai bonus `rerank_by_overlap()` thì kỳ vọng có thể là **`42 passed`**.

Chạy thêm manual demo để kiểm tra output báo cáo:

```powershell
python template.py
```

`python template.py` chỉ là smoke/manual demo; không thay thế `pytest tests/ -v` và không chứng minh
đã pass đủ 42 test.

Nếu PowerShell không nhận lệnh `pytest`, dùng Python trong virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

## Mẫu bàn giao cho agent tiếp theo

Agent hoàn thành nên báo cáo ngắn theo mẫu sau:

```text
CP2 status: PASS hoặc BLOCKED

Files changed:
- template.py
- solution/solution.py (nếu đã copy)

Targeted tests:
- Task 1: X passed
- Task 2: X passed, Y skipped
- Task 3: X passed
- Task 4: X passed
- Task 5: X passed

Full suite: X passed, Y skipped, Z failed
Bonus reranking: implemented / not implemented
Remaining issue: none hoặc ghi rõ test + nguyên nhân
```

Chỉ dùng `PASS` khi full suite đạt tiêu chí CP2; nếu chưa đạt thì dùng `BLOCKED` hoặc báo cáo
`IN PROGRESS`, kèm bằng chứng test thực tế.

---

## Checklist CP2

- [ ] Không đổi signatures hoặc tests.
- [ ] Task 1: QAPair, EvalResult, overall_score hoàn chỉnh.
- [ ] Task 1 targeted: `3 passed`.
- [ ] Task 2: 3 answer metrics, 2 retrieval metrics, run_full_eval wiring hoàn chỉnh.
- [ ] Task 2 targeted: `14 passed, 1 skipped`.
- [ ] Task 3: init, score_response, detect_bias hoàn chỉnh.
- [ ] Task 3 targeted: `4 passed`.
- [ ] Task 4: run, report, regression, identify_failures hoàn chỉnh.
- [ ] Task 4 targeted: `11 passed`.
- [ ] Task 5: categorize, root cause, suggestions, improvement log hoàn chỉnh.
- [ ] Task 5 targeted: `9 passed`.
- [ ] Đã copy bản hoàn thiện sang `solution/solution.py`.
- [ ] Full suite đạt tối thiểu `41 passed, 1 skipped`.
