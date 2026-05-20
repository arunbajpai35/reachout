"""Outreach generation (DB-bound wrapper).

Delegates the actual LLM call to `outreach_generator.generate_outreach_variants`,
then persists each variant + runs the quality evaluator. Regeneration creates
new rows; nothing is overwritten.
"""
from __future__ import annotations

import hashlib
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.llm.base import LLMClient
from app.adapters.llm.prompts import (
    DEFAULT_TONE,
    OUTREACH_PROMPT_VERSION,
    build_outreach_user_prompt,
)
from app.config import get_settings
from app.core.errors import AppError, NotFoundError, ValidationError
from app.core.logging import log
from app.db.models import Candidate, Company, Job, Outreach, Recruiter
from app.domain.outreach.quality import QualityReport, evaluate_draft
from app.services.outreach_generator import generate_outreach_variants


class OutreachService:
    def __init__(self, session: AsyncSession, *, llm: LLMClient) -> None:
        self.session = session
        self.llm = llm

    async def generate(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
        recruiter_id: UUID,
        channels: list[str],
        tone: str = DEFAULT_TONE,
    ) -> list[tuple[Outreach, QualityReport]]:
        if not channels:
            raise ValidationError("at least one channel required")

        job = await self.session.get(Job, job_id)
        if job is None:
            raise NotFoundError(f"job {job_id} not found")
        if not job.parsed:
            raise AppError("job has not been extracted yet")

        recruiter = await self.session.get(Recruiter, recruiter_id)
        if recruiter is None:
            raise NotFoundError(f"recruiter {recruiter_id} not found")

        company = await self.session.get(Company, job.company_id) if job.company_id else None
        company_name = (company.name if company else None) or (
            (job.parsed or {}).get("company_name") or "the company"
        )

        candidate = await self.session.scalar(
            select(Candidate).where(Candidate.user_id == user_id)
        )
        candidate_ctx = _candidate_to_dict(candidate)
        recruiter_ctx = {
            "full_name": recruiter.full_name,
            "title": recruiter.title,
            "location": recruiter.location,
        }

        settings = get_settings()
        variants = await generate_outreach_variants(
            self.llm,
            candidate=candidate_ctx,
            job=job.parsed,
            company_name=company_name,
            recruiter=recruiter_ctx,
            channels=channels,
            tone=tone,
            model=settings.openai_model_outreach,
        )

        # Prompt hash is stamped per generation -- includes tone so identical
        # JD+candidate combos across tones produce distinguishable hashes.
        user_prompt = build_outreach_user_prompt(
            candidate=candidate_ctx,
            job=job.parsed,
            company_name=company_name,
            recruiter=recruiter_ctx,
            channels=channels,
        )
        prompt_hash = hashlib.sha256(
            f"{OUTREACH_PROMPT_VERSION}|{tone}|{user_prompt}".encode()
        ).hexdigest()[:16]

        produced: list[tuple[Outreach, QualityReport]] = []
        for v in variants:
            ch = v.get("channel")
            body = v.get("body") or ""
            subject = v.get("subject")
            quality = evaluate_draft(channel=ch, subject=subject, body=body)
            row = Outreach(
                job_id=job.id,
                recruiter_id=recruiter.id,
                channel=ch,
                subject=subject,
                body=body,
                status="draft",
                model=settings.openai_model_outreach,
                prompt_version=OUTREACH_PROMPT_VERSION,
                tone=tone,
                prompt_hash=prompt_hash,
            )
            self.session.add(row)
            produced.append((row, quality))

        await self.session.commit()
        for row, _ in produced:
            await self.session.refresh(row)
        log.info(
            "outreach.generated",
            job_id=str(job_id),
            recruiter_id=str(recruiter_id),
            channels=[r.channel for r, _ in produced],
            prompt_version=OUTREACH_PROMPT_VERSION,
            tone=tone,
            quality=[q.score for _, q in produced],
        )
        return produced

    async def get(self, outreach_id: UUID) -> Outreach:
        row = await self.session.get(Outreach, outreach_id)
        if row is None:
            raise NotFoundError(f"outreach {outreach_id} not found")
        return row

    async def regenerate(
        self, *, user_id: UUID, outreach_id: UUID, tone: str | None = None
    ) -> list[tuple[Outreach, QualityReport]]:
        original = await self.get(outreach_id)
        return await self.generate(
            user_id=user_id,
            job_id=original.job_id,
            recruiter_id=original.recruiter_id,
            channels=[original.channel],
            tone=tone or original.tone or DEFAULT_TONE,
        )

    async def list_for_pair(
        self, *, job_id: UUID, recruiter_id: UUID
    ) -> list[Outreach]:
        stmt = (
            select(Outreach)
            .where(Outreach.job_id == job_id, Outreach.recruiter_id == recruiter_id)
            .order_by(Outreach.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())


def _candidate_to_dict(c: Candidate | None) -> dict:
    if c is None:
        return {
            "summary": None,
            "years_experience": None,
            "target_role": None,
            "skills": [],
            "notable_projects": [],
        }
    return {
        "summary": c.summary,
        "years_experience": float(c.years_experience) if c.years_experience is not None else None,
        "target_role": c.target_role,
        "skills": c.skills or [],
        "notable_projects": c.notable_projects or [],
    }
