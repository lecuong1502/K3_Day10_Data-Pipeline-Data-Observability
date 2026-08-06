from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, safe_slug, write_json

CROSSREF_API_URL = "https://api.crossref.org/works"
RETRYABLE_STATUS_CODES = {429, 503}
MAX_RETRIES = 5
BASE_BACKOFF_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 30
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _strip_markup(text: str) -> str:
    """Remove XML/HTML tags (e.g. <jats:p>) commonly present in Crossref abstracts."""
    if not text:
        return ""
    return _TAG_RE.sub(" ", text)


def _extract_date(item: dict, keys: list[str]) -> str:
    """Extract the first available date-parts field and format it as YYYY-MM-DD."""
    for key in keys:
        node = item.get(key)
        if not node:
            continue
        date_parts = node.get("date-parts")
        if not date_parts or not date_parts[0]:
            continue
        parts = date_parts[0]
        if not parts or parts[0] is None:
            continue
        year = parts[0]
        month = parts[1] if len(parts) > 1 and parts[1] else 1
        day = parts[2] if len(parts) > 2 and parts[2] else 1
        try:
            return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        except (TypeError, ValueError):
            continue
    return ""


def _extract_pdf_url(item: dict) -> str:
    for link in item.get("link", []) or []:
        if link.get("content-type") == "application/pdf":
            return link.get("URL", "")
    return ""


def _extract_authors(item: dict) -> list[str]:
    authors: list[str] = []
    for author in item.get("author", []) or []:
        given = author.get("given", "")
        family = author.get("family", "")
        name = normalize_whitespace(f"{given} {family}")
        if name:
            authors.append(name)
    return authors


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord.

    1. Duyet payload["message"]["items"].
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le (thieu title/abstract).
    4. Tra ve list PaperRecord.
    """
    items = (payload or {}).get("message", {}).get("items", []) or []
    records: list[PaperRecord] = []

    for item in items:
        titles = item.get("title") or []
        title = normalize_whitespace(_strip_markup(titles[0])) if titles else ""

        raw_summary = item.get("abstract") or item.get("description") or ""
        summary = normalize_whitespace(_strip_markup(raw_summary))

        if not title or not summary:
            continue

        doi = item.get("DOI", "")
        authors = _extract_authors(item)

        categories = [
            normalize_whitespace(subject)
            for subject in (item.get("subject") or [])
            if subject
        ]
        primary_category = categories[0] if categories else ""

        published = _extract_date(
            item, ["published", "published-print", "published-online", "issued", "created"]
        )
        updated = _extract_date(item, ["deposited", "indexed"]) or published

        abs_url = item.get("URL", "") or (f"https://doi.org/{doi}" if doi else "")
        pdf_url = _extract_pdf_url(item)

        container_titles = item.get("container-title") or []
        comment = normalize_whitespace(container_titles[0]) if container_titles else ""

        paper_id = doi or safe_slug(title)

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )

    return records


def _request_with_retry(params: dict) -> requests.Response:
    """Call Crossref API with retry/backoff for 429/503 status codes."""
    headers = {"User-Agent": "Day10-Data-Observability-Lab/1.0 (mailto:student@example.com)"}
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                CROSSREF_API_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS
            )
        except requests.RequestException as exc:  # network-level errors: retry too
            last_error = exc
            time.sleep(BASE_BACKOFF_SECONDS * (2**attempt))
            continue

        if response.status_code in RETRYABLE_STATUS_CODES:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    wait_seconds = float(retry_after)
                except ValueError:
                    wait_seconds = BASE_BACKOFF_SECONDS * (2**attempt)
            else:
                wait_seconds = BASE_BACKOFF_SECONDS * (2**attempt)
            time.sleep(wait_seconds)
            continue

        response.raise_for_status()
        return response

    raise RuntimeError(
        f"Crossref request failed after {MAX_RETRIES} retries."
        + (f" Last error: {last_error}" if last_error else "")
    )


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi Crossref API, luu raw response, parse thanh records.

    1. Tao params tu settings.source_query, settings.source_filter, settings.max_results.
    2. Goi API voi retry cho 429/503.
    3. Luu raw response vao settings.paths.raw_api_response.
    4. Parse payload bang parse_crossref_payload.
    5. Luu records vao settings.paths.raw_records_json.
    """
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }

    response = _request_with_retry(params)
    payload = response.json()

    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh PaperRecord."""
    data = read_json(path)
    return [PaperRecord(**item) for item in data]