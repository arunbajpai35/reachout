"""Apify-backed recruiter discovery.

Calls a LinkedIn company-employees actor on Apify via direct REST API. We bypass
`apify-client` because its pydantic schema validation breaks on actors using the
newer pay-per-event pricing model (e.g. harvestapi/linkedin-company-employees).

NOT default in dev -- requires RECRUITER_PROVIDER=apify. Each call spins up an
Apify actor run; expect 30-90 seconds of wall time.

The actor id is configurable via APIFY_RECRUITER_ACTOR. Different actors return
slightly different JSON shapes; the parser below is defensive.
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.adapters.recruiter_providers.base import (
    RecruiterCandidate,
    RecruiterDiscoveryProvider,
)
from app.config import get_settings
from app.core.errors import UpstreamError
from app.core.logging import log

# Default actor: harvestapi's linkedin-company-employees. Pricing tier we send
# below; override via APIFY_RECRUITER_ACTOR if you prefer a different actor.
DEFAULT_ACTOR = "harvestapi/linkedin-company-employees"

# Pricing tier on harvestapi's actor. Cheapest variant. The actor expects the
# literal label, NOT a slug -- the price suffix is part of the enum value.
DEFAULT_SCRAPER_MODE = "Short ($4 per 1k)"

_API_BASE = "https://api.apify.com/v2"
_POLL_INTERVAL_SECS = 3.0
_RUN_TIMEOUT_SECS = 180


class ApifyRecruiterProvider(RecruiterDiscoveryProvider):
    name = "apify"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.apify_token:
            raise UpstreamError("APIFY_TOKEN missing in env")
        self._token = settings.apify_token
        self._actor_id = settings.apify_recruiter_actor or DEFAULT_ACTOR

    async def find_recruiters(
        self,
        *,
        company_linkedin_slug: str,
        company_name: str,
        limit: int = 25,
    ) -> list[RecruiterCandidate]:
        company_url = f"https://www.linkedin.com/company/{company_linkedin_slug}"
        run_input: dict[str, Any] = {
            "companies": [company_url],
            "profileScraperMode": DEFAULT_SCRAPER_MODE,
            "locations": ["India"],
            # Bias the upstream search toward recruiter-flavored titles so we
            # don't waste limit slots on random non-recruiter employees. Local
            # classifier still has final say on linking to the job.
            "jobTitles": [
                "recruiter",
                "talent acquisition",
                "technical recruiter",
                "engineering recruiter",
                "tag",
            ],
            "maxItems": limit,
            # Legacy / alternate-actor compatibility keys (harmless if ignored).
            "companyUrl": company_url,
            "companyUrls": [company_url],
            "company": company_linkedin_slug,
            "country": "India",
            "location": "India",
            "maxResults": limit,
        }

        log.info(
            "apify.recruiter_search.start",
            actor=self._actor_id,
            company=company_linkedin_slug,
            limit=limit,
        )

        # The actor id uses "owner/name"; Apify's REST API path uses "owner~name".
        actor_path = self._actor_id.replace("/", "~")
        headers = {"Authorization": f"Bearer {self._token}"}

        async with httpx.AsyncClient(
            base_url=_API_BASE, headers=headers, timeout=30.0
        ) as client:
            try:
                # 1. Start the run.
                r = await client.post(f"/acts/{actor_path}/runs", json=run_input)
                r.raise_for_status()
                run = r.json()["data"]
                run_id = run["id"]
                dataset_id = run["defaultDatasetId"]
                log.info("apify.run.started", run_id=run_id)

                # 2. Poll until terminal status.
                elapsed = 0.0
                while elapsed < _RUN_TIMEOUT_SECS:
                    await asyncio.sleep(_POLL_INTERVAL_SECS)
                    elapsed += _POLL_INTERVAL_SECS
                    r = await client.get(f"/actor-runs/{run_id}")
                    r.raise_for_status()
                    status = r.json()["data"]["status"]
                    if status == "SUCCEEDED":
                        break
                    if status in {"FAILED", "ABORTED", "TIMED-OUT"}:
                        raise UpstreamError(f"apify actor run ended with status={status}")
                else:
                    raise UpstreamError(
                        f"apify actor run timed out after {_RUN_TIMEOUT_SECS}s"
                    )

                # 3. Fetch the dataset items.
                r = await client.get(
                    f"/datasets/{dataset_id}/items",
                    params={"limit": str(limit * 2), "clean": "true"},
                )
                r.raise_for_status()
                items: list[dict[str, Any]] = r.json()
            except httpx.HTTPError as e:
                raise UpstreamError(f"apify call failed: {e}") from e

        log.info(
            "apify.recruiter_search.done",
            actor=self._actor_id,
            run_id=run_id,
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
        if not title:
            # harvestapi: title lives at currentPositions[0].title
            positions = it.get("currentPositions") or it.get("experience") or []
            if positions and isinstance(positions[0], dict):
                title = positions[0].get("title") or positions[0].get("position")
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
        # harvestapi returns location as {linkedinText: "..."}. Other actors return a flat string.
        if isinstance(location, dict):
            location = (
                location.get("linkedinText")
                or location.get("text")
                or location.get("name")
                or location.get("city")
            )
        if not name or not url:
            continue
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
