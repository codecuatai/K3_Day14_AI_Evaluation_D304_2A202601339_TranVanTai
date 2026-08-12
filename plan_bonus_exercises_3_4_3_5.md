# Plan — Bonus Exercises 3.4 & 3.5

> **Lab:** Day 14 — AI Evaluation & Benchmarking Pipeline
> **Bonus tối đa:** +15 điểm
> **Phạm vi:** Exercise 3.4 (+10) và Exercise 3.5 (+5)
> **File ghi kết quả:** `exercises.md`
> **Nguyên tắc:** bonus không thay thế CP1–CP4 và không sửa tests để lấy điểm.

---

## Agent Brief — đọc trước khi làm

Mục tiêu bonus là tạo bằng chứng thực nghiệm, không chỉ viết mô tả lý thuyết:

```text
Exercise 3.4: cùng input → so sánh RAGAS và DeepEval → ghi phương pháp + kết quả + trade-off
Exercise 3.5: cùng chunks → rerank → đo Recall/Precision trước và sau → chứng minh Recall không đổi
```

### Definition of Done

Bonus 3.4 đạt khi `exercises.md` có:

- cùng dataset/input được dùng cho cả hai framework;
- mapping metrics và protocol công bằng;
- kết quả hoặc bảng quan sát được;
- phân tích điểm giống, khác, chi phí và khi nào dùng framework nào;
- ghi rõ version, model/judge và giới hạn nếu experiment không chạy được đầy đủ.

Bonus 3.5 đạt khi `exercises.md` có:

- ít nhất 5 traces thật từ `artifacts/actual_answers.json`;
- Recall/Precision trước và sau cho từng trace;
- cùng tập chunks trước/sau, chỉ thay đổi thứ tự;
- Recall không đổi hoặc giải thích được sai lệch;
- Precision delta và kết luận khi reranking không đủ.

**Nếu framework chưa cài hoặc không có API:** không bịa số liệu. Ghi rõ `NOT RUN`/`BLOCKED`,
hoàn thành phần protocol và comparison matrix; điểm bonus có thể bị giới hạn. Bonus 3.5 vẫn có thể
hoàn thành đầy đủ vì dùng core heuristic hiện có.

---

## Bước 0 — Preflight

### 0.1 Kiểm tra phần bắt buộc

Bonus chỉ làm sau khi các điều kiện sau đã đạt:

```powershell
python validate_golden_dataset.py
pytest tests/ -q
Test-Path -LiteralPath 'artifacts\actual_answers.json'
Test-Path -LiteralPath 'artifacts\benchmark_results.json'
```

Kỳ vọng hiện tại: validator PASS, full suite tối thiểu `41 passed, 1 skipped` hoặc tốt hơn, actual
artifact đủ 20 records.

### 0.2 Kiểm tra implementation reranker

`rerank_by_overlap()` hiện đã có trong `template.py` và `solution/solution.py`. Không viết lại nếu
implementation đang pass:

```powershell
pytest tests/test_solution.py::TestContextMetrics::test_reranking_improves_or_keeps_precision -v
```

Nếu test pass, chuyển thẳng sang đo trước/sau. Nếu fail, chỉ sửa reranker sau khi giữ nguyên tập
chunks và xác định nguyên nhân bằng test.

### 0.3 Cẩn thận với `exercises.md`

Trước khi điền, tìm đúng các heading `Exercise 3.4` và `Exercise 3.5`. Nếu file có block rerank
trùng hoặc block bị đặt lệch, chỉ điền vào block canonical gần cuối Part 3; không tạo thêm bản sao.

---

# Exercise 3.4 (+10) — So sánh RAGAS và DeepEval

## Bước 1 — Chọn cùng input cho hai framework

### Protocol khuyến nghị

Dùng cùng 20 records của golden dataset và actual answers:

| Input | Nguồn |
|---|---|
| Question | `golden_dataset.json` |
| Expected/reference answer | `golden_dataset.json` |
| Actual answer | `artifacts/actual_answers.json` |
| Retrieved contexts | `artifacts/actual_answers.json` |
| Gold contexts | `golden_dataset.json` |

Không thay model answer, không đổi context, không chấm hai framework trên hai subset khác nhau.
Nếu chạy toàn bộ 20 quá tốn chi phí, chọn một subset stratified tối thiểu 8 cases: 2 Easy, 2
Medium, 2 Hard, 2 Adversarial; phải ghi rõ subset và lý do.

### Giữ công bằng giữa framework

- Dùng cùng model/judge LLM nếu cả hai framework cần LLM.
- Dùng cùng temperature, prompt rubric và request budget nếu cấu hình được.
- Chạy trên cùng một snapshot artifact; không regenerate answer giữa hai lần đo.
- Lưu version package, model name, timestamp và số lượng cases.
- Không dùng expected answer/gold context để sinh actual answer; chỉ dùng chúng ở evaluation stage.

## Bước 2 — Chuẩn hóa metric mapping

Ghi mapping trước khi chạy:

| Concept trong lab | RAGAS | DeepEval |
|---|---|---|
| Faithfulness/groundedness | Faithfulness | FaithfulnessMetric hoặc tương đương |
| Answer relevance | Answer Relevancy | Answer relevancy / task-specific metric |
| Completeness/reference coverage | Context Recall hoặc custom completeness | custom GEval/AnswerCompleteness |
| Retrieved context ranking | Context Precision | custom retrieval/ranking metric nếu framework hỗ trợ |
| Pass/fail gate | threshold của lab | assertion/threshold của DeepEval |

Không giả vờ rằng tên metric giống nhau nghĩa là đo cùng một thứ. Nếu framework không có metric
trực tiếp, ghi `custom metric` và mô tả công thức/prompt.

## Bước 3 — Cài/kiểm tra framework

Kiểm tra trước khi cài:

```powershell
python -c "import importlib.util; print('ragas=', bool(importlib.util.find_spec('ragas'))); print('deepeval=', bool(importlib.util.find_spec('deepeval')))"
```

Nếu package chưa có:

- không tự động sửa `requirements.txt` của phần bắt buộc;
- chỉ cài tạm trong `.venv` nếu có quyền/network và ghi lại version;
- nếu môi trường/API không cho phép, dùng comparison protocol + kết quả core heuristic, ghi rõ giới hạn.

## Bước 4 — Chạy experiment hoặc ghi trạng thái minh bạch

### Trường hợp A — Có framework và API

Chạy hai evaluation độc lập trên cùng prepared input. Lưu raw outputs ngoài `exercises.md` nếu cần,
ví dụ `artifacts/framework_comparison.json`, với các field:

```text
framework, version, model, dataset_ids, metric_values, thresholds, run_at, errors
```

Không lưu API key hoặc prompt chứa secret.

### Trường hợp B — Không thể chạy framework

Không điền số giả. Ghi:

```text
RAGAS: NOT RUN — package/API unavailable
DeepEval: NOT RUN — package/API unavailable
```

Sau đó vẫn hoàn thành bảng so sánh về focus, metric semantics, test integration, tracing, cost và
độ phù hợp. Ghi core lab heuristic là baseline tham khảo, không gọi đó là kết quả RAGAS/DeepEval.

## Bước 5 — Phân tích kết quả

Trong `exercises.md`, trả lời tối thiểu:

1. Framework nào phát hiện groundedness tốt hơn trên các case hallucination?
2. Framework nào thuận tiện hơn cho CI/CD assertion?
3. Framework nào phù hợp hơn cho tracing/online monitoring?
4. Các score có tương quan không? Case nào bất đồng lớn nhất và tại sao?
5. Chi phí/latency/reproducibility trade-off là gì?
6. Với Northstar Student Services, framework nào nên làm quality gate và framework nào nên làm monitoring?

### Kết luận mẫu cần tùy chỉnh theo dữ liệu thật

```text
DeepEval phù hợp hơn cho pytest-native assertions và CI blocking.
RAGAS phù hợp hơn cho bộ RAG metrics chuẩn hóa.
Không chọn framework chỉ vì average score cao hơn; kiểm tra disagreement ở các case high-stakes.
```

Không được trình bày kết luận mẫu này như kết quả đo nếu experiment chưa chạy.

## Bước 6 — Điền Exercise 3.4

Nên thêm các phần sau vào `exercises.md`:

```text
### Method
Dataset/input, subset, model, versions, thresholds, repeatability.

### Metric mapping
RAGAS ↔ DeepEval ↔ lab metrics.

### Results
Bảng theo framework và metric; ghi N/A/NOT RUN nếu không có.

### Disagreement analysis
Hai hoặc ba cases có chênh lệch lớn nhất.

### Decision
Framework dùng cho offline CI, framework dùng cho online/human calibration, và lý do.
```

---

# Exercise 3.5 (+5) — Reranking

## Bước 1 — Chọn traces

Chọn ít nhất 5 IDs có retrieved contexts và ưu tiên các trace có noise/relevant ordering khác nhau:

- ít nhất 2 case có `context_precision < 1.0` nếu dataset có;
- ít nhất 1 Easy, 1 Medium, 1 Hard;
- có thể thêm 1 Adversarial để kiểm tra safety evidence ordering;
- không chọn chỉ các case đang pass hoặc chỉ các case dễ nhất.

## Bước 2 — Đo trước rerank

Với mỗi case:

1. Lấy `question`, `expected_answer` và `retrieved_contexts` từ artifact/golden.
2. Giữ nguyên list chunks và thứ tự ban đầu.
3. Tính `Context Recall` và `Context Precision` bằng `RAGASEvaluator`.
4. Ghi thứ tự chunk IDs/source docs để có provenance.

## Bước 3 — Rerank

```python
from template import RAGASEvaluator, rerank_by_overlap

before = list(retrieved_contexts)
after = rerank_by_overlap(before, question)
```

Kiểm tra invariants trước khi đo lại:

```text
len(before) == len(after)
sorted(before) == sorted(after)
set(before) == set(after)
```

Chỉ thứ tự được thay đổi; không thêm, xóa, cắt hoặc sửa text chunk.

## Bước 4 — Đo sau rerank

Tính lại hai metrics trên `after`. Điền bảng:

| ID | Recall before | Recall after | Precision before | Precision after | Delta Precision |
|---|---:|---:|---:|---:|---:|
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| **Avg** | | | | | |

`Delta Precision = Precision after - Precision before`.

## Bước 5 — Giải thích Recall và Precision

### Vì sao Recall dự kiến không đổi?

Recall dùng union của chunk tokens. Reranking chỉ đổi thứ tự, không đổi union; vì vậy Recall phải
giữ nguyên, trừ trường hợp implementation vô tình thay đổi nội dung/list hoặc có lỗi đo.

### Khi nào Precision tăng?

Precision là rank-aware AP@K. Nếu chunk relevant được đưa lên sớm hơn noise, precision tăng.
Nếu không tăng, ghi trung thực rằng query-overlap không phù hợp với expected relevance của các case
đó; không ép số liệu.

### Khi reranking không đủ?

Cần sửa retriever/query/chunking khi:

- evidence quan trọng không xuất hiện trong list trước và sau rerank;
- Recall thấp vì retriever chưa lấy được chunk cần thiết;
- query wording không overlap với policy wording;
- chunk quá dài hoặc cắt mất claim/date/exception;
- noise chiếm phần lớn top-k dù rerank đã chạy.

## Bước 6 — Kiểm tra tối thiểu

```powershell
pytest tests/test_solution.py::TestContextMetrics::test_reranking_improves_or_keeps_precision -v
pytest tests/ -q
```

Full suite không được giảm vì bonus. Nếu `rerank_by_overlap()` làm thay đổi answer-side score hoặc
pass rule, đó là dấu hiệu bonus đã vượt scope và cần hoàn nguyên.

---

## WOW Layer cho bonus — không phải blocker

- [ ] Lưu `artifacts/framework_comparison.json` có versions, model, IDs và raw metric summary.
- [ ] Lưu `artifacts/rerank_results.json` có before/after và invariant checks.
- [ ] Vẽ hoặc mô tả một cặp ranking trước/sau cho case có Delta Precision lớn nhất.
- [ ] Ghi confidence/variability nếu framework dùng LLM judge chạy nhiều lần.
- [ ] Nêu rõ metric nào là heuristic, metric nào là semantic/LLM-based.
- [ ] Kết luận framework theo use case: CI gate, offline RAG diagnosis, online monitoring, human calibration.

## WOW++ Layer — nâng cấp chuyên nghiệp, không phải blocker

### WOW++ 1 — Per-case agreement matrix

Không chỉ so sánh average của RAGAS và DeepEval. Tạo bảng theo từng ID:

| ID | Difficulty | RAGAS Faithfulness | DeepEval Faithfulness | Delta | Agreement |
|---|---|---:|---:|---:|---|
| E01 | easy | | | | Agree/Disagree |

Quy tắc:

- Dùng đúng cùng question, answer và contexts cho hai framework.
- `Delta = abs(RAGAS - DeepEval)` hoặc công thức đã mô tả rõ.
- Đánh dấu `Disagree` nếu delta vượt ngưỡng đã chọn, ví dụ `0.20`.
- Chọn 2–3 case disagreement lớn nhất để giải thích: paraphrase, unsupported claim,
  refusal, missing condition hoặc khác biệt trong rubric.
- Không kết luận framework nào “đúng hơn” chỉ vì score cao hơn; cần đọc trace và human review.

Nếu có nhiều metrics, tạo agreement matrix riêng cho Faithfulness, Relevance và Completeness hoặc
ghi rõ chỉ chọn metric nào để phân tích sâu.

### WOW++ 2 — Reproducibility manifest

Tạo tùy chọn `artifacts/bonus_reproducibility.json` để lưu metadata của experiment:

```json
{
  "run_at": "...",
  "corpus_id": "northstar-student-services-v1",
  "dataset_file": "golden_dataset.json",
  "dataset_sha256": "...",
  "actual_answers_sha256": "...",
  "benchmark_sha256": "...",
  "frameworks": {
    "ragas": "version-or-NOT_RUN",
    "deepeval": "version-or-NOT_RUN"
  },
  "model": "...",
  "top_k": 5,
  "case_ids": ["E01", "E02"]
}
```

Mục tiêu là để người khác biết chính xác experiment dùng artifact nào. Không lưu API key, prompt
secret hoặc dữ liệu ngoài corpus. Nếu không tạo JSON, ghi các metadata này trực tiếp trong
`exercises.md` cũng được.

### WOW++ 3 — Variance/confidence check

Nếu framework dùng LLM judge và có đủ thời gian/budget:

1. Chạy cùng input tối đa 3 lần hoặc dùng seed/config cố định nếu framework hỗ trợ.
2. Tính `mean`, `min`, `max` và range cho từng metric.
3. Đánh dấu case không ổn định nếu range vượt `0.10`.
4. Ghi rõ variance có thể đến từ stochastic judge, prompt hoặc model version.

| ID | Metric | Run 1 | Run 2 | Run 3 | Mean | Range | Stable? |
|---|---|---:|---:|---:|---:|---:|---|
| | Faithfulness | | | | | | Yes/No |

Nếu không đủ API budget, ghi `NOT RUN — budget/time constraint`; không tự tạo confidence interval.

### WOW++ 4 — Bonus regression gate

Bổ sung một quality gate cho kết quả bonus:

- Framework agreement delta vượt ngưỡng → human review, không tự động chọn framework theo score.
- Reranking làm Precision giảm → không chấp nhận reranker dù Recall không đổi.
- Recall thay đổi sau rerank → kiểm tra invariant vì có thể đã thêm/xóa/sửa chunk.
- Variance quá cao → đánh dấu metric chưa đủ ổn định để dùng làm deployment gate.

### WOW++ 5 — Dashboard integration

Nếu đã có `artifacts/dashboard.html`, có thể thêm một panel nhỏ hiển thị:

- Framework agreement/disagreement count;
- Rerank average Delta Precision;
- Recall invariant status;
- Framework versions và run timestamp.

Đây là phần trình bày tùy chọn; không được để việc sửa dashboard làm ảnh hưởng benchmark hoặc
`exercises.md` bắt buộc.

---

## Checklist bonus

- [ ] CP1–CP4 đã PASS trước khi làm bonus.
- [ ] Exercise 3.4 dùng cùng dataset/input cho cả hai framework.
- [ ] Exercise 3.4 có metric mapping, method, results, disagreement và decision.
- [ ] Không bịa số liệu khi framework/API unavailable.
- [ ] Exercise 3.5 chọn ít nhất 5 traces thật.
- [ ] Rerank giữ nguyên tập chunks, chỉ đổi thứ tự.
- [ ] Recall before/after được ghi cho từng trace và aggregate.
- [ ] Precision before/after và Delta Precision được ghi cho từng trace và aggregate.
- [ ] Có giải thích tại sao Recall không đổi.
- [ ] Có tiêu chí khi nào reranking không đủ.
- [ ] Targeted rerank test và full suite vẫn pass.
- [ ] Bonus không làm thay đổi core pass rule hoặc `overall_score()`.

### Checklist WOW++ — không phải blocker

- [ ] Có per-case agreement matrix và disagreement analysis.
- [ ] Có reproducibility manifest với hash/version/timestamp, không có secret.
- [ ] Có variance/confidence check hoặc ghi rõ `NOT RUN` với lý do.
- [ ] Có bonus regression gate cho framework disagreement và rerank invariants.
- [ ] Dashboard có panel bonus hoặc ghi rõ lý do không tích hợp.

---

## Mẫu bàn giao bonus

```text
Bonus status: PASS / PARTIAL / BLOCKED

Exercise 3.4:
- Frameworks compared: RAGAS / DeepEval
- Same input: yes / no
- Run status: executed / NOT RUN
- Results recorded: yes / no
- Main decision: ...

Exercise 3.5:
- Traces measured: X
- Recall changed: yes / no
- Precision delta average: ...
- Invariants preserved: yes / no
- Rerank test: pass / fail

Artifacts:
- framework comparison: path or none
- rerank results: path or none

Remaining issue: none hoặc ghi rõ
```
