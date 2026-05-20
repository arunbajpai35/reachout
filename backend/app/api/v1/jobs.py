from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.schemas.job import CreateJobRequest, JobCompany, JobResponse
from app.api.schemas.recruiter import ConfirmCompanyRequest
from app.config import get_settings
from app.db.models import Company, Job
from app.deps import ArqDep, SessionDep
from app.domain.company import suggest_linkedin_slug

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(payload: CreateJobRequest, session: SessionDep, arq: ArqDep) -> JobResponse:
    """Accept a job URL OR pasted JD text, persist a pending row, enqueue extraction."""
    settings = get_settings()
    # For raw text input, `source_url` is the sentinel "text://" and the body
    # lives in `raw_html`. Keeps the URL column small + the worker self-routing.
    job = Job(
        user_id=settings.dev_user_id,
        source_url=str(payload.url) if payload.url else "text://",
        raw_html=payload.text if payload.text else None,
        status="pending",
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    await arq.enqueue_job("extract_job", str(job.id))
    return _to_response(job)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: UUID, session: SessionDep) -> JobResponse:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return _to_response(job)


@router.get("", response_model=list[JobResponse])
async def list_jobs(session: SessionDep, limit: int = 50) -> list[JobResponse]:
    settings = get_settings()
    stmt = (
        select(Job)
        .where(Job.user_id == settings.dev_user_id)
        .order_by(Job.created_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_response(j) for j in rows]


@router.patch("/{job_id}/company", response_model=JobResponse)
async def confirm_company(
    job_id: UUID,
    payload: ConfirmCompanyRequest,
    session: SessionDep,
    arq: ArqDep,
) -> JobResponse:
    """Confirm (or correct) the company's LinkedIn slug, then kick off recruiter discovery.

    This is the explicit user action that authorizes the system to spend recruiter-provider
    credits. Nothing happens automatically before this call.
    """
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.company_id is None:
        raise HTTPException(status_code=409, detail="job has no company yet (still extracting?)")
    if job.status not in {"extracted", "recruiters_found", "failed"}:
        # Allow re-confirmation after a previous run completed or failed.
        raise HTTPException(
            status_code=409,
            detail=f"job is in status '{job.status}'; cannot confirm company yet",
        )

    company = await session.get(Company, job.company_id)
    if company is None:
        raise HTTPException(status_code=500, detail="company row missing")

    company.linkedin_slug = payload.linkedin_slug.strip().lower()
    if payload.name:
        company.name = payload.name.strip()

    job.status = "recruiters_pending"
    job.error = None
    await session.commit()
    await session.refresh(job)

    await arq.enqueue_job("find_recruiters", str(job.id))
    return _to_response(job)


def _to_response(job: Job) -> JobResponse:
    company = (
        JobCompany(
            id=job.company.id,
            name=job.company.name,
            linkedin_slug=job.company.linkedin_slug,
            domain=job.company.domain,
        )
        if job.company
        else None
    )
    # Only emit the suggestion while the slug is still unconfirmed.
    slug_suggestion: str | None = None
    if company and not company.linkedin_slug:
        slug_suggestion = suggest_linkedin_slug(company.name)

    return JobResponse(
        id=job.id,
        source_url=job.source_url,
        source=job.source,
        title=job.title,
        status=job.status,
        error=job.error,
        parsed=job.parsed,
        created_at=job.created_at,
        company=company,
        company_slug_suggestion=slug_suggestion,
    )
