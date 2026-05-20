from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CandidateProject(BaseModel):
    name: str
    description: str
    stack: list[str] = Field(default_factory=list)


class CandidateUpsert(BaseModel):
    """Idempotent upsert payload. All fields optional so partial updates work.

    Same shape is produced by resume parsing -- the frontend merges the parsed
    fields into this payload when the user clicks Apply.
    """

    summary: str | None = Field(default=None, max_length=3_000)
    years_experience: float | None = Field(default=None, ge=0, le=60)
    target_role: str | None = Field(default=None, max_length=160)
    skills: list[str] | None = Field(default=None, max_length=80)
    notable_projects: list[CandidateProject] | None = Field(default=None, max_length=10)
    resume_id: UUID | None = Field(
        default=None,
        description="Link to the parsed Resume row this profile was last derived from.",
    )


class CandidateResponse(BaseModel):
    id: UUID
    summary: str | None
    years_experience: float | None
    target_role: str | None
    skills: list[str] | None
    notable_projects: list[dict] | None
    resume_id: UUID | None
    updated_at: datetime
    created_at: datetime
