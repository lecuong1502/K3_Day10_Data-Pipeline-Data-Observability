# Data Corruption & Repair - Comparison Report

Generated at: 2026-08-06T03:51:01.411923+00:00

## Metrics Comparison

| Metric | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| `samples` | 10 | 10 | 10 |
| `retrieval_hit_rate` | 1.0000 | 1.0000 | 1.0000 |
| `mean_token_f1` | 1.0000 | 0.5000 | 1.0000 |
| `judge_accuracy` | 1.0000 | 0.9000 | 1.0000 |
| `mean_judge_score` | 5 | 4.5000 | 5 |

## Data Quality - Corrupted

Overall: **❌ FAIL** (26 rows checked)

| Check | Status | Details |
| --- | --- | --- |
| `row_count` | ✅ PASS | row_count=26 |
| `paper_id_not_null_unique` | ❌ FAIL | null_count=0, duplicate_count=2 |
| `title_not_null` | ✅ PASS | null_count=0 |
| `summary_min_length` | ❌ FAIL | min_chars=100, too_short_count=12 |
| `freshness` | ❌ FAIL | freshness_threshold_days=180, stale_count=3 |

## Data Quality - Repaired

Overall: **✅ PASS** (24 rows checked)

| Check | Status | Details |
| --- | --- | --- |
| `row_count` | ✅ PASS | row_count=24 |
| `paper_id_not_null_unique` | ✅ PASS | null_count=0, duplicate_count=0 |
| `title_not_null` | ✅ PASS | null_count=0 |
| `summary_min_length` | ✅ PASS | min_chars=100, too_short_count=0 |
| `freshness` | ✅ PASS | freshness_threshold_days=180, stale_count=0 |

## Freshness - Corrupted

Overall: **❌ FAIL**

| Field | Value |
| --- | --- |
| `latest_published` | 2026-08-01 |
| `oldest_published` | 2000-01-01 |
| `stale_rows` | 3 |
| `total_rows` | 26 |
| `freshness_threshold_days` | 180 |

## Freshness - Repaired

Overall: **✅ PASS**

| Field | Value |
| --- | --- |
| `latest_published` | 2026-08-01 |
| `oldest_published` | 2026-02-12 |
| `stale_rows` | 0 |
| `total_rows` | 24 |
| `freshness_threshold_days` | 180 |

