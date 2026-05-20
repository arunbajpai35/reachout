from __future__ import annotations

from app.adapters.scrapers.base import JobScraper, ScrapeFailedError, ScrapeResult


class RawTextScraper(JobScraper):
    """Pseudo-scraper for user-pasted JD text. First-class input mode."""

    source = "raw_text"

    async def fetch(self, *, url: str | None = None, text: str | None = None) -> ScrapeResult:
        if not text or not text.strip():
            raise ScrapeFailedError("raw text input is empty")
        # Title/company unknown from raw text; LLM extracts company_name from the body.
        return ScrapeResult(source=self.source, description_text=text.strip())
