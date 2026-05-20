"""In-process background tasks (FastAPI BackgroundTasks) — replaces the Arq worker
when deploying as a single service.

Each function does the same work as the corresponding `app/workers/*.py` task,
but takes the shared adapters as explicit kwargs (populated from `app.state` at
the call site) instead of reading them from an Arq worker context.

Failure handling: any exception is logged with the job_id and structured detail.
We do NOT re-raise — BackgroundTasks runs after the response is sent, so raising
would just go to the unhandled-task log and the client already has a 201. The
service code itself sets `job.status = 'failed'` and writes `job.error`.
"""
from __future__ import annotations

from uuid import UUID

from app.adapters.contact_providers.base import ContactEnrichmentProvider
from app.adapters.embeddings.openai_embeddings import OpenAIEmbeddings
from app.adapters.llm.base import LLMClient
from app.adapters.recruiter_providers.base import RecruiterDiscoveryProvider
from app.adapters.scrapers.router import ScraperRouter
from app.core.logging import log
from app.db.session import SessionLocal
from app.services.contact_service import ContactService
from app.services.job_service import JobService
from app.services.recruiter_service import RecruiterService


async def run_extract_job(
    job_id: UUID,
    *,
    llm: LLMClient,
    embeddings: OpenAIEmbeddings,
    scraper_router: ScraperRouter,
) -> None:
    try:
        async with SessionLocal() as session:
            await JobService(
                session, llm=llm, embeddings=embeddings, router=scraper_router
            ).extract(job_id)
    except Exception:
        log.exception("bg.extract_job.failed", job_id=str(job_id))


async def run_find_recruiters(
    job_id: UUID,
    *,
    provider: RecruiterDiscoveryProvider,
) -> None:
    try:
        async with SessionLocal() as session:
            await RecruiterService(session, provider=provider).find_for_job(job_id)
    except Exception:
        log.exception("bg.find_recruiters.failed", job_id=str(job_id))


async def run_enrich_recruiter(
    recruiter_id: UUID,
    *,
    provider: ContactEnrichmentProvider,
) -> None:
    """Currently unused -- contact enrichment is synchronous from the API. Kept here
    in case we want to bulk-enrich in a background task later."""
    try:
        async with SessionLocal() as session:
            await ContactService(session, provider=provider).enrich_recruiter(recruiter_id)
    except Exception:
        log.exception("bg.enrich_recruiter.failed", recruiter_id=str(recruiter_id))
