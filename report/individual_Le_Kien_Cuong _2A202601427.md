# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Lê Kiên Cường             |
| MSSV               | 2A202601427                     |
| Khóa/Lớp         | K3              |
| Tên nhóm         | Cường Độ Đức Trí     |
| Vai trò chính    | Leader                 |
| Repository         | https://github.com/lecuong1502/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Controlled corruption | `src/ingestion/corruption.py` — `corrupt_clean_dataframe()` | `papers_clean.csv` (baseline, 24 dòng), `target_paper_ids` lấy từ `ground_truth_doc_ids` của frozen test set | `data/clean/papers_clean_corrupted.csv/json`, `data/results/corruption_log.json` | Hoàn thành |
| Baseline orchestration | `src/pipelines/phase1.py` — `main()` | `.env`/`Settings`, Crossref API | `data/raw/*`, `data/clean/papers_clean.*`, `data/embeddings/papers_embeddings.json`, `data/eval/test_set.json`, `data/results/baseline_*.json`, `data/quality/baseline_*`, `data/reports/phase1_report.md` | Hoàn thành |
| Corruption/repair orchestration | `src/pipelines/corruption_flow.py` — `main()` | `papers_clean.csv`, `crossref_records.json`, `test_set.json` (đọc lại, không sinh mới) | `data/results/corrupted_*`, `data/results/repaired_*`, `data/reports/corruption_report.md` | Hoàn thành |

Đây là 3 module tích hợp cuối pipeline — không tạo dữ liệu mới mà ghép output của 3 thành viên còn lại (`crossref.py`, `cleaning.py`/`testset.py`, `quality.py`/`reporting.py`) thành một luồng chạy được end-to-end.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Debug tích hợp | `src/retrieval/qa.py` (starter code, không thuộc ownership của ai trong nhóm) | Phát hiện `_extract_answer()` chỉ nhận diện từ khoá tiếng Anh trong khi `testset.py` sinh câu hỏi tiếng Việt, khiến toàn bộ câu trả lời `authors`/`date`/`categories` sai. Đã vá và xác minh lại bằng cách chạy lại cả `phase1.py` và `corruption_flow.py` — `mean_token_f1` baseline tăng từ mức lỗi lên đúng `1.0000`. |
| Đổi hạ tầng embedding | `src/retrieval/embeddings.py` | Chuyển từ `sentence-transformers` (bị lỗi driver CUDA cũ trên máy chạy) sang embedding local qua Ollama (`bge-m3:567m`), giữ nguyên interface `MiniLMEmbeddings` để không phải sửa `index.py` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Thiết kế 4 kịch bản corruption có kiểm soát, ép overlap 100% với frozen test set | `corrupt_clean_dataframe()` trong `corruption.py` | `data/results/corruption_log.json`: `target_paper_ids` (10 DOI) trùng khớp tuyệt đối với `ground_truth_doc_ids` của `test_set.json` | Đối chiếu thủ công 10 DOI trong `target_paper_ids` với 10 `ground_truth_doc_ids` trong `test_set.json` — khớp 10/10 |
| Ghép baseline pipeline end-to-end | `phase1.py` | `baseline_metrics.json`: `retrieval_hit_rate=1.0`, `mean_token_f1=1.0`, `judge_accuracy=1.0`, `mean_judge_score=5.0` trên 10 câu hỏi | `uv run python script/run_phase1.py`, kiểm tra `data/reports/phase1_report.md` |
| Ghép corruption → evaluate → repair → evaluate → compare flow | `corruption_flow.py` | `corrupted_metrics.json` (`mean_token_f1=0.5`), `repaired_metrics.json` (khớp lại baseline `1.0` tuyệt đối), `data/reports/corruption_report.md` | `uv run python script/run_corruption_flow.py`, đối chiếu bảng so sánh 3 cột trong `corruption_report.md` |

Output cụ thể tiêu biểu nhất phần việc của tôi tạo ra: `data/reports/corruption_report.md` — bảng so sánh baseline/corrupted/repaired chứng minh bằng số liệu rằng dữ liệu hỏng làm giảm chất lượng agent (`mean_token_f1` 1.0 → 0.5) và repair khôi phục về đúng 100% baseline ở mọi chỉ số, dựa trên artifact thật `corruption_log.json`, `corrupted_quality_report.json`, `repaired_quality_report.json`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần của tôi giải quyết bài toán "chứng minh bằng số liệu — không phải bằng lời — rằng chất lượng dữ liệu ảnh hưởng trực tiếp đến chất lượng RAG agent, và pipeline có khả năng phát hiện + phục hồi sau lỗi dữ liệu". Cụ thể: (1) tạo lỗi dữ liệu có chủ đích chứ không phải lỗi ngẫu nhiên vô nghĩa, (2) đảm bảo lỗi đó thực sự "đụng trúng" các câu hỏi trong bộ eval frozen (nếu không, metrics sẽ không đổi và không chứng minh được gì), (3) orchestrate đúng thứ tự baseline → corrupt → evaluate → repair → evaluate → compare mà không làm rò rỉ trạng thái giữa các bước (ví dụ không được vô tình dùng lại Chroma collection cũ).

### Cách triển khai

`corrupt_clean_dataframe()` nhận `target_paper_ids` (chính là union của `ground_truth_doc_ids` trong frozen test set) làm tham số bắt buộc phải overlap. Toàn bộ 10 target luôn nhận đồng thời 2 corruption (`blank_summary` + `noise_injection`) để đảm bảo ảnh hưởng rõ ràng lên cả answer-quality metrics lẫn embedding. Song song đó, 3 `paper_id` **ngoài** nhóm target được ép chọn riêng cho `stale_date` (ban đầu tôi để logic này phụ thuộc vào "quota 35%" chung với nhóm target — đây chính là bug ở Mục 6) và 2 `paper_id` trong nhóm target bị nhân đôi cho `duplicate_row`. Sau khi corrupt, `text_for_embedding` luôn được rebuild lại từ các field đã sửa để đảm bảo embedding thực sự phản ánh dữ liệu hỏng (không phải hỏng field nhưng vẫn embed text cũ).

`phase1.py` và `corruption_flow.py` orchestrate theo đúng thứ tự pseudo-code đề bài, với một quyết định quan trọng: mỗi trạng thái (baseline/corrupted/repaired) dùng `embeddings_output_path` riêng (`papers_embeddings.json` / `..._corrupted.json` / `..._repaired.json`), và `LocalEmbeddingIndex.build()` tự map sang đúng Chroma collection riêng (`papers-baseline`/`papers-corrupted`/`papers-repaired`) — nhờ vậy 3 lần evaluate không bao giờ vô tình đọc nhầm index của trạng thái khác.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `papers_clean.csv` (baseline, từ `cleaning.py`), `test_set.json` (từ `testset.py`), `crossref_records.json` (từ `crossref.py`) |
| Output                         | `papers_clean_corrupted.csv/json`, `papers_clean_repaired.csv/json`, `corruption_log.json`, `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_report.md` |
| Module phụ thuộc             | `ingestion/cleaning.py` (`build_clean_dataframe`, dùng lại y hệt để repair), `ingestion/crossref.py` (`load_raw_records`), `evaluation/metrics.py` (`evaluate_pipeline`), `observability/quality.py`, `observability/reporting.py`, `retrieval/index.py` |
| Module sử dụng output        | `observability/reporting.py` (đọc `*_metrics.json` để dựng bảng so sánh), giảng viên/rubric (đọc trực tiếp `corruption_report.md`) |
| Điều kiện lỗi cần xử lý | Thiếu baseline artifact (`baseline_metrics.json`/`clean_csv`/`eval_testset`/`raw_records_json` không tồn tại) → `corruption_flow.py` raise `RuntimeError` yêu cầu chạy `phase1.py` trước, thay vì chạy tiếp với dữ liệu rỗng/sai |

### Cách xác minh

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** cả hai lệnh chạy hết không lỗi; `corruption_report.md` có đủ bảng so sánh 3 cột cho cả RAG metrics và quality/freshness signal; quality/freshness của trạng thái `corrupted` phải có ít nhất một dòng FAIL.
- **Kết quả thực tế:** đúng như mong đợi — `corrupted_quality_report.json` có 3/5 check FAIL (`paper_id_not_null_unique`, `summary_min_length`, `freshness`), `repaired_quality_report.json` 5/5 PASS, `corruption_report.md` sinh đúng lúc `2026-08-06T03:51:01Z`.
- **Artifact/log:** `data/results/corruption_log.json`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần đảm bảo corruption "đụng trúng" bộ test set frozen (yêu cầu bắt buộc của đề bài), nhưng vẫn phải sinh đủ 4 loại corruption đa dạng để bài toán quality/freshness observability có ý nghĩa, không chỉ tập trung vào 1-2 check.
- **Các phương án đã cân nhắc:**
  1. Corrupt hoàn toàn ngẫu nhiên trên toàn bộ dataset, không quan tâm đến test set — đơn giản nhất nhưng rủi ro cao: nếu ngẫu nhiên không trúng tài liệu nào được hỏi, `retrieval_hit_rate`/`token_f1` sẽ không đổi và không chứng minh được gì (đúng cảnh báo `[!WARNING]` trong đề bài).
  2. Ép corrupt **chỉ** các paper trong `target_paper_ids`, không corrupt thêm gì khác — đảm bảo overlap tuyệt đối nhưng dữ liệu hỏng sẽ chỉ tập trung 1 chỗ, không đa dạng loại lỗi.
  3. (Đã chọn) Ép `target_paper_ids` luôn nhận `blank_summary + noise_injection`, đồng thời tách riêng một pool nhỏ (`forced_stale_paper_ids`, `duplicated_paper_ids`) không phụ thuộc vào kích thước target để đảm bảo `stale_date`/`duplicate_row` luôn xảy ra dù test set có bao nhiêu câu hỏi.
- **Phương án đã chọn:** Phương án 3.
- **Lý do:** Cân bằng giữa 2 yêu cầu đối lập của đề bài — "phải overlap với test set" (ưu tiên retrieval/answer metrics) và "phải có ≥3 kịch bản lỗi đa dạng" (ưu tiên quality/freshness checks) — mà không đánh đổi cái này lấy cái kia.
- **Bằng chứng quyết định phù hợp:** `corruption_log.json` cho thấy cả hai mục tiêu đều đạt: `target_paper_ids` (10) khớp 100% với test set, đồng thời `forced_stale_paper_ids` (3, nằm ngoài target) vẫn đảm bảo `freshness` FAIL độc lập với việc test set lớn hay nhỏ.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Lần chạy `corruption_flow.py` đầu tiên, `corruption_report.md` báo `Freshness - Corrupted` là `✅ PASS` với `stale_rows: 0`, dù `corrupt_clean_dataframe()` có cài đặt kịch bản `stale_date` (đưa ngày về `2000-01-01`).
- **Lệnh hoặc bước tái hiện:** `uv run python script/run_corruption_flow.py`, sau đó mở `data/quality/corrupted_freshness_report.json` — không có `oldest_published: 2000-01-01` nào xuất hiện.
- **Nguyên nhân gốc:** Trong bản đầu, `stale_date` chỉ được gán cho các `paper_id` nằm trong `extra_scenario_map` — tập hợp này được tính bằng `desired_total = max(len(target_ids), ceil(0.35 × tổng dòng)) − len(target_ids)`. Vì `target_ids` (10 câu hỏi test set) đã tự nó vượt ngưỡng 35% của 24 dòng dữ liệu, `extra_needed = 0` → `extra_scenario_map` rỗng → **không dòng nào bao giờ được gán `stale_date`**, bất kể chạy lại bao nhiêu lần với seed nào.
- **Cách xử lý:** Tách `stale_date` ra khỏi cơ chế "quota 35%" — thêm biến `forced_stale_ids` chọn cứng tối thiểu `min(3, tổng dòng)` paper_id (ưu tiên ngoài `target_ids`, fallback vào target nếu dataset quá nhỏ), áp dụng độc lập với kích thước `target_ids`/`extra_ids`.
- **Cách xác minh sau khi sửa:** Chạy lại `corruption_flow.py`; `corrupted_freshness_report.json` báo `stale_rows: 3`, `oldest_published: 2000-01-01`, `is_fresh: false`; `corruption_report.md` hiển thị `Freshness - Corrupted: ❌ FAIL`.
- **Điều học được:** Khi thiết kế logic "chọn N phần tử theo tỉ lệ", phải kiểm tra kỹ trường hợp biên khi một tập con bắt buộc (ở đây là `target_ids`) đã tự nó vượt ngưỡng tỉ lệ — nếu không, các nhánh logic phụ thuộc vào "phần còn dư" sẽ âm thầm không bao giờ chạy mà không hề báo lỗi (silent failure), rất khó phát hiện nếu không kiểm tra artifact thực tế (`freshness_report.json`) thay vì chỉ tin log "Done." không lỗi.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** `crossref.py` gọi `GET https://api.crossref.org/works` với query/filter cấu hình trong `Settings`, có retry/backoff cho `429`/`503`, lưu response thô vào `crossref_response.json` rồi parse thành `PaperRecord` lưu vào `crossref_records.json`. `cleaning.py` đọc `crossref_records.json`, strip tag XML/JATS, lọc record thiếu title/summary hoặc summary < 100 ký tự, ghép `authors_joined`/`categories_joined`, tính `age_days`, dựng `text_for_embedding`, xuất `papers_clean.csv/json`. `retrieval/index.py` (`LocalEmbeddingIndex.build`) đọc `papers_clean.csv`, gọi `MiniLMEmbeddings` (hiện là `bge-m3:567m` qua Ollama) để embed `text_for_embedding`, nạp vào ChromaDB collection tương ứng, đồng thời ghi file manifest `papers_embeddings.json`.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?** `testset.py` chọn ngẫu nhiên (nhưng trải đều) một số paper từ `papers_clean.json`, với mỗi paper sinh 1 câu hỏi thuộc 1 trong 4 loại (`summary`/`authors`/`date`/`categories`), ground truth lấy trực tiếp từ field tương ứng của chính paper đó, và `ground_truth_doc_ids = [paper_id]`. Khi evaluate, `retrieval_hit_rate` kiểm tra `paper_id` retriever trả về có nằm trong `ground_truth_doc_ids` không (đo retriever), còn `mean_token_f1`/`judge_accuracy` so khớp câu trả lời agent sinh ra với `ground_truth` (đo generation).

3. **Quality checks khác freshness monitoring ở điểm nào?** `quality.py`'s `run_data_quality_checks` kiểm tra tính toàn vẹn/hợp lệ tại một thời điểm snapshot (row count, `paper_id` null/duplicate, `title` null, `summary` đủ dài) — đây là các thuộc tính **tĩnh** của dữ liệu. `build_freshness_report` đo một chiều **thời gian** — khoảng cách giữa `published` và ngày hiện tại (`age_days`) so với ngưỡng — dữ liệu có thể hoàn toàn "sạch" theo nghĩa completeness/validity nhưng vẫn "stale" nếu quá cũ, nên đây là 2 khái niệm độc lập, cùng cần thiết để mô tả đầy đủ "chất lượng dữ liệu".

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Để cô lập đúng một biến độc lập (trạng thái dữ liệu) khi so sánh — nếu bộ câu hỏi đổi giữa các lần đánh giá, chênh lệch metrics có thể đến từ độ khó câu hỏi khác nhau chứ không phải từ việc dữ liệu bị hỏng, khiến phép so sánh 3 cột ở Mục 10 (group report) mất ý nghĩa khoa học.

5. **Repair được xem là thành công dựa trên artifact và metric nào?** Dựa trên 2 lớp bằng chứng độc lập: (a) `repaired_quality_report.json` và `repaired_freshness_report.json` đều trở lại `PASS` toàn bộ (giống hệt baseline), và (b) `repaired_metrics.json` khớp lại đúng giá trị `baseline_metrics.json` ở cả 4 chỉ số RAG (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`). Chỉ khi cả hai lớp bằng chứng đều khớp mới coi là repair thành công — nếu chỉ quality PASS nhưng metrics RAG chưa khớp baseline, nghĩa là dữ liệu "sạch" nhưng chưa chắc đã đúng nội dung gốc.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   1.0000 |    1.0000 |   1.0000 | Không đổi — corpus chỉ 24-26 tài liệu và `top_k=4` khá khoan dung, noise nhẹ chèn vào title chưa đủ mạnh để đẩy tài liệu đúng ra khỏi top-4. Đây là giới hạn của quy mô thử nghiệm, không phải corruption "vô hại". |
| `mean_token_f1`      |   1.0000 |    0.5000 |   1.0000 | Giảm đúng bằng đúng tỉ lệ câu hỏi loại `summary` nhắm vào tài liệu bị `blank_summary` — logic corruption hoạt động chính xác như thiết kế. |
| `judge_accuracy`     |   1.0000 |    0.9000 |   1.0000 | Nhất quán với `mean_token_f1` — 1/10 câu bị chấm sai vì trả lời rỗng. |
| `mean_judge_score`   |   5.0000 |    4.5000 |   5.0000 | — |
| Quality checks         | 5/5 PASS | 3/5 FAIL | 5/5 PASS | 3 check FAIL đúng khớp với 3 trong 4 kịch bản corruption (`duplicate_row`→uniqueness, `blank_summary`→validity, `stale_date`→freshness); `noise_injection` không có check riêng vì nó chủ ý nhắm vào embedding chứ không phải schema. |
| Freshness status       | Fresh | Stale (3 dòng) | Fresh | Repair khôi phục đúng 3 ngày gốc từ raw snapshot, không "làm sạch" bằng cách xoá dòng lỗi. |

### Kết luận từ số liệu

1. **`blank_summary` (corruption trên 10 target) → `summary_min_length` FAIL (`too_short_count=12`, quality signal) → `mean_token_f1` giảm 1.0 → 0.5 (agent metric)**, vì các câu hỏi loại `summary` trong frozen test set trúng đúng các tài liệu bị xoá `summary`, agent trả lời rỗng.
2. **Repair (`build_clean_dataframe` chạy lại trên `crossref_records.json` gốc) → toàn bộ quality/freshness check quay lại PASS → 4 chỉ số RAG phục hồi về đúng 100% giá trị baseline**, vì repair không đọc lại phần dữ liệu đã hỏng mà dựng lại độc lập từ raw snapshot chưa từng bị corrupt.

Corruption ảnh hưởng rõ nhất: `blank_summary` — vì nó là kịch bản duy nhất trực tiếp làm mất thông tin agent cần để trả lời (khác với `noise_injection` chỉ làm nhiễu chứ không xoá thông tin, hay `stale_date`/`duplicate_row` chỉ ảnh hưởng observability chứ không chạm vào nội dung câu trả lời).

Kết quả khác kỳ vọng ban đầu: tôi kỳ vọng `noise_injection` sẽ kéo `retrieval_hit_rate` xuống dưới 1.0, nhưng thực tế không đổi. Giả thuyết: corpus quá nhỏ (24-26 tài liệu) và `top_k=4` đủ khoan dung để vài token rác chèn vào title không đủ sức đẩy tài liệu đúng ra khỏi top-4. Đã kiểm tra bằng cách xem trực tiếp `retrieved_doc_ids` trong `corrupted_answers.json` — tài liệu đúng vẫn luôn xuất hiện ở vị trí đầu top-4 dù title đã bị chèn 3 token rác, xác nhận giả thuyết corpus nhỏ/top_k khoan dung là nguyên nhân, không phải lỗi code.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** Contract giữa các bước (ví dụ schema `PaperRecord` → cleaned dataframe → `text_for_embedding`) phải được giữ nhất quán xuyên suốt kể cả khi dữ liệu bị corrupt — mọi corruption phải rebuild lại `text_for_embedding` từ field gốc, nếu không embedding sẽ không phản ánh đúng corruption và toàn bộ thí nghiệm mất giá trị.
2. **Về data quality/observability:** Quality (tĩnh) và freshness (theo thời gian) là hai trục độc lập cần đo riêng — một dataset có thể "sạch" hoàn toàn theo completeness/validity nhưng vẫn stale, hoặc ngược lại.
3. **Về ảnh hưởng của data đến RAG agent:** Retrieval và generation là hai tầng có độ nhạy khác nhau với cùng một loại lỗi dữ liệu — corpus nhỏ khiến retrieval khá "chịu đựng" được nhiễu nhẹ, nhưng generation (trả lời) lại phụ thuộc trực tiếp vào nội dung field cụ thể nên nhạy hơn nhiều với việc field đó bị xoá.

### Nếu có thêm thời gian

Tôi sẽ tăng cường độ của `noise_injection` (thay toàn bộ `text_for_embedding` bằng nội dung không liên quan thay vì chỉ append vài token vào title) và giảm `top_k` xuống 1-2, sau đó đo lại xem `retrieval_hit_rate` có thực sự giảm hay không — nếu có, sẽ xác nhận được rằng hệ thống retrieval có độ nhạy hợp lý với corruption nặng chứ không phải luôn luôn "miễn nhiễm" bất kể mức độ corruption.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lê Kiên Cường
**Ngày xác nhận:** 2026-08-06