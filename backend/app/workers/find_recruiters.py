from __future__ import annotations

from uuid import UUID

from app.adapters.recruiter_providers.router import get_recruiter_provider
from app.db.session import SessionLocal
from app.services.recruiter_service import RecruiterService


async def find_recruiters(ctx: dict, job_id: str) -> int:
    """Arq task: discover, classify, rank, and link recruiters for a job.

    Idempotent: re-reads job state, uses ON CONFLICT for linking.
    """
    provider = ctx.get("recruiter_provider") or get_recruiter_provider()
    async with SessionLocal() as session:
        service = RecruiterService(session, provider=provider)
        return await service.find_for_job(UUID(job_id))
