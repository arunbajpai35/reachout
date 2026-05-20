"""LinkedIn scraper placeholder.

Per Slice 2 decision: we do NOT scrape LinkedIn in v0. When an Apify adapter is added,
implement `fetch()` to call the actor and shape the response into a ScrapeResult.

The placeholder still registers a matcher so the router can return a friendly
'paste the JD text instead' message rather than a generic 'unsupported source'.
"""
from __future__ import annotations

import re

from app.adapters.scrapers.base import JobScraper, ScrapeResult, UnsupportedSourceError

_URL_RE = re.compile(
    r"^https?://(?:[a-z]+\.)?linkedin\.com/jobs/(?:view|collections)/",
    re.IGNORECASE,
)


class LinkedInScraper(JobScraper):
    source = "linkedin"

    @classmethod
    def matches(cls, url: str) -> bool:
        return _URL_RE.match(url) is not None

    async def fetch(self, *, url: str | None = None, text: str | None = None) -> ScrapeResult:
        raise UnsupportedSourceError(
            "LinkedIn URLs aren't supported yet. Please paste the job description text instead.",
            code="linkedin_paste_required",
        )
