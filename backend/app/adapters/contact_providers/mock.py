"""Deterministic mock enrichment for dev. No vendor calls, no spend.

Generates a plausible work_email from the recruiter's name + company slug.
Half the time also returns a phone number so the UI can render the multi-contact case.
"""
from __future__ import annotations

import hashlib
import re

from app.adapters.contact_providers.base import (
    ContactEnrichmentProvider,
    EnrichedContact,
    EnrichmentResult,
)


def _slugify_name(name: str) -> str:
    n = name.strip().lower()
    n = re.sub(r"[^a-z0-9]+", ".", n).strip(".")
    return n


def _company_domain(name: str | None) -> str:
    if not name:
        return "example.com"
    n = name.strip().lower()
    n = re.sub(r"\b(inc|llc|ltd|limited|pvt|private)\b\.?", "", n)
    n = re.sub(r"[^a-z0-9]+", "", n).strip()
    return f"{n or 'example'}.com"


class MockEnrichmentProvider(ContactEnrichmentProvider):
    name = "mock"

    async def enrich(
        self,
        *,
        linkedin_url: str | None,
        full_name: str,
        company_name: str | None,
        company_domain: str | None,
    ) -> EnrichmentResult:
        domain = company_domain or _company_domain(company_name)
        email = f"{_slugify_name(full_name)}@{domain}"
        contacts: list[EnrichedContact] = [
            EnrichedContact(
                kind="work_email",
                value=email,
                confidence=0.85,
                verified=False,
                source=self.name,
            )
        ]
        # Deterministic 50/50 phone availability so the UI sees both paths.
        seed = int(hashlib.sha256(full_name.encode()).hexdigest(), 16)
        if seed % 2 == 0:
            contacts.append(
                EnrichedContact(
                    kind="phone",
                    value=f"+91-9{seed % 1_000_000_000:09d}"[:15],
                    confidence=0.6,
                    verified=False,
                    source=self.name,
                )
            )
        return EnrichmentResult(contacts=contacts, raw_payload={"mock": True})
