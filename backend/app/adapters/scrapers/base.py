from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.core.errors import AppError


class UnsupportedSourceError(AppError):
    """The given URL is from a source we don't support reliably yet.

    The frontend should treat this as a hint to ask the user to paste JD text instead.
    """

    status_code = 422
    code = "unsupported_source"


class ScrapeFailedError(AppError):
    """Scraper reached the source but couldn't extract a usable payload."""

    status_code = 502
    code = "scrape_failed"


@dataclass
class ScrapeResult:
    """The output every scraper produces. Deterministic fields + raw description text.

    - `source` matches the routing key (e.g. "greenhouse", "lever", "raw_text").
    - `description_text` is what gets fed to the LLM normalization step.
    - `raw_payload` is the verbatim upstream response (HTML or JSON), kept for re-extraction.
    """

    source: str
    description_text: str
    title: str | None = None
    company_name: str | None = None
    company_domain: str | None = None
    location: str | None = None
    raw_payload: str | None = None
    extras: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class JobScraper(Protocol):
    source: str  # routing key

    async def fetch(self, *, url: str | None = None, text: str | None = None) -> ScrapeResult: ...
