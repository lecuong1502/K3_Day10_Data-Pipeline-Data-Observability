from __future__ import annotations

import random
from typing import Any

import pandas as pd

from core.utils import now_utc, write_json

MIN_ROWS_REQUIRED = 3
STALE_YEAR = "2000"
NOISE_TOKENS = [
    "asldkj##9182",
    "zzz-noise-zzz",
    "lorem ipsum qwerty",
    "%%%CORRUPTED%%%",
    "xj3kd_random_token",
    "###injected###",
]


def _noise_suffix(rng: random.Random) -> str:
    tokens = rng.sample(NOISE_TOKENS, k=min(3, len(NOISE_TOKENS)))
    return " ".join(tokens)


def _rebuild_text_for_embedding(row: dict[str, Any]) -> str:
    title = row.get("title", "")
    authors = row.get("authors_joined", "")
    summary = row.get("summary", "")
    return f"Title: {title} | Authors: {authors} | Summary: {summary}"


def corrupt_clean_dataframe(
    df: pd.DataFrame,
    output_log_path,
    target_paper_ids: list[str] | None = None,
    seed: int = 42,
) -> pd.DataFrame:
    """Simulate cac dang data corruption co kiem soat tren cleaned dataframe.

    Kich ban ap dung (>= 3):
    1. Blank summary: xoa summary o mot so ban ghi.
    2. Stale date: dua published ve nam 2000 de danh lua freshness check.
    3. Noise injection: chen ky tu/noi dung rac vao title (roi rebuild
       text_for_embedding) de lam nhieu vector embedding.
    4. Duplicate rows: nhan doi mot so ban ghi, giu nguyen paper_id.

    target_paper_ids (paper_id xuat hien trong ground_truth_doc_ids cua bo
    test frozen) LUON duoc uu tien nam trong tap bi corrupt, va duoc ap dung
    dong thoi blank_summary + noise_injection de dam bao anh huong ro ret
    len ca retrieval lan token-f1/judge score.
    """
    if df is None or df.empty:
        raise ValueError("Cannot corrupt an empty dataframe.")
    if len(df) < MIN_ROWS_REQUIRED:
        raise ValueError(f"Need at least {MIN_ROWS_REQUIRED} rows to corrupt, got {len(df)}.")

    rng = random.Random(seed)
    working = df.copy().reset_index(drop=True)
    all_ids = working["paper_id"].tolist()

    target_ids = {pid for pid in (target_paper_ids or []) if pid in all_ids}

    # Fill up the corruption pool with extra random rows so overall corruption
    # rate is meaningful (~35%), while guaranteeing every target id is included.
    non_target_pool = [pid for pid in all_ids if pid not in target_ids]
    rng.shuffle(non_target_pool)
    desired_total = max(len(target_ids), max(3, int(len(working) * 0.35)))
    extra_needed = max(0, desired_total - len(target_ids))
    extra_ids = set(non_target_pool[:extra_needed])

    # Rotate single-effect scenarios across the "extra" (non-target) pool so
    # quality checks see a mix of failure types.
    rotating_scenarios = ["blank_summary", "stale_date", "noise_injection"]
    extra_scenario_map = {pid: rotating_scenarios[i % len(rotating_scenarios)] for i, pid in enumerate(sorted(extra_ids))}

    # Guarantee `stale_date` fires on at least MIN_STALE rows regardless of
    # how large target_ids/extra_ids already are (otherwise, when target_ids
    # alone already meets the ~35% quota, stale_date never gets scheduled and
    # the freshness check would always PASS on corrupted data, which defeats
    # the point of this scenario). Prefer ids not already scheduled for a
    # scenario; fall back to stacking onto target ids if the dataset is tiny.
    MIN_STALE = min(3, len(all_ids))
    already_scheduled = set(extra_scenario_map.keys())
    stale_candidates = [pid for pid in non_target_pool if pid not in already_scheduled]
    if len(stale_candidates) < MIN_STALE:
        stale_candidates += [pid for pid in sorted(target_ids) if pid not in stale_candidates]
    forced_stale_ids = set(stale_candidates[:MIN_STALE])

    log_entries: list[dict[str, Any]] = []
    corrupted_records: list[dict[str, Any]] = []

    for row in working.to_dict(orient="records"):
        pid = row["paper_id"]
        applied: list[str] = []

        if pid in target_ids:
            # Guaranteed-impact combo: blanks the summary AND injects noise
            # into the title, so both retrieval (embedding) and answer
            # quality (token-f1/judge) visibly degrade for these documents,
            # which are the ones actually asked about in the frozen test set.
            before_summary = row["summary"]
            row["summary"] = ""
            log_entries.append(
                {"paper_id": pid, "scenario": "blank_summary", "field": "summary",
                 "before": before_summary, "after": ""}
            )
            applied.append("blank_summary")

            before_title = row["title"]
            row["title"] = f"{before_title} {_noise_suffix(rng)}"
            log_entries.append(
                {"paper_id": pid, "scenario": "noise_injection", "field": "title",
                 "before": before_title, "after": row["title"]}
            )
            applied.append("noise_injection")

        elif pid in extra_scenario_map:
            scenario = extra_scenario_map[pid]
            if scenario == "blank_summary":
                before_summary = row["summary"]
                row["summary"] = ""
                log_entries.append(
                    {"paper_id": pid, "scenario": "blank_summary", "field": "summary",
                     "before": before_summary, "after": ""}
                )
            elif scenario == "stale_date":
                before_published = row["published"]
                row["published"] = f"{STALE_YEAR}-01-01"
                row["age_days"] = (now_utc().date() - pd.Timestamp(f"{STALE_YEAR}-01-01").date()).days
                log_entries.append(
                    {"paper_id": pid, "scenario": "stale_date", "field": "published",
                     "before": before_published, "after": row["published"]}
                )
            elif scenario == "noise_injection":
                before_title = row["title"]
                row["title"] = f"{before_title} {_noise_suffix(rng)}"
                log_entries.append(
                    {"paper_id": pid, "scenario": "noise_injection", "field": "title",
                     "before": before_title, "after": row["title"]}
                )
            applied.append(scenario)

        if pid in forced_stale_ids and "stale_date" not in applied:
            before_published = row["published"]
            row["published"] = f"{STALE_YEAR}-01-01"
            row["age_days"] = (now_utc().date() - pd.Timestamp(f"{STALE_YEAR}-01-01").date()).days
            log_entries.append(
                {"paper_id": pid, "scenario": "stale_date", "field": "published",
                 "before": before_published, "after": row["published"]}
            )
            applied.append("stale_date")

        row["text_for_embedding"] = _rebuild_text_for_embedding(row)
        corrupted_records.append(row)

    corrupted_df = pd.DataFrame(corrupted_records, columns=working.columns)

    # Duplicate scenario: append exact duplicate rows (same paper_id) for a
    # couple of records, preferring target ids so uniqueness checks fail on
    # documents that matter for evaluation too.
    duplicate_candidates = list(target_ids) if target_ids else all_ids[:1]
    duplicate_ids = duplicate_candidates[: min(2, len(duplicate_candidates))]
    for pid in duplicate_ids:
        dup_row = corrupted_df[corrupted_df["paper_id"] == pid].iloc[[0]]
        corrupted_df = pd.concat([corrupted_df, dup_row], ignore_index=True)
        log_entries.append({"paper_id": pid, "scenario": "duplicate_row", "field": "__row__",
                             "before": "1 copy", "after": "2 copies"})

    log_payload = {
        "generated_at": now_utc().isoformat(),
        "seed": seed,
        "total_rows_before": len(working),
        "total_rows_after": len(corrupted_df),
        "target_paper_ids": sorted(target_ids),
        "extra_corrupted_paper_ids": sorted(extra_ids),
        "forced_stale_paper_ids": sorted(forced_stale_ids),
        "duplicated_paper_ids": duplicate_ids,
        "scenarios_used": ["blank_summary", "stale_date", "noise_injection", "duplicate_row"],
        "entries": log_entries,
    }
    write_json(output_log_path, log_payload)

    return corrupted_df