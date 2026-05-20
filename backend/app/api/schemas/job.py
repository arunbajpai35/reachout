from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, model_validator


class CreateJobRequest(BaseModel):
    """Either `url` or `text` must be provided. Not both."""

    url: HttpUrl | None = None
    text: str | None = Field(default=None, min_length=50, max_length=50_000)

    @model_validator(mode="after")
    def _exactly_one(self) -> "CreateJobRequest":
        if bool(self.url) == bool(self.text):
            raise ValueError("provide exactly one of `url` or `text`")
        return self


class JobCompany(BaseModel):
    id: UUID
    name: str
    linkedin_slug: str | None = None
    domain: str | None = None


class JobResponse(BaseModel):
    id: UUID
    source_url: str
    source: str | None
    title: str | None
    status: str
    error: str | None
    company: JobCompany | None = None
    company_slug_suggestion: str | None = Field(
        default=None,
        description=(
            "Heuristic linkedin slug suggestion derived from the company name. "
            "Present only while company.linkedin_slug is not yet confirmed."
        ),
    )
    parsed: dict[str, Any] | None = Field(
        default=None,
        description="Structured JD: {skills, yoe, location, work_mode, seniority, ...}",
    )
    created_at: datetime

    class Config:
        from_attributes = True
