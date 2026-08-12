# Plan — Checkpoint CP1: Part 1 Warm-up

> **Lab:** Day 14 — AI Evaluation & Benchmarking Pipeline
> **File cần điền:** `exercises.md` → Part 1 (Exercise 1.1 → 1.3)
> **Thời gian:** 09:30–09:45 (15 phút)
> **Không cần sửa code** — chỉ phân tích lý thuyết

---

## Mục tiêu CP1

| Tiêu chí | Mô tả |
|---|---|
| 1.1 đầy đủ | Bảng 5 metrics x 3 cột: Acceptable Low / Critical Low / Action |
| 1.2 đầy đủ | 3 câu hỏi về bias trong LLM-as-a-Judge |
| 1.3 đầy đủ | Threshold deployment + khi nào dùng loại evaluation nào |
| Key diagnostic | Recall thấp + Completeness thấp → nghi ngờ retriever; Faithfulness thấp khi Context Recall và Context Precision đều cao → nghi ngờ generator |

---

## Nền tảng lý thuyết cần nắm

### RAG Pipeline và metrics flow

```
Question → [Retriever] → Chunks → [Generator] → Answer
               |              |                     |
        Context Recall  Context Precision       Faithfulness
                                               Answer Relevance
                                               Completeness
```

- **Retrieval-side:** Context Recall, Context Precision — chẩn đoán bước GET-CONTEXT
- **Answer-side:** Faithfulness, Relevance, Completeness — chẩn đoán bước GENERATE

### Heuristic word-overlap (dùng trong lab)

| Metric | Công thức |
|---|---|
| Faithfulness | `|answer ∩ context| / |answer|` |
| Relevance | `|answer ∩ question| / |question|` |
| Completeness | `|answer ∩ expected| / |expected|` |
| Context Recall | `|expected ∩ union(chunks)| / |expected|` |
| Context Precision | Average Precision@K (rank-aware) |

> Word-overlap là simplified approximation — paraphrasing hợp lệ có thể bị đánh thấp dù nội dung đúng. Cần hiểu điều này khi giải thích "Acceptable Low".

### Quy tắc diễn giải retrieval metrics

- `Context Recall` và `Context Precision` là **retrieval-side diagnostics**: chúng giúp xác định
  retriever lấy thiếu evidence hay lấy quá nhiều noise.
- Hai metric này được tính trên `QAPair.retrieved_contexts`, nhưng **không đưa vào
  `overall_score()` và không thay đổi pass rule gốc** của core lab.
- Không kết luận lỗi generator chỉ từ `Context Recall` cao. Muốn nói retrieval tốt, cần xem đồng
  thời `Context Recall` và `Context Precision`, đồng thời kiểm tra thủ công một số case high-stakes.

### Score thresholds

| Range | Tình trạng | Hành động |
|---|---|---|
| 0.8–1.0 | Good | Monitor, maintain |
| 0.6–0.8 | Needs work | Analyze failures, iterate |
| < 0.6 | Significant issues | Deep investigation |

---

## Kế hoạch từng Exercise

---

### Exercise 1.1 — RAGAS Metric Thresholds

**Nhiệm vụ:** Điền bảng 5 metrics với 3 cột: Acceptable Low / Critical Low / Action

**Cách tiếp cận:** Với mỗi metric, hỏi 2 câu:
1. Khi nào score thấp là *bình thường* (giới hạn heuristic, không phải lỗi thật)?
2. Khi nào score thấp là *nguy hiểm* (lỗi thật ảnh hưởng sinh viên Northstar)?

#### Faithfulness

**Acceptable Low:**
Answer paraphrase đúng nghĩa nhưng từ ngữ khác context → word-overlap giảm dù không hallucinate.
Ví dụ: context nói "submit within 5 business days", answer nói "nộp trong 1 tuần làm việc" → nghĩa đúng nhưng overlap thấp.

**Critical Low (< 0.3):**
Generator thêm thông tin KHÔNG có trong context = hallucination.
Trong Student Services: bịa deadline học bổng, bịa điều kiện học phí → sinh viên hành động sai.
**Đây là lỗi nguy hiểm nhất trong domain giáo dục.**

**Action:** Kiểm tra grounding guardrail trong system prompt, giảm temperature, thêm post-processing check.

---

#### Answer Relevance

**Acceptable Low:**
Câu hỏi rất ngắn (2–3 từ) nhưng answer dài và đúng → ít token để match.
Ví dụ: Question = "tuition deadline?" → overlap tự nhiên thấp dù answer trả lời đúng.

**Critical Low (< 0.3):**
Answer đi hoàn toàn lạc chủ đề.
Ví dụ: hỏi về đăng ký môn học, trả lời về quy trình khiếu nại → sinh viên bỏ lỡ thông tin.

**Action:** Xem lại intent detection, routing logic; kiểm tra domain scope filter (00_system_scope.md).

---

#### Context Recall

**Acceptable Low:**
Gold expected answer có thêm các chi tiết nền hoặc chi tiết tùy chọn không cần thiết cho task,
trong khi retriever vẫn lấy đủ evidence cốt lõi để trả lời đúng. Khi đó recall có thể thấp theo
heuristic nhưng answer vẫn đạt mục tiêu; cần kiểm tra thủ công trước khi coi là regression.

**Critical Low (< 0.5):**
Retriever bỏ sót evidence quan trọng của câu hỏi cross-document.
Ví dụ: câu hỏi về incomplete grade cần doc 05 (grading) + doc 08 (appeals) nhưng chỉ lấy 1.
**Generator nhận context thiếu → answer incomplete là tất yếu dù generator hoàn hảo.**

**Action:** Tăng top_k, cải thiện chunking strategy, thử query expansion.

---

#### Context Precision

**Acceptable Low:**
Gold context/label chưa bao quát một chunk paraphrase hoặc một nguồn evidence hợp lệ khác. Heuristic
word-overlap có thể đánh chunk đó là không relevant dù answer vẫn grounded; đây là trường hợp cần
human review, không nên tự động pass chỉ dựa trên score.

**Critical Low (< 0.3):**
Noise chunks đứng đầu ranking → context window bị pha loãng.
Generator đọc noise trước relevant → có thể hallucinate hoặc bỏ sót evidence thật.

**Action:** Áp dụng reranking (overlap với query), fine-tune BM25 params, thêm cross-encoder.

---

#### Completeness

**Acceptable Low:**
Expected answer verbose/dài nhưng sinh viên chỉ cần phần core → overlap thấp dù đúng bản chất.
Paraphrasing hợp lệ cũng giảm overlap.

**Critical Low (< 0.4):**
Answer bỏ sót thông tin then chốt.
Ví dụ: trả lời "có thể nộp đơn khiếu nại" nhưng bỏ qua deadline và form cần điền.
Sinh viên nghĩ mình đã đủ thông tin → hành động sai.

**Action:**
- Context Recall cũng thấp → lỗi retriever → fix retriever
- Context Recall cao nhưng Completeness thấp → lỗi generator → fix prompt hoặc tăng max_tokens

---

### Key Diagnostic Framework

```
Recall thấp + Completeness thấp
    → TÍN HIỆU MẠNH CỦA LỖI RETRIEVER (sau khi kiểm tra gold expected)
    → Generator nhận thiếu evidence, không thể complete dù muốn
    → Fix: top_k tăng, chunking cải thiện, query expansion

Recall cao + Precision cao + Faithfulness thấp
    → LỖI GENERATOR (Hallucination)
    → Retriever đủ evidence nhưng generator thêm thông tin ngoài context
    → Fix: grounding instruction mạnh hơn, temperature giảm

Recall cao + Precision cao + Completeness thấp
    → LỖI GENERATOR (Incomplete generation)
    → Evidence có sẵn nhưng generator bỏ sót khi trả lời
    → Fix: prompt rõ hơn "answer every part", max_tokens tăng

Precision thấp + Faithfulness thấp
    → ƯU TIÊN KIỂM TRA RETRIEVER/RERANKER TRƯỚC
    → Noise hoặc chunk sai có thể làm generator bị xao lãng
    → Không quy kết ngay cho generator nếu retrieval chưa được xác nhận tốt
```

---

### Exercise 1.2 — Bias trong LLM-as-a-Judge

#### Câu 1: Position Bias Experiment Design

Mục tiêu: Chứng minh judge ưu tiên answer ở vị trí đầu tiên.

**Thiết kế 2 conditions:**
```
Chuẩn bị: 10+ questions, mỗi câu có Answer-A (tốt hơn) và Answer-B (kém hơn)

Condition 1 (AB order):  Trình bày A trước, B sau → ghi score_A_pos1, score_B_pos2
Condition 2 (BA order):  Trình bày B trước, A sau → ghi score_B_pos1, score_A_pos2
```

**Phát hiện bias nếu:**
- `avg(score_pos1) >> avg(score_pos2)` bất kể answer nào ở vị trí đó
- Paired t-test: p < 0.05 và delta trung bình > 0.1 → bias có ý nghĩa thống kê

Để tránh content bias, cùng một answer phải xuất hiện một lần ở vị trí 1 và một lần ở vị trí 2;
thứ tự AB/BA nên được randomize hoặc counterbalance giữa các câu hỏi. Không kết luận position bias
từ một prompt hoặc một cặp answer duy nhất.

---

#### Câu 2: Giảm Verbosity Bias bằng Rubric Design

Root cause: Rubric mơ hồ → judge dùng heuristic "dài = chi tiết = tốt"

**4 kỹ thuật:**

1. **Tách dimensions:** `Correctness` và `Conciseness` là 2 cột riêng, không gộp
2. **Score theo claim, không theo length:**
   - Score 5 = claim quan trọng đúng hết, không có claim thừa
   - Score 3 = claim đúng nhưng có noise/lặp
   - Score 1 = dài nhưng sai hoặc hallucinate
3. **Explicit judge instruction:** "Do NOT reward longer answers. Score factual accuracy only."
4. **Dimension Precision:** `useful claims / total claims` → penalty cho noise

---

#### Câu 3: Tại sao cần Calibrate với Human Labels

LLM judge nhất quán với chính nó nhưng có thể lệch khỏi ground truth của con người.

| Lý do | Công cụ đo | Ngưỡng hành động |
|---|---|---|
| Đo độ tin cậy thực sự | Cohen's Kappa giữa LLM và human | Kappa < 0.6 → refine rubric |
| Phát hiện blind spot subtler | Human annotation trực tiếp | Lỗi policy date sai 1 ngày |
| Domain high-stakes | Human review bắt buộc | Deadline học bổng, quy trình khiếu nại |

---

### Exercise 1.3 — Evaluation trong CI/CD

#### Câu 1: Threshold Block Deployment

Nguyên tắc: Metric liên quan độ an toàn thông tin → threshold cao; metric có thể do heuristic limitation → threshold thấp hơn.

| Metric | Threshold | Lý do domain-specific |
|---|---|---|
| Faithfulness | 0.70 | Block — hallucination trong Student Services có hệ quả thực tế (sinh viên hành động theo chính sách sai) |
| Answer Relevance | 0.60 | Block — lạc đề nghĩa là sinh viên không nhận được thông tin cần thiết |
| Completeness | 0.55 | Alert trước (không block ngay) vì có thể do heuristic paraphrase; block nếu kết hợp Recall thấp |

Đây là các **starting thresholds** cho lab, không phải ngưỡng phổ quát. Khi đưa vào CI/CD thật,
cần hiệu chỉnh bằng baseline, human labels và confidence interval. Nên dùng hai lớp quality gate:

1. **Dataset-level gate:** điểm trung bình và regression so với baseline không được vượt threshold.
2. **Case-level safety gate:** một case có hallucination nghiêm trọng, policy sai hoặc faithfulness
   cực thấp vẫn phải block và chuyển human review, dù điểm trung bình toàn dataset đạt.

#### Câu 2: Ba loại Evaluation — Khi nào dùng

```
Code / prompt / retrieval thay đổi
        |
        v
[OFFLINE EVAL — RAGAS on golden dataset]
  Khi nào: Tự động mỗi khi có thay đổi, TRƯỚC khi deploy
  Câu hỏi: "Thay đổi này có làm metrics giảm so với baseline?"
  Block deploy nếu Faithfulness < 0.70
        |
        v  (sau deploy)
[ONLINE EVAL — TruLens / Langfuse on real traffic]
  Khi nào: Chạy continuous sau deploy
  Phát hiện: distribution shift (câu hỏi mới, học kỳ mới, chính sách mới)
  Alert khi metric drift > 0.05 so với offline baseline
        |
        v  (khi cần)
[HUMAN REVIEW — sampling + annotation]
  Khi nào:
    (1) Failure cluster mới chưa có trong golden dataset
    (2) Online/offline metrics không nhất quán
    (3) Trước major release hoặc policy domain thay đổi lớn
    (4) Định kỳ calibrate LLM judge
  Lưu ý: không thể chạy mọi request — chỉ dùng cho high-stakes cases và sampling
```

---

## Checklist CP1

- [x] Exercise 1.1: Bảng 5 metrics x 3 cột đã điền với ví dụ domain-specific (Northstar)
- [x] Exercise 1.2: 3 câu đã trả lời (experiment design, rubric fix, calibration reason)
- [x] Exercise 1.3: Threshold table + giải thích offline / online / human review
- [x] Có thể giải thích bằng miệng:
  - Recall thấp + Completeness thấp → retriever lỗi (tại sao?)
  - Faithfulness thấp khi Recall và Precision đều cao → generator hallucinate (tại sao?)
