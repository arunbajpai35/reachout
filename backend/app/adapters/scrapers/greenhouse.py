from __future__ import annotations

import json
import re
from html import unescape

import httpx
from bs4 import BeautifulSoup

from app.adapters.scrapers.base import JobScraper, ScrapeFailedError, ScrapeResult
from app.core.retry import default_retry

# Direct Greenhouse-hosted board URLs:
#   https://boards.greenhouse.io/<token>/jobs/<id>
#   https://job-boards.greenhouse.io/<token>/jobs/<id>
_URL_RE = re.compile(
    r"^https?://(?:boards|job-boards)\.greenhouse\.io/(?P<token>[^/]+)/jobs/(?P<id>\d+)",
    re.IGNORECASE,
)

# Company career pages that embed Greenhouse and pass the job id via query param.
# Example: https://www.skillz.com/careers/list/?gh_jid=7261035&gh_src=...
_EMBED_JID_RE = re.compile(r"[?&]gh_jid=(?P<id>\d+)", re.IGNORECASE)

# On the embed page, the board token usually appears as `for=<token>` inside the
# Greenhouse iframe URL or boostrap script.
_BOARD_TOKEN_RE = re.compile(r"\bfor=([a-z0-9_-]+)", re.IGNORECASE)

_API = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job_id}?content=true"

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class GreenhouseScraper(JobScraper):
    source = "greenhouse"

    @classmethod
    def matches(cls, url: str) -> bool:
        return bool(_URL_RE.match(url) or _EMBED_JID_RE.search(url))

    async def fetch(self, *, url: str | None = None, text: str | None = None) -> ScrapeResult:
        if not url:
            raise ScrapeFailedError("greenhouse scraper requires a URL")

        m = _URL_RE.match(url)
        if m:
            return await self._fetch_by_token(m["token"], m["id"])

        em = _EMBED_JID_RE.search(url)
        if em:
            token = await self._resolve_token_from_page(url)
            return await self._fetch_by_token(token, em["id"])

        raise ScrapeFailedError(f"not a greenhouse url: {url}")

    async def _resolve_token_from_page(self, page_url: str) -> str:
        """Fetch a company embed page and pull out the Greenhouse board token."""
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                async for attempt in default_retry(retry_on=(httpx.HTTPError,)):
                    with attempt:
                        r = await client.get(page_url, headers={"user-agent": _BROWSER_UA})
                        r.raise_for_status()
                        html = r.text
            except httpx.HTTPError as e:
                raise ScrapeFailedError(f"failed to fetch company embed page: {e}") from e

        match = _BOARD_TOKEN_RE.search(html)
        if not match:
            raise ScrapeFailedError(
                "Could not detect the Greenhouse board token on the company page. "
                "Try the canonical boards.greenhouse.io URL or paste the JD text."
            )
        return match.group(1)

    async def _fetch_by_token(self, token: str, job_id: str) -> ScrapeResult:
        api = _API.format(token=token, job_id=job_id)
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            async for attempt in default_retry(retry_on=(httpx.HTTPError,)):
                with attempt:
                    r = await client.get(api, headers={"accept": "application/json"})
                    r.raise_for_status()
                    data = r.json()

        title = data.get("title")
        location = (data.get("location") or {}).get("name")
        content_html = data.get("content") or ""
        description_text = _html_to_text(unescape(content_html))
        company_name = data.get("company_name") or token.replace("-", " ").title()

        return ScrapeResult(
            source=self.source,
            description_text=description_text,
            title=title,
            company_name=company_name,
            location=location,
            raw_payload=json.dumps(data),
            extras={"board_token": token, "external_id": str(data.get("id", job_id))},
        )


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for block in soup.find_all(["p", "li", "h1", "h2", "h3", "h4", "div"]):
        block.append("\n")
    text = soup.get_text()
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)
