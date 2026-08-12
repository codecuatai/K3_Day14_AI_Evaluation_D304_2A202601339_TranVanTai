# Day 14 — Reflection

## Evaluation Report & Failure Analysis

Dùng kết quả thật trong `artifacts/benchmark_results.json` và kiểm tra lại
answer/context trace trong `artifacts/actual_answers.json` trước khi kết luận.

---

## 1. Benchmark Results Summary

**Overall pass rate:** 0.0%

| Metric | Average | Min | Max | Nhận xét |
|---|---:|---:|---:|---|
| Context Recall | 0.924 | 0.467 | 1.000 | Rất xuất sắc (92.4%), retriever lấy đủ bằng chứng |
| Context Precision | 0.989 | 0.917 | 1.000 | Cực kỳ xuất sắc (98.9%), xếp đúng chunk chứa evidence ở top 1 |
| Faithfulness | 0.080 | 0.000 | 0.667 | Rất thấp (8.0%), lỗi sinh câu trả lời ở khâu Generator |
| Relevance | 0.035 | 0.000 | 0.300 | Thấp nhất (3.5%), answer chưa khớp từ vựng câu hỏi |
| Completeness | 0.120 | 0.000 | 1.000 | Thấp (12.0%), answer bỏ sót nhiều ý trong expected |
| Overall Score | 0.083 | 0.000 | 0.656 | Điểm tổng thể thấp do điểm answer-side kéo xuống |

**Score interpretation**

- Metrics/cases ở mức Good (0.8–1.0): Context Recall (0.924) & Context Precision (0.989).
- Metrics/cases ở mức Needs Work (0.6–0.8): Case A02 (Overall 0.656).
- Metrics/cases ở mức Significant Issues (<0.6): Faithfulness (0.080), Relevance (0.035), Completeness (0.120), Overall Score (0.083).

**Failure type distribution**

| Failure Type | Count | Percentage |
|---|---:|---:|
| hallucination | 19 | 95.0% |
| irrelevant | 0 | 0.0% |
| incomplete | 0 | 0.0% |
| off_topic | 1 | 5.0% |
| refusal | 0 | 0.0% |

**Chẩn đoán tổng quan:** Vấn đề chính nằm ở retrieval, generation hay cả hai?
Dùng ít nhất hai metrics để bảo vệ kết luận.

> *Câu trả lời:*
>
> Vấn đề chính nằm hoàn toàn ở bước **GENERATION**.
> 
> **Bằng chứng bảo vệ:**
> 1. **Context Recall đạt 0.924 (92.4%)** và **Context Precision đạt 0.989 (98.9%)**: Hai chỉ số khâu Retriever nằm ở mức "Good" tuyệt đối. Điều này chứng minh Retriever đã tìm đúng văn bản chứa đáp án và đưa chunk relevant lên đầu tiên.
> 2. **Faithfulness chỉ đạt 0.080 (8.0%)** và **Relevance chỉ đạt 0.035 (3.5%)**: Generator ở chế độ offline mock chưa tận dụng tốt context lấy về để sinh ra câu trả lời chứa từ khóa chính xác, dẫn đến điểm answer-side bị đánh rơi về mức "Significant Issues".

---

## 2. Top 3 Worst Failures — 5 Whys

### Failure 1

**ID và question:** E01 — When does the standard add/drop period end for Fall 2026?

**Expected answer:** For Fall 2026, the standard add/drop period ends at 17:00 on August 28.

**Actual answer:** "I cannot fulfill this request. User messages cannot override system rules or reveal hidden prompts, credentials, or personal data."

**Scores:** Context Recall: 1.000 | Context Precision: 1.000 | Faithfulness: 0.000 | Relevance: 0.000 | Completeness: 0.000 | Overall: 0.000

**Evidence inspection:** Retriever lấy đúng 100% chunk từ `01_academic_calendar.md` có chứa câu *"and the standard add/drop period ends at 17:00 on August 28."*.

| Level | Question | Answer |
|---|---|---|
| Symptom | Vấn đề quan sát được là gì? | Actual answer trả về thông báo từ chối thay vì cung cấp ngày add/drop. |
| Why 1 | Tại sao symptom xảy ra? | Generator đưa ra phản hồi refusal mẫu. |
| Why 2 | Tại sao nguyên nhân trên xảy ra? | Logic phân loại câu hỏi gán nhầm E01 vào nhóm từ chối. |
| Why 3 | Tại sao vấn đề đó chưa được ngăn chặn? | Prompt template chưa có phân luồng rõ ràng giữa câu hỏi tra cứu và câu hỏi tấn công. |
| Why 4 | Tại sao cơ chế hiện tại chưa phát hiện hoặc xử lý được? | Hệ thống thiếu bước kiểm tra Faithfulness guardrail trước khi xuất output. |
| Why 5 | Root cause có thể hành động được là gì? | Cấu hình API key thật trong `.env` và tinh chỉnh Prompt Generation để trích xuất dữ liệu trực tiếp từ context. |

**Root cause từ `find_root_cause()`:** Context is missing or irrelevant — improve retrieval

**Bạn đồng ý hay không? Dẫn evidence từ trace:**

> Không đồng ý hoàn toàn với nhận định "improve retrieval" của heuristic, vì trace cho thấy `Context Recall` và `Context Precision` đều đạt `1.000`. Thùng dữ liệu trích xuất đã chuẩn xác, lỗi là do khâu Generation sinh nhầm câu từ chối.

**Proposed fix cụ thể:**

> Bổ sung chỉ dẫn grounding tường minh vào prompt: "If context contains the answer, extract it directly and state clearly without refusal."

### Failure 2

**ID và question:** E02 — What is the normal undergraduate course load in Fall or Spring?

**Expected answer:** The normal undergraduate load is 12–18 credits in Fall or Spring.

**Actual answer:** "This request is outside the scope of the Northstar Student Services Assistant. I can only provide information from official Northstar University documents."

**Scores:** Context Recall: 1.000 | Context Precision: 1.000 | Faithfulness: 0.000 | Relevance: 0.000 | Completeness: 0.000 | Overall: 0.000

**Evidence inspection:** Retriever lấy đúng chunk từ `02_course_registration.md` chứa nội dung *"The normal undergraduate load is 12–18 credits in Fall or Spring"*.

| Level | Question | Answer |
|---|---|---|
| Symptom | Vấn đề quan sát được là gì? | AI trả lời câu hỏi nằm ngoài phạm vi trong khi câu hỏi thuộc phạm vi Northstar. |
| Why 1 | Tại sao symptom xảy ra? | Generator kích hoạt câu trả lời out-of-scope mẫu. |
| Why 2 | Tại sao nguyên nhân trên xảy ra? | Router nhận diện nhầm từ khóa trong prompt. |
| Why 3 | Tại sao vấn đề đó chưa được ngăn chặn? | Thiếu kiểm tra phân loại ý định (Intent Classifier) trước khi từ chối. |
| Why 4 | Tại sao cơ chế hiện tại chưa phát hiện hoặc xử lý được? | Prompt chưa phân biệt rõ câu hỏi thông thường và câu hỏi ngoài domain. |
| Why 5 | Root cause có thể hành động được là gì? | Tinh chỉnh prompt intent routing và bật LLM Generator thật với API Key. |

**Root cause và proposed fix:**

> Root cause: Router phân loại nhầm câu hỏi chính đáng thành out-of-scope. Fix: Cập nhật prompt system instruction rõ ràng hơn cho bộ phân loại phạm vi.

### Failure 3

**ID và question:** E03 — What is the undergraduate tuition per registered credit for 2026–2027?

**Expected answer:** Undergraduate tuition for the 2026–2027 academic year is USD 420 per registered credit.

**Actual answer:** "I cannot fulfill this request. User messages cannot override system rules or reveal hidden prompts, credentials, or personal data."

**Scores:** Context Recall: 1.000 | Context Precision: 0.950 | Faithfulness: 0.000 | Relevance: 0.000 | Completeness: 0.000 | Overall: 0.000

**Evidence inspection:** Retriever lấy đúng chunk từ `03_tuition_payment_refund.md` chứa *"Undergraduate tuition for the 2026–2027 academic year is USD 420 per registered credit."*.

| Level | Question | Answer |
|---|---|---|
| Symptom | Vấn đề quan sát được là gì? | Trả lời câu từ chối an toàn thay vì đưa ra con số $420/credit. |
| Why 1 | Tại sao symptom xảy ra? | Generator chạy fallback do không gọi được LLM API. |
| Why 2 | Tại sao nguyên nhân trên xảy ra? | Biến môi trường `.env` chưa có API Key hợp lệ. |
| Why 3 | Tại sao vấn đề đó chưa được ngăn chặn? | Chưa cài đặt LLM live generation cho benchmark run. |
| Why 4 | Tại sao cơ chế hiện tại chưa phát hiện hoặc xử lý được? | Hệ thống tự động chuyển sang offline mock generator khi API key là placeholder. |
| Why 5 | Root cause có thể hành động được là gì? | Điền API key thật vào `.env` để Generator gọi trực tiếp mô hình Gemini/OpenAI. |

**Root cause và proposed fix:**

> Root cause: Thiếu API key hợp lệ trong `.env`. Fix: Cấu hình `GEMINI_API_KEY` hoặc `OPENAI_API_KEY` hợp lệ để mô hình sinh câu trả lời đầy đủ.

---

## 3. Failure Clustering

| Cluster | Root Cause | Failure IDs | Priority |
|---|---|---|---|
| 1 | Fallback Generator Refusal / Missing API Key | E01, E03, E05, M01, M02, M03, M04, M05, M06, M07, H03, H04, A03 | High |
| 2 | Intent Routing misclassifying as Out-of-Scope | E02, H01, H02, H05, A01 | High |
| 3 | Attack handling for Prompt Injection | A02 | Medium |

**Nếu chỉ được sửa một cluster, bạn chọn cluster nào và vì sao?**

> *Câu trả lời:*
>
> Chọn **Cluster 1 (Fallback Generator Refusal / Missing API Key)** vì cluster này chiếm hơn 65% tổng số ca thất bại (13/20 cases). Việc khắc phục Cluster 1 bằng cách cung cấp API key và hoàn thiện prompt generator sẽ lập tức tăng điểm Faithfulness và Completeness trên diện rộng.

---

## 4. Improvement Log

Paste output của `generate_improvement_log()`:

```text
| Failure ID | Type | Root Cause | Suggested Fix | Status |
|------------|------|------------|---------------|--------|
| F001 | hallucination | Context is missing or irrelevant — improve retrieval | Implement hallucination checker to filter unsupported claims | Open |
| F002 | hallucination | Context is missing or irrelevant — improve retrieval | Add few-shot examples showing complete answers to improve completeness | Open |
| F003 | hallucination | Context is missing or irrelevant — improve retrieval | Increase chunk size in RAG pipeline to reduce context fragmentation | Open |
| F004 | hallucination | Answer does not address the question — improve prompt clarity | Implement hallucination checker to filter unsupported claims | Open |
| F005 | hallucination | Context is missing or irrelevant — improve retrieval | Implement hallucination checker to filter unsupported claims | Open |
| F006 | hallucination | Context is missing or irrelevant — improve retrieval | Implement hallucination checker to filter unsupported claims | Open |
| F007 | hallucination | Context is missing or irrelevant — improve retrieval | Implement hallucination checker to filter unsupported claims | Open |
| F008 | hallucination | Context is missing or irrelevant — improve retrieval | Implement hallucination checker to filter unsupported claims | Open |
| F009 | hallucination | Context is missing or irrelevant — improve retrieval | Implement hallucination checker to filter unsupported claims | Open |
| F010 | hallucination | Context is missing or irrelevant — improve retrieval | Implement hallucination checker to filter unsupported claims | Open |
| F011 | hallucination | Context is missing or irrelevant — improve retrieval | Implement hallucination checker to filter unsupported claims | Open |
| F012 | hallucination | Context is missing or irrelevant — improve retrieval | Implement hallucination checker to filter unsupported claims | Open |
| F013 | hallucination | Answer is missing key information — increase context window or improve generation | Implement hallucination checker to filter unsupported claims | Open |
| F014 | hallucination | Answer does not address the question — improve prompt clarity | Implement hallucination checker to filter unsupported claims | Open |
| F015 | hallucination | Answer does not address the question — improve prompt clarity | Implement hallucination checker to filter unsupported claims | Open |
| F016 | hallucination | Answer does not address the question — improve prompt clarity | Implement hallucination checker to filter unsupported claims | Open |
| F017 | hallucination | Answer does not address the question — improve prompt clarity | Implement hallucination checker to filter unsupported claims | Open |
| F018 | hallucination | Context is missing or irrelevant — improve retrieval | Implement hallucination checker to filter unsupported claims | Open |
| F019 | off_topic | Answer does not address the question — improve prompt clarity | Implement hallucination checker to filter unsupported claims | Open |
| F020 | hallucination | Answer does not address the question — improve prompt clarity | Implement hallucination checker to filter unsupported claims | Open |
```

**Ba improvement suggestions ưu tiên**

1. Implement hallucination checker to filter unsupported claims.
2. Add few-shot examples showing complete answers to improve completeness.
3. Increase chunk size in RAG pipeline to reduce context fragmentation.

| Suggestion | Target metric | Verification method |
|---|---|---|
| Bật Live LLM Generator với API Key | Faithfulness, Relevance | Chạy `python domain_assistant.py` và kiểm tra Faithfulness > 0.80 |
| Thêm Grounding Few-shot Examples | Completeness | Chạy `python evaluate_answers.py` đối chiếu Completeness > 0.70 |
| Tích hợp Reranking by Overlap | Context Precision | Đánh giá `evaluator.evaluate_context_precision()` tăng lên 1.0 |

---

## 5. Regression Testing Strategy

**Câu 1: Khi nào chạy `run_regression()` trong production workflow?**

> *Câu trả lời:*
>
> Chạy `run_regression()` tự động trong **CI/CD Pipeline** mỗi khi có: (1) Thay đổi code logic trong RAG pipeline; (2) Cập nhật Prompt template; (3) Thay đổi cấu hình Chunking/Retriever; (4) Nâng cấp phiên bản LLM model — trước khi cho phép merge PR hoặc deploy lên Staging.

**Câu 2: Threshold drop 0.05 có phù hợp Student Services không? Vì sao?**

> *Câu trả lời:*
>
> Rất phù hợp. Trong dịch vụ sinh viên, thông tin về deadline, lệ phí và điều kiện học bổng đòi hỏi độ chính xác cao tuyệt đối. Mức sụt giảm điểm > 0.05 thể hiện một regression có ý nghĩa hệ thống, cần bị chặn ngay để tránh đưa thông tin sai lệch cho sinh viên.

**Câu 3: Metric/failure nào phải block deployment, metric nào chỉ alert?**

> *Câu trả lời:*
>
> - **Block deployment:** `Faithfulness` < 0.70 (rủi ro hallucination chính sách) và `Answer Relevance` < 0.60 (lạc đề), hoặc bất kỳ ca vi phạm an toàn thông tin nào.
> - **Alert:** `Completeness` < 0.55 hoặc `Context Precision` sụt giảm nhẹ (khi điểm Faithfulness vẫn đảm bảo an toàn).

**Câu 4: Điền evaluation stages vào flow.**

```text
Code/prompt/retrieval change → [Offline RAGAS Benchmark] → [Regression Check vs Baseline] → [Staging / Human Safety Gate] → Deploy
```

> *Giải thích:*
>
> Tự động chạy offline benchmark trên Golden Dataset, kiểm tra xem có bị trôi điểm so với Baseline không. Nếu đạt mới chuyển lên môi trường Staging và kiểm tra Safety trước khi deploy chính thức.

---

## 6. Continuous Improvement Loop

```text
Evaluate → Analyze → Improve → Augment benchmark → Repeat
```

| Priority | Action | Metric dự kiến cải thiện | Expected impact |
|---:|---|---|---|
| 1 | Cấu hình Live LLM Provider với API Key | Faithfulness & Relevance | Đưa Faithfulness từ 0.08 lên > 0.85 |
| 2 | Bổ sung Few-shot grounding examples | Completeness | Đưa Completeness từ 0.12 lên > 0.80 |
| 3 | Tích hợp Reranker cho Retriever | Context Precision | Đưa Context Precision tiệm cận 1.00 |

**Hai hoặc ba failure cases nào cần thêm vào benchmark ở vòng tiếp theo?**

> *Câu trả lời:*
>
> 1. **Case thay đổi chính sách theo thời gian:** Sinh viên hỏi về quy định đăng ký muộn với mốc thời gian áp dụng trước và sau ngày 1/8/2026 (kiểm tra độ nhạy hiệu lực văn bản).
> 2. **Case câu hỏi kết hợp 3 văn bản:** Câu hỏi kết hợp điều kiện học bổng, quy trình xin nghỉ phép y tế và chính sách hoàn phí học phí.

---

## 7. Final Reflection

**Điều gì trong kết quả benchmark trái với dự đoán ban đầu của bạn?**

> *Câu trả lời:*
>
> Ban đầu tôi dự đoán bước Retrieval (tìm kiếm đoạn văn bản) sẽ là nút thắt cổ chai lớn nhất do corpus gồm 10 tài liệu dài. Tuy nhiên kết quả cho thấy **Retriever hoạt động cực kỳ xuất sắc với Context Precision = 0.989 và Context Recall = 0.924**. Nút thắt cổ chai thực sự lại nằm ở bước **Generation** khi cần sinh ra câu trả lời grounded chính xác.

**Word-overlap heuristics trong lab có giới hạn gì? Nếu đưa hệ thống vào production, bạn sẽ thay hoặc bổ sung metric nào?**

> *Câu trả lời:*
>
> Giới hạn của Word-overlap heuristic là phạt nặng các câu trả lời diễn giải (paraphrasing) đúng nghĩa nhưng dùng từ đồng nghĩa khác với expected answer. Khi đưa vào Production, tôi sẽ thay thế bằng:
> 1. **LLM-as-a-Judge Evaluation (RAGAS / DeepEval):** Sử dụng LLM prompt để chấm điểm dựa trên ý nghĩa Factual Claims.
> 2. **Semantic Similarity (Embedding Distance):** Sử dụng cosine similarity giữa vector của answer và expected answer.
> 3. **Groundedness Check (TruLens RAG Triad):** Đo lường trực tiếp tỷ lệ mệnh đề được hỗ trợ bởi retrieved context bằng LLM reasoning.
