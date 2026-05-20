from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.recruiter_providers.base import (
    RecruiterCandidate,
    RecruiterDiscoveryProvider,
)
from app.core.errors import AppError, NotFoundError
from app.core.logging import log
from app.db.models import Company, Job, JobRecruiter, Recruiter
from app.domain.recruiter.classifier import TitleCategory
from app.domain.recruiter.ranking import RankedCandidate, rank

# Minimum score required to link a recruiter to a job.
# Anything below is persisted globally (for future jobs) but hidden from this job's view.
LINK_THRESHOLD = 0.30


class RecruiterService:
    """Orchestrates: discover -> classify -> rank -> persist."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        provider: RecruiterDiscoveryProvider,
    ) -> None:
        self.session = session
        self.provider = provider

    async def find_for_job(self, job_id: UUID, *, limit: int = 25) -> int:
        """Discover and rank recruiters for the given job. Returns # linked to the job."""
        job = await self.session.get(Job, job_id)
        if job is None:
            raise NotFoundError(f"job {job_id} not found")
        if job.company_id is None:
            raise AppError("job has no company; confirm company first")
        company = await self.session.get(Company, job.company_id)
        if company is None or not company.linkedin_slug:
            raise AppError("company has no confirmed linkedin_slug; confirm first")

        try:
            candidates = await self.provider.find_recruiters(
                company_linkedin_slug=company.linkedin_slug,
                company_name=company.name,
                limit=limit,
            )
        except AppError:
            job.status = "failed"
            job.error = f"recruiter provider '{self.provider.name}' failed"
            await self.session.commit()
            raise

        log.info(
            "recruiters.discovered",
            job_id=str(job.id),
            provider=self.provider.name,
            count=len(candidates),
        )

        linked = 0
        for c in candidates:
            ranked = rank(title=c.title, location=c.location, job_parsed=job.parsed)
            recruiter = await self._upsert_recruiter(c, company_id=company.id)
            if ranked.score >= LINK_THRESHOLD and ranked.title_category != TitleCategory.UNRELATED:
                await self._link_to_job(job_id=job.id, recruiter_id=recruiter.id, ranked=ranked)
                linked += 1
            else:
                log.debug(
                    "recruiter.below_threshold",
                    name=c.full_name,
                    score=ranked.score,
                    rationale=ranked.rationale,
                )

        job.status = "recruiters_found"
        job.error = None
        await self.session.commit()
        log.info("recruiters.ranked", job_id=str(job.id), linked=linked, total=len(candidates))
        return linked

    async def _upsert_recruiter(
        self, c: RecruiterCandidate, *, company_id: UUID
    ) -> Recruiter:
        if c.linkedin_url:
            stmt = select(Recruiter).where(Recruiter.linkedin_url == c.linkedin_url)
            existing = await self.session.scalar(stmt)
        else:
            existing = None

        if existing is not None:
            # Refresh changeable fields; recruiters move teams.
            existing.title = c.title or existing.title
            existing.location = c.location or existing.location
            existing.company_id = company_id
            existing.source = c.source
            existing.source_payload = c.source_payload
            return existing

        recruiter = Recruiter(
            company_id=company_id,
            full_name=c.full_name,
            title=c.title,
            linkedin_url=c.linkedin_url,
            location=c.location,
            source=c.source,
            source_payload=c.source_payload,
        )
        self.session.add(recruiter)
        await self.session.flush()
        return recruiter

    async def _link_to_job(
        self, *, job_id: UUID, recruiter_id: UUID, ranked: RankedCandidate
    ) -> None:
        # Upsert via ON CONFLICT so re-running discovery refreshes scores in place.
        stmt = (
            pg_insert(JobRecruiter)
            .values(
                job_id=job_id,
                recruiter_id=recruiter_id,
                score=ranked.score,
                rationale=ranked.rationale,
            )
            .on_conflict_do_update(
                index_elements=[JobRecruiter.job_id, JobRecruiter.recruiter_id],
                set_={"score": ranked.score, "rationale": ranked.rationale},
            )
        )
        await self.session.execute(stmt)

    async def list_for_job(self, job_id: UUID) -> list[tuple[Recruiter, JobRecruiter]]:
        stmt = (
            select(Recruiter, JobRecruiter)
            .join(JobRecruiter, JobRecruiter.recruiter_id == Recruiter.id)
            .where(JobRecruiter.job_id == job_id)
            .order_by(JobRecruiter.score.desc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [(r, jr) for (r, jr) in rows]
