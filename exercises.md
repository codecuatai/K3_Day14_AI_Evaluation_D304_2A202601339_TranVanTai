# Day 14 — Exercises

## AI Evaluation & Benchmarking · Lab Worksheet

**Thời gian làm bài:** 09:15–12:00

**Domain:** Northstar University Student Services

Điền trực tiếp câu trả lời vào file này. Golden dataset 20 QA được viết một lần
duy nhất trong `golden_dataset.json`, không chép lại toàn bộ vào Markdown.

---

Từ 09:15–09:30, cài môi trường và chạy baseline tests theo `guide_lab.md`.

---

## Part 1 — Warm-up (09:30–09:45)

### Exercise 1.1 — RAGAS Metric Thresholds

Theo bài giảng:

- 0.8–1.0: Good — monitor, maintain.
- 0.6–0.8: Needs work — analyze failures, iterate.
- Dưới 0.6: Significant issues — investigate.

Với từng metric, xác định khi nào score thấp có thể chấp nhận và khi nào là critical.

| Metric | Acceptable Low Score Scenario | Critical Low Score Scenario | Action Required |
|---|---|---|---|
| Faithfulness | Câu hỏi yêu cầu tóm tắt/diễn giải chính sách — answer dùng từ ngữ paraphrase khác context khiến word-overlap giảm dù ý nghĩa hoàn toàn đúng. | < 0.3: Model tự ý bịa thông tin không có trong retrieved context (hallucination), ví dụ: bịa deadline nộp học phí hoặc bịa điều kiện gia hạn học bổng — gây rủi ro lớn cho sinh viên. | Kiểm tra grounding guardrail trong prompt, bổ sung yêu cầu "chỉ dùng thông tin từ context", xem xét giảm temperature. |
| Answer Relevance | Câu hỏi rất ngắn (2–3 từ kỹ thuật như "tuition deadline?") nhưng answer trả lời dài, đúng và đầy đủ — tỉ lệ word-overlap thấp do câu hỏi ít token. | < 0.3: Answer đi hoàn toàn lạc chủ đề (ví dụ: sinh viên hỏi đăng ký môn học nhưng AI trả lời về quy trình khiếu nại điểm số). | Xem lại intent detection và routing logic; kiểm tra domain scope filter trong system prompt. |
| Context Recall | Gold expected answer có thêm chi tiết nền hoặc chi tiết tùy chọn không cần cho task, trong khi retriever vẫn lấy đủ evidence cốt lõi để trả lời đúng. Recall thấp theo heuristic khi đó cần được kiểm tra thủ công trước khi coi là regression. | < 0.5: Retriever bỏ sót evidence quan trọng của câu hỏi cross-document (ví dụ: câu hỏi về incomplete grade cần dữ liệu từ 05_attendance và 08_appeals nhưng chỉ lấy 1 doc). Generator nhận thiếu context nên answer tất yếu bị incomplete. | Tăng top_k, cải thiện chiến lược chunking, thử áp dụng query expansion hoặc hybrid search. |
| Context Precision | Gold context/label chưa bao quát một chunk paraphrase hoặc một nguồn evidence hợp lệ khác. Heuristic word-overlap có thể đánh chunk đó là không relevant dù answer vẫn grounded; cần human review. | < 0.3: Noise chunks (tài liệu không liên quan) đứng ở đầu ranking, làm pha loãng context window làm generator dễ bị xao lãng và sinh hallucination. | Áp dụng Reranking (xắp xếp lại theo word-overlap hoặc cross-encoder), fine-tune tham số BM25. |
| Completeness | Expected answer được viết rất dài/verbose nhưng sinh viên thực tế chỉ cần ý chính core — overlap thấp dù câu trả lời đạt mục đích. | < 0.4: Answer bỏ sót điều kiện/thông tin then chốt (ví dụ: hướng dẫn nộp phúc khảo nhưng bỏ qua deadline 10 ngày làm việc) dẫn tới sinh viên làm sai quy trình. | Phân tích root cause: Nếu Context Recall thấp → fix Retriever; nếu Context Recall cao → fix Generator prompt/tăng max_tokens. |

`Context Recall` và `Context Precision` là retrieval-side diagnostics trên `QAPair.retrieved_contexts`.
Hai metric này không được đưa vào `overall_score()` và không thay đổi pass rule gốc của core lab.

**Diagnostic:**

- `Context Recall` thấp + `Completeness` thấp thường là tín hiệu mạnh của lỗi retriever: generator
  không thể dùng evidence chưa được lấy ra.
- `Context Recall` và `Context Precision` đều cao nhưng `Faithfulness` thấp thường trỏ về lỗi
  generator/hallucination: evidence đã có nhưng answer thêm thông tin ngoài context.
- `Context Precision` thấp + `Faithfulness` thấp: ưu tiên kiểm tra retriever/reranker trước, không
  quy kết ngay cho generator.

### Exercise 1.2 — Bias trong LLM-as-a-Judge

Ba bias thường gặp:

- Position bias: judge ưu tiên answer xuất hiện trước.
- Verbosity bias: judge ưu tiên answer dài hơn.
- Self-preference: judge ưu tiên output giống chính model đó.

**Câu 1: Thiết kế experiment phát hiện position bias với ít nhất hai conditions.**

> *Câu trả lời:*
>
> **Thiết kế Thí nghiệm:** Sử dụng tập 10+ câu hỏi test set, mỗi câu hỏi có 2 câu trả lời A (chất lượng tốt hơn) và B (chất lượng kém hơn).
> - **Condition 1 (AB Order):** Đưa cho LLM Judge đánh giá theo thứ tự: Answer A đứng trước, Answer B đứng sau. Ghi lại điểm số `Score_A_pos1` và `Score_B_pos2`.
> - **Condition 2 (BA Order):** Tráo đổi vị trí, đưa cho LLM Judge đánh giá theo thứ tự: Answer B đứng trước, Answer A đứng sau. Ghi lại điểm số `Score_B_pos1` và `Score_A_pos2`.
>
> **Đánh giá & Kết luận:** So sánh điểm số trung bình của các câu trả lời khi ở vị trí 1 so với vị trí 2. Nếu `avg(Score_pos1)` cao hơn rõ rệt so với `avg(Score_pos2)` bất kể nội dung câu trả lời là A hay B (với kiểm định thống kê Paired t-test có p-value < 0.05 và delta > 0.1), ta kết luận LLM Judge mắc Position Bias.
>
> Để tránh content bias, cùng một answer phải xuất hiện một lần ở vị trí 1 và một lần ở vị trí 2. Thứ tự AB/BA nên được randomize hoặc counterbalance giữa các câu hỏi; không kết luận position bias từ một prompt hoặc một cặp answer duy nhất.

**Câu 2: Làm thế nào giảm verbosity bias bằng rubric design?**

> *Câu trả lời:*
>
> 1. **Tách biệt tiêu chí (Dimensions):** Tách bạch rõ tiêu chí `Correctness` (Độ chính xác) và `Conciseness` (Độ súc tích), không gộp chung thành một tiêu chí "Quality" chung chung.
> 2. **Định nghĩa điểm số theo Claim/Ý chính:** Định nghĩa mức Score 5 là "trả lời đủ và đúng các ý chính, không chứa thông tin thừa/rác", thay vì dựa trên số lượng từ.
> 3. **Thêm Hướng dẫn Trực tiếp (Explicit Prompt Guard):** Thêm chỉ dẫn nghiêm ngặt vào judge prompt: *"Do NOT award higher scores for longer responses. Evaluate factual accuracy and relevance only."*
> 4. **Bổ sung tiêu chí Precision:** Đánh giá tỉ lệ `từ/ý hữu ích trên tổng số từ` để phạt các câu trả lời dài dòng nhưng nhiều thông tin rác.

**Câu 3: Tại sao cần calibrate LLM judge với human labels?**

> *Câu trả lời:*
>
> LLM Judge dù có tính nhất quán nội tại cao nhưng vẫn có thể mắc phải các **systematic bias (định kiến hệ thống)** khiến kết quả chấm bị lệch so với thực tế. Việc Calibrate với Human Labels giúp:
> 1. **Đo lường độ tin cậy thực tế:** Tính chỉ số đồng thuận (như Cohen's Kappa hoặc Spearman Correlation) giữa điểm của LLM Judge và chuyên gia con người. Nếu Kappa < 0.6, rubric cần phải được sửa lại.
> 2. **Phát hiện Blind Spots:** Con người có thể phát hiện các lỗi sai tinh vi mang tính domain-specific (như sai mốc thời gian 1 ngày, nhầm lẫn giữa quy định cũ và mới) mà LLM Judge dễ bỏ qua.
> 3. **Đảm bảo an toàn cho các tác vụ High-stakes:** Trong môi trường giáo dục (Northstar Student Services), câu trả lời sai về deadline hoặc điều kiện học bổng gây hậu quả thực tế nghiêm trọng, cần kiểm chứng bằng đánh giá của con người.

### Exercise 1.3 — Evaluation trong CI/CD

**Câu 1: Chọn threshold để block deployment.**

| Metric | Threshold | Lý do |
|---|---:|---|
| Faithfulness | 0.70 | Mức rủi ro hallucination nghiêm trọng. Trong dịch vụ sinh viên, AI không được phép bịa đặt quy định/chính sách. Block deployment nếu dưới 0.70. |
| Answer Relevance | 0.60 | Dưới threshold này câu trả lời bị lạc đề, sinh viên không nhận được thông tin cần thiết. Block deployment nếu dưới 0.60. |
| Completeness | 0.55 | Đặt threshold mềm hơn (Alert trước) do Completeness có thể bị ảnh hưởng bởi paraphrasing của heuristic word-overlap. Block nếu đi kèm Context Recall thấp. |

Đây là các starting thresholds cho lab, cần hiệu chỉnh bằng baseline, human labels và confidence
interval khi đưa vào CI/CD thật. Nên dùng hai lớp quality gate:

1. **Dataset-level gate:** điểm trung bình và regression so với baseline không được vượt threshold.
2. **Case-level safety gate:** một case có hallucination nghiêm trọng, policy sai hoặc faithfulness
   cực thấp vẫn phải block và chuyển human review, dù điểm trung bình toàn dataset đạt.

**Câu 2: Khi nào dùng offline evaluation, online evaluation và human review?**

> *Câu trả lời:*
>
> - **Offline Evaluation (RAGAS / Automated Benchmark):** Dùng tự động trong CI/CD Pipeline **trước khi deploy** mỗi khi có thay đổi code, prompt, retriever hoặc model. Mục tiêu: Đảm bảo không bị suy giảm chất lượng (regression) trên Golden Dataset.
> - **Online Evaluation (TruLens / Langfuse / Production Monitoring):** Dùng liên tục trên real user traffic **sau khi deploy**. Mục tiêu: Phát hiện *distribution shift* (câu hỏi thực tế của sinh viên khác với tập golden dataset) và cảnh báo khi metric bị trôi (drift).
> - **Human Review:** Dùng theo dạng **sampling định kỳ**, khi có sự kiện đặc biệt (major release, thay đổi chính sách trường), hoặc khi Online/Offline metrics phát hiện ra failure cluster mới để kiểm chứng và calibrate lại LLM Judge.

---

## Part 2 — Core Coding (09:45–10:40)

Hoàn thiện các TODO bắt buộc trong `template.py`.

### Task 1 — Data Models

- `QAPair`: question, expected answer, gold context, metadata và retrieved contexts.
- `EvalResult`: answer-side scores, optional retrieval scores, pass/failure fields.
- `overall_score()`: trung bình Faithfulness, Relevance và Completeness.

### Task 2 — RAGASEvaluator

Answer-side:

- `evaluate_faithfulness(answer, context)`
- `evaluate_relevance(answer, question)`
- `evaluate_completeness(answer, expected)`

Retrieval-side:

- `evaluate_context_recall(contexts, expected)`
- `evaluate_context_precision(contexts, expected)`

Full pipeline:

- `run_full_eval(..., contexts=None)` luôn tính ba answer metrics.
- Nếu có `contexts`, tính và lưu thêm Context Recall và Context Precision.
- Retrieval scores không làm thay đổi `overall_score()` và pass rule gốc.

### Task 3 — LLMJudge

- `score_response(question, answer, rubric)`
- `detect_bias(scores_batch)`

### Task 4 — BenchmarkRunner

- `run(qa_pairs, agent_fn, evaluator)`
- `generate_report(results)`
- `run_regression(new_results, baseline_results)`
- `identify_failures(results, threshold)`

`BenchmarkRunner.run()` phải truyền `pair.retrieved_contexts` vào
`run_full_eval()`. Report phải có average của hai retrieval metrics.

### Task 5 — FailureAnalyzer

- `categorize_failures(failures)`
- `find_root_cause(failure)`
- `generate_improvement_suggestions(failures)`
- `generate_improvement_log(failures, suggestions)`

Kiểm tra:

```bash
pytest tests/ -v
```

`rerank_by_overlap()` là TODO bonus của Exercise 3.5. Test tương ứng được skip
nếu bạn chưa làm bonus.

---

## Part 3 — Golden Dataset & Real Benchmark (10:40–11:35)

### Exercise 3.1 — Build the Golden Dataset

Thiết kế và validate dataset theo Mục 5–6 trong `guide_lab.md`. Nội dung 20 QA
được điền trực tiếp trong `golden_dataset.json`; phần dưới chỉ ghi lại kết quả
và quyết định thiết kế, không chép lại toàn bộ QA.

**Kết quả dataset**

| Hạng mục | Kết quả |
|---|---|
| Tổng số records | ____ / 20 |
| Easy | ____ / 5 |
| Medium | ____ / 7 |
| Hard | ____ / 5 |
| Adversarial | ____ / 3 |
| Source documents được sử dụng | ____ / 10 |
| Validator status | PASS / FAIL |

**Ba case đại diện cho quyết định thiết kế**

| ID | Difficulty | Source document(s) | Vì sao case phù hợp với difficulty/attack type? |
|---|---|---|---|
| | | | |
| | | | |
| | | | |

**Điểm khó nhất khi xây dựng expected answer hoặc evidence là gì?**

> *Câu trả lời:*

**Xác nhận:**

- [ ] Mọi claim trong expected answer đều có evidence hỗ trợ.
- [ ] Không có questions trùng ý và không dùng kiến thức ngoài corpus.
- [ ] `python validate_golden_dataset.py` báo `PASS`.

### Exercise 3.2 — Benchmark Run

Chạy:

```bash
python domain_assistant.py
python evaluate_answers.py
```

Copy bảng terminal vào đây hoặc điền từ `artifacts/benchmark_results.json`.

| ID | Question (short) | Ctx Recall | Ctx Precision | Faithfulness | Relevance | Completeness | Overall | Passed? | Failure Type |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| E01 | | | | | | | | | |
| E02 | | | | | | | | | |
| E03 | | | | | | | | | |
| E04 | | | | | | | | | |
| E05 | | | | | | | | | |
| M01 | | | | | | | | | |
| M02 | | | | | | | | | |
| M03 | | | | | | | | | |
| M04 | | | | | | | | | |
| M05 | | | | | | | | | |
| M06 | | | | | | | | | |
| M07 | | | | | | | | | |
| H01 | | | | | | | | | |
| H02 | | | | | | | | | |
| H03 | | | | | | | | | |
| H04 | | | | | | | | | |
| H05 | | | | | | | | | |
| A01 | | | | | | | | | |
| A02 | | | | | | | | | |
| A03 | | | | | | | | | |

**Aggregate Report**

- Overall pass rate: ____%
- Avg Context Recall: ____
- Avg Context Precision: ____
- Avg Faithfulness: ____
- Avg Relevance: ____
- Avg Completeness: ____
- Failure type distribution: ____

**Ba cases có Overall Score thấp nhất**

1. ID: ____ | Score: ____ | Failure type: ____
2. ID: ____ | Score: ____ | Failure type: ____
3. ID: ____ | Score: ____ | Failure type: ____

**Nhận xét ngắn:** Metric nào yếu nhất? Kết quả gợi ý vấn đề nằm ở retrieval
hay generation?

> *Câu trả lời:*

### Exercise 3.3 — LLM-as-a-Judge Rubric Design

Thiết kế rubric domain-specific cho Student Services. Mỗi mức phải đủ cụ thể để
hai người chấm độc lập có thể hiểu giống nhau.

Chọn 3–5 dimensions:

- [ ] Correctness
- [ ] Completeness
- [ ] Relevance
- [ ] Evidence/citation
- [ ] Actionability
- [ ] Safety/privacy
- [ ] Tone/clarity
- [ ] Dimension khác: __________

| Score | Tiêu chí domain-specific | Ví dụ response |
|---:|---|---|
| 5 | | |
| 4 | | |
| 3 | | |
| 2 | | |
| 1 | | |

**Ba edge cases khó chấm**

| Edge Case | Tại sao khó chấm? | Rubric xử lý thế nào? |
|---|---|---|
| | | |
| | | |
| | | |

**Bias controls:** Rubric hoặc evaluation protocol của bạn giảm position bias,
verbosity bias và self-preference bằng cách nào?

> *Câu trả lời:*

### Exercise 3.4 — Framework Comparison (Bonus +10)

Chỉ làm sau khi hoàn thành 3.1–3.3. Chọn hai framework trong RAGAS, DeepEval
và TruLens; chạy hoặc thiết kế một so sánh có cùng input dataset.

| Tiêu chí | Framework 1: ____ | Framework 2: ____ |
|---|---|---|
| Setup complexity | | |
| Metrics available | | |
| CI/CD integration | | |
| Kết quả trên cùng dataset | | |
| Insight rút ra | | |

- Scores có nhất quán không?
- Framework nào strict hơn và vì sao?
- Hai framework có tìm ra cùng failure cases không?

> *Phân tích:*

### Exercise 3.5 — Retrieval Reranking (Bonus +5)

Mục tiêu: kiểm tra việc đổi thứ tự chunks có tăng Context Precision mà không
thay đổi Context Recall hay không.

1. Chọn ít nhất 5 cases từ `artifacts/actual_answers.json`.
2. Tính Context Recall và Context Precision trước rerank.
3. Implement `rerank_by_overlap()` hoặc một reranker khác.
4. Rerank cùng tập chunks, không thêm hoặc xóa chunk.
5. Tính lại hai metrics và giải thích kết quả.

| ID | Recall before | Recall after | Precision before | Precision after | Delta Precision |
|---|---:|---:|---:|---:|---:|
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| **Avg** | | | | | |

**Tại sao Recall dự kiến không đổi?**

> *Câu trả lời:*

**Khi nào reranking không đủ và cần sửa retriever/query/chunking?**

> *Câu trả lời:*

---

## Part 4 — Reflection (11:35–11:50)

Hoàn thành `reflection.md` bằng kết quả thật từ Exercise 3.2.

---

## Completion Checklist

Hoàn thành kiểm tra cuối trong khoảng 11:50–12:00.

- [ ] Tất cả required tests pass.
- [ ] `golden_dataset.json` validate thành công.
- [ ] Exercise 3.1 hoàn thành trong file JSON và bảng kết quả phía trên.
- [ ] Exercise 3.2 có năm metrics, aggregate report và ba cases thấp nhất.
- [ ] Exercise 3.3 có rubric 1–5 và bias controls.
- [ ] `reflection.md` có ba failure analyses và regression strategy.
- [ ] Đã copy `template.py` thành `solution/solution.py`.
- [ ] Exercise 3.4 và 3.5 chỉ làm nếu chọn bonus.
