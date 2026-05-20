"""Hunter.io email-finder provider.

Hunter's email-finder takes (domain, first_name, last_name) and returns the
target's work email with a confidence score. Free tier: 50 searches/month.

Doc: https://hunter.io/api-documentation/v2#email-finder
"""
from __future__ import annotations

import re

import httpx

from app.adapters.contact_providers.base import (
    ContactEnrichmentProvider,
    EnrichedContact,
    EnrichmentResult,
)
from app.config import get_settings
from app.core.errors import UpstreamError
from app.core.logging import log
from app.core.retry import default_retry

_ENDPOINT = "https://api.hunter.io/v2/email-finder"


class HunterIoProvider(ContactEnrichmentProvider):
    name = "hunter"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.hunter_api_key:
            raise UpstreamError("HUNTER_API_KEY missing in env")
        self._api_key = settings.hunter_api_key

    async def enrich(
        self,
        *,
        linkedin_url: str | None,
        full_name: str,
        company_name: str | None,
        company_domain: str | None,
    ) -> EnrichmentResult:
        first, last = _split_name(full_name)
        if not first or not last:
            return EnrichmentResult()

        # Domain: prefer the explicit one, else guess from company name.
        # Guess pattern: lowercase + strip legal suffixes + ".com".
        domain = company_domain or _guess_domain(company_name)
        if not domain:
            log.info("hunter.skipped", reason="no domain", company=company_name)
            return EnrichmentResult()

        params = {
            "domain": domain,
            "first_name": first,
            "last_name": last,
            "api_key": self._api_key,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                async for attempt in default_retry(retry_on=(httpx.HTTPError,)):
                    with attempt:
                        r = await client.get(_ENDPOINT, params=params)
                        # Hunter returns 4xx with structured errors; treat 404 as "not found", not failure.
                        if r.status_code == 404:
                            return EnrichmentResult(raw_payload=r.json() if r.text else {})
                        r.raise_for_status()
                        data = r.json()
            except httpx.HTTPError as e:
                raise UpstreamError(f"hunter call failed: {e}") from e

        contact_data = (data.get("data") or {})
        email = contact_data.get("email")
        if not email:
            return EnrichmentResult(raw_payload=data)

        # Hunter "score" is 0-100; convert to 0-1.
        score = contact_data.get("score")
        confidence = (float(score) / 100.0) if isinstance(score, (int, float)) else None
        verified = contact_data.get("verification", {}).get("status") == "valid"

        return EnrichmentResult(
            contacts=[
                EnrichedContact(
                    kind="work_email",
                    value=email,
                    confidence=confidence,
                    verified=verified,
                    source=self.name,
                )
            ],
            raw_payload=data,
        )


# ---- helpers ----

_LEGAL_SUFFIXES = ("inc", "llc", "ltd", "limited", "pvt", "private", "corp", "holdings")


def _split_name(full_name: str) -> tuple[str, str]:
    parts = [p for p in re.split(r"\s+", full_name.strip()) if p]
    if len(parts) < 2:
        return (parts[0] if parts else "", "")
    # First token = first name, last token = last name. Drops middle names.
    return parts[0], parts[-1]


def _guess_domain(company_name: str | None) -> str | None:
    if not company_name:
        return None
    n = company_name.strip().lower()
    # Strip legal suffixes
    for suf in _LEGAL_SUFFIXES:
        if n.endswith(" " + suf) or n.endswith("." + suf):
            n = n[: -(len(suf) + 1)].rstrip(" ,.")
    # Keep alphanumerics only
    slug = re.sub(r"[^a-z0-9]+", "", n)
    if not slug:
        return None
    return f"{slug}.com"
