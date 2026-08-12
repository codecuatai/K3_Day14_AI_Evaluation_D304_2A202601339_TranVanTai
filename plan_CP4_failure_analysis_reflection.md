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
