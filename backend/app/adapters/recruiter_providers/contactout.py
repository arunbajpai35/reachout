"""ContactOut discovery provider.

Implements the people-search endpoint. NOT the default in dev -- callers must
opt in via RECRUITER_PROVIDER=contactout. This is intentional: ContactOut
charges per query, and we want every credit consumed to be a deliberate action.

API reference (paraphrased; verify against current docs before going live):
  POST https://api.contactout.com/v1/people/search
  Headers: { "token": <api_key>, "authorization": "Basic ...", "content-type": "application/json" }
  Body  : { company: [slug], current_title: [...], country: ["India"], page: 1 }
"""
from __future__ import annotations

import httpx

from app.adapters.recruiter_providers.base import RecruiterCandidate, RecruiterDiscoveryProvider
from app.config import get_settings
from app.core.errors import UpstreamError
from app.core.retry import default_retry

_ENDPOINT = "https://api.contactout.com/v1/people/search"

# We bias the title filter toward recruiter roles. Final filtering is still done
# by our local classifier so untouched-by-us provider drift can't silently
# include "Compensation Analyst".
_TITLE_FILTERS = [
    "recruiter",
    "talent acquisition",
    "technical recruiter",
    "engineering recruiter",
    "tag",
]


class ContactOutProvider(RecruiterDiscoveryProvider):
    name = "contactout"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.contactout_api_key:
            raise UpstreamError("CONTACTOUT_API_KEY missing in env")
        self._api_key = settings.contactout_api_key

    async def find_recruiters(
        self,
        *,
        company_linkedin_slug: str,
        company_name: str,
        limit: int = 25,
    ) -> list[RecruiterCandidate]:
        body = {
            "company": [company_linkedin_slug],
            "current_title": _TITLE_FILTERS,
            "country": ["India"],
            "page": 1,
            # ContactOut returns ~25/page; we don't auto-paginate in MVP.
        }
        headers = {
            "token": self._api_key,
            "accept": "application/json",
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                async for attempt in default_retry(retry_on=(httpx.HTTPError,)):
                    with attempt:
                        r = await client.post(_ENDPOINT, headers=headers, json=body)
                        r.raise_for_status()
                        data = r.json()
            except httpx.HTTPError as e:
                raise UpstreamError(f"contactout call failed: {e}") from e

        # Defensive shape handling -- vendor JSON keys vary across plans.
        profiles = data.get("profiles") or data.get("results") or data.get("data") or []
        out: list[RecruiterCandidate] = []
        for p in profiles[:limit]:
            out.append(
                RecruiterCandidate(
                    full_name=p.get("full_name") or p.get("name") or "",
                    title=p.get("title") or p.get("current_title"),
                    linkedin_url=p.get("linkedin_url") or p.get("li_url"),
                    location=p.get("location") or p.get("country"),
                    company_name=company_name,
                    source=self.name,
                    source_payload=p,
                )
            )
        return out
