# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                                                 |
| --------------- | ------------------------------------------------------------------------ |
| Họ và tên       | Trần Công Đức                                                            |
| MSSV            | 2A202601423                                                              |
| Khóa/Lớp        | K3                                                                       |
| Tên nhóm        | Cường Độ Đức Trí                                                         |
| Vai trò chính   | Dev — Data modeling & Evaluation-set owner                               |
| Repository      | https://github.com/lecuong1502/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06                                                               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable               | File/hàm phụ trách                                      | Input nhận vào                                          | Output bàn giao                                                                                              | Trạng thái |
| -------------------------------- | ------------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ---------- |
| Cleaning & data modeling         | `src/ingestion/cleaning.py` — `build_clean_dataframe()` | `list[PaperRecord]` từ `data/raw/crossref_records.json` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` (24 dòng, schema chuẩn + `text_for_embedding`) | Hoàn thành |
| Evaluation set (frozen test set) | `src/evaluation/testset.py` — `build_test_set()`        | `papers_clean` dataframe (từ cleaning.py)               | `data/eval/test_set.json` (10 câu hỏi, sinh một lần duy nhất, dùng lại cho cả baseline/corrupted/repaired)   | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                                 | Thành viên/module được hỗ trợ                 | Kết quả                                                                                                                                                                                                                    |
| ----------------------------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Đối chiếu overlap test set với corruption | `src/ingestion/corruption.py` (Lê Kiên Cường) | Xác nhận thủ công 10 `ground_truth_doc_ids` trong `test_set.json` do tôi sinh ra trùng khớp 100% với `target_paper_ids` mà Cường dùng để corrupt — điều kiện bắt buộc để corruption thực sự "đụng trúng" bộ câu hỏi frozen |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                                                                                   | File/hàm/artifact liên quan                   | Kết quả bàn giao                                                                                | Cách xác minh                                                                                                                                                             |
| ------------------------------------------------------------------------------------------------------- | --------------------------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cài đặt pipeline cleaning: strip markup, lọc record thiếu/ngắn, dedupe, dựng `text_for_embedding`       | `build_clean_dataframe()` trong `cleaning.py` | `papers_clean.csv/json`: 24/24 record thô qua được filter (0 record bị loại)                    | So sánh `len(data/raw/crossref_records.json)` = `len(data/clean/papers_clean.json)` = 24; `baseline_quality_report.json` → `title_not_null`/`summary_min_length` đều PASS |
| Sinh bộ 10 câu hỏi evaluation tiếng Việt, xoay vòng 4 loại, ground truth lấy trực tiếp từ field dữ liệu | `build_test_set()` trong `testset.py`         | `data/eval/test_set.json`: 10 câu, phân bố thực tế `summary=5, authors=3, date=2, categories=0` | `uv run python script/run_phase1.py`, đọc trực tiếp `data/eval/test_set.json`                                                                                             |

Output cụ thể: `data/eval/test_set.json` là bộ test set frozen — được `phase1.py` sinh **một lần duy nhất** rồi `corruption_flow.py` chỉ đọc lại (không sinh mới), nên toàn bộ bảng so sánh baseline/corrupted/repaired ở Mục 10 báo cáo nhóm đứng vững được là nhờ artifact này giữ nguyên trong suốt cả hai lần chạy pipeline.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần của tôi là điểm nối giữa dữ liệu thô lấy về từ Crossref (`crossref.py`, do Xuân Thế Độ phụ trách) và mọi bước phía sau (embedding, quality checks, corruption, evaluation): phải biến `list[PaperRecord]` — vốn có thể chứa markup XML/JATS, field thiếu, hoặc record trùng — thành một dataframe **đúng schema chuẩn, ổn định**, đồng thời tạo được `text_for_embedding` — chuỗi thực sự được đưa vào embedding model. Nếu cleaning sai (ví dụ không lọc record rác, không dedupe), toàn bộ pipeline phía sau (index, quality, corruption) sẽ kế thừa lỗi mà không tự phát hiện được. Song song đó, `testset.py` phải sinh ra một bộ câu hỏi **đóng băng được** với ground truth tính trực tiếp từ dữ liệu sạch, để dùng làm "thước đo cố định" xuyên suốt 3 trạng thái baseline/corrupted/repaired.

### Cách triển khai

`build_clean_dataframe()`: với mỗi `PaperRecord`, strip tag XML/JATS bằng regex (`_TAG_RE = re.compile(r"<[^>]+>")`) rồi `normalize_whitespace`, áp dụng cho cả `title` và `summary`. Record bị loại nếu thiếu `title`, thiếu `summary`, hoặc `summary` sau khi làm sạch ngắn hơn `MIN_SUMMARY_CHARS = 100` ký tự. `paper_id` rỗng hoặc trùng (`seen_ids`) cũng bị loại — đây là lớp dedupe đầu tiên, độc lập với `df.drop_duplicates(subset=["paper_id"])` chạy lại lần nữa sau khi build xong dataframe (double-check). `authors_joined`/`categories_joined` ghép bằng `compact_join`. `age_days` tính từ `published` (parse theo `%Y-%m-%d`, trả `None` nếu không parse được) so với `run_date` truyền vào từ pipeline. Cuối cùng dựng `text_for_embedding = f"Title: {title} | Authors: {authors_joined} | Summary: {summary}"` — mẫu này được giữ cố định để bất kỳ ai (kể cả corruption/repair) muốn dữ liệu phản ánh đúng vào embedding đều phải rebuild lại đúng field này. Dataframe kết quả được sort theo `published` giảm dần rồi `paper_id` tăng dần, đảm bảo output **deterministic** giữa các lần chạy trên cùng input.

`build_test_set()`: chọn `MAX_QUESTIONS = 10` dòng đại diện bằng cách rải đều theo chỉ số (`step = total // num_candidates`) thay vì random, để bộ câu hỏi phủ nhiều tài liệu khác nhau trong 24 dòng thay vì tập trung vào một cụm. Với mỗi dòng, một trong 4 generator (`summary`/`authors`/`date`/`categories`) được thử theo thứ tự xoay vòng (`offset = row_idx % 4`) — generator nào trả về `None` (field rỗng) thì bỏ qua, thử generator kế tiếp trong vòng xoay, đến khi có 1 câu hỏi hợp lệ cho dòng đó rồi dừng (`break`). Ground truth không do LLM sinh mà lấy **trực tiếp** từ field tương ứng (`first_sentence(summary)`, `authors_joined`, `published`, `categories_joined`) — quyết định này đảm bảo ground truth luôn chính xác tuyệt đối so với dữ liệu, loại bỏ rủi ro ground truth sai do một mô hình khác sinh ra.

### Input, output và contract

| Thành phần              | Mô tả                                                                                                                                                                                                                                                                                                                                                                                                   |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Input                   | `cleaning.py`: `list[PaperRecord]` (`data/raw/crossref_records.json`) + `run_date`. `testset.py`: dataframe trả về từ `build_clean_dataframe()`                                                                                                                                                                                                                                                         |
| Output                  | `cleaning.py`: `pd.DataFrame` 14 cột (`paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `primary_category`, `published`, `updated`, `age_days`, `summary_chars`, `abs_url`, `pdf_url`, `comment`, `text_for_embedding`) → ghi `papers_clean.csv/json`. `testset.py`: `list[dict]` schema `{id, question_type, question, ground_truth, ground_truth_doc_ids}` → ghi `test_set.json` |
| Module phụ thuộc        | `ingestion/crossref.py` (`PaperRecord`), `core/utils.py` (`normalize_whitespace`, `compact_join`, `first_sentence`, `write_json`)                                                                                                                                                                                                                                                                       |
| Module sử dụng output   | `retrieval/index.py` (embed `text_for_embedding`), `observability/quality.py` (check `title_not_null`/`summary_min_length`/`freshness` trên cùng schema), `ingestion/corruption.py` (corrupt trên `papers_clean.csv`, dùng `ground_truth_doc_ids` của `test_set.json` làm `target_paper_ids`), `evaluation/metrics.py` (đọc `test_set.json` để evaluate cả 3 trạng thái)                                |
| Điều kiện lỗi cần xử lý | Dataframe rỗng hoặc `< MIN_CLEAN_DOCS_REQUIRED = 3` dòng → `build_test_set` raise `ValueError`; sinh được `< MIN_QUESTIONS = 5` câu hỏi (do quá nhiều field rỗng ở các dòng đại diện) → raise `ValueError` thay vì âm thầm trả về bộ test set quá nhỏ                                                                                                                                                   |

### Cách xác minh

```bash
uv run python script/run_phase1.py
```

- **Kết quả mong đợi:** `papers_clean.csv/json` có đúng số dòng ≤ số record thô (không tăng thêm), không có `paper_id` trùng, mọi `summary_chars ≥ 100`; `test_set.json` có 5–10 câu hỏi, mỗi câu đủ 5 trường schema.
- **Kết quả thực tế:** 24 record thô → 24 dòng clean (không record nào bị loại ở lần fetch này); `baseline_quality_report.json` xác nhận `paper_id_not_null_unique` và `summary_min_length` đều PASS (`duplicate_count=0`, `too_short_count=0`); `test_set.json` sinh đúng 10 câu, phân bố `summary=5, authors=3, date=2, categories=0` (giải thích ở Mục 6).
- **Artifact/log:** `data/clean/papers_clean.csv`, `data/clean/papers_clean.json`, `data/eval/test_set.json`, `data/quality/baseline_quality_report.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần chọn ngưỡng "summary quá ngắn để loại bỏ" khi cleaning. Ngưỡng này ảnh hưởng trực tiếp đến số record còn lại cho embedding/evaluation, đồng thời phải khớp với ngưỡng mà `observability/quality.py` (Nguyễn Công Trí phụ trách) dùng để check `summary_min_length` — nếu hai ngưỡng lệch nhau, dữ liệu có thể "sạch" theo cleaning nhưng vẫn bị quality report báo FAIL, gây mâu thuẫn giữa hai module.
- **Các phương án đã cân nhắc:**
  1. Không lọc theo độ dài `summary`, chỉ loại record thiếu hẳn `title`/`summary` — giữ được nhiều dữ liệu nhất nhưng để lọt các abstract dạng placeholder cực ngắn (ví dụ chỉ có "Abstract." hoặc vài từ do JATS strip hỏng), làm `text_for_embedding` gần như vô nghĩa.
  2. Đặt ngưỡng cao (ví dụ 300 ký tự) để chỉ giữ abstract "đầy đủ" — an toàn hơn về chất lượng nhưng với corpus nhỏ (24 record thô) có nguy cơ loại quá nhiều, không đủ `MIN_CLEAN_DOCS_REQUIRED` cho `testset.py`.
  3. (Đã chọn) `MIN_SUMMARY_CHARS = 100`, thống nhất với hằng số `min_chars=100` trong `quality.py`.
- **Phương án đã chọn:** Phương án 3.
- **Lý do:** 100 ký tự đủ để loại các abstract dạng placeholder/hỏng nhưng không quá khắt khe để loại oan record hợp lệ trên corpus 24 bài; quan trọng hơn, dùng chung một con số với `quality.py` giữ cho hai module không mâu thuẫn nhau — record "đủ điều kiện" ở bước cleaning cũng chính là record "PASS" ở bước quality check, tránh tình trạng dữ liệu đi qua cleaning nhưng vẫn bị flag lỗi ở quality report.
- **Bằng chứng quyết định phù hợp:** `baseline_quality_report.json` → check `summary_min_length` với `min_chars: 100, too_short_count: 0` — khớp chính xác với `MIN_SUMMARY_CHARS = 100` trong `cleaning.py`, xác nhận hai module đồng bộ ngưỡng. Khi Cường corrupt xóa rỗng `summary` của 10+2 dòng, `corrupted_quality_report.json` báo đúng `too_short_count: 12` — chứng minh ngưỡng 100 hoạt động nhất quán ở cả trạng thái sạch lẫn hỏng.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Khi kiểm tra `data/eval/test_set.json` sau khi chạy `phase1.py`, phân bố `question_type` thực tế là `summary=5, authors=3, date=2, categories=0` — không có bất kỳ câu hỏi loại `categories` nào trong 10 câu, mặc dù `_build_categories_question` và `"categories"` đã có mặt trong `_QUESTION_GENERATORS` và được đưa vào vòng xoay như 3 loại còn lại.
- **Lệnh hoặc bước tái hiện:** `uv run python script/run_phase1.py`, sau đó đếm `question_type` trong `data/eval/test_set.json` (`Counter(q["question_type"] for q in questions)` → `{'summary': 5, 'authors': 3, 'date': 2}`, không có key `'categories'`).
- **Nguyên nhân gốc:** Kiểm tra trực tiếp `data/clean/papers_clean.csv` cho thấy **cả 24/24 dòng** đều có `categories_joined` rỗng. Trong `ingestion/crossref.py`, `categories`/`primary_category` được lấy từ trường `subject` trong response Crossref (`item.get("subject")`), nhưng với query/filter mà nhóm dùng (`"agentic retrieval augmented generation large language model"`, `from-pub-date:...,has-abstract:true`), Crossref không trả `subject` cho bất kỳ record nào trong 24 kết quả — đây là giới hạn của **nguồn dữ liệu** (nhiều publisher không khai báo `subject` với Crossref), không phải lỗi logic trong `cleaning.py` hay `testset.py`. Vì `categories_joined` luôn rỗng ở mọi dòng, `_build_categories_question` luôn trả về `None` bất kể dòng nào được chọn làm candidate hay thứ tự xoay vòng ra sao, nên generator `categories` không bao giờ có cơ hội tạo được câu hỏi.
- **Cách xử lý:** Không sửa `testset.py` vì hành vi hiện tại (generator trả `None` → fallback sang generator kế tiếp trong vòng xoay, không crash) là graceful degradation đúng thiết kế, và kết quả (10 câu, `MIN_QUESTIONS = 5` vẫn được đáp ứng) không chặn pipeline. Tôi xác nhận đây là giới hạn dữ liệu nguồn cần ghi nhận minh bạch trong báo cáo (Mục 9) thay vì cố "sửa" bằng cách chèn giá trị giả cho `categories_joined`, vì điều đó sẽ làm ground truth không còn phản ánh đúng dữ liệu thật.
- **Cách xác minh sau khi sửa:** Đọc `data/clean/papers_clean.csv` xác nhận `categories_joined` rỗng ở toàn bộ 24 dòng; đọc `src/ingestion/crossref.py` dòng 107–112 xác nhận `categories` phụ thuộc hoàn toàn vào `item.get("subject")` từ response Crossref — không có lỗi tính toán ở phía `cleaning.py`/`testset.py`.
- **Điều học được:** Rotation-with-fallback là chiến lược đúng để tránh crash khi field nguồn không đồng đều, nhưng nên cân nhắc log cảnh báo khi một `question_type` hoàn toàn vắng mặt trong bộ test set frozen, để người review biết ngay bộ test không cover đều 4 loại câu hỏi thay vì phải tự đếm lại từ file JSON.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** `crossref.py` gọi `GET https://api.crossref.org/works` với query/filter cấu hình sẵn (`source_query`, `source_filter` trong `Settings`), có retry/backoff cho lỗi `429`/`503`, lưu response thô vào `crossref_response.json` và parse thành `list[PaperRecord]` lưu vào `crossref_records.json`. Đây là đầu vào duy nhất cho phần việc của tôi: `build_clean_dataframe()` (trong `cleaning.py`) strip markup XML/JATS khỏi `title`/`summary`, loại record thiếu field hoặc `summary` < 100 ký tự, dedupe theo `paper_id`, tính `age_days`, và dựng `text_for_embedding` theo mẫu cố định. Kết quả (`papers_clean.csv/json`) được `retrieval/index.py` đọc để embed `text_for_embedding` (qua `bge-m3:567m`/Ollama) và nạp vào ChromaDB.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?** `testset.py` (do tôi cài đặt) chọn 10 dòng rải đều trong `papers_clean`, mỗi dòng sinh 1 câu hỏi (xoay vòng 4 loại `summary`/`authors`/`date`/`categories`) với `ground_truth` lấy trực tiếp từ field tương ứng và `ground_truth_doc_ids = [paper_id]` của chính dòng đó — không có bước "sinh câu hỏi bằng LLM" nên ground truth luôn khớp tuyệt đối với dữ liệu sạch. Khi evaluate, `retrieval_hit_rate` kiểm tra retriever có trả về đúng `paper_id` trong `ground_truth_doc_ids` ở top-k không (đo tầng retrieval), còn `mean_token_f1`/`judge_accuracy` so khớp câu trả lời agent sinh ra với `ground_truth` (đo tầng generation).
3. **Quality checks khác freshness monitoring ở điểm nào?** `quality.py` (Nguyễn Công Trí) kiểm tra các thuộc tính tĩnh của một snapshot dữ liệu — completeness (`row_count`, `paper_id`/`title` không null), uniqueness (`paper_id` không trùng), validity (`summary` đủ dài, dùng đúng ngưỡng `MIN_SUMMARY_CHARS=100` mà tôi đặt ở `cleaning.py`). Freshness đo một chiều khác — khoảng cách thời gian giữa `published` và ngày chạy pipeline (`age_days`) so với ngưỡng 180 ngày — nên một dataset có thể "sạch" hoàn toàn về completeness/validity nhưng vẫn "stale" nếu dữ liệu quá cũ.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Vì mục tiêu là cô lập đúng một biến độc lập — trạng thái dữ liệu — khi đo ảnh hưởng lên chất lượng RAG. Đây cũng chính là lý do tôi thiết kế `test_set.json` được sinh **một lần duy nhất** ở `phase1.py`; `corruption_flow.py` chỉ đọc lại chứ không gọi lại `build_test_set()`. Nếu bộ câu hỏi đổi giữa các lần đánh giá, chênh lệch `mean_token_f1`/`judge_accuracy` có thể đến từ độ khó câu hỏi khác nhau, không phải từ việc dữ liệu bị hỏng — làm mất ý nghĩa khoa học của bảng so sánh 3 cột.
5. **Repair được xem là thành công dựa trên artifact và metric nào?** Dựa trên hai lớp bằng chứng độc lập nhưng phải khớp nhau: (a) `repaired_quality_report.json`/`repaired_freshness_report.json` trở lại PASS toàn bộ giống hệt baseline, và (b) `repaired_metrics.json` khớp lại đúng `baseline_metrics.json` ở cả 4 chỉ số RAG. Vì repair chạy lại chính `build_clean_dataframe()` — hàm tôi viết — trên `crossref_records.json` gốc (chưa từng bị corruption chạm vào), nên nếu logic cleaning là deterministic (không phụ thuộc trạng thái ngoài), repair phải cho ra dataframe giống hệt baseline byte-for-byte về nội dung — đây chính là lý do repair "thành công tuyệt đối" (100%) ở mọi chỉ số trong Mục 10 báo cáo nhóm.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal        | Baseline |                                                       Corrupted | Repaired | Nhận xét của cá nhân                                                                                                                                                                                                                                                                                                                                                                                                       |
| -------------------- | -------: | --------------------------------------------------------------: | -------: | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `retrieval_hit_rate` |   1.0000 |                                                          1.0000 |   1.0000 | Không đổi ở cả 3 trạng thái — corpus nhỏ (24–26 tài liệu) và `top_k=4` đủ khoan dung nên `noise_injection` (chèn vài token rác vào `title`) không đẩy tài liệu đúng ra khỏi top-4. Đây là giới hạn quy mô thử nghiệm, không phải do lỗi ở tầng cleaning/test-set của tôi.                                                                                                                                                  |
| `mean_token_f1`      |   1.0000 |                                                          0.5000 |   1.0000 | Giảm đúng 0.5 ở corrupted vì 5/10 câu hỏi trong `test_set.json` do tôi sinh ra thuộc loại `summary`, và toàn bộ 5 tài liệu đích của các câu đó nằm trong 10 `target_paper_ids` bị `blank_summary`. Vì `ground_truth_doc_ids` chỉ chứa đúng `paper_id` của dòng sinh câu hỏi, corruption "đụng trúng" test set là hệ quả trực tiếp của việc tôi giữ `ground_truth_doc_ids = [paper_id]` chặt chẽ khi thiết kế `testset.py`. |
| `judge_accuracy`     |   1.0000 |                                                          0.9000 |   1.0000 | Nhất quán với `mean_token_f1` — 1/10 câu (loại `summary`) bị judge chấm sai vì câu trả lời rỗng.                                                                                                                                                                                                                                                                                                                           |
| `mean_judge_score`   |   5.0000 |                                                          4.5000 |   5.0000 | Cùng xu hướng với `judge_accuracy`.                                                                                                                                                                                                                                                                                                                                                                                        |
| Quality checks       | 5/5 PASS | 3/5 FAIL (`paper_id_unique`, `summary_min_length`, `freshness`) | 5/5 PASS | `summary_min_length` FAIL đúng bằng ngưỡng `MIN_SUMMARY_CHARS=100` tôi đặt ở `cleaning.py` — khi `blank_summary` xóa rỗng `summary`, check này bắt được ngay (`too_short_count=12`).                                                                                                                                                                                                                                       |
| Freshness status     |    Fresh |                                          Stale (`stale_rows=3`) |    Fresh | Không liên quan trực tiếp đến phần việc của tôi, nhưng repair chạy lại `build_clean_dataframe()` khôi phục đúng `published`/`age_days` gốc, nên freshness cũng tự động PASS trở lại.                                                                                                                                                                                                                                       |

### Kết luận từ số liệu

1. **`blank_summary` (Cường corrupt trên 10 `target_paper_ids` = trùng khớp `ground_truth_doc_ids` của `test_set.json`) → `summary_min_length` FAIL (`too_short_count=12`, quality signal) → `mean_token_f1` giảm từ 1.0 xuống 0.5 (agent metric)**, vì 5/10 câu hỏi loại `summary` trong test set do tôi sinh trúng đúng các tài liệu bị xóa `summary`, agent trả lời rỗng.
2. **Repair (`build_clean_dataframe()` — hàm tôi viết — chạy lại trên `crossref_records.json` gốc) → `summary_min_length`/`paper_id_not_null_unique`/`freshness` quay lại PASS → `mean_token_f1`/`judge_accuracy`/`mean_judge_score` phục hồi về đúng giá trị baseline**, vì cleaning là hàm thuần túy trên input (không giữ state ngoài), nên chạy lại trên cùng raw snapshot luôn cho ra kết quả giống hệt.

Corruption ảnh hưởng rõ nhất: `blank_summary`, vì đây là kịch bản duy nhất xóa trực tiếp nội dung mà agent cần để trả lời câu hỏi loại `summary` — khác với `noise_injection` (chỉ làm nhiễu `title`, không xóa thông tin) hay `stale_date`/`duplicate_row` (chỉ chạm vào quality/freshness, không chạm vào nội dung câu trả lời).

Kết quả khác kỳ vọng ban đầu: tôi kỳ vọng `test_set.json` sẽ có đủ cả 4 loại câu hỏi (`summary`/`authors`/`date`/`categories`) vì cả 4 generator đều nằm trong vòng xoay của `testset.py`. Thực tế 0/10 câu thuộc loại `categories`. Đã kiểm tra bằng cách đọc trực tiếp `papers_clean.csv` và xác nhận `categories_joined` rỗng ở toàn bộ 24/24 dòng do Crossref không trả trường `subject` cho query này (chi tiết ở Mục 6) — không phải lỗi logic trong `testset.py`.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** Một hàm cleaning "sạch" (thuần túy, deterministic, không phụ thuộc state ngoài) là điều kiện tiên quyết để repair-từ-raw-snapshot hoạt động đúng — vì repair trong bài này thực chất chỉ là "gọi lại `build_clean_dataframe()`", nên nếu hàm có side-effect hoặc phụ thuộc thời điểm chạy theo cách không kiểm soát được, repair sẽ không thể phục hồi chính xác 100% như đã thấy ở Mục 8.
2. **Về data quality/observability:** Ngưỡng dùng trong cleaning (`MIN_SUMMARY_CHARS`) và ngưỡng dùng trong quality check phải được đồng bộ tường minh giữa các thành viên — nếu không, "dữ liệu qua được cleaning" và "dữ liệu PASS quality" có thể là hai khái niệm khác nhau, gây hiểu lầm khi đọc report.
3. **Về ảnh hưởng của data đến RAG agent:** Cách thiết kế evaluation set (đặc biệt là `ground_truth_doc_ids`) quyết định corruption có "đo được" hay không — nếu tôi không giữ `ground_truth_doc_ids = [paper_id]` sát với từng tài liệu cụ thể, sẽ khó chứng minh corruption trên 10 target thực sự ảnh hưởng đến đúng 10 câu hỏi tương ứng.

### Nếu có thêm thời gian

Tôi sẽ mở rộng nguồn cho `categories`: hoặc gọi thêm Crossref field khác (ví dụ `container-title`/`type` làm proxy khi `subject` rỗng), hoặc nới `_select_representative_rows` để ưu tiên bù thêm ứng viên khi một loại câu hỏi bị thiếu hoàn toàn sau vòng xoay đầu, thay vì chấp nhận bộ test set thiếu hẳn 1/4 loại câu hỏi như hiện tại — sau đó đo lại xem `test_set.json` có phủ đều cả 4 loại và liệu điều đó có làm lộ thêm ảnh hưởng của corruption mà bộ test hiện tại (0 câu `categories`) chưa bắt được hay không.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Công Đức
**Ngày xác nhận:** 2026-08-06
