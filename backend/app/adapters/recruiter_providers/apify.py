"""Apify-backed recruiter discovery.

Calls a LinkedIn company-employees actor on Apify and parses the items into our
RecruiterCandidate shape. NOT default in dev -- requires RECRUITER_PROVIDER=apify.
Each call spins up an Apify actor run; expect 30-90 seconds of wall time and
~$0.05-0.15 of Apify credit consumption depending on the actor and result count.

The actor id is configurable via APIFY_RECRUITER_ACTOR. Different actors return
slightly different JSON shapes; the parser below is defensive.
"""
from __future__ import annotations

from typing import Any

from apify_client import ApifyClientAsync

from app.adapters.recruiter_providers.base import (
    RecruiterCandidate,
    RecruiterDiscoveryProvider,
)
from app.config import get_settings
from app.core.errors import UpstreamError
from app.core.logging import log

# A reasonable default. Override via APIFY_RECRUITER_ACTOR if you prefer a
# different one or have a private actor.
DEFAULT_ACTOR = "apimaestro/linkedin-company-employees-scraper"

# Title keywords we ask the actor to filter on. The local classifier still has
# the final say -- this just biases the upstream search.
DEFAULT_KEYWORDS = "recruiter OR talent acquisition OR TAG OR engineering recruiter"


class ApifyRecruiterProvider(RecruiterDiscoveryProvider):
    name = "apify"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.apify_token:
            raise UpstreamError("APIFY_TOKEN missing in env")
        self._client = ApifyClientAsync(token=settings.apify_token)
        self._actor_id = settings.apify_recruiter_actor or DEFAULT_ACTOR

    async def find_recruiters(
        self,
        *,
        company_linkedin_slug: str,
        company_name: str,
        limit: int = 25,
    ) -> list[RecruiterCandidate]:
        # Most LinkedIn-employees actors accept either a company URL or slug.
        # We send both forms in the input so the actor can pick what it needs.
        company_url = f"https://www.linkedin.com/company/{company_linkedin_slug}"
        run_input: dict[str, Any] = {
            "companyUrl": company_url,
            "companyUrls": [company_url],
            "company": company_linkedin_slug,
            "keywords": DEFAULT_KEYWORDS,
            "country": "India",
            "location": "India",
            "maxResults": limit,
            "maxItems": limit,
        }

        log.info(
            "apify.recruiter_search.start",
            actor=self._actor_id,
            company=company_linkedin_slug,
            limit=limit,
        )

        try:
            run = await self._client.actor(self._actor_id).call(
                run_input=run_input,
                timeout_secs=180,
                wait_secs=180,
            )
        except Exception as e:
            raise UpstreamError(f"apify actor call failed: {e}") from e

        if not run or "defaultDatasetId" not in run:
            raise UpstreamError("apify run completed without a dataset")

        items: list[dict[str, Any]] = []
        async for item in self._client.dataset(run["defaultDatasetId"]).iterate_items():
            items.append(item)
            if len(items) >= limit * 2:  # generous, we filter locally below
                break

        log.info(
            "apify.recruiter_search.done",
            actor=self._actor_id,
            run_id=run.get("id"),
            items=len(items),
        )

        return _items_to_candidates(items, company_name=company_name)


def _items_to_candidates(items: list[dict], *, company_name: str) -> list[RecruiterCandidate]:
    """Map vendor JSON to our RecruiterCandidate shape. Tolerant of key drift."""
    out: list[RecruiterCandidate] = []
    seen_urls: set[str] = set()
    for it in items:
        name = (
            it.get("fullName")
            or it.get("name")
            or " ".join(filter(None, [it.get("firstName"), it.get("lastName")])).strip()
        )
        title = (
            it.get("headline")
            or it.get("title")
            or it.get("currentJobTitle")
            or it.get("jobTitle")
        )
        url = (
            it.get("profileUrl")
            or it.get("linkedinUrl")
            or it.get("url")
            or it.get("publicProfileUrl")
        )
        location = (
            it.get("location")
            or it.get("locationName")
            or it.get("city")
            or it.get("country")
            or it.get("addressWithCountry")
        )
        if not name or not url:
            continue
        # Dedupe within a single response by URL.
        url = str(url).split("?")[0]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        out.append(
            RecruiterCandidate(
                full_name=str(name).strip(),
                title=str(title).strip() if title else None,
                linkedin_url=url,
                location=str(location).strip() if location else None,
                company_name=company_name,
                source="apify",
                source_payload=it,
            )
        )
    return out
