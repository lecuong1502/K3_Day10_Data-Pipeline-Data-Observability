# Phase 1 - Baseline Report

Generated at: 2026-08-06T03:29:15.103410+00:00

## Data Source

| Field | Value |
| --- | --- |
| `source_api` | Crossref REST API |
| `source_query` | agentic retrieval augmented generation large language model |
| `source_filter` | from-pub-date:2026-02-07,has-abstract:true |
| `max_results` | 24 |
| `raw_record_count` | 24 |
| `clean_record_count` | 24 |

## Evaluation Metrics (Baseline)

| Metric | Value |
| --- | --- |
| `samples` | 10 |
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 0.5000 |
| `judge_accuracy` | 0.5000 |
| `mean_judge_score` | 3 |

**Ragas**

- `skipped`: Set RUN_RAGAS=1 to enable the slower Ragas pass.

## Data Quality

Overall: **✅ PASS** (24 rows checked)

| Check | Status | Details |
| --- | --- | --- |
| `row_count` | ✅ PASS | row_count=24 |
| `paper_id_not_null_unique` | ✅ PASS | null_count=0, duplicate_count=0 |
| `title_not_null` | ✅ PASS | null_count=0 |
| `summary_min_length` | ✅ PASS | min_chars=100, too_short_count=0 |
| `freshness` | ✅ PASS | freshness_threshold_days=180, stale_count=0 |

## Freshness

Overall: **✅ PASS**

| Field | Value |
| --- | --- |
| `latest_published` | 2026-08-01 |
| `oldest_published` | 2026-02-12 |
| `stale_rows` | 0 |
| `total_rows` | 24 |
| `freshness_threshold_days` | 180 |

