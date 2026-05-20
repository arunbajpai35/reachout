from __future__ import annotations

import json
import re

import httpx

from app.adapters.scrapers.base import JobScraper, ScrapeFailedError, ScrapeResult
from app.adapters.scrapers.greenhouse import _html_to_text
from app.core.retry import default_retry

# Accepts:
#   https://jobs.lever.co/<site>/<posting_id>
_URL_RE = re.compile(
    r"^https?://jobs\.lever\.co/(?P<site>[^/]+)/(?P<id>[0-9a-fA-F-]+)",
    re.IGNORECASE,
)

_API = "https://api.lever.co/v0/postings/{site}/{posting_id}"


class LeverScraper(JobScraper):
    source = "lever"

    @classmethod
    def matches(cls, url: str) -> bool:
        return _URL_RE.match(url) is not None

    async def fetch(self, *, url: str | None = None, text: str | None = None) -> ScrapeResult:
        if not url:
            raise ScrapeFailedError("lever scraper requires a URL")
        m = _URL_RE.match(url)
        if not m:
            raise ScrapeFailedError(f"not a lever url: {url}")
        api = _API.format(site=m["site"], posting_id=m["id"])

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            async for attempt in default_retry(retry_on=(httpx.HTTPError,)):
                with attempt:
                    r = await client.get(api, headers={"accept": "application/json"})
                    r.raise_for_status()
                    data = r.json()

        title = data.get("text")  # Lever calls posting title "text"
        categories = data.get("categories") or {}
        location = categories.get("location")
        # description fields: data["description"] (HTML) + data["lists"] (structured bullets) + data["additional"]
        desc_html = data.get("descriptionPlain") or _html_to_text(data.get("description") or "")
        bullets = []
        for section in data.get("lists") or []:
            section_text = section.get("text") or ""
            content_text = _html_to_text(section.get("content") or "")
            bullets.append(f"{section_text}\n{content_text}")
        additional = _html_to_text(data.get("additional") or "")
        description_text = "\n\n".join(p for p in [desc_html, *bullets, additional] if p)

        # Lever doesn't include company name in the posting; the site slug is the closest thing.
        company_name = m["site"].replace("-", " ").title()

        return ScrapeResult(
            source=self.source,
            description_text=description_text,
            title=title,
            company_name=company_name,
            location=location,
            raw_payload=json.dumps(data),
            extras={"site": m["site"], "external_id": data.get("id", m["id"])},
        )
