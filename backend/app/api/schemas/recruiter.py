from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ConfirmCompanyRequest(BaseModel):
    """Explicit user confirmation of the company target. Triggers recruiter discovery."""

    linkedin_slug: str = Field(min_length=1, max_length=120)
    name: str | None = None  # optional override if the inferred name was wrong


class RecruiterContact(BaseModel):
    kind: str
    value: str
    verified: bool
    source: str | None
    confidence: float | None


class RankedRecruiter(BaseModel):
    id: UUID
    full_name: str
    title: str | None
    linkedin_url: str | None
    location: str | None
    source: str | None
    score: float
    rationale: str
    contacts: list[RecruiterContact] = []
    enriched_at: datetime | None = None
    last_seen_at: datetime


class EnrichRecruiterResponse(BaseModel):
    recruiter_id: UUID
    enriched_at: datetime | None
    contacts: list[RecruiterContact]
