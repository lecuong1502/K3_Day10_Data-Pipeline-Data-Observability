from __future__ import annotations

from typing import Any

from core.utils import now_utc, write_text


def _fmt_status(passed: bool) -> str:
    return "✅ PASS" if passed else "❌ FAIL"


def _fmt_number(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _render_metrics_section(title: str, metrics: dict[str, Any]) -> list[str]:
    lines = [f"## {title}", ""]
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    for key in ("samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        if key in metrics:
            lines.append(f"| `{key}` | {_fmt_number(metrics[key])} |")
    lines.append("")

    ragas = metrics.get("ragas")
    if isinstance(ragas, dict) and ragas:
        lines.append("**Ragas**")
        lines.append("")
        for key, value in ragas.items():
            lines.append(f"- `{key}`: {_fmt_number(value)}")
        lines.append("")

    return lines


def _render_quality_section(title: str, quality: dict[str, Any]) -> list[str]:
    lines = [f"## {title}", ""]
    lines.append(f"Overall: **{_fmt_status(quality.get('overall_passed', False))}** "
                 f"({quality.get('row_count', 0)} rows checked)")
    lines.append("")
    lines.append("| Check | Status | Details |")
    lines.append("| --- | --- | --- |")
    for check in quality.get("checks", []):
        details = ", ".join(f"{k}={v}" for k, v in (check.get("details") or {}).items())
        lines.append(f"| `{check.get('check')}` | {_fmt_status(check.get('passed', False))} | {details} |")
    lines.append("")
    return lines


def _render_freshness_section(title: str, freshness: dict[str, Any]) -> list[str]:
    lines = [f"## {title}", ""]
    lines.append(f"Overall: **{_fmt_status(freshness.get('is_fresh', False))}**")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("| --- | --- |")
    for key in ("latest_published", "oldest_published", "stale_rows", "total_rows", "freshness_threshold_days"):
        if key in freshness:
            lines.append(f"| `{key}` | {freshness[key]} |")
    lines.append("")
    return lines


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viet markdown report cho baseline phase.

    1. Gom source summary.
    2. In metrics retrieval/evaluation.
    3. In data quality va freshness.
    4. Ghi markdown vao report_path.
    """
    lines: list[str] = []
    lines.append("# Phase 1 - Baseline Report")
    lines.append("")
    lines.append(f"Generated at: {now_utc().isoformat()}")
    lines.append("")

    lines.append("## Data Source")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("| --- | --- |")
    for key, value in source_summary.items():
        lines.append(f"| `{key}` | {value} |")
    lines.append("")

    lines.extend(_render_metrics_section("Evaluation Metrics (Baseline)", metrics))
    lines.extend(_render_quality_section("Data Quality", quality))
    lines.extend(_render_freshness_section("Freshness", freshness))

    write_text(report_path, "\n".join(lines) + "\n")


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Viet markdown report so sanh baseline/corrupted/repaired."""
    lines: list[str] = []
    lines.append("# Data Corruption & Repair - Comparison Report")
    lines.append("")
    lines.append(f"Generated at: {now_utc().isoformat()}")
    lines.append("")

    lines.append("## Metrics Comparison")
    lines.append("")
    lines.append("| Metric | Baseline | Corrupted | Repaired |")
    lines.append("| --- | --- | --- | --- |")
    for key in ("samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        base_val = _fmt_number(baseline_metrics.get(key, "n/a"))
        corrupt_val = _fmt_number(corrupted_metrics.get(key, "n/a"))
        repair_val = _fmt_number(repaired_metrics.get(key, "n/a"))
        lines.append(f"| `{key}` | {base_val} | {corrupt_val} | {repair_val} |")
    lines.append("")

    lines.extend(_render_quality_section("Data Quality - Corrupted", corrupted_quality))
    lines.extend(_render_quality_section("Data Quality - Repaired", repaired_quality))
    lines.extend(_render_freshness_section("Freshness - Corrupted", corrupted_freshness))
    lines.extend(_render_freshness_section("Freshness - Repaired", repaired_freshness))

    write_text(report_path, "\n".join(lines) + "\n")