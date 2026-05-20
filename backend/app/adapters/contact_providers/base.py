from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

ContactKind = Literal["work_email", "personal_email", "phone"]


@dataclass
class EnrichedContact:
    """One contact returned by an enrichment provider."""

    kind: ContactKind
    value: str
    confidence: float | None = None  # 0..1 if vendor supplies it
    verified: bool = False           # vendor-side verification, when available
    source: str = ""                 # provider name


@dataclass
class EnrichmentResult:
    contacts: list[EnrichedContact] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ContactEnrichmentProvider(Protocol):
    """Given a known recruiter (LinkedIn URL + name), return their work contact info.

    Implementations should be conservative: return what the vendor confidently has,
    never invent fallbacks like guessed @company.com addresses.
    """

    name: str

    async def enrich(
        self,
        *,
        linkedin_url: str | None,
        full_name: str,
        company_name: str | None,
        company_domain: str | None,
    ) -> EnrichmentResult:
        ...
