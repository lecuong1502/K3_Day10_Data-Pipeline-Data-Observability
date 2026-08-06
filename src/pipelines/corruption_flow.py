from __future__ import annotations

import pandas as pd

from core.config import load_settings, require_llm_credentials
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _flatten_target_ids(test_set: list[dict]) -> list[str]:
    ids: list[str] = []
    for item in test_set:
        ids.extend(item.get("ground_truth_doc_ids", []))
    return sorted(set(ids))


def main() -> None:
    """Corruption -> evaluate -> repair -> compare flow (Pha 2).

    1. Load baseline metrics va clean dataset.
    2. Tao corrupted dataframe (overlap voi frozen test set).
    3. Save corrupted artifacts.
    4. Rebuild index va evaluate tren corrupted data.
    5. Run quality checks/freshness tren corrupted data.
    6. Repair lai tu raw records (khong fetch API lai).
    7. Evaluate repaired dataset.
    8. Tao comparison report (baseline vs corrupted vs repaired).
    """
    settings = load_settings()
    require_llm_credentials(settings)
    paths = settings.paths

    if not paths.baseline_metrics.exists() or not paths.clean_csv.exists():
        raise RuntimeError(
            "Missing baseline artifacts. Run `script/run_phase1.py` first "
            f"(expected {paths.baseline_metrics} and {paths.clean_csv})."
        )
    if not paths.eval_testset.exists():
        raise RuntimeError(f"Missing frozen evaluation set at {paths.eval_testset}. Run phase 1 first.")
    if not paths.raw_records_json.exists():
        raise RuntimeError(f"Missing raw records snapshot at {paths.raw_records_json}. Run phase 1 first.")

    baseline_metrics = read_json(paths.baseline_metrics)
    baseline_df = pd.read_csv(paths.clean_csv)
    test_set = read_json(paths.eval_testset)
    target_paper_ids = _flatten_target_ids(test_set)
    print(f"[corruption_flow] Frozen test set target paper_ids: {target_paper_ids}")

    # 2-3. Corrupt data + save artifacts
    print("[corruption_flow] Corrupting clean dataset ...")
    corrupted_df = corrupt_clean_dataframe(
        baseline_df, paths.corruption_log, target_paper_ids=target_paper_ids
    )
    write_csv(corrupted_df, paths.corrupted_clean_csv)
    write_json(paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    print(f"[corruption_flow] Corrupted rows: {len(corrupted_df)} -> {paths.corrupted_clean_csv}")

    # 4. Rebuild index va evaluate tren corrupted data
    print("[corruption_flow] Building Chroma index on corrupted data ...")
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings, embeddings_output_path=paths.corrupted_embeddings_json
    )
    print("[corruption_flow] Evaluating corrupted state ...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.corrupted_metrics,
        answers_output_path=paths.corrupted_answers,
    )
    print(f"[corruption_flow] Corrupted metrics: {corrupted_bundle.summary}")

    # 5. Quality checks / freshness tren corrupted data
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, report_name="corrupted")
    corrupted_freshness_path = paths.quality_dir / "corrupted_freshness_report.json"
    corrupted_freshness = build_freshness_report(corrupted_df, settings, corrupted_freshness_path)
    print(f"[corruption_flow] Corrupted quality overall_passed={corrupted_quality['overall_passed']} "
          f"freshness is_fresh={corrupted_freshness['is_fresh']}")

    # 6. Repair tu raw records (KHONG fetch API lai)
    print("[corruption_flow] Repairing from raw snapshot ...")
    raw_records = load_raw_records(paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, now_utc())
    write_csv(repaired_df, paths.repaired_clean_csv)
    write_json(paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    print(f"[corruption_flow] Repaired rows: {len(repaired_df)} -> {paths.repaired_clean_csv}")

    # 5(repeat)-7. Rebuild index va evaluate repaired dataset
    print("[corruption_flow] Building Chroma index on repaired data ...")
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, embeddings_output_path=paths.repaired_embeddings_json
    )
    print("[corruption_flow] Evaluating repaired state ...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.repaired_metrics,
        answers_output_path=paths.repaired_answers,
    )
    print(f"[corruption_flow] Repaired metrics: {repaired_bundle.summary}")

    repaired_quality = run_data_quality_checks(repaired_df, settings, report_name="repaired")
    repaired_freshness_path = paths.quality_dir / "repaired_freshness_report.json"
    repaired_freshness = build_freshness_report(repaired_df, settings, repaired_freshness_path)
    print(f"[corruption_flow] Repaired quality overall_passed={repaired_quality['overall_passed']} "
          f"freshness is_fresh={repaired_freshness['is_fresh']}")

    # 8. Comparison report (baseline vs corrupted vs repaired)
    generate_corruption_report(
        report_path=paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"[corruption_flow] Comparison report written to {paths.comparison_report}")
    print("[corruption_flow] Done.")


if __name__ == "__main__":
    main()