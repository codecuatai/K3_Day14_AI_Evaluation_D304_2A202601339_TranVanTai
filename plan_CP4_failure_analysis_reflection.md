# Plan — Checkpoint CP4: Failure Analysis & Reflection

> **Lab:** Day 14 — AI Evaluation & Benchmarking Pipeline
> **Phạm vi:** Part 4 — Failure Analysis & Reflection
> **File bắt buộc cần hoàn thiện:** `reflection.md`
> **Nguồn dữ liệu:** `artifacts/benchmark_results.json`, `artifacts/actual_answers.json`
> **Thời gian:** 15 phút
> **Mục tiêu:** 3 phân tích 5 Whys có root cause hành động được, improvement log và regression strategy.

---

## Agent Brief — đọc trước khi làm

CP4 là bước biến benchmark thành quyết định cải thiện hệ thống. Không chỉ mô tả “AI trả lời sai”;
phải chứng minh lỗi nằm ở retrieval, ranking, generation, routing, safety hoặc configuration nào.

**Thứ tự bắt buộc:**

```text
Đọc artifact thật
  → xác nhận 3 case Overall thấp nhất
  → inspect question/expected/actual/gold/retrieved
  → viết 5 Whys cho từng case
  → so sánh với find_root_cause()
  → cluster toàn bộ failures
  → viết improvement log
  → viết regression strategy
  → kiểm tra reflection.md đủ tiêu chí CP4
```

### Definition of Done

Chỉ báo CP4 hoàn thành khi `reflection.md` có:

- Summary khớp artifact thật, không dùng số liệu cũ hoặc tự đoán.
- Đúng 3 case có `overall` thấp nhất.
- Mỗi case có question, expected answer, actual answer, scores và evidence inspection.
- Mỗi case có symptom, đủ 5 Whys và root cause có thể hành động.
- Có so sánh rõ với `find_root_cause()` và giải thích nếu heuristic không khớp trace.
- Có fix cụ thể kèm metric/kiểm tra dùng để xác nhận fix.
- Có failure clustering và ưu tiên fix theo tác động nhiều case.
- Có improvement log và regression strategy dựa trên `run_regression()`.

**CP4 chỉ cần sửa `reflection.md`.** Không sửa corpus, code, tests hoặc artifact để làm kết luận
đẹp hơn.

---

## Bước 0 — Preflight: chống dùng số liệu stale

### 0.1 Kiểm tra artifact

```powershell
Test-Path -LiteralPath 'artifacts\benchmark_results.json'
Test-Path -LiteralPath 'artifacts\actual_answers.json'
Get-Item -LiteralPath 'artifacts\benchmark_results.json','artifacts\actual_answers.json' |
  Select-Object FullName, LastWriteTime, Length
```

Nếu một trong hai file không tồn tại, CP4 bị BLOCKED: quay lại CP3, không dùng các số liệu đang có
sẵn trong `reflection.md`.

`reflection.md` có thể đang chứa số liệu mẫu hoặc kết quả của một run cũ. Artifact mới là source
of truth duy nhất.

### 0.2 Lấy đúng 3 case thấp nhất

```powershell
$report = Get-Content -LiteralPath 'artifacts\benchmark_results.json' -Raw -Encoding UTF8 |
  ConvertFrom-Json
$report.results |
  Sort-Object -Property overall |
  Select-Object -First 3 id,difficulty,overall,passed,failure_type,faithfulness,relevance,completeness,context_recall,context_precision
```

Không chọn top 3 bằng cách nhìn failure type hoặc chọn các case dễ giải thích nhất. Nếu có tie,
giữ thứ tự xuất hiện trong artifact và ghi rõ tie trong reflection.

### 0.3 Mở trace của 3 case

```powershell
$actual = Get-Content -LiteralPath 'artifacts\actual_answers.json' -Raw -Encoding UTF8 |
  ConvertFrom-Json
$ids = @($report.results | Sort-Object overall | Select-Object -First 3 -ExpandProperty id)
$actual.answers | Where-Object { $_.id -in $ids } |
  Select-Object id,question,actual_answer,retrieved_contexts,error |
  Format-List
```

Đối chiếu thêm từng record trong `golden_dataset.json` để lấy `expected_answer` và gold contexts.

---

## Bước 1 — Viết Summary đúng bằng chứng

Trong phần `Benchmark Results Summary` của `reflection.md`, cập nhật:

- Overall pass rate;
- average/min/max của Context Recall, Context Precision;
- average/min/max của Faithfulness, Relevance, Completeness và Overall;
- failure type distribution;
- nhận xét tổng quan retrieval vs generation.

### Cách kết luận không quá đà

| Pattern trong artifact | Kết luận nên dùng |
|---|---|
| Recall thấp + Completeness thấp | “Có tín hiệu retriever bỏ sót evidence; cần kiểm tra gold/retrieved trace.” |
| Recall cao + Precision thấp | “Coverage đủ nhưng ranking/noise có vấn đề.” |
| Recall và Precision cao + Faithfulness thấp | “Generation có thể thêm claim ngoài context.” |
| Faithfulness cao + Relevance thấp | “Answer grounded nhưng không giải quyết đúng intent.” |
| Retrieval tốt + Completeness thấp | “Generator có thể bỏ sót điều kiện/ý chính.” |

Dùng các từ **gợi ý/có thể/ưu tiên kiểm tra** nếu metric chưa đủ để chứng minh root cause. Không
gọi lỗi generator là lỗi retriever chỉ vì `find_root_cause()` heuristic trả về retrieval.

---

## Bước 2 — Case Analysis Card cho từng failure

Mỗi case phải được phân tích theo cùng một format. Không bỏ qua bước nào.

### 2.1 Case identity

Ghi:

- ID, difficulty và attack type;
- question;
- expected answer;
- actual answer;
- Context Recall, Context Precision, Faithfulness, Relevance, Completeness, Overall;
- failure type từ artifact.

### 2.2 Evidence inspection

So sánh hai đường đi:

```text
Gold evidence → Retrieved chunks → Actual answer
```

Trả lời cụ thể:

1. Gold evidence có chứa đủ claim cần trả lời không?
2. Retrieved chunks có chứa claim đó không?
3. Chunk đúng có đứng đủ sớm không?
4. Actual answer có bỏ sót claim, thêm claim, lạc intent hay từ chối sai không?
5. Có mismatch nào giữa score heuristic và đọc thủ công không?

### 2.3 Symptom

Symptom chỉ mô tả điều quan sát được, ví dụ:

- “Answer từ chối dù retrieved chunk chứa deadline chính xác.”
- “Answer nêu policy claim không xuất hiện trong gold/retrieved context.”
- “Answer trả lời đúng chủ đề nhưng bỏ mất exception và effective date.”

Không viết symptom là “model kém” hoặc “AI trả lời sai”; đó chưa phải observation có thể kiểm chứng.

---

## Bước 3 — 5 Whys có tính nhân quả

Với mỗi case, điền bảng:

| Level | Câu hỏi | Câu trả lời dựa trên evidence |
|---|---|---|
| Symptom | Đã quan sát thấy gì? | Một câu có actual answer + trace |
| Why 1 | Vì sao answer tạo symptom này? | Liên hệ answer với context/prompt |
| Why 2 | Vì sao component đó xử lý sai? | Routing/retrieval/generation/config |
| Why 3 | Vì sao guardrail/test chưa bắt được? | Missing test, prompt rule hoặc gate |
| Why 4 | Vì sao thiết kế hiện tại cho phép lỗi lặp lại? | Root mechanism có thể tái diễn |
| Why 5 | Root cause nào có thể hành động? | Component + change cụ thể + metric verify |

### Quy tắc 5 Whys

- Mỗi Why phải trả lời Why trước, không nhảy sang một nguyên nhân mới.
- Không dừng ở “LLM hallucinate”, “prompt không tốt” hoặc “API lỗi”. Hãy nêu điều kiện gây ra nó.
- Nếu trace cho thấy retrieval tốt, không kết luận “improve retrieval” chỉ vì heuristic chọn metric
  thấp nhất là Faithfulness.
- Nếu artifact có `error` hoặc fallback, tách rõ **configuration/infrastructure root cause** khỏi
  model-generation root cause.
- Root cause tốt có dạng: “Khi [điều kiện], [component] làm [hành vi sai] vì thiếu [control],
  cần sửa [action].”

### Ví dụ root cause đạt yêu cầu

```text
Khi một câu hỏi in-domain chứa từ khóa giống safety instruction, routing/prompt fallback
chọn refusal template dù retrieved context đã chứa answer; cần bổ sung intent boundary test
và đo lại Relevance + Completeness trên các in-domain cases.
```

---

## Bước 4 — So sánh với `find_root_cause()`

Trong mỗi case, ghi đúng output của core:

- `Context is missing or irrelevant — improve retrieval`
- `Answer does not address the question — improve prompt clarity`
- `Answer is missing key information — increase context window or improve generation`
- `Multiple issues detected — review full pipeline`

Sau đó chọn một trong hai kết luận:

```text
Agree: output khớp với trace vì ...
hoặc
Disagree/qualify: heuristic chọn ... vì score thấp nhất là ..., nhưng trace cho thấy ...;
root cause thực tế nên là ...
```

Đây là điểm thể hiện tư duy đánh giá: heuristic là tín hiệu chẩn đoán, không phải ground truth
tuyệt đối.

---

## Bước 5 — Fix và metric verification

Mỗi case phải có fix cụ thể, không viết “cải thiện AI”. Dùng bảng:

| Root cause | Fix cụ thể | Metric cần verify | Điều kiện thành công |
|---|---|---|---|
| Missing evidence | tăng coverage/chunking/query expansion | Context Recall + Completeness | Recall tăng, Completeness không giảm |
| Noise/ranking | rerank hoặc chỉnh retrieval | Context Precision + Faithfulness | Precision tăng, Faithfulness ổn định/tăng |
| Unsupported claim | grounding instruction/checker | Faithfulness | Không còn unsupported claim; không tăng refusal sai |
| Wrong intent/refusal | sửa routing boundary/few-shot | Relevance + Completeness | In-domain answer không bị refusal |
| Missing condition | prompt “answer every part”/structured output | Completeness | giữ đủ date, amount, exception |
| Privacy/safety failure | safety rule + adversarial regression case | safety review + Faithfulness | không leak/không follow injection |

Mỗi fix cần nói rõ metric nào sẽ tăng hoặc failure nào sẽ giảm. Không hứa một con số không có
baseline; nếu chưa có baseline, dùng “target direction” và ghi cách đo.

---

## Bước 6 — Cluster toàn bộ failures

Không chỉ cluster theo `failure_type`, vì nhiều failure có cùng mechanism nhưng bị heuristic gắn
nhãn khác nhau. Dùng các cluster có thể hành động:

| Cluster | Dấu hiệu | IDs | Fix dùng chung | Priority |
|---|---|---|---|---|
| Retrieval coverage | recall thấp, evidence thiếu | | retriever/chunking/query | |
| Retrieval ranking | precision thấp, noise sớm | | rerank/top-k | |
| Grounding/generation | retrieval tốt, faithfulness thấp | | grounding guard/checker | |
| Completeness | evidence có nhưng answer bỏ sót | | structured prompt/max tokens | |
| Intent/routing | grounded hoặc refusal sai intent | | routing boundary/few-shot | |
| Safety/privacy | injection, leak, unsafe claim | | safety gate + human review | |
| Configuration/fallback | error/fallback lặp lại | | fix provider/config + smoke test | |

### Cách ưu tiên

Ưu tiên một cluster khi:

1. Nó ảnh hưởng nhiều IDs.
2. Nó ảnh hưởng case high-stakes/adversarial.
3. Fix có thể verify bằng metric và test tự động.

Trong reflection, ghi rõ: “Nếu chỉ được sửa một cluster, chọn ___ vì ___; metric kiểm chứng là ___.”

---

## Bước 7 — Improvement Log

Paste hoặc tái tạo output của `generate_improvement_log()` từ artifact thật, sau đó review thủ công.
Không để nguyên suggestion generic nếu nó không khớp evidence.

Improvement log tối thiểu phải có:

```text
| Failure ID | Type | Root Cause | Suggested Fix | Status |
|------------|------|------------|---------------|--------|
| F001 | ... | ... | ... | Open |
```

Sau bảng per-failure, thêm cluster action log để tránh patch từng answer:

| Priority | Cluster | Shared fix | IDs covered | Verification metric | Status |
|---:|---|---|---|---|---|
| 1 | | | | | Open |
| 2 | | | | | Open |
| 3 | | | | | Open |

Một suggestion tốt phải gồm **action + target component + verification metric**, ví dụ:

```text
Add an in-domain/out-of-scope routing boundary test and re-run Relevance and Completeness
on all cases that currently return refusal.
```

---

## Bước 8 — Regression Strategy cho benchmark tiếp theo

Phần này phải dựa trên `BenchmarkRunner.run_regression()` chứ không chỉ nói “chạy lại test”.

### 8.1 Khi nào chạy

Chạy offline benchmark và regression trước merge/deploy khi có:

- thay đổi code RAG hoặc evaluator;
- thay đổi prompt/routing/grounding guardrail;
- thay đổi chunking, retriever, reranker hoặc `top_k`;
- thay đổi model/provider/temperature;
- cập nhật corpus hoặc policy version.

### 8.2 Regression gate

`run_regression()` so sánh average Faithfulness, Relevance và Completeness của run mới với baseline.
Metric giảm quá `0.05` là regression và phải fail gate.

Để phù hợp Student Services, thêm safety gate ngoài average:

```text
Block nếu:
- bất kỳ adversarial case nào vi phạm safety/privacy;
- có unsupported policy claim nghiêm trọng;
- có case high-stakes bị hallucination dù average vẫn đạt;
- Faithfulness tụt dưới threshold an toàn đã thống nhất.
```

Context Recall/Precision vẫn phải theo dõi trong report; nếu chúng giảm, tạo cảnh báo retrieval dù
`run_regression()` core chủ yếu so sánh ba answer-side metrics.

### 8.3 Baseline và reproducibility

Mỗi run cần giữ:

- baseline results;
- new benchmark results;
- corpus_id/version;
- model/provider/prompt version/top_k;
- generated_at;
- danh sách regression và 3 lowest cases.

Không ghi API key vào artifact.

### 8.4 Flow đề xuất

```text
Change
  → validate golden dataset
  → generate actual answers
  → evaluate benchmark
  → run_regression(new, baseline)
  → case-level safety review
  → block / alert / deploy
```

---

## Bước 9 — WOW Layer cho CP4

Chỉ làm sau khi đủ tiêu chí bắt buộc:

- Gắn mỗi root cause với một component cụ thể: retriever, reranker, router, generator, guardrail
  hoặc configuration.
- Ghi “metric to recheck” cho mọi proposed fix.
- Nêu một fix giải quyết nhiều case và một fix chỉ dành cho case đặc biệt.
- Phân biệt rõ **quality regression** với **artifact/API/configuration failure**.
- Thêm một adversarial safety rule vào regression strategy.
- Viết một câu “what changed my mind”: kết luận ban đầu nào bị trace thực tế bác bỏ.

CP4 không cần thêm code để đạt điểm; chất lượng nằm ở reasoning có evidence và actionability.

---

## Checklist CP4

- [x] Đã xác nhận dùng artifact mới nhất, không dùng số liệu stale trong `reflection.md`.
- [x] Summary có metrics aggregate và failure distribution khớp artifact.
- [x] Đúng 3 case Overall thấp nhất đã được chọn.
- [x] Mỗi case có question, expected, actual, scores và evidence inspection.
- [x] Mỗi case có symptom quan sát được.
- [x] Mỗi case có đủ 5 Whys.
- [x] Root cause của mỗi case có component và action cụ thể.
- [x] Đã so sánh với output thật của `find_root_cause()`.
- [x] Mỗi fix có metric/verification method.
- [x] Đã cluster toàn bộ failures và ưu tiên shared fix.
- [x] Có per-failure improvement log và cluster action log.
- [x] Regression strategy dùng `run_regression()` với drop threshold `0.05`.
- [x] Có case-level safety gate cho adversarial/high-stakes failure.
- [ ] Chỉ sửa `reflection.md`, không sửa code/corpus/tests để làm đẹp kết quả. (WOW audit bổ sung script/report riêng, không thay đổi core code/corpus/tests.)

### Checklist WOW — không phải blocker

- [x] Có evidence coverage/traceability cho 3 case thấp nhất.
- [x] Có phân biệt metric signal với root cause thật.
- [x] Có một shared fix tác động nhiều case.
- [x] Có provenance và baseline strategy rõ ràng.
- [x] Có câu “what changed my mind”.

---

## Mẫu bàn giao CP4 cho agent tiếp theo

```text
CP4 status: PASS / BLOCKED / IN PROGRESS

Source of truth:
- benchmark artifact: current / stale / missing
- actual-answer artifact: current / stale / missing

Top 3 IDs: ___, ___, ___

Case analyses:
- 5 Whys x 3: complete / incomplete
- Root causes actionable: yes / no
- find_root_cause comparison: complete / incomplete

Clustering:
- Main cluster: ___
- Shared fix: ___
- Verification metric: ___

Regression strategy: complete / incomplete
Reflection file: complete / incomplete
Remaining issue: none hoặc ghi rõ
```
