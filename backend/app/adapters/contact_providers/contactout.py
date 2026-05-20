"""ContactOut enrichment provider.

Uses ContactOut's "people by linkedin url" endpoint to fetch verified contact
info for a known LinkedIn profile. NOT the default in dev -- requires
`CONTACT_PROVIDER=contactout` to opt in. Every call burns a credit.

API surface paraphrased; verify against current docs before going live:
  POST https://api.contactout.com/v1/people/linkedin
  Headers: { token: <key>, accept: application/json, content-type: application/json }
  Body  : { linkedin_url: <url>, include_phone: true }
  Response keys vary by plan -- the parser is defensive.
"""
from __future__ import annotations

import httpx

from app.adapters.contact_providers.base import (
    ContactEnrichmentProvider,
    EnrichedContact,
    EnrichmentResult,
)
from app.config import get_settings
from app.core.errors import UpstreamError
from app.core.retry import default_retry

_ENDPOINT = "https://api.contactout.com/v1/people/linkedin"


class ContactOutEnrichmentProvider(ContactEnrichmentProvider):
    name = "contactout"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.contactout_api_key:
            raise UpstreamError("CONTACTOUT_API_KEY missing in env")
        self._api_key = settings.contactout_api_key

    async def enrich(
        self,
        *,
        linkedin_url: str | None,
        full_name: str,
        company_name: str | None,
        company_domain: str | None,
    ) -> EnrichmentResult:
        if not linkedin_url:
            # Without a LinkedIn URL there's nothing to look up by.
            return EnrichmentResult()

        body = {"linkedin_url": linkedin_url, "include_phone": True}
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
                raise UpstreamError(f"contactout enrichment failed: {e}") from e

        return EnrichmentResult(contacts=_extract_contacts(data), raw_payload=data)


def _extract_contacts(data: dict) -> list[EnrichedContact]:
    """Map vendor JSON to our shape. Tolerant of plan-to-plan key variation."""
    contacts: list[EnrichedContact] = []
    profile = data.get("profile") or data.get("data") or data

    work_emails = profile.get("work_emails") or profile.get("work_email") or []
    if isinstance(work_emails, str):
        work_emails = [work_emails]
    for em in work_emails:
        if isinstance(em, dict):
            value = em.get("value") or em.get("email")
            verified = bool(em.get("verified"))
            confidence = em.get("confidence")
        else:
            value, verified, confidence = em, False, None
        if value:
            contacts.append(
                EnrichedContact(
                    kind="work_email",
                    value=str(value),
                    verified=verified,
                    confidence=float(confidence) if confidence is not None else None,
                    source="contactout",
                )
            )

    personal_emails = profile.get("personal_emails") or profile.get("personal_email") or []
    if isinstance(personal_emails, str):
        personal_emails = [personal_emails]
    for em in personal_emails:
        value = em.get("value") if isinstance(em, dict) else em
        if value:
            contacts.append(
                EnrichedContact(
                    kind="personal_email",
                    value=str(value),
                    source="contactout",
                )
            )

    phones = profile.get("phones") or profile.get("phone") or []
    if isinstance(phones, str):
        phones = [phones]
    for ph in phones:
        value = ph.get("value") if isinstance(ph, dict) else ph
        if value:
            contacts.append(
                EnrichedContact(kind="phone", value=str(value), source="contactout")
            )

    return contacts
