# Member Role Report — Day 10: Data Pipeline & Data Observability

> Báo cáo này phản ánh phần việc trực tiếp của mình trong nhóm: thiết kế và triển khai ingestion từ Crossref, lưu raw snapshot, và đảm bảo pipeline có thể chạy lại deterministically cho baseline, corrupted và repaired. Nội dung đã được đối chiếu với nhóm report và README để giữ thống nhất về vai trò, luồng pipeline và artifact bắt buộc.

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Xuân Thế Độ |
| MSSV | 2A202601847 |
| Khóa/Lớp | K3 |
| Tên nhóm | Cường Độ Đức Trí |
| Vai trò chính | Dev / implementer cho ingestion và raw data contract |
| Repository | https://github.com/lecuong1502/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Crossref ingestion | src/ingestion/crossref.py | Crossref API response và settings từ core config | Raw response JSON, parsed paper records, retry-aware fetch logic | Hoàn thành |
| Raw snapshot persistence | src/ingestion/crossref.py | Payload từ API | data/raw/crossref_response.json và data/raw/crossref_records.json | Hoàn thành |
| Data contract chuẩn hóa | src/ingestion/crossref.py | Raw item từ Crossref | PaperRecord với paper_id, title, summary, authors, categories, published, updated | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Hỗ trợ tích hợp pipeline | src/pipelines/phase1.py và src/pipelines/corruption_flow.py | Đảm bảo fetch raw → parse → save snapshot → clean → evaluate hoạt động liên tục và có thể repair từ raw snapshot |
| Kiểm tra artifact | data/results/* và data/quality/* | Xác nhận baseline, corrupted và repaired đều có artifact đầy đủ và số liệu nhất quán |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Implement fetch API có retry/backoff | src/ingestion/crossref.py | Raw data được tải ổn định hơn và không bị lỗi 429/503 làm pipeline dừng | Chạy baseline và kiểm tra data/raw/crossref_response.json, data/raw/crossref_records.json |
| Parse payload Crossref thành schema thống nhất | src/ingestion/crossref.py | 24 record được lưu đúng format với paper_id/title/summary/authors/categories/published | So sánh file JSON raw với dữ liệu clean và metrics |
| Tạo raw snapshot phục vụ repair | data/raw/crossref_response.json, data/raw/crossref_records.json | Repair có thể rebuild lại dữ liệu sạch từ nguồn gốc, không phụ thuộc vào API live | Chạy corruption flow và kiểm tra repaired metrics |

Output cụ thể mà phần việc tạo ra là bộ raw snapshot và schema chuẩn hóa, làm nền tảng cho baseline, corruption và repair chạy đúng như mục tiêu lab.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Cần đảm bảo pipeline có thể lấy dữ liệu từ Crossref một cách ổn định, lưu lại bản raw để sau này có thể repair dữ liệu mà không phụ thuộc vào trạng thái API live, đồng thời chuyển payload thô thành schema rõ ràng cho các bước cleaning và evaluation tiếp theo.

### Cách triển khai

Quy trình được triển khai theo hướng deterministic và dễ audit, đúng với luồng nêu trong README và group report:

1. Gọi API Crossref với tham số query và filter đã cấu hình để tạo baseline raw data.
2. Dùng retry/backoff cho các lỗi HTTP 429/503 để tránh pipeline phá vỡ do rate limit.
3. Lưu toàn bộ payload thô vào các file raw response/raw records trước khi bất kỳ bước cleaning nào diễn ra, tạo artifact bắt buộc cho cả pha baseline và pha corruption/repair.
4. Parse từng item thành cấu trúc PaperRecord, bao gồm paper_id, title, summary, authors, categories, published, updated, URL và comment.
5. Loại bỏ các record thiếu title hoặc summary ngay ở tầng parse để tránh đưa dữ liệu không hợp lệ vào bước cleaning và các bước later evaluation/quality.
6. Dùng paper_id từ DOI khi có, nếu không thì fallback bằng safe_slug(title) để giữ tên khóa ổn định và có thể dùng lại cho repair từ raw snapshot.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Payload JSON từ Crossref API, settings query/filter/max_results từ core config |
| Output | List PaperRecord và các file JSON raw snapshot |
| Module phụ thuộc | src/core/config.py, src/core/utils.py |
| Module sử dụng output | src/ingestion/cleaning.py, src/pipelines/phase1.py, src/pipelines/corruption_flow.py |
| Điều kiện lỗi cần xử lý | 429/503 từ Crossref, payload thiếu title/abstract, date-part thiếu hoặc không parse được |

### Cách xác minh

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

- Kết quả mong đợi: baseline và corruption flow tạo được raw artifacts và metrics đầy đủ.
- Kết quả thực tế: cả hai flow chạy thành công, tạo ra data/raw/*, data/clean/*, data/results/* và data/quality/*.
- Artifact/log: data/raw/crossref_response.json, data/raw/crossref_records.json, data/results/baseline_metrics.json, data/results/corrupted_metrics.json, data/results/repaired_metrics.json.

## 5. Một quyết định kỹ thuật quan trọng

- Bối cảnh: cần có một nguồn dữ liệu gốc đáng tin cậy để repair dữ liệu hỏng mà không phụ thuộc vào việc Crossref API còn hoạt động hay có thay đổi kết quả.
- Các phương án đã cân nhắc:
  - Chỉ lưu dữ liệu clean và repair bằng cách fetch lại API mỗi lần.
  - Lưu raw snapshot từ lần fetch đầu tiên và dùng lại cho repair.
- Phương án đã chọn: lưu raw snapshot và repair lại từ raw snapshot bằng logic cleaning xác định.
- Lý do: cách này tăng reproducibility, giảm dependency vào môi trường mạng và làm so sánh baseline/corrupted/repaired công bằng hơn.
- Bằng chứng quyết định phù hợp: repaired metrics khôi phục về đúng baseline (retrieval_hit_rate 1.0, mean_token_f1 1.0, judge_accuracy 1.0) sau khi rebuild từ raw snapshot.

## 6. Một lỗi hoặc blocker đã xử lý

- Triệu chứng/lỗi nguyên văn: trong quá trình chạy pipeline, việc fetch dữ liệu có thể bị chặn bởi 429/503 hoặc mất kết nối tạm thời, làm flow dừng giữa chừng.
- Lệnh hoặc bước tái hiện: chạy baseline nhiều lần liên tiếp hoặc trong môi trường rate-limited.
- Nguyên nhân gốc: Crossref API không đảm bảo availability tuyệt đối và không có cơ chế retry trong code ban đầu.
- Cách xử lý: thêm logic retry/backoff với exponential delay và ưu tiên header Retry-After khi có.
- Cách xác minh sau khi sửa: chạy lại phase1 và corruption flow; raw artifacts được tạo đầy đủ và không có lỗi fetch làm pipeline dừng.
- Điều học được: ingestion layer cần có resilience built-in, và raw snapshot là một phần của audit trail bắt buộc cho data pipeline.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của mình:

1. Dữ liệu đi từ Crossref đến vector index như thế nào? Crossref trả về payload metadata bài báo, module ingestion parse thành record chuẩn, bước cleaning chuẩn hóa nội dung, sau đó dữ liệu được dùng để build embedding và index vào ChromaDB cho retrieval.
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao? Test set gồm 10 câu hỏi, mỗi câu gắn với một paper_id mục tiêu; retrieval được chấm bằng việc kiểm tra paper_id đúng có xuất hiện trong top-k kết quả, còn answer quality được chấm bằng token F1 và judge score.
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab? Quality checks đánh giá tính đầy đủ và hợp lệ của dữ liệu (row count, unique paper_id, title không null, summary min length), trong khi freshness monitoring kiểm tra published date có quá cũ so với ngưỡng 180 ngày.
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired? Để biến độc lập duy nhất là trạng thái dữ liệu, tránh việc khác biệt về câu hỏi làm sai lệch kết quả so sánh.
5. Repair được xem là thành công dựa trên artifact và metric nào? Nếu repair tạo lại được dữ liệu sạch từ raw snapshot và metrics quay về đúng baseline (retrieval_hit_rate 1.0, mean_token_f1 1.0, judge_accuracy 1.0, quality/freshness PASS), thì repair được coi là thành công.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| retrieval_hit_rate | 1.0000 | 1.0000 | 1.0000 | Retrieval vẫn ổn trong kịch bản này vì corpus nhỏ và top-k đủ khoan dung. |
| mean_token_f1 | 1.0000 | 0.5000 | 1.0000 | Giảm rõ ở corrupted do các câu hỏi summary trúng vào tài liệu bị blank summary. |
| judge_accuracy | 1.0000 | 0.9000 | 1.0000 | Có 1/10 câu bị chấm sai do answer rỗng ở corrupted. |
| mean_judge_score | 5.0000 | 4.5000 | 5.0000 | Phù hợp với judge_accuracy. |
| Quality checks | 5/5 PASS | 3/5 FAIL | 5/5 PASS | Corrupted bị ảnh hưởng bởi duplicate, summary short và stale date. |
| Freshness status | Fresh | Stale | Fresh | Stale date làm corrupted fail freshness, repair khôi phục lại trạng thái fresh. |

### Kết luận từ số liệu

1. Blank summary → quality signal fail (summary_min_length, too_short_count=12) → mean_token_f1 giảm từ 1.0 xuống 0.5.
2. Repair từ raw snapshot → quality và freshness check quay về PASS → retrieval_hit_rate, mean_token_f1, judge_accuracy và mean_judge_score đều phục hồi về baseline.

Corruption nào ảnh hưởng rõ nhất và vì sao? Blank summary là kịch bản ảnh hưởng rõ nhất vì nó trực tiếp làm câu hỏi summary trả lời rỗng và kéo token F1 giảm rõ rệt. Ngoài ra, stale date cũng làm freshness fail, nhưng tác động đến answer metric không lớn bằng blank summary.

Kết quả khác với kỳ vọng ban đầu: retrieval_hit_rate không thay đổi trong cả ba trạng thái. Đây là kết quả thực tế được ghi nhận từ artifact, không phải suy diễn. Điều này cho thấy corruption nhẹ ở title và corpus nhỏ không đủ để làm retrieval fail trong top-k 4.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Data pipeline cần một tầng ingestion mạnh và có audit trail; raw snapshot là nền tảng cho reproducibility.
2. Data quality và freshness là hai lớp observability khác nhau: quality checks đánh giá hợp lệ/đầy đủ, freshness kiểm tra temporal validity.
3. Trong RAG, dữ liệu xấu không chỉ làm retrieval sai mà còn làm answer quality giảm rõ rệt, đặc biệt là khi corruption chạm trực tiếp vào field được dùng để trả lời.

### Nếu có thêm thời gian

Có thể cải thiện bằng cách tăng độ nhạy của retrieval test: giảm top_k hoặc tăng mức độ noise trong title/summary, sau đó so sánh lại thay đổi retrieval_hit_rate để thấy rõ hơn tác động của corruption.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Xuân Thế Độ
**Ngày xác nhận:** 2026-08-06
