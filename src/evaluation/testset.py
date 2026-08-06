from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json

MIN_CLEAN_DOCS_REQUIRED = 3
MIN_QUESTIONS = 5
MAX_QUESTIONS = 10


def _build_summary_question(row: dict[str, Any]) -> tuple[str, str] | None:
    summary = (row.get("summary") or "").strip()
    if not summary:
        return None
    question = f"Nội dung chính của bài báo '{row['title']}' đề cập đến điều gì?"
    ground_truth = first_sentence(summary)
    return question, ground_truth


def _build_authors_question(row: dict[str, Any]) -> tuple[str, str] | None:
    authors_joined = (row.get("authors_joined") or "").strip()
    if not authors_joined:
        return None
    question = f"Tác giả của bài báo '{row['title']}' là ai?"
    return question, authors_joined


def _build_date_question(row: dict[str, Any]) -> tuple[str, str] | None:
    published = (row.get("published") or "").strip()
    if not published:
        return None
    question = f"Bài báo '{row['title']}' được xuất bản vào ngày nào?"
    return question, published


def _build_categories_question(row: dict[str, Any]) -> tuple[str, str] | None:
    categories_joined = (row.get("categories_joined") or "").strip()
    if not categories_joined:
        return None
    question = f"Bài báo '{row['title']}' thuộc (các) category/lĩnh vực nào?"
    return question, categories_joined


# Order matters: used to rotate question types across selected papers so the
# frozen set has a mix of summary / authors / date / categories questions.
_QUESTION_GENERATORS: list[tuple[str, Any]] = [
    ("summary", _build_summary_question),
    ("authors", _build_authors_question),
    ("date", _build_date_question),
    ("categories", _build_categories_question),
]


def _select_representative_rows(df: pd.DataFrame, num_candidates: int) -> list[dict[str, Any]]:
    """Pick evenly spaced rows across the cleaned dataframe for diversity."""
    total = len(df)
    num_candidates = min(num_candidates, total)
    step = max(1, total // num_candidates)
    indices = list(range(0, total, step))[:num_candidates]
    return df.iloc[indices].to_dict(orient="records")


def build_test_set(df: pd.DataFrame, output_path: Path | str) -> list[dict[str, Any]]:
    """Tao bo evaluation set (frozen) tu cleaned dataframe.

    1. Kiem tra so luong document toi thieu.
    2. Chon mot so paper dai dien (rai deu tren dataframe).
    3. Voi moi paper, sinh 1 cau hoi theo mot trong 4 loai: summary / authors / date / categories,
       xoay vong loai cau hoi giua cac paper de bo test da dang.
    4. Moi sample tuan thu schema: id, question_type, question, ground_truth, ground_truth_doc_ids.
    5. Ghi file JSON vao output_path va tra ve list cau hoi.
    """
    if df is None or df.empty:
        raise ValueError("Cannot build evaluation set: cleaned dataframe is empty.")
    if len(df) < MIN_CLEAN_DOCS_REQUIRED:
        raise ValueError(
            f"Need at least {MIN_CLEAN_DOCS_REQUIRED} clean documents to build an evaluation set, "
            f"got {len(df)}."
        )

    candidate_rows = _select_representative_rows(df, MAX_QUESTIONS)

    questions: list[dict[str, Any]] = []
    num_generators = len(_QUESTION_GENERATORS)

    for row_idx, row in enumerate(candidate_rows):
        if len(questions) >= MAX_QUESTIONS:
            break

        # Rotate the starting generator per row so question types don't cluster.
        offset = row_idx % num_generators
        ordered_generators = _QUESTION_GENERATORS[offset:] + _QUESTION_GENERATORS[:offset]

        for question_type, generator in ordered_generators:
            result = generator(row)
            if result is None:
                continue
            question_text, ground_truth = result
            questions.append(
                {
                    "id": f"q{len(questions) + 1}",
                    "question_type": question_type,
                    "question": question_text,
                    "ground_truth": ground_truth,
                    "ground_truth_doc_ids": [row["paper_id"]],
                }
            )
            break  # one question per paper is enough to keep doc coverage broad

    if len(questions) < MIN_QUESTIONS:
        raise ValueError(
            f"Only generated {len(questions)} evaluation questions (need >= {MIN_QUESTIONS}). "
            "Cleaned dataset may be missing authors/date/categories metadata for enough papers."
        )

    write_json(Path(output_path), questions)
    return questions