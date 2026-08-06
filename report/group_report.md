# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K3              |
| Tên nhóm         | Cường Độ Đức Trí     |
| Repository         | https://github.com/lecuong1502/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06               |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Xuân Thế Độ | 2A202601847 | Dev | crossref.py |
| 2 | Trần Công Đức | 2A202601423 | Dev | cleaning.py, testset.py |
| 3 | Nguyễn Công Trí | 2A202601715 | Dev | quality.py, reporting.py |
| 4 | Lê Kiên Cường | 2A202601427 | Leader | corruption.py, phase1.py, corruption_flow.py |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành toàn bộ luồng end-to-end: ingestion từ Crossref REST API, cleaning về schema chuẩn, đóng băng bộ test set 10 câu hỏi, index ChromaDB (embedding local qua Ollama `bge-m3:567m`), evaluate baseline, corrupt dữ liệu có kiểm soát, evaluate corrupted, repair từ raw snapshot, evaluate repaired, và xuất báo cáo so sánh 3 trạng thái. Baseline pipeline tạo đầy đủ artifact bắt buộc (`data/raw/`, `data/clean/`, `data/embeddings/`, `data/eval/`, `data/results/baseline_metrics.json`, `data/quality/`, `data/reports/phase1_report.md`) với 24 bản ghi sạch (24 raw → 24 clean, không có bản ghi nào bị loại) và đạt `retrieval_hit_rate = 1.0`, `mean_token_f1 = 1.0`, `judge_accuracy = 1.0` trên 10 câu hỏi frozen.

Kịch bản `blank_summary` (xoá `summary`) là kịch bản ảnh hưởng rõ nhất đến agent: các câu hỏi loại `summary` nhắm vào 10 tài liệu bị corrupt trả lời rỗng, kéo `mean_token_f1` xuống `0.5` và `judge_accuracy` xuống `0.9`. Kịch bản `paper_id` trùng lặp (`duplicate_row`) và `stale_date` (đưa 3 tài liệu về năm 2000) khiến toàn bộ quality/freshness check của trạng thái corrupted chuyển `FAIL`. Repair (dựng lại từ `crossref_records.json` gốc, không gọi lại API) phục hồi **toàn bộ** chỉ số về đúng bằng baseline (`retrieval_hit_rate=1.0`, `mean_token_f1=1.0`, `judge_accuracy=1.0`, quality/freshness `PASS` 100%).

Blocker quan trọng nhất nhóm gặp và đã xử lý: hàm `_extract_answer` trong starter code `retrieval/qa.py` chỉ nhận diện từ khoá tiếng Anh trong khi bộ test set của nhóm là tiếng Việt, khiến agent luôn trả lời sai loại câu hỏi `authors`/`date`/`categories` (chi tiết ở Mục 11). Sau khi vá, toàn bộ số liệu ở trên là số liệu **sau fix**, đã chạy lại đầy đủ cả hai flow để đảm bảo nhất quán.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records          (data/raw/)
    -> cleaning và data modeling          (data/clean/)
    -> embedding (Ollama bge-m3:567m) + ChromaDB index  (data/embeddings/, data/chroma/)
    -> evaluation baseline                (data/eval/, data/results/baseline_*)
    -> quality/freshness reports          (data/quality/)
    -> corruption                         (data/clean/papers_clean_corrupted.csv, data/results/corruption_log.json)
    -> re-index và re-evaluate            (data/results/corrupted_*)
    -> repair từ dữ liệu nguồn (raw snapshot, KHÔNG fetch lại API)  (data/clean/papers_clean_repaired.csv)
    -> re-index và re-evaluate            (data/results/repaired_*)
    -> comparison report                  (data/reports/corruption_report.md)
```

Luồng thực tế khớp hoàn toàn với starter — không có thay đổi kiến trúc so với đề bài.

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref `/works` API, query `"agentic retrieval augmented generation large language model"` | Gọi API với retry/backoff cho 429/503, parse `date-parts`, strip tag JATS/XML, lọc record thiếu title/abstract | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Xuân Thế Độ |
| Cleaning          | `crossref_records.json` | Strip markup, drop record thiếu title hoặc summary < 100 ký tự, ghép `authors_joined`/`categories_joined`, tính `age_days`, dựng `text_for_embedding` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Trần Công Đức |
| Embedding/index   | `papers_clean.csv` | Embed `text_for_embedding` bằng `bge-m3:567m` (Ollama, local), lưu vào ChromaDB collection riêng cho từng trạng thái (baseline/corrupted/repaired) | `data/embeddings/*.json`, `data/chroma/` | (starter code, không phân công riêng) |
| Evaluation        | `papers_clean.json` | Sinh 10 câu hỏi xoay vòng 4 loại (`summary`/`authors`/`date`/`categories`), đóng băng test set; tính `retrieval_hit_rate`, `mean_token_f1`, gọi LLM judge (OpenRouter `openai/gpt-4o-mini`) | `data/eval/test_set.json`, `data/results/*_metrics.json`, `data/results/*_answers.json` | Trần Công Đức |
| Observability     | Cleaned dataframe của từng trạng thái | Check `row_count`, `paper_id` not-null/unique, `title` not-null, `summary` ≥ 100 ký tự, `freshness` (ngưỡng 180 ngày) | `data/quality/*_quality_report.json`, `data/quality/*_freshness_report.json` | Nguyễn Công Trí |
| Corruption/repair | `papers_clean.csv` (corrupt), `crossref_records.json` (repair) | 4 kịch bản: `blank_summary`, `stale_date`, `noise_injection`, `duplicate_row`, ép buộc overlap với `ground_truth_doc_ids` của test set; repair chạy lại đúng `build_clean_dataframe` trên raw snapshot | `data/clean/papers_clean_corrupted.csv`, `data/clean/papers_clean_repaired.csv`, `data/results/corruption_log.json` | Lê Kiên Cường |
| Orchestration     | Toàn bộ module trên | `phase1.py`: fetch → clean → index → eval → quality → report. `corruption_flow.py`: corrupt → eval → repair → eval → compare | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Lê Kiên Cường |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `openrouter`         |
| `LLM_MODEL`                | `openai/gpt-4o-mini` |
| Embedding model              | `bge-m3:567m` (local qua Ollama, `OLLAMA_BASE_URL=http://localhost:11434`) |
| Số lượng Crossref records | `max_results=24` (raw=24, clean=24, không record nào bị loại) |
| Retrieval `top_k`           | `4`                 |
| Freshness threshold          | `180` ngày         |
| Random seed, nếu có        | `seed=42` (mặc định trong `corrupt_clean_dataframe`) |

Không dán nội dung API key hoặc file `.env` vào báo cáo.

### Lệnh cài đặt

```bash
uv sync
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công | 2026-08-06 (giờ chính xác: điền theo log máy chạy) | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow   | Thành công | 2026-08-06 (`corruption_log.json` lúc 03:50:14 UTC → `corruption_report.md` lúc 03:51:01 UTC) | `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md`, `data/results/corruption_log.json` |

> Ghi chú: đây là kết quả **sau khi** vá lỗi `_extract_answer` (Mục 11) — nhóm đã chạy lại cả hai lệnh trên trước khi ghi các số liệu ở Mục 7–10.

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | -------------------------------------- |
| Source                      | Crossref REST API — `https://api.crossref.org/works` |
| Query/filter                | `query="agentic retrieval augmented generation large language model"`, `filter=from-pub-date:<180 ngày trước>,has-abstract:true` |
| Thời điểm lấy dữ liệu | Trong cùng lần chạy `phase1.py` đã sinh `data/quality/freshness_report.json` lúc `2026-08-06T03:49:47.523529+00:00` (fetch Crossref xảy ra ngay trước bước cleaning/freshness trong cùng lần chạy) |
| Số record nhận được    | 24 record thô, cả 24 đều qua được filter title/abstract → 24 record trong `crossref_records.json` |
| Cơ chế retry/backoff      | Retry tối đa 5 lần cho HTTP `429`/`503`, exponential backoff (`1s, 2s, 4s, 8s, 16s`), tôn trọng header `Retry-After` nếu server trả về |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | `str` (DOI, fallback slug từ title) | Có | Khoá chính, dùng làm document ID trong ChromaDB | Nếu thiếu DOI → dùng `safe_slug(title)`; nếu thiếu cả hai → record bị loại khi cleaning |
| `title` | `str` | Có | Tiêu đề bài báo | Record không có title bị loại ở bước parse Crossref |
| `summary` | `str` | Có, tối thiểu 100 ký tự | Abstract đã strip tag XML/JATS | Record thiếu abstract bị loại ở bước parse; abstract < 100 ký tự bị loại ở bước cleaning |
| `authors_joined` | `str` | Không | Danh sách tác giả nối bằng `, ` | Nếu Crossref không trả `author` → chuỗi rỗng |
| `categories_joined` | `str` | Không | Danh sách `subject` nối bằng `, ` | Nếu không có `subject` → chuỗi rỗng |
| `published` | `str (YYYY-MM-DD)` | Không | Ngày xuất bản, ưu tiên `published` > `published-print` > `published-online` > `issued` > `created` | Nếu không parse được `date-parts` → chuỗi rỗng, `age_days = None` |
| `age_days` | `int \| None` | Không | Số ngày kể từ `published` đến thời điểm chạy pipeline | `None` nếu `published` rỗng/không hợp lệ — bị tính là stale trong freshness check |
| `text_for_embedding` | `str` | Có | `Title: ... \| Authors: ... \| Summary: ...`, input cho embedding model | Dựng lại mỗi khi bất kỳ field thành phần nào thay đổi (kể cả sau corruption) |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Loại record không có `title` hoặc `summary` | Completeness | 0/24 (không có record nào bị loại ở lần fetch này) | So sánh `len(crossref_records.json)` với `len(papers_clean.json)` — cả hai đều 24 |
| Loại record có `summary` < 100 ký tự | Validity | 0/24 | `summary_min_length` check trong `baseline_quality_report.json` → PASS |
| Dedupe theo `paper_id` | Uniqueness | 0/24 | `paper_id_not_null_unique` check → `duplicate_count=0` ở baseline |

Cách tạo `text_for_embedding`: ghép `f"Title: {title} | Authors: {authors_joined} | Summary: {summary}"` sau khi các field thành phần đã được chuẩn hoá whitespace và strip tag. `paper_id` lấy trực tiếp DOI trả về từ Crossref (fallback slug hoá title nếu thiếu DOI). `age_days` tính bằng `(ngày_chạy_pipeline − published).days`, dùng để đánh giá freshness với ngưỡng 180 ngày.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 10 |
| Các `question_type`                    | `summary`, `authors`, `date`, `categories` (xoay vòng theo từng paper được chọn) |
| Ground-truth document ID                 | Chính `paper_id` của paper được dùng để sinh câu hỏi (`ground_truth_doc_ids = [paper_id]`) |
| Embedding model                          | `bge-m3:567m` qua Ollama (`http://localhost:11434`) |
| Vector store/collection                  | ChromaDB, 3 collection tách biệt: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k`                       | 4 |
| LLM provider/model                       | OpenRouter — `openai/gpt-4o-mini` |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (được sinh **một lần** ở phase 1, `corruption_flow.py` chỉ đọc lại, không sinh mới) |

**Vì sao test set phải giữ nguyên khi đánh giá baseline, corrupted và repaired:** mục tiêu của thí nghiệm là cô lập **một biến độc lập duy nhất** — trạng thái của dữ liệu (sạch/hỏng/đã sửa) — để đo ảnh hưởng của nó lên chất lượng RAG. Nếu bộ câu hỏi thay đổi giữa các lần đánh giá, sự khác biệt về `retrieval_hit_rate`/`mean_token_f1`/`judge_accuracy` có thể đến từ việc câu hỏi khác nhau (độ khó khác nhau) chứ không phải từ việc dữ liệu bị hỏng. Đóng băng test set đảm bảo phép so sánh 3 cột trong Mục 10 có ý nghĩa khoa học.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Có | 24 record |
| Cleaned dataset          | `data/clean/papers_clean.csv`, `.json` | Có | 24 record, 0 bị loại |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Có | collection `papers-baseline` |
| Evaluation set           | `data/eval/test_set.json` | Có | 10 câu hỏi, 4 loại |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | xem bảng dưới |
| Quality/freshness        | `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json` | Có | tất cả PASS |
| Baseline report          | `data/reports/phase1_report.md` | Có | — |

### Baseline metrics

| Metric                 |  Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` | 1.0000 | Cả 10/10 câu hỏi, retriever (ChromaDB + bge-m3) trả về đúng `paper_id` mục tiêu trong top-4 kết quả |
| `mean_token_f1`      | 1.0000 | Vì ground truth được sinh trực tiếp từ chính field dữ liệu (`authors_joined`/`published`/`categories_joined`/`first_sentence(summary)`) và agent trả lời đúng chính các field đó trên dữ liệu sạch, nên khớp tuyệt đối là kết quả mong đợi, không phải overfit |
| `judge_accuracy`     | 1.0000 | LLM judge (OpenRouter `openai/gpt-4o-mini`) đánh giá toàn bộ 10 câu trả lời là đúng nội dung |
| `mean_judge_score`   | 5.0000 | Điểm tuyệt đối trên thang 1–5 |
| Ragas, nếu có        | N/A (`RUN_RAGAS` không được bật) | Nhóm không bật cờ `RUN_RAGAS=1` vì thời gian chạy lâu hơn đáng kể; có thể bật thêm nếu cần bằng chứng bổ sung |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `row_count` | Completeness | > 0 | PASS — 24 dòng | `baseline_quality_report.json` |
| `paper_id_not_null_unique` | Uniqueness/Completeness | `null_count=0`, `duplicate_count=0` | PASS | `baseline_quality_report.json` |
| `title_not_null` | Completeness | `null_count=0` | PASS | `baseline_quality_report.json` |
| `summary_min_length` | Validity | `min_chars=100`, `too_short_count=0` | PASS | `baseline_quality_report.json` |
| `freshness` | Timeliness | `age_days ≤ 180` cho mọi dòng | PASS — `stale_count=0` | `baseline_quality_report.json`, `freshness_report.json` |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ------------------------------------ |
| Freshness được đo tại | `papers_clean.csv` (baseline, 24 dòng) |
| Timestamp mới nhất       | `latest_published: 2026-08-01` (bài "SafeRAG..." — `10.2118/234689-pa`, `published-print` ngày 2026-08-01, cũng chính là 1 trong 10 target bị corrupt sau này) |
| Ngưỡng freshness         | 180 ngày |
| Trạng thái baseline      | Fresh (`is_fresh: true`) |
| Lý do                     | Query Crossref có filter `from-pub-date:<180 ngày trước>`, nên toàn bộ 24 bài báo baseline nằm trong ngưỡng 180 ngày ngay từ nguồn, `stale_count=0` |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| `blank_summary` | Xoá `summary` = `""`, áp dụng cho toàn bộ 10 `paper_id` nằm trong `target_paper_ids` (= trùng khớp 100% với `ground_truth_doc_ids` của 10 câu hỏi trong frozen test set — `extra_corrupted_paper_ids: []` vì 10 target đã đủ quota 35%, không cần chọn thêm ngoài target) | 10 record gốc, +2 do bị duplicate → 12 dòng có `summary` rỗng | `summary_min_length` FAIL | `too_short_count=12` trong `corrupted_quality_report.json` (khớp chính xác 10+2); `mean_token_f1` giảm 1.0 → 0.5, `judge_accuracy` giảm 1.0 → 0.9 (câu hỏi loại `summary` trả lời rỗng) | `build_clean_dataframe` chạy lại trên `crossref_records.json` → khôi phục nguyên văn `summary` |
| `noise_injection` | Chèn cụm token rác (`asldkj##9182`, `###injected###`, `%%%CORRUPTED%%%`, `zzz-noise-zzz`, `xj3kd_random_token`, `lorem ipsum qwerty`) vào `title`, rebuild `text_for_embedding`, áp dụng đồng thời với `blank_summary` trên cùng 10 `paper_id` target (ví dụ `10.2118/234689-pa`: `"SafeRAG: ..." → "SafeRAG: ... asldkj##9182 ###injected### xj3kd_random_token"`) | 10 dòng (trùng hoàn toàn với nhóm `blank_summary`) | Không có check "noise" trực tiếp trong `quality.py`, ảnh hưởng gián tiếp qua embedding | `retrieval_hit_rate` không đổi (vẫn 1.0000 cả 3 trạng thái) — corpus 24-26 tài liệu, `top_k=4` đủ khoan dung để vài token rác chèn vào title không đẩy tài liệu đúng ra khỏi top-4 | Rebuild `title` từ raw snapshot |
| `stale_date` | Đưa `published` về `2000-01-01`, ép áp dụng cho 3 `paper_id` **ngoài** nhóm target: `10.32473/flairs.39.1.141782` (gốc `2026-05-06`), `10.1093/sleep/zsag091.0346` (gốc `2026-05-01`), `10.35314/3y9hy151` (gốc `2026-02-26`) — đảm bảo scenario này luôn chạy độc lập với kích thước `target_paper_ids` | 3 dòng | `freshness` FAIL | `stale_rows=3`, `oldest_published=2000-01-01` trong `corrupted_freshness_report.json` | Rebuild `published`/`age_days` từ raw snapshot (raw giữ nguyên ngày gốc 2026, không có khái niệm "stale") |
| `duplicate_row` | Nhân đôi 2 dòng thuộc nhóm target với cùng `paper_id`: `10.21203/rs.3.rs-10012178/v1` và `10.20944/preprints202604.0339.v1` | 2 dòng nhân đôi → tổng `24 + 2 = 26` dòng | `paper_id_not_null_unique` FAIL | `duplicate_count=2` trong `corrupted_quality_report.json` (khớp chính xác) | Dedupe tự nhiên xảy ra vì repair dựng lại từ raw records (mỗi DOI xuất hiện đúng 1 lần trong raw) |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có (`generated_at: 2026-08-06T03:50:14.803051+00:00`, `seed=42`)
- Nhận xét: log ghi đủ 4 loại scenario với 25 entry chi tiết (20 entry từ 10 target × 2 field `summary`+`title`, 3 entry `stale_date`, 2 entry `duplicate_row`), kèm giá trị `before`/`after` nguyên văn cho từng field và 3 danh sách truy vết (`target_paper_ids`, `forced_stale_paper_ids`, `duplicated_paper_ids`) — xác nhận corruption **overlap 100%** với `ground_truth_doc_ids` của frozen test set (toàn bộ 10/10 target trùng khớp danh sách paper được hỏi ở Mục 6), đúng yêu cầu bắt buộc của đề bài.

**Vì sao repair phải dựng lại từ raw snapshot thay vì fetch lại API:** Raw response (`crossref_response.json`/`crossref_records.json`) là "nguồn sự thật" đã được lưu và audit từ đầu, hoàn toàn không bị corruption chạm vào (corruption chỉ tác động tầng clean data). Vì vậy repair chỉ cần chạy lại đúng logic cleaning xác định (deterministic) trên raw đã lưu là khôi phục chính xác trạng thái sạch ban đầu — không phụ thuộc việc Crossref API có còn khả dụng, ổn định hay đã trả về tập kết quả khác hay không (mất mạng, rate limit, index Crossref thay đổi... đều không ảnh hưởng). Đây cũng là điều kiện để đảm bảo `repaired` tương đương `baseline` một cách công bằng, phục vụ đúng mục đích so sánh khoa học ở Mục 10.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |   1.0000 |    1.0000 |   1.0000 | 0 (không đổi) | 100% | Corpus nhỏ (24-26 tài liệu) + top-4 đủ khoan dung nên noise nhẹ ở title không đẩy tài liệu đúng ra khỏi kết quả retrieval |
| `mean_token_f1`        |   1.0000 |    0.5000 |   1.0000 | −0.5000 | 100% | Giảm đúng bằng tỉ lệ câu hỏi loại `summary` nhắm vào tài liệu bị blank — các loại câu hỏi khác (authors/date/categories) không bị ảnh hưởng vì metadata tương ứng không bị corrupt |
| `judge_accuracy`       |   1.0000 |    0.9000 |   1.0000 | −0.1000 | 100% | 1/10 câu (loại `summary`) bị judge chấm sai do câu trả lời rỗng |
| `mean_judge_score`     |   5.0000 |    4.5000 |   5.0000 | −0.5000 | 100% | Nhất quán với `judge_accuracy` |
| Quality checks pass/fail | 5/5 PASS | 3/5 FAIL (`paper_id_unique`, `summary_min_length`, `freshness`) | 5/5 PASS | 3 check chuyển FAIL | 100% | Đúng như 4 kịch bản corruption đã thiết kế |
| Freshness status         | Fresh | Stale (`stale_rows=3`) | Fresh | 3 dòng bị đẩy về năm 2000 | 100% | Repair khôi phục đúng ngày gốc từ raw |

Hai kết luận nhân-quả được hỗ trợ bởi artifact thực tế:

1. **`blank_summary` (corruption) → `summary_min_length` FAIL (quality signal, `too_short_count=12`) → `mean_token_f1` giảm từ 1.0 xuống 0.5 (answer metric)**, vì các câu hỏi loại `summary` trong frozen test set trực tiếp trúng vào những tài liệu bị xoá `summary`, khiến agent trả lời rỗng.
2. **Repair từ raw snapshot (`build_clean_dataframe` chạy lại trên `crossref_records.json`) → toàn bộ quality/freshness check quay về PASS → `retrieval_hit_rate`/`mean_token_f1`/`judge_accuracy`/`mean_judge_score` phục hồi về đúng giá trị baseline (100%)**, vì repair không phụ thuộc vào phần dữ liệu đã bị hỏng mà dựng lại độc lập từ nguồn chưa từng bị corrupt.

Không có kết luận nào bị áp đặt khi số liệu không đổi: `retrieval_hit_rate` được ghi nhận trung thực là **không đổi** (0 thay đổi) thay vì suy diễn corruption "có ảnh hưởng" đến retrieval — vì corpus nhỏ khiến top-4 đủ khoan dung với mức nhiễu title hiện tại.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Ở lần chạy `corruption_flow.py` đầu tiên, toàn bộ 10 câu trả lời trong `corrupted_answers.json` có `"answer": ""`, nhưng LLM judge vẫn chấm điểm cao (4-5/5) với `reasoning` mô tả nội dung khớp hoàn hảo — mâu thuẫn logic rõ ràng.
- **Nguyên nhân:** Hàm `_extract_answer()` trong starter code `retrieval/qa.py` chỉ nhận diện các cụm từ khoá **tiếng Anh** (`"who authored"`, `"when was"`, `"what categories"`...) để quyết định trả lời gì, trong khi bộ test set của nhóm (`testset.py`) sinh câu hỏi hoàn toàn bằng **tiếng Việt**. Không câu nào khớp cụm tiếng Anh, nên hàm luôn rơi vào nhánh mặc định `first_sentence(metadata["summary"])` — kể cả với câu hỏi loại `authors`/`date`/`categories`. Khi `summary` bị corruption xoá rỗng (vì mọi paper trong test set đều nằm trong nhóm bị corrupt), `first_sentence("")` trả về chuỗi rỗng cho toàn bộ 10 câu.
- **Cách xử lý:** Bổ sung nhận diện cụm từ khoá tiếng Việt khớp đúng template câu hỏi của `testset.py` (`"tác giả"` → authors, `"ngày nào"` → date, `"lĩnh vực"`/`"category"` → categories) vào `_extract_answer()`, giữ nguyên phần logic tiếng Anh để không phá vỡ khả năng tương thích ngược.
- **Cách xác minh:** Chạy lại `script/run_phase1.py` và `script/run_corruption_flow.py` từ đầu, kiểm tra `data/results/*_answers.json` — trường `answer` của câu hỏi loại `authors` phải là danh sách tên tác giả (không phải câu tóm tắt), câu `date` phải đúng định dạng `YYYY-MM-DD`. Sau khi vá, `mean_token_f1` baseline tăng từ mức trước đó lên đúng `1.0000` (khớp hoàn toàn với ground truth được sinh từ cùng field dữ liệu).

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Corpus chỉ 24 tài liệu, `top_k=4` khá khoan dung | `retrieval_hit_rate` không phản ánh được mức độ nhiễu nhẹ (noise_injection chỉ chèn vài token vào title) | Tăng corpus (tăng `max_results`) hoặc giảm `top_k` xuống 1-2 để retrieval nhạy hơn với corruption; hoặc làm noise mạnh hơn (thay toàn bộ `text_for_embedding` thay vì chỉ append vào title) và so sánh lại `retrieval_hit_rate` |
| LLM judge (`openai/gpt-4o-mini` qua OpenRouter) không có ràng buộc tường minh với câu trả lời rỗng trong prompt | Nếu `answer=""`, judge có thể tự suy diễn dựa trên `ground_truth` thay vì chấm dựa trên `answer` thực tế (đã quan sát ở lần chạy trước khi vá bug Mục 11) | Bổ sung rule cứng vào prompt `_judge_answer()`: "Nếu Model answer rỗng hoặc chỉ chứa khoảng trắng, correct PHẢI là false và score PHẢI là 1", chạy lại và so sánh `judge_accuracy` trước/sau |
| Ragas chưa được bật (`RUN_RAGAS` mặc định tắt) | Thiếu bộ chỉ số `faithfulness`/`context_precision`/`context_recall` độc lập để đối chiếu chéo với LLM judge tự viết | Bật `RUN_RAGAS=1` cho ít nhất 1 lần chạy đầy đủ và ghi vào `data/results/baseline_metrics.json["ragas"]` để tăng độ tin cậy đánh giá |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp (`corruption_log.json` timestamp `2026-08-06T03:50:14.803051+00:00`, `corruption_report.md` timestamp `03:51:01`).
- [x] Baseline, corrupted và repaired dùng cùng evaluation set (`data/eval/test_set.json`, sinh một lần duy nhất ở phase 1).
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng. *(mỗi người tự viết `individual_report.md`)*
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.