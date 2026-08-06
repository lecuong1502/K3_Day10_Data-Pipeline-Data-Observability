from __future__ import annotations

from datetime import date, datetime
import re

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord

MIN_SUMMARY_CHARS = 100
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_markup(text: str) -> str:
    if not text:
        return ""
    return _TAG_RE.sub(" ", text)


def _clean_text(text: str) -> str:
    return normalize_whitespace(_strip_markup(text or ""))


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _compute_age_days(published: str, run_date: datetime) -> int | None:
    parsed = _parse_date(published)
    if parsed is None:
        return None
    return (run_date.date() - parsed).days


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed.

    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days.
    4. Tao cot helper: authors_joined, categories_joined, summary_chars, text_for_embedding.
    5. Drop duplicates va filter row xau.
    6. Sort dataframe va return.
    """
    rows: list[dict] = []
    seen_ids: set[str] = set()

    for record in records:
        title = _clean_text(record.title)
        summary = _clean_text(record.summary)

        # Loai bo ban ghi rac: thieu title, hoac summary qua ngan.
        if not title or not summary or len(summary) < MIN_SUMMARY_CHARS:
            continue

        paper_id = record.paper_id or ""
        if not paper_id or paper_id in seen_ids:
            continue
        seen_ids.add(paper_id)

        authors_joined = compact_join(a for a in record.authors if a)
        categories_joined = compact_join(c for c in record.categories if c)

        published = record.published or ""
        updated = record.updated or published
        age_days = _compute_age_days(published, run_date)

        text_for_embedding = f"Title: {title} | Authors: {authors_joined} | Summary: {summary}"

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "primary_category": record.primary_category or "",
                "published": published,
                "updated": updated,
                "age_days": age_days,
                "summary_chars": len(summary),
                "abs_url": record.abs_url or "",
                "pdf_url": record.pdf_url or "",
                "comment": record.comment or "",
                "text_for_embedding": text_for_embedding,
            }
        )

    columns = [
        "paper_id",
        "title",
        "summary",
        "authors_joined",
        "categories_joined",
        "primary_category",
        "published",
        "updated",
        "age_days",
        "summary_chars",
        "abs_url",
        "pdf_url",
        "comment",
        "text_for_embedding",
    ]

    if not rows:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows, columns=columns)
    df = df.drop_duplicates(subset=["paper_id"]).reset_index(drop=True)
    df = df.sort_values(by=["published", "paper_id"], ascending=[False, True], na_position="last")
    df = df.reset_index(drop=True)

    return df