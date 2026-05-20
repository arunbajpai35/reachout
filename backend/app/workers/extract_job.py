from __future__ import annotations

from uuid import UUID

from app.db.session import SessionLocal
from app.services.job_service import JobService


async def extract_job(ctx: dict, job_id: str) -> None:
    """Arq task: pull a pending job through the scrape -> normalize -> embed pipeline.

    Idempotent: re-reads the DB row each time, so retries are safe.
    """
    async with SessionLocal() as session:
        service = JobService(
            session,
            llm=ctx["llm"],
            embeddings=ctx["embeddings"],
            router=ctx["router"],
        )
        await service.extract(UUID(job_id))
