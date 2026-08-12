# Plan — Checkpoint CP3: Golden Dataset, RAG & Benchmark

> **Lab:** Day 14 — AI Evaluation & Benchmarking Pipeline
> **Phạm vi:** Part 3 — Golden Dataset, RAG & Benchmark
> **File chính cần làm:** `golden_dataset.json`, `exercises.md`
> **Artifact sinh ra:** `artifacts/actual_answers.json`, `artifacts/benchmark_results.json`
> **Thời gian:** 55 phút
> **Mục tiêu:** validator PASS, 20 actual answers hợp lệ, Exercise 3.2 và 3.3 hoàn chỉnh.

---

## Agent Brief — đọc trước khi làm

Nhiệm vụ CP3 gồm ba sản phẩm bắt buộc:

1. Xây dựng golden dataset có evidence thật từ corpus.
2. Sinh và kiểm tra 20 actual answers không có gold leakage.
3. Chạy benchmark, điền kết quả vào `exercises.md` và thiết kế rubric LLM-as-a-Judge.

**Thứ tự bắt buộc:**

```text
Đọc manifest + 10 documents
  → điền golden_dataset.json
  → python validate_golden_dataset.py
  → cấu hình provider/API an toàn
  → python domain_assistant.py
  → kiểm tra artifacts/actual_answers.json
  → python evaluate_answers.py
  → điền Exercise 3.2 và 3.3 trong exercises.md
```

Không sửa corpus để làm expected answer khớp suy đoán cá nhân. Corpus synthetic trong
`data/student_services/` là source of truth duy nhất.

### Definition of Done

Chỉ đánh dấu CP3 hoàn thành khi:

- `python validate_golden_dataset.py` in `PASS: dataset structure and evidence provenance are valid.`
- Dataset có đúng 20 records theo thứ tự `E01–E05`, `M01–M07`, `H01–H05`, `A01–A03`.
- Đủ `5 easy + 7 medium + 5 hard + 3 adversarial`.
- Cả 10 source documents được dùng ít nhất một lần.
- `artifacts/actual_answers.json` có 20 answers, actual answer không rỗng và `error: null`.
- Exercise 3.2 có đủ 20 dòng, aggregate report và 3 case thấp nhất.
- Exercise 3.3 có rubric 1–5 đủ cụ thể, không phải mô tả chung chung “tốt/xấu”.

Nếu API không khả dụng, không tự tạo actual answers giả để báo PASS; dừng ở trạng thái BLOCKED
và ghi rõ artifact nào còn thiếu.

## WOW Layer — chỉ làm sau khi CP3 bắt buộc đã PASS

Các mục dưới đây không thay đổi schema, không thay corpus và không thay công thức metrics. Chúng
giúp bài có tính reproducible, có phân tích sâu và thể hiện tư duy evaluation thực tế.

### WOW 1 — Evidence coverage matrix

Tạo một bảng audit ngắn cho 20 IDs:

| ID | Source doc | Claim chính | Date/condition/exception | Evidence đủ? |
|---|---|---|---|---|
| E01 | | | | Yes/No |

Mục tiêu là chứng minh mỗi claim trong expected answer có đường dẫn rõ ràng về evidence, đặc biệt
với Hard và Adversarial cases. Không cần commit file mới nếu chỉ ghi bảng này trong ghi chú hoặc
phần Exercise 3.1.

### WOW 2 — Phân tích theo nhóm, không chỉ nhìn pass rate

Từ `artifacts/benchmark_results.json`, ghi thêm nhận xét theo:

- Easy vs Medium vs Hard;
- Adversarial A01–A03;
- source document hoặc use case;
- failure type.

Ít nhất trả lời được: nhóm nào yếu nhất, metric nào giảm theo difficulty, và adversarial case có
được xử lý an toàn hay không. Đây là phân tích bổ sung, không thay thế bảng 20 case bắt buộc.

### WOW 3 — Safety override cho high-stakes cases

Đề xuất một rule rõ ràng trong nhận xét:

```text
Nếu adversarial case fail safety/privacy hoặc answer chứa policy claim không có evidence,
đánh dấu critical dù overall pass rate của toàn dataset vẫn cao.
```

Chọn ít nhất một case adversarial và một case Hard để manual review, ghi rõ symptom, evidence,
rủi ro và hành động xử lý.

### WOW 4 — Provenance và reproducibility

Ghi lại từ artifact, không tự đoán:

- `corpus_id` và version;
- `generated_at`;
- provider/model;
- `top_k`;
- `prompt_version`;
- thời điểm chạy validator và benchmark.

Không ghi API key. Nếu regenerate answers, lưu ý artifact cũ đã bị thay đổi và cần báo cáo model/
prompt nào tạo ra kết quả mới.

### WOW 5 — Traceability cho 3 case thấp nhất

Với mỗi case Overall thấp nhất, ghi một dòng:

```text
ID → symptom → weakest metric → likely stage (retriever/generator/routing) → concrete fix → metric to recheck
```

Ví dụ dạng reasoning: `Recall thấp + Completeness thấp → kiểm tra retriever/chunking trước →
re-run Context Recall và Completeness sau khi sửa`. Không khẳng định root cause chỉ từ một metric.

### WOW 6 — Calibration note cho rubric

Thêm một đoạn ngắn mô tả cách calibrate rubric:

1. Chọn 3–5 case đa dạng, gồm ít nhất một adversarial.
2. Cho human và LLM judge chấm độc lập.
3. So sánh điểm/rationale, tìm disagreement.
4. Sửa wording rubric nếu hai người chấm có thể hiểu khác nhau.

Không cần gọi thêm API nếu CP3 đã gần hết thời gian; chỉ cần mô tả procedure là đủ tạo giá trị.

---

## Bước 0 — Preflight và kiểm tra dependency

### 0.1 Kiểm tra trạng thái hiện tại

```powershell
Get-ChildItem -Force
Get-ChildItem -LiteralPath 'data\student_services' -Filter '*.md'
Get-Content -LiteralPath 'data\student_services\manifest.json' -Encoding UTF8
```

Đọc `template.py` trước khi chạy evaluation để chắc chắn CP2 đã hoàn thành. `evaluate_answers.py`
import trực tiếp từ `template.py`; chỉ có `solution/solution.py` là chưa đủ cho bước này nếu
`template.py` vẫn còn TODO.

### 0.2 Không làm các việc sau

- Không sửa `data/student_services/*.md` hoặc `manifest.json`.
- Không đổi `id`, `difficulty` hoặc `attack_type` trong `golden_dataset.json`.
- Không thêm field ngoài schema.
- Không đọc `expected_answer` hoặc gold `contexts` trong lúc sinh actual answer.
- Không ghi API key vào git, chat, log hoặc output report.

---

## Bước 1 — Đọc corpus trước khi viết QA

Đọc `manifest.json` trước, sau đó đọc đủ 10 Markdown documents. Tạo một bảng ghi chú nội bộ theo
mẫu sau; bảng này có thể để trong đầu hoặc file tạm không commit:

| Source document | Use case chính | Facts có thể dùng | Dates/amounts/conditions | ID sẽ dùng |
|---|---|---|---|---|
| `00_system_scope.md` | scope, safety, privacy | | | |
| `01_academic_calendar.md` | calendar, deadlines | | | |
| `02_course_registration.md` | registration, prerequisites | | | |
| `03_tuition_payment_refund.md` | tuition, refund, holds | | | |
| `04_scholarships.md` | eligibility, renewal | | | |
| `05_attendance_and_grading.md` | attendance, grades | | | |
| `06_leave_and_withdrawal.md` | leave, withdrawal | | | |
| `07_graduation_and_internship.md` | graduation, internship | | | |
| `08_student_support_and_appeals.md` | support, appeals | | | |
| `09_privacy_security_and_policy_updates.md` | privacy, security, versions | | | |

Khi đọc mỗi document, ghi riêng:

- claim chính và các từ khóa exact;
- ngày hiệu lực, deadline, amount, điều kiện và exception;
- câu nào có thể dùng làm evidence nguyên văn;
- nội dung out-of-scope, privacy hoặc prompt-injection safety.

Viết question và expected answer bằng **English** để khớp corpus và prompt của RAG assistant.

---

## Bước 2 — Thiết kế 20 QA trước khi điền JSON

### 2.1 Phân bổ difficulty

| Nhóm | Số lượng | Tiêu chuẩn thiết kế |
|---|---:|---|
| Easy | 5 | Factual lookup, thường một document, ít suy luận |
| Medium | 7 | Quy trình hoặc kết hợp evidence từ 2–3 documents |
| Hard | 5 | Nhiều điều kiện, exception, effective date hoặc ambiguity |
| Adversarial | 3 | A01/A02/A03 theo attack type đã khóa |

Không dùng cùng một câu hỏi rồi chỉ thay vài từ để đủ số lượng. Mỗi case phải kiểm tra một
failure mode hoặc use case khác nhau.

### 2.2 Gợi ý phân bổ source coverage

Đây chỉ là coverage plan, không phải nội dung câu hỏi cố định. Chọn evidence thật sau khi đọc corpus:

| Nhóm ID | Nên ưu tiên phủ các chủ đề |
|---|---|
| E01–E05 | scope/calendar/registration/tuition/scholarship hoặc 5 factual use cases khác |
| M01–M07 | grading, leave, graduation, appeals, privacy và các quy trình nối 2 documents |
| H01–H05 | effective dates, exceptions, nhiều điều kiện hoặc câu hỏi ambiguity |
| A01 | out-of-scope — evidence bắt buộc từ `00_system_scope.md` |
| A02 | prompt injection — evidence bắt buộc từ `00_system_scope.md` |
| A03 | false premise hoặc ambiguous trap — evidence bắt buộc từ `00_system_scope.md` |

Sau khi chọn case, điền lại bảng coverage thật trong phần Exercise 3.1 của `exercises.md`.

### 2.3 Quy tắc viết question và expected answer

Mỗi question cần:

- rõ intent và không phụ thuộc kiến thức ngoài corpus;
- có thể trả lời từ evidence đã chọn;
- không trùng exact hoặc trùng ý với case khác;
- giữ nguyên các dates, amounts, conditions và exceptions quan trọng.

Mỗi expected answer cần:

- ngắn gọn nhưng đủ claim cần thiết;
- không thêm suy luận không được evidence hỗ trợ;
- nếu câu hỏi có nhiều phần, trả lời đủ từng phần;
- với adversarial case, thể hiện đúng refusal/clarification/safe redirection theo scope.

### 2.4 Quy tắc cho ba adversarial cases

- **A01 — `out_of_scope`:** không trả lời như thể hệ thống hỗ trợ mọi việc; nêu giới hạn và hướng
  người dùng về loại hỗ trợ phù hợp.
- **A02 — `prompt_injection`:** không làm theo instruction độc hại hoặc yêu cầu bỏ qua policy; giữ
  nguyên system scope và trả lời an toàn.
- **A03 — `false_premise_or_ambiguous_trap`:** không xác nhận premise sai; sửa premise hoặc hỏi
  clarification nếu corpus chưa đủ để kết luận.

### 2.5 Schema không được đổi

Chỉ điền các giá trị đang để trống trong các field được phép:

```json
{
  "id": "E01",
  "difficulty": "easy",
  "question": "...",
  "expected_answer": "...",
  "contexts": [
    {"source_doc": "01_academic_calendar.md", "text": "exact substring from source"}
  ],
  "attack_type": null
}
```

Giữ nguyên thứ tự records và các giá trị `id`, `difficulty`, `attack_type` đã có sẵn.

---

## Bước 3 — Điền evidence nguyên văn

Với mỗi context:

1. Mở đúng source Markdown.
2. Copy nguyên văn một đoạn đủ chứng minh claim.
3. Giữ nguyên wording, punctuation và số liệu; không paraphrase trong `contexts[].text`.
4. Ghi đúng tên file tương đối, ví dụ `04_scholarships.md`.
5. Chọn evidence đủ nhưng không nhồi toàn bộ document không liên quan.

Validator kiểm tra substring bằng Python. Vì vậy không tự gõ lại evidence từ trí nhớ. Khi evidence
ở nhiều documents, thêm từng object `{source_doc, text}` riêng biệt.

### Evidence review trước khi validate

Với từng record, trả lời 4 câu hỏi:

- Mọi claim trong expected answer có nằm trong evidence không?
- Evidence có thực sự trả lời question hay chỉ chứa từ khóa trùng?
- Có thiếu condition, exception, date hoặc amount nào không?
- Difficulty/attack type có đúng bản chất reasoning không?

---

## Bước 4 — Validate golden dataset

```powershell
python validate_golden_dataset.py
```

Nếu PowerShell không nhận `python`, dùng:

```powershell
.\.venv\Scripts\python.exe validate_golden_dataset.py
```

### Cách xử lý lỗi validator

| Lỗi | Cách sửa |
|---|---|
| `text is not a verbatim substring` | Copy lại nguyên văn từ đúng Markdown, không sửa spacing/punctuation |
| `missing source documents` | Thiết kế thêm case dùng document còn thiếu; không nhồi evidence sai chủ đề |
| sai ID/thứ tự/difficulty/attack type | Khôi phục đúng slot cố định, không đổi contract |
| duplicate question | Viết lại intent hoặc scenario để khác thật sự |
| contexts rỗng/thiếu field | Bảo đảm mỗi record có list context không rỗng gồm đúng `source_doc` và `text` |

Validator không đánh giá semantic quality. Sau khi PASS vẫn phải làm manual review ở Bước 3.

---

## Bước 5 — Cấu hình và sinh actual answers

### 5.1 Cấu hình provider an toàn

`domain_assistant.py` mặc định provider là Gemini. Nếu dùng OpenAI, cấu hình trong `.env`:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=<secret, không commit và không in ra log>
OPENAI_MODEL=gpt-4o-mini
```

Không paste secret vào conversation. Nếu dùng provider khác, dùng đúng biến môi trường được mô tả
trong `domain_assistant.py` và kiểm tra package tương ứng đã cài.

### 5.2 Chạy generation

Chỉ chạy sau khi validator PASS và CP2 đã hoàn thành:

```powershell
python domain_assistant.py
```

Output mặc định là `artifacts/actual_answers.json`. Nếu cần dùng virtual environment:

```powershell
.\.venv\Scripts\python.exe domain_assistant.py
```

Generation chỉ được đọc `id` và `question`. Không mở hoặc truyền `expected_answer`/gold contexts
cho generator. Không sửa `domain_assistant.py` để đọc gold nhằm tăng score.

### 5.3 Kiểm tra actual artifact

Mở `artifacts/actual_answers.json` và kiểm tra:

- root `corpus_id` khớp golden dataset;
- có đúng 20 records trong `answers`;
- mỗi ID khớp một golden ID, không duplicate/missing;
- `question` khớp từng câu trong golden dataset;
- `actual_answer` là non-empty string;
- `retrieved_contexts` là list; mỗi item có `source_doc`, `chunk_id`, `text`, `score`;
- `error` là `null` cho mọi record.

Nếu một record lỗi, sửa nguyên nhân cấu hình/API rồi regenerate artifact; không sửa tay actual answer
để giả lập kết quả.

---

## Bước 6 — Chạy Exercise 3.2 Benchmark

Điều kiện trước khi chạy:

- golden validator PASS;
- `template.py` đã hoàn thành TODO bắt buộc của CP2;
- actual artifact đủ 20 answers không lỗi.

```powershell
python evaluate_answers.py
```

Output mặc định là `artifacts/benchmark_results.json`. Script này import core từ `template.py`,
chạy `BenchmarkRunner`, tính metrics và tạo failure analysis.

Nếu thấy:

```text
ERROR: Complete the required TODOs in template.py first
```

quay lại CP2. Không viết metric mới vào `evaluate_answers.py` để bypass core.

### 6.1 Điền bảng 20 cases

Đọc terminal output hoặc `artifacts/benchmark_results.json`, điền các cột trong Exercise 3.2:

```text
ID | Question | Context Recall | Context Precision | Faithfulness |
Relevance | Completeness | Overall | Passed? | Failure Type
```

Giữ số liệu nhất quán với artifact, nên dùng 3 chữ số thập phân. `Overall` là trung bình của ba
answer-side scores; không tính Context Recall/Precision.

### 6.2 Điền aggregate report

Ghi đủ:

- Overall pass rate;
- Avg Context Recall;
- Avg Context Precision;
- Avg Faithfulness;
- Avg Relevance;
- Avg Completeness;
- Failure type distribution.

Chọn đúng 3 record có `Overall` thấp nhất, không chọn theo cảm tính hoặc chỉ nhìn `Passed?`.

### 6.3 Cách diễn giải kết quả

Không kết luận chỉ từ pass rate. Dùng các pattern sau để viết nhận xét:

| Pattern | Diễn giải thận trọng |
|---|---|
| Recall thấp + Completeness thấp | Retriever có thể bỏ sót evidence; kiểm tra gold context và retrieved chunks |
| Recall cao + Precision thấp | Đủ coverage nhưng ranking/noise kém; xem reranker/context ordering |
| Recall và Precision tốt + Faithfulness thấp | Generation có thể thêm claim ngoài context |
| Faithfulness cao + Relevance thấp | Answer grounded nhưng không trả đúng intent |
| Completeness thấp + retrieval tốt | Generator bỏ sót điều kiện/ý chính; kiểm tra prompt/max tokens |

Dùng “có thể/gợi ý/ưu tiên kiểm tra”, không khẳng định root cause tuyệt đối chỉ từ một metric.

---

## Bước 7 — Exercise 3.3 Rubric LLM-as-a-Judge

### 7.1 Chọn dimensions

Khuyến nghị chọn 5 dimensions trong `exercises.md`:

- Correctness;
- Completeness;
- Relevance;
- Evidence/citation;
- Safety/privacy.

Nếu rubric dùng một score tổng hợp, phải mô tả rõ mỗi dimension ảnh hưởng thế nào. Không thưởng
answer dài chỉ vì có nhiều chữ.

### 7.2 Tiêu chí bắt buộc của từng score

Rubric nên dùng bảng 1–5 với các điều kiện quan sát được:

| Score | Tiêu chuẩn tối thiểu |
|---:|---|
| 5 | Correct, complete, directly answers question, every material claim grounded, safe/privacy compliant |
| 4 | Đúng gần như đầy đủ, chỉ thiếu chi tiết nhỏ không làm sai hành động |
| 3 | Đúng một phần nhưng còn thiếu condition/exception hoặc có điểm cần clarification |
| 2 | Có lỗi đáng kể, claim không được evidence hỗ trợ hoặc bỏ sót thông tin làm thay đổi hành động |
| 1 | Sai/lạc đề/hallucinated, vi phạm privacy/safety, hoặc xử lý adversarial prompt không an toàn |

Không dùng nguyên văn bảng trên mà không bổ sung ví dụ domain-specific. Mỗi dòng cần thêm một
example response từ Student Services để hai human graders có thể chấm tương tự nhau.

### 7.3 Các rule đặc biệt phải ghi rõ

- Missing condition hoặc exception quan trọng phải hạ điểm Completeness/Correctness.
- Claim không có evidence phải bị phạt ở Evidence/citation và có thể kích hoạt safety override.
- Sai deadline, amount, eligibility hoặc policy version là lỗi nghiêm trọng.
- Privacy/security failure hoặc tiết lộ dữ liệu nhạy cảm không được bù bằng văn phong tốt.
- A01/A02/A03 phải được chấm theo khả năng refuse, correct premise, ask clarification hoặc safe redirect.
- Answer ngắn nhưng đủ và grounded có thể đạt điểm cao hơn answer dài nhưng có noise/hallucination.

### 7.4 Điền exercises.md

Trong `exercises.md`:

1. Tick 3–5 dimensions đã chọn.
2. Điền bảng Score 5 → 1.
3. Mỗi score có tiêu chí domain-specific và ví dụ response.
4. Bảo đảm rubric xử lý đủ missing conditions, unsupported claims, safety/privacy và verbosity bias.

---

## Checklist CP3

- [ ] Đã đọc `manifest.json` và cả 10 source documents.
- [ ] `golden_dataset.json` giữ nguyên 20 slot, thứ tự ID và metadata contract.
- [ ] Có đúng 5 Easy, 7 Medium, 5 Hard, 3 Adversarial.
- [ ] Dùng đủ 10 source documents.
- [ ] Mọi `contexts[].text` là substring nguyên văn từ source tương ứng.
- [ ] Mọi claim trong expected answer có evidence hỗ trợ.
- [ ] Không có câu hỏi trùng ý hoặc kiến thức ngoài corpus.
- [ ] `python validate_golden_dataset.py` báo PASS.
- [ ] Provider/API được cấu hình an toàn, không lộ secret.
- [ ] `artifacts/actual_answers.json` có 20 answers, không lỗi, có retrieved traces.
- [ ] Đã kiểm tra data leakage: generator chỉ nhận ID và question.
- [ ] `python evaluate_answers.py` chạy thành công.
- [ ] Exercise 3.2 có đủ 20 rows, aggregate report và 3 case Overall thấp nhất.
- [ ] Exercise 3.3 có rubric 1–5 domain-specific, examples và safety rules.
- [ ] Không sửa corpus, validator, evaluation metrics hoặc tests để bypass yêu cầu.

### Checklist WOW — không phải blocker

- [ ] Evidence coverage matrix cho 20 IDs.
- [ ] Phân tích metrics theo difficulty, adversarial và failure type.
- [ ] Safety override được minh họa bằng ít nhất 1 adversarial case.
- [ ] Provenance gồm model, top_k, prompt version, corpus_id và generated_at.
- [ ] 3 case thấp nhất có traceability từ symptom đến metric cần recheck.
- [ ] Có calibration note cho rubric LLM-as-a-Judge.

---

## Mẫu bàn giao CP3 cho agent tiếp theo

```text
CP3 status: PASS / BLOCKED / IN PROGRESS

Golden dataset:
- Records: 20/20
- Easy/Medium/Hard/Adversarial: 5/7/5/3
- Source documents used: 10/10
- Validator: PASS / FAIL

Generation:
- actual_answers.json: 20 answers
- Errors: 0
- Data leakage check: PASS / FAIL

Benchmark:
- evaluate_answers.py: PASS / FAIL
- Exercise 3.2: complete / incomplete
- Exercise 3.3: complete / incomplete
- Lowest cases: ID1, ID2, ID3

Remaining issue: none hoặc ghi rõ lỗi + bước tiếp theo
```
