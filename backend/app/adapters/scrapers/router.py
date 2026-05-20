"""Picks the right scraper based on the input.

Adding a new source = add one line to `_URL_SCRAPERS`. No other refactors.
"""
from __future__ import annotations

from app.adapters.scrapers.base import JobScraper, UnsupportedSourceError
from app.adapters.scrapers.greenhouse import GreenhouseScraper
from app.adapters.scrapers.lever import LeverScraper
from app.adapters.scrapers.linkedin import LinkedInScraper
from app.adapters.scrapers.raw_text import RawTextScraper

# Order matters only if multiple matchers overlap; today they don't.
_URL_SCRAPERS: list[type[JobScraper]] = [
    GreenhouseScraper,
    LeverScraper,
    LinkedInScraper,
]


class ScraperRouter:
    """Stateless dispatcher. Holds instantiated scrapers so they can keep clients later."""

    def __init__(self) -> None:
        self._url_scrapers = [s() for s in _URL_SCRAPERS]
        self._raw_text = RawTextScraper()

    def for_url(self, url: str) -> JobScraper:
        for s in self._url_scrapers:
            if s.__class__.matches(url):  # type: ignore[attr-defined]
                return s
        raise UnsupportedSourceError(
            "We don't support this job board yet. Please paste the JD text instead.",
        )

    def for_text(self) -> JobScraper:
        return self._raw_text
