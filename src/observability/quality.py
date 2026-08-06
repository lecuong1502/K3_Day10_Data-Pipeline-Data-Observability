from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json


def _check_row_count(df: pd.DataFrame) -> dict[str, Any]:
    row_count = len(df)
    passed = row_count > 0
    return {
        "check": "row_count",
        "passed": passed,
        "details": {"row_count": row_count},
    }


def _check_paper_id(df: pd.DataFrame) -> dict[str, Any]:
    if "paper_id" not in df.columns:
        return {"check": "paper_id_not_null_unique", "passed": False, "details": {"error": "missing column"}}
    null_count = int(df["paper_id"].isna().sum() + (df["paper_id"].astype(str).str.strip() == "").sum())
    duplicate_count = int(df["paper_id"].duplicated().sum())
    passed = null_count == 0 and duplicate_count == 0
    return {
        "check": "paper_id_not_null_unique",
        "passed": passed,
        "details": {"null_count": null_count, "duplicate_count": duplicate_count},
    }


def _check_title(df: pd.DataFrame) -> dict[str, Any]:
    if "title" not in df.columns:
        return {"check": "title_not_null", "passed": False, "details": {"error": "missing column"}}
    null_count = int(df["title"].isna().sum() + (df["title"].astype(str).str.strip() == "").sum())
    passed = null_count == 0
    return {
        "check": "title_not_null",
        "passed": passed,
        "details": {"null_count": null_count},
    }


def _check_summary_length(df: pd.DataFrame, min_chars: int = 100) -> dict[str, Any]:
    if "summary" not in df.columns:
        return {"check": "summary_min_length", "passed": False, "details": {"error": "missing column"}}
    too_short = df["summary"].fillna("").astype(str).str.len() < min_chars
    too_short_count = int(too_short.sum())
    passed = too_short_count == 0
    return {
        "check": "summary_min_length",
        "passed": passed,
        "details": {"min_chars": min_chars, "too_short_count": too_short_count},
    }


def _check_freshness(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    if "age_days" not in df.columns:
        return {"check": "freshness", "passed": False, "details": {"error": "missing column"}}
    ages = pd.to_numeric(df["age_days"], errors="coerce")
    stale_mask = ages.isna() | (ages > settings.freshness_threshold_days)
    stale_count = int(stale_mask.sum())
    passed = stale_count == 0
    return {
        "check": "freshness",
        "passed": passed,
        "details": {
            "freshness_threshold_days": settings.freshness_threshold_days,
            "stale_count": stale_count,
        },
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chay bo data quality checks va ghi ket qua vao data/quality/.

    1. Check row count.
    2. Check paper_id not null va unique.
    3. Check title not null.
    4. Check do dai summary.
    5. Check freshness bang age_days.
    6. Ghi ket qua vao data/quality/.
    """
    checks = [
        _check_row_count(df),
        _check_paper_id(df),
        _check_title(df),
        _check_summary_length(df),
        _check_freshness(df, settings),
    ]

    overall_passed = all(check["passed"] for check in checks)

    report = {
        "report_name": report_name,
        "generated_at": now_utc().isoformat(),
        "row_count": len(df),
        "overall_passed": overall_passed,
        "checks": checks,
    }

    report_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"
    write_json(report_path, report)

    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tong hop freshness report.

    1. Tim latest va oldest published date.
    2. Dem so dong stale.
    3. Tao payload: latest_published, oldest_published, stale_rows, total_rows, is_fresh.
    4. Ghi JSON report.
    """
    total_rows = len(df)

    published_series = df["published"].astype(str) if "published" in df.columns else pd.Series(dtype=str)
    valid_published = published_series[published_series.str.strip() != ""]
    latest_published = valid_published.max() if not valid_published.empty else None
    oldest_published = valid_published.min() if not valid_published.empty else None

    if "age_days" in df.columns:
        ages = pd.to_numeric(df["age_days"], errors="coerce")
        stale_rows = int((ages.isna() | (ages > settings.freshness_threshold_days)).sum())
    else:
        stale_rows = total_rows

    is_fresh = total_rows > 0 and stale_rows == 0

    payload = {
        "generated_at": now_utc().isoformat(),
        "freshness_threshold_days": settings.freshness_threshold_days,
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "is_fresh": is_fresh,
    }

    write_json(report_path, payload)

    return payload