# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Công Trí             |
| MSSV               | 2A202601715                     |
| Khóa/Lớp         | K3              |
| Tên nhóm         | Cường Độ Đức Trí     |
| Vai trò chính    | Dev — Data Observability                 |
| Repository         | https://github.com/lecuong1502/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Data quality checks | `src/observability/quality.py` — `run_data_quality_checks()` (và 5 hàm check con: `_check_row_count`, `_check_paper_id`, `_check_title`, `_check_summary_length`, `_check_freshness`) | Dataframe đã clean (baseline/corrupted/repaired), `Settings` (đọc `freshness_threshold_days`) | `data/quality/{baseline,corrupted,repaired}_quality_report.json` | Hoàn thành |
| Freshness monitoring | `src/observability/quality.py` — `build_freshness_report()` | Dataframe đã clean, cột `published`/`age_days` | `data/quality/freshness_report.json`, `data/quality/{corrupted,repaired}_freshness_report.json` | Hoàn thành |
| Markdown reporting | `src/observability/reporting.py` — `generate_phase1_report()`, `generate_corruption_report()` (và các hàm render nội bộ `_render_metrics_section`, `_render_quality_section`, `_render_freshness_section`) | `metrics` (từ `evaluate_pipeline`), `quality_report`, `freshness_report` | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Hoàn thành |

Tôi không sở hữu logic chọn "khi nào" gọi các hàm trên (đó là orchestration trong `phase1.py`/`corruption_flow.py` của Lê Kiên Cường) — phần của tôi là định nghĩa **check gì**, **ngưỡng bao nhiêu**, và **hiển thị kết quả thế nào**, để 3 trạng thái baseline/corrupted/repaired đều dùng chung một bộ tiêu chí khách quan, không phải đánh giá cảm tính.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Đối chiếu số liệu | `corruption_flow.py` (Lê Kiên Cường) | Sau lần chạy đầu tiên phát hiện `corrupted_freshness_report.json` báo `stale_rows: 0` dù kịch bản `stale_date` đã cấu hình — đối chiếu ngược từ output của `quality.py` giúp xác nhận đây là bug ở logic chọn `paper_id` trong `corruption.py`, không phải bug ở phần freshness check của tôi (report chỉ trung thực phản ánh input nó nhận được) |
| Kiểm tra artifact cuối cùng | `phase1_report.md`, `corruption_report.md` | Xác nhận cả 2 file markdown hiển thị đúng bảng PASS/FAIL và đúng 4 chỉ số RAG cho cả 3 trạng thái trước khi nhóm nộp bài |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Cài đặt 5 quality check (row count, `paper_id` not-null/unique, `title` not-null, `summary` ≥ 100 ký tự, freshness) | `quality.py` — `run_data_quality_checks()` | `baseline_quality_report.json`: `overall_passed=true`, 5/5 PASS | `cat data/quality/baseline_quality_report.json` |
| Cài đặt freshness report độc lập (latest/oldest published, `stale_rows`, `is_fresh`) | `quality.py` — `build_freshness_report()` | `freshness_report.json`: `is_fresh=true`, `stale_rows=0/24` | `cat data/quality/freshness_report.json` |
| Cài đặt renderer markdown tái sử dụng được cho cả báo cáo baseline và báo cáo so sánh 3 trạng thái | `reporting.py` — `generate_phase1_report()`, `generate_corruption_report()` | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` — hiển thị đúng bảng metric và bảng PASS/FAIL | Mở trực tiếp 2 file `.md`, đối chiếu số liệu với JSON gốc |

Output cụ thể tiêu biểu nhất phần việc của tôi tạo ra: `data/quality/corrupted_quality_report.json` — report này là bằng chứng đầu tiên "bắt được" 3 kịch bản corruption ở tầng dữ liệu (`duplicate_count=2`, `too_short_count=12`, freshness `stale_count=3`), **trước khi** bất kỳ ai cần chạy agent để thấy ảnh hưởng lên câu trả lời — đúng đúng mục đích của observability là phát hiện sớm.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần của tôi trả lời câu hỏi: "làm sao biết dữ liệu đang sạch hay hỏng mà không cần chạy agent, chỉ cần nhìn vào chính dataframe?". Đây là lớp observability nằm giữa cleaning và evaluation — nếu không có lớp này, nhóm sẽ chỉ biết dữ liệu có vấn đề *gián tiếp* qua việc agent trả lời sai, mà không biết chính xác **cái gì** trong dữ liệu bị hỏng, hỏng ở **mức nào** (bao nhiêu dòng), và **khía cạnh chất lượng** nào (completeness/uniqueness/validity/timeliness) đang vi phạm. Yêu cầu thứ hai là trình bày lại các con số đó thành báo cáo con người đọc được, khớp 1-1 với JSON gốc để không có sai lệch giữa "số liệu thật" và "số liệu báo cáo".

### Cách triển khai

`quality.py` tách 5 khía cạnh chất lượng thành 5 hàm check độc lập, mỗi hàm nhận `pd.DataFrame` và trả về một dict thuần (`check`, `passed`, `details`) — không phụ thuộc lẫn nhau, không side-effect, dễ test riêng lẻ và dễ thêm check mới sau này mà không đụng vào các check cũ:

- `_check_row_count`: `row_count > 0`.
- `_check_paper_id`: đếm `null_count` (rỗng hoặc `NaN`, kể cả chuỗi toàn khoảng trắng) và `duplicate_count` (`df["paper_id"].duplicated().sum()`) — cả hai phải bằng 0.
- `_check_title`: tương tự `null_count` cho `title`.
- `_check_summary_length`: đếm số dòng có `len(summary) < min_chars` (mặc định 100).
- `_check_freshness`: parse `age_days` thành số (`pd.to_numeric(..., errors="coerce")`), một dòng bị coi là "stale" nếu `age_days` không parse được (`NaN`) **hoặc** vượt `freshness_threshold_days` — cố ý coi thiếu dữ liệu ngày tháng là rủi ro, không mặc định là "an toàn".

`run_data_quality_checks()` chạy cả 5 check, gộp `overall_passed = all(...)`, rồi ghi ra `data/quality/{report_name}_quality_report.json` — `report_name` là tham số truyền vào (`"baseline"`/`"corrupted"`/`"repaired"`) nên cùng một hàm phục vụ cả 3 trạng thái mà không cần viết lại logic.

`build_freshness_report()` là một report riêng, không lặp lại logic của `_check_freshness` mà bổ sung thêm góc nhìn tổng hợp: `latest_published`/`oldest_published` (dùng `.max()`/`.min()` trên cột `published` dạng chuỗi `YYYY-MM-DD`, đã lọc bỏ chuỗi rỗng trước khi so sánh) và `stale_rows`/`total_rows`/`is_fresh`. Tách riêng khỏi `quality.py`'s check vì freshness là một *chiều thời gian* độc lập, không phải một thuộc tính tĩnh của dữ liệu — dữ liệu có thể pass hết completeness/validity nhưng vẫn stale.

`reporting.py` không tính toán lại bất kỳ số liệu nào — chỉ đọc dict/JSON đã có sẵn (`metrics`, `quality_report`, `freshness_report`) và format thành markdown, đảm bảo báo cáo không bao giờ "diễn giải sai" số liệu gốc. `_render_quality_section()` và `_render_freshness_section()` được viết dùng chung cho cả `generate_phase1_report()` (1 trạng thái) và `generate_corruption_report()` (gọi lại 4 lần cho corrupted quality/repaired quality/corrupted freshness/repaired freshness) — tránh lặp code khi từ 1 trạng thái tăng lên phải hiển thị 3 trạng thái song song.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `pd.DataFrame` đã qua `build_clean_dataframe()` (cột bắt buộc: `paper_id`, `title`, `summary`, `published`, `age_days`), `Settings.freshness_threshold_days` (mặc định 180) |
| Output                         | `data/quality/*_quality_report.json` (schema: `report_name`, `generated_at`, `row_count`, `overall_passed`, `checks[]`), `data/quality/*freshness_report.json` (schema: `latest_published`, `oldest_published`, `stale_rows`, `total_rows`, `is_fresh`), `data/reports/*.md` |
| Module phụ thuộc             | `ingestion/cleaning.py` (`build_clean_dataframe` — nguồn dataframe đầu vào), `core/config.py` (`Settings`), `core/utils.py` (`now_utc`, `write_json`, `write_text`) |
| Module sử dụng output        | `pipelines/phase1.py` và `pipelines/corruption_flow.py` (gọi trực tiếp cả `quality.py` lẫn `reporting.py` để lắp vào flow), giảng viên/rubric (đọc trực tiếp `data/reports/*.md` và `data/quality/*.json`) |
| Điều kiện lỗi cần xử lý | Thiếu cột bắt buộc (`paper_id`/`title`/`summary`/`age_days` không tồn tại trong dataframe) → từng hàm check trả về `passed=False` kèm `details={"error": "missing column"}` thay vì raise exception, để một cột thiếu không làm sập toàn bộ report — các check còn lại vẫn chạy và ghi kết quả bình thường |

### Cách xác minh

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
cat data/quality/baseline_quality_report.json
cat data/quality/corrupted_quality_report.json
cat data/quality/repaired_quality_report.json
```

- **Kết quả mong đợi:** baseline và repaired đều `overall_passed: true` (5/5 check PASS), corrupted phải có ít nhất các check `paper_id_not_null_unique`, `summary_min_length`, `freshness` chuyển `false`, và `data/reports/corruption_report.md` phải hiển thị đúng các bảng PASS/FAIL đó bằng ký hiệu ✅/❌.
- **Kết quả thực tế:** đúng như mong đợi. `baseline_quality_report.json`: `overall_passed=true`, 5/5 PASS, `row_count=24`. `corrupted_quality_report.json`: `overall_passed=false`, `row_count=26`, `paper_id_not_null_unique` FAIL (`duplicate_count=2`), `summary_min_length` FAIL (`too_short_count=12`), `freshness` FAIL (`stale_count=3`); `title_not_null` và `row_count` vẫn PASS đúng như thiết kế (2 kịch bản corruption còn lại không đụng đến title/row-existence). `repaired_quality_report.json`: `overall_passed=true`, `row_count=24`, cả 5/5 PASS trở lại. `freshness_report.json` (baseline) `is_fresh=true`, `corrupted_freshness_report.json` `is_fresh=false, stale_rows=3, oldest_published=2000-01-01`, `repaired_freshness_report.json` `is_fresh=true, stale_rows=0`.
- **Artifact/log:** `data/quality/baseline_quality_report.json`, `data/quality/corrupted_quality_report.json`, `data/quality/repaired_quality_report.json`, `data/quality/freshness_report.json`, `data/quality/corrupted_freshness_report.json`, `data/quality/repaired_freshness_report.json`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần quyết định freshness nên được cài như một **check trong `run_data_quality_checks()`** (trả về pass/fail giống 4 check kia) hay như một **report độc lập** (`build_freshness_report()`, không có khái niệm pass/fail nhị phân mà trả về số liệu mô tả).
- **Các phương án đã cân nhắc:**
  1. Chỉ cần 1 check `freshness` trong `run_data_quality_checks()` là đủ — đơn giản, đồng nhất với 4 check còn lại, không phải viết thêm hàm/file JSON riêng.
  2. Chỉ cần `build_freshness_report()` độc lập, bỏ check freshness khỏi `run_data_quality_checks()` — tránh trùng lặp logic tính "thế nào là stale".
  3. (Đã chọn) Giữ cả hai: `_check_freshness()` là một trong 5 check nhị phân (để `overall_passed` của quality report phản ánh đúng "toàn bộ dữ liệu có đạt chuẩn không, kể cả yếu tố thời gian"), đồng thời có `build_freshness_report()` riêng cho góc nhìn mô tả chi tiết hơn (latest/oldest published, không chỉ đúng/sai).
- **Phương án đã chọn:** Phương án 3.
- **Lý do:** Đề bài yêu cầu rõ "freshness monitoring" là một mục riêng biệt với "quality checks" (Mục 8 báo cáo nhóm liệt kê tách hai dòng: "Quality checks" và "Freshness status"), nghĩa là người đọc báo cáo cần cả câu trả lời nhanh (PASS/FAIL, gộp vào `overall_passed`) lẫn ngữ cảnh chi tiết (bài nào cũ nhất, mới nhất — hữu ích để debug khi freshness FAIL, không chỉ biết "có FAIL" mà biết FAIL ở đâu). Tách hai không tốn nhiều chi phí thêm vì cả hai đều tái dùng chung logic tính `stale_mask` trên `age_days`.
- **Bằng chứng quyết định phù hợp:** Khi debug corruption flow, chính `build_freshness_report()` (không phải `_check_freshness`) là thứ giúp xác nhận nhanh `oldest_published: 2000-01-01` — nếu chỉ có check nhị phân `freshness: FAIL`, cả nhóm sẽ phải tự tra `age_days` thủ công trong CSV mới biết dòng nào bị đẩy về quá khứ.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Ở lần chạy `corruption_flow.py` đầu tiên, `data/quality/corrupted_freshness_report.json` do chính `build_freshness_report()` của tôi ghi ra báo `is_fresh: true`, `stale_rows: 0` — dù kịch bản `stale_date` trong `corruption.py` (Lê Kiên Cường phụ trách) đáng lẽ phải đẩy 3 bản ghi về năm 2000.
- **Lệnh hoặc bước tái hiện:** `uv run python script/run_corruption_flow.py`, sau đó mở `data/quality/corrupted_freshness_report.json` — không thấy `oldest_published` nào là năm 2000.
- **Nguyên nhân gốc:** Ban đầu tôi nghi ngờ chính logic `_check_freshness`/`build_freshness_report` của mình tính sai `age_days`, nên việc đầu tiên tôi làm là kiểm tra trực tiếp cột `age_days`/`published` trong `papers_clean_corrupted.csv` — phát hiện **không có dòng nào** trong CSV có `published = 2000-01-01`, nghĩa là dữ liệu đầu vào cho freshness report vốn đã không hề bị corrupt, lỗi không nằm ở module của tôi mà nằm ở bước tạo `corrupted_clean_csv` (`corrupt_clean_dataframe()` trong `corruption.py`) — cụ thể là logic chọn `paper_id` cho kịch bản `stale_date` bị phụ thuộc vào một quota tỉ lệ (`extra_needed`) mà `target_paper_ids` (10 câu hỏi test set) đã tự vượt ngưỡng đó, nên nhóm `stale_date` luôn rỗng.
- **Cách xử lý:** Đây không phải phần code tôi sở hữu (`corruption.py` do Lê Kiên Cường phụ trách), nên tôi báo lại phát hiện kèm bằng chứng cụ thể (đối chiếu `age_days` trong CSV vs. `stale_rows` trong report của tôi) để Lê Kiên Cường sửa logic chọn `paper_id` cho `stale_date` tách khỏi cơ chế quota chung. Phần việc của tôi là xác nhận lại sau khi sửa: chạy lại toàn bộ freshness/quality report trên dữ liệu đã fix.
- **Cách xác minh sau khi sửa:** Chạy lại `run_corruption_flow.py` — `data/quality/corrupted_freshness_report.json` báo đúng `stale_rows: 3`, `oldest_published: 2000-01-01`, `is_fresh: false`; `corrupted_quality_report.json`'s check `freshness` chuyển `passed: false` (`stale_count: 3`); `data/reports/corruption_report.md` hiển thị đúng `Freshness - Corrupted: ❌ FAIL`.
- **Điều học được:** Một report chỉ trung thực với đúng dữ liệu nó nhận được — khi số liệu ra "sai kỳ vọng", việc đầu tiên cần làm là xác minh input (dữ liệu upstream) trước khi nghi ngờ logic tính toán của chính mình; đồng thời, chính vì `build_freshness_report()` được tách độc lập và ghi log chi tiết (`oldest_published`, không chỉ pass/fail), nó mới đủ khả năng "bắt lỗi ngược" một module khác trong pipeline — minh chứng cho quyết định thiết kế ở Mục 5.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** `crossref.py` gọi Crossref REST API (`/works`) với query và filter cấu hình sẵn, có retry/backoff cho lỗi `429`/`503`, lưu response thô và danh sách record đã parse vào `data/raw/`. `cleaning.py` đọc raw records, loại bỏ record thiếu `title`/`summary` hoặc `summary` quá ngắn, chuẩn hoá các trường (`authors_joined`, `categories_joined`, `age_days`, `text_for_embedding`), xuất `papers_clean.csv/json`. Cuối cùng `retrieval/index.py` embed cột `text_for_embedding` (qua Ollama `bge-m3:567m`) và nạp vào ChromaDB — đây là bước duy nhất trong luồng mà module quality/reporting của tôi **không** đụng vào trực tiếp, tôi chỉ kiểm tra dữ liệu ở bước ngay trước nó (dataframe đã clean).
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?** `testset.py` sinh 10 câu hỏi từ chính dữ liệu đã clean, mỗi câu hỏi gắn với `ground_truth_doc_ids = [paper_id]` của paper được dùng để sinh câu đó. Khi evaluate, `retrieval_hit_rate` đo retriever có trả đúng `paper_id` đó trong top-k không; `mean_token_f1`/`judge_accuracy` đo câu trả lời agent sinh ra có khớp ground truth (lấy trực tiếp từ field dữ liệu) không. Bộ test set này được "đóng băng" — sinh một lần ở phase 1, `corruption_flow.py` chỉ đọc lại chứ không sinh mới.
3. **Quality checks khác freshness monitoring ở điểm nào?** Đây chính là phần tôi trực tiếp thiết kế: 4 trong 5 check của `run_data_quality_checks()` (row count, `paper_id` not-null/unique, `title` not-null, `summary` đủ dài) đo tính toàn vẹn/hợp lệ tại một **thời điểm snapshot** — không quan tâm dữ liệu cũ hay mới, chỉ quan tâm nó có "đúng hình dạng" (schema, completeness, uniqueness) hay không. Freshness (cả check thứ 5 trong `quality.py` lẫn `build_freshness_report()` riêng) đo một chiều hoàn toàn khác: **khoảng cách thời gian** giữa `published` và hiện tại so với ngưỡng 180 ngày. Một dataset có thể PASS tuyệt đối 4 check completeness/validity nhưng vẫn FAIL freshness nếu dữ liệu quá cũ — hai khái niệm độc lập, không thể suy ra cái này từ cái kia, nên cần đo tách biệt.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Vì mục tiêu là cô lập đúng một biến độc lập — trạng thái dữ liệu — khi so sánh 3 lần evaluate. Nếu đổi câu hỏi giữa các lần, chênh lệch `mean_token_f1`/`judge_accuracy` có thể đến từ việc câu hỏi khác độ khó chứ không phải từ dữ liệu bị hỏng, làm bảng so sánh ở Mục 10 báo cáo nhóm mất giá trị khoa học.
5. **Repair được xem là thành công dựa trên artifact và metric nào?** Dựa trên chính artifact do module của tôi sinh ra: `repaired_quality_report.json` phải có `overall_passed=true` (khớp lại baseline: 5/5 PASS thay vì 3/5 FAIL như corrupted) và `repaired_freshness_report.json` phải có `is_fresh=true, stale_rows=0` (khớp lại baseline). Song song đó, `repaired_metrics.json` (không phải module của tôi, nhưng tôi đọc để đối chiếu) phải khớp lại đúng 4 chỉ số RAG của baseline. Chỉ khi cả hai lớp — quality/freshness của tôi VÀ agent metrics — cùng khớp baseline mới coi là repair thành công thật sự, không chỉ "trông có vẻ sạch".

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   1.0000 |    1.0000 |   1.0000 | Không thuộc phạm vi quality/freshness — ghi lại để đối chiếu; không đổi vì corpus nhỏ (24-26 tài liệu), `top_k=4` đủ khoan dung với noise nhẹ ở title |
| `mean_token_f1`      |   1.0000 |    0.5000 |   1.0000 | Giảm đúng bằng tỉ lệ câu hỏi loại `summary` trúng vào 10 tài liệu bị `blank_summary` — khớp với những gì `summary_min_length` báo (12 dòng FAIL) |
| `judge_accuracy`     |   1.0000 |    0.9000 |   1.0000 | 1/10 câu bị chấm sai vì `answer` rỗng, nhất quán với `mean_token_f1` |
| `mean_judge_score`   |   5.0000 |    4.5000 |   5.0000 | Nhất quán với `judge_accuracy` |
| Quality checks         | 5/5 PASS (`baseline_quality_report.json`) | 3/5 FAIL — `paper_id_not_null_unique` (`duplicate_count=2`), `summary_min_length` (`too_short_count=12`), `freshness` (`stale_count=3`) | 5/5 PASS | `row_count` và `title_not_null` **không** FAIL ở corrupted — đúng thiết kế vì `noise_injection` chỉ chèn token vào title (không xoá title), không có kịch bản nào xoá `paper_id`/`title` hoàn toàn |
| Freshness status       | Fresh (`stale_rows=0/24`) | Stale (`stale_rows=3/26`, `oldest_published=2000-01-01`) | Fresh (`stale_rows=0/24`) | Repair khôi phục đúng `oldest_published=2026-02-12` — bằng với baseline, không phải một giá trị "sạch" khác đi |

### Kết luận từ số liệu

1. **`blank_summary` (corruption) → `summary_min_length` FAIL trong `corrupted_quality_report.json` (`too_short_count=12`, quality signal do module tôi tạo ra) → `mean_token_f1` giảm từ 1.0 xuống 0.5 (agent metric)**: 12 = 10 tài liệu gốc bị xoá `summary` + 2 tài liệu bị nhân đôi bởi `duplicate_row` (cũng nằm trong nhóm target nên cũng rỗng summary) — con số này khớp chính xác với cách 2 kịch bản corruption tương tác với nhau, không phải trùng hợp.
2. **Repair (`build_clean_dataframe` chạy lại trên `crossref_records.json` gốc) → cả `repaired_quality_report.json` và `repaired_freshness_report.json` quay lại PASS/`is_fresh=true` hoàn toàn → 4 chỉ số RAG phục hồi đúng 100% giá trị baseline**: vì check của tôi đo trực tiếp trên dataframe, kết quả PASS trở lại là bằng chứng độc lập (không suy ra từ agent metrics) rằng dữ liệu đã thực sự sạch lại, chứ không phải agent "tình cờ" trả lời đúng.

Corruption ảnh hưởng rõ nhất theo góc nhìn quality/freshness của tôi: `blank_summary` — vì đây là kịch bản duy nhất làm FAIL đồng thời một quality check (`summary_min_length`) **và** kéo tụt trực tiếp agent metric (`mean_token_f1`, `judge_accuracy`); `stale_date` và `duplicate_row` cũng làm FAIL check tương ứng (`freshness`, `paper_id_not_null_unique`) nhưng không chạm đến agent metric nào vì retrieval/judge không dùng trực tiếp `published` hay tính duy nhất của `paper_id` để đánh giá đúng/sai câu trả lời.

Kết quả khác kỳ vọng ban đầu: tôi kỳ vọng `duplicate_row` (2 dòng nhân đôi) sẽ kéo `retrieval_hit_rate` xuống vì retriever có thể trả về 2 kết quả trùng `paper_id` trong top-4, làm "lãng phí" một suất top-k đáng lẽ dành cho tài liệu khác. Thực tế `retrieval_hit_rate` vẫn giữ 1.0 — kiểm tra bằng cách xem `retrieved_doc_ids` trong `corrupted_answers.json` thì thấy các câu hỏi không thuộc 2 `paper_id` bị nhân đôi hoàn toàn không bị ảnh hưởng, và với `top_k=4` trên corpus 26 dòng, việc dư 1 slot do trùng `paper_id` không đủ để đẩy tài liệu đúng ra khỏi top-4 cho các câu hỏi khác — xác nhận giả thuyết ban đầu của tôi sai vì đã đánh giá quá cao mức độ "chật chội" của top-k trên một corpus nhỏ.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** Một module observability (quality/freshness) phải được thiết kế để nhận **bất kỳ trạng thái dữ liệu nào** — sạch, hỏng có chủ đích, hay đã sửa — mà không cần biết trước ngữ cảnh; nếu code check chỉ hoạt động đúng trên dữ liệu "đẹp" thì nó vô dụng đúng lúc cần nhất (khi dữ liệu thật sự có vấn đề), như lỗi `NaN` ở Mục 6 đã cho thấy.
2. **Về data quality/observability:** Completeness/uniqueness/validity (tĩnh) và freshness (theo thời gian) là hai trục độc lập, và một `overall_passed` gộp chung dễ che mất chi tiết — cần cả check nhị phân (trả lời nhanh có/không) lẫn report mô tả (trả lời "ở đâu", "bao nhiêu") thì mới đủ để debug thực tế.
3. **Về ảnh hưởng của data đến RAG agent:** Không phải mọi corruption bị quality check bắt được đều ảnh hưởng đến agent metric, và ngược lại — `stale_date`/`duplicate_row` làm FAIL quality check rõ ràng nhưng không đổi agent metric nào, trong khi `blank_summary` ảnh hưởng cả hai. Quality check và agent metric là hai lớp bằng chứng bổ sung cho nhau, không thay thế được nhau.

### Nếu có thêm thời gian

Tôi sẽ thêm một check `text_for_embedding_consistency` — so sánh `text_for_embedding` hiện tại với giá trị được rebuild lại từ chính các field `title`/`authors_joined`/`summary` của cùng dòng đó, để phát hiện trường hợp một corruption sửa field gốc (ví dụ `summary`) nhưng quên rebuild `text_for_embedding` tương ứng (bug tiềm ẩn dạng "field đã sửa nhưng embedding vẫn dùng bản cũ", không xảy ra trong lần chạy này nhưng là rủi ro thực tế nếu thêm corruption mới sau này). Cách đo cải thiện: chạy check này trên baseline (phải PASS 100%) và trên một bản corrupted cố ý inject lỗi "quên rebuild" (chỉnh tay 1 dòng) để xác nhận check bắt được đúng trường hợp đó.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Công Trí
**Ngày xác nhận:** 2026-08-06
