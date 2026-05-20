from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

Channel = Literal["recruiter_email", "linkedin_dm", "networking_intro"]
DEFAULT_CHANNELS: list[Channel] = ["recruiter_email", "linkedin_dm", "networking_intro"]

Tone = Literal["concise", "technical", "warm", "founder-energy"]
DEFAULT_TONE: Tone = "concise"


class GenerateOutreachRequest(BaseModel):
    job_id: UUID
    recruiter_id: UUID
    channels: list[Channel] = Field(default_factory=lambda: list(DEFAULT_CHANNELS))
    tone: Tone = DEFAULT_TONE


class QualityViolation(BaseModel):
    rule: str
    detail: str
    severity: Literal["block", "warn"]


class QualityReportModel(BaseModel):
    channel: str
    word_count: int
    sentence_count: int
    avg_sentence_words: float
    max_sentence_words: int
    score: float
    violations: list[QualityViolation]


class OutreachDraft(BaseModel):
    id: UUID
    job_id: UUID
    recruiter_id: UUID
    channel: Channel
    subject: str | None
    body: str
    status: str
    model: str | None
    prompt_version: str | None
    tone: str | None
    created_at: datetime
    quality: QualityReportModel | None = None


class GenerateOutreachResponse(BaseModel):
    drafts: list[OutreachDraft]


class EvaluateOutreachRequest(BaseModel):
    channel: Channel
    subject: str | None = None
    body: str = Field(min_length=1)


class EvaluateOutreachResponse(BaseModel):
    quality: QualityReportModel
