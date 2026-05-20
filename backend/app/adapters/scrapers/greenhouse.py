from __future__ import annotations

import json
import re
from html import unescape

import httpx
from bs4 import BeautifulSoup

from app.adapters.scrapers.base import JobScraper, ScrapeFailedError, ScrapeResult
from app.core.retry import default_retry

# Accepts:
#   https://boards.greenhouse.io/<token>/jobs/<id>
#   https://job-boards.greenhouse.io/<token>/jobs/<id>
_URL_RE = re.compile(
    r"^https?://(?:boards|job-boards)\.greenhouse\.io/(?P<token>[^/]+)/jobs/(?P<id>\d+)",
    re.IGNORECASE,
)

_API = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job_id}?content=true"


class GreenhouseScraper(JobScraper):
    source = "greenhouse"

    @classmethod
    def matches(cls, url: str) -> bool:
        return _URL_RE.match(url) is not None

    async def fetch(self, *, url: str | None = None, text: str | None = None) -> ScrapeResult:
        if not url:
            raise ScrapeFailedError("greenhouse scraper requires a URL")
        m = _URL_RE.match(url)
        if not m:
            raise ScrapeFailedError(f"not a greenhouse url: {url}")
        api = _API.format(token=m["token"], job_id=m["id"])

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            async for attempt in default_retry(retry_on=(httpx.HTTPError,)):
                with attempt:
                    r = await client.get(api, headers={"accept": "application/json"})
                    r.raise_for_status()
                    data = r.json()

        title = data.get("title")
        location = (data.get("location") or {}).get("name")
        content_html = data.get("content") or ""
        # Greenhouse returns description as escaped HTML inside the JSON string.
        description_text = _html_to_text(unescape(content_html))

        # company name lives at data["company_name"] on some boards, otherwise infer from token
        company_name = data.get("company_name") or m["token"].replace("-", " ").title()

        return ScrapeResult(
            source=self.source,
            description_text=description_text,
            title=title,
            company_name=company_name,
            location=location,
            raw_payload=json.dumps(data),
            extras={"board_token": m["token"], "external_id": str(data.get("id", m["id"]))},
        )


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    # Preserve paragraph and list breaks so the LLM sees structure.
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for block in soup.find_all(["p", "li", "h1", "h2", "h3", "h4", "div"]):
        block.append("\n")
    text = soup.get_text()
    # collapse triple-newlines, strip trailing spaces per line
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)
