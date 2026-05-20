from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class RecruiterCandidate:
    """One candidate returned by a discovery provider. NOT yet ranked or persisted."""

    full_name: str
    title: str | None
    linkedin_url: str | None
    location: str | None
    company_name: str | None
    source: str                                # "mock" | "contactout"
    source_payload: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class RecruiterDiscoveryProvider(Protocol):
    """Interface every discovery provider implements. Stateless w.r.t. callers."""

    name: str

    async def find_recruiters(
        self,
        *,
        company_linkedin_slug: str,
        company_name: str,
        limit: int = 25,
    ) -> list[RecruiterCandidate]:
        """Return candidates. May return more than `limit` if vendor pagination overshoots."""
        ...
