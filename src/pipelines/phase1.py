from __future__ import annotations

from core.config import load_settings, require_llm_credentials
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex

NUM_DEMO_QUESTIONS = 3


def main() -> None:
    """Baseline pipeline end-to-end tren du lieu sach.

    1. Load settings.
    2. Load hoac fetch raw records.
    3. Clean data.
    4. Save clean CSV/JSON.
    5. Build Chroma index.
    6. Tao hoac load evaluation set.
    7. Evaluate.
    8. Run quality checks va freshness report.
    9. Tao markdown report.
    10. Demo agent tren vai sample question.
    """
    settings = load_settings()
    require_llm_credentials(settings)
    paths = settings.paths

    # 2. Load hoac fetch raw records
    if settings.refresh_source or not paths.raw_records_json.exists():
        print(f"[phase1] Fetching raw records from {settings.source_api} ...")
        records = fetch_source_records(settings)
    else:
        print(f"[phase1] Loading cached raw records from {paths.raw_records_json}")
        records = load_raw_records(paths.raw_records_json)
    print(f"[phase1] Raw records: {len(records)}")

    # 3-4. Clean data va save clean CSV/JSON
    df = build_clean_dataframe(records, now_utc())
    if df.empty:
        raise RuntimeError("Cleaning produced an empty dataframe; check ingestion/cleaning filters.")
    write_csv(df, paths.clean_csv)
    write_json(paths.clean_json, df.to_dict(orient="records"))
    print(f"[phase1] Clean records: {len(df)} -> {paths.clean_csv}")

    # 5. Build Chroma index
    print("[phase1] Building Chroma vector index ...")
    index = LocalEmbeddingIndex.build(df, settings, embeddings_output_path=paths.embeddings_json)

    # 6. Tao hoac load evaluation set (frozen)
    if settings.refresh_test_set or not paths.eval_testset.exists():
        print("[phase1] Building evaluation test set ...")
        test_set = build_test_set(df, paths.eval_testset)
    else:
        print(f"[phase1] Loading frozen evaluation test set from {paths.eval_testset}")
        test_set = read_json(paths.eval_testset)
    print(f"[phase1] Evaluation questions: {len(test_set)}")

    # 7. Evaluate baseline
    print("[phase1] Running evaluation pipeline (agent + retrieval + judge) ...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.baseline_metrics,
        answers_output_path=paths.baseline_answers,
    )
    print(f"[phase1] Baseline metrics: {bundle.summary}")

    # 8. Quality checks va freshness report
    quality_report = run_data_quality_checks(df, settings, report_name="baseline")
    freshness_report = build_freshness_report(df, settings, paths.freshness_report)
    print(f"[phase1] Quality overall_passed={quality_report['overall_passed']} "
          f"freshness is_fresh={freshness_report['is_fresh']}")

    # 9. Markdown report
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "max_results": settings.max_results,
        "raw_record_count": len(records),
        "clean_record_count": len(df),
    }
    generate_phase1_report(
        report_path=paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality_report,
        freshness=freshness_report,
    )
    print(f"[phase1] Report written to {paths.baseline_report}")

    # 10. Demo agent tren vai sample question
    print("[phase1] Running agent demo on a few sample questions ...")
    agent = build_agent(settings, index)
    demo_answers = []
    for item in test_set[:NUM_DEMO_QUESTIONS]:
        answer = run_agent_question(agent, item["question"])
        demo_answers.append({"id": item["id"], "question": item["question"], "answer": answer})
    write_json(paths.demo_answers, demo_answers)
    print(f"[phase1] Demo answers written to {paths.demo_answers}")

    print("[phase1] Done.")


if __name__ == "__main__":
    main()