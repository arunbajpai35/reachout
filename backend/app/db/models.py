from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

EMBED_DIM = 1536  # text-embedding-3-small


class Base(DeclarativeBase):
    pass


def _pk() -> Mapped[UUID]:
    return mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)


def _ts() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = _pk()
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[datetime] = _ts()


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[UUID] = _pk()
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text)
    parsed: Mapped[dict | None] = mapped_column(JSONB)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBED_DIM))
    created_at: Mapped[datetime] = _ts()


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[UUID] = _pk()
    name: Mapped[str] = mapped_column(String, nullable=False)
    linkedin_slug: Mapped[str | None] = mapped_column(String, unique=True)
    domain: Mapped[str | None] = mapped_column(String)
    company_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = _ts()


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[UUID] = _pk()
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String)
    company_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id")
    )
    title: Mapped[str | None] = mapped_column(String)
    raw_html: Mapped[str | None] = mapped_column(Text)
    parsed: Mapped[dict | None] = mapped_column(JSONB)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBED_DIM))
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts()

    company: Mapped[Company | None] = relationship("Company", lazy="joined")


class Recruiter(Base):
    __tablename__ = "recruiters"

    id: Mapped[UUID] = _pk()
    company_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id")
    )
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(String)
    linkedin_url: Mapped[str | None] = mapped_column(String, unique=True)
    location: Mapped[str | None] = mapped_column(String)
    seniority: Mapped[str | None] = mapped_column(String)
    source: Mapped[str | None] = mapped_column(String)
    source_payload: Mapped[dict | None] = mapped_column(JSONB)
    last_seen_at: Mapped[datetime] = _ts()


class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = (UniqueConstraint("recruiter_id", "kind", "value"),)

    id: Mapped[UUID] = _pk()
    recruiter_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("recruiters.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric)
    verified: Mapped[bool] = mapped_column(default=False)
    source: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = _ts()


class JobRecruiter(Base):
    __tablename__ = "job_recruiters"

    job_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    recruiter_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("recruiters.id", ondelete="CASCADE"),
        primary_key=True,
    )
    score: Mapped[float | None] = mapped_column(Numeric)
    rationale: Mapped[str | None] = mapped_column(Text)


class Outreach(Base):
    __tablename__ = "outreach"

    id: Mapped[UUID] = _pk()
    job_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE")
    )
    recruiter_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("recruiters.id", ondelete="CASCADE")
    )
    channel: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="draft", nullable=False)
    model: Mapped[str | None] = mapped_column(String)
    prompt_version: Mapped[str | None] = mapped_column(String)
    tone: Mapped[str | None] = mapped_column(String)
    prompt_hash: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = _ts()


class Candidate(Base):
    """The candidate context fed into outreach generation.

    Single row per user for MVP. Populated by hand now (PUT /candidate);
    resume parsing in a later slice writes to the same shape.
    """

    __tablename__ = "candidates"

    id: Mapped[UUID] = _pk()
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    summary: Mapped[str | None] = mapped_column(Text)
    years_experience: Mapped[float | None] = mapped_column(Numeric)
    target_role: Mapped[str | None] = mapped_column(String)
    skills: Mapped[list[str] | None] = mapped_column(JSONB)
    notable_projects: Mapped[list[dict] | None] = mapped_column(JSONB)
    resume_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = _ts()
