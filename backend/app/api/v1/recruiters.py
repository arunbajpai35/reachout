from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.adapters.contact_providers.router import get_contact_provider
from app.api.schemas.recruiter import (
    EnrichRecruiterResponse,
    RankedRecruiter,
    RecruiterContact,
)
from app.db.models import Contact, Job
from app.deps import SessionDep
from app.services.contact_service import ContactService
from app.services.recruiter_service import RecruiterService

router = APIRouter(tags=["recruiters"])


@router.get("/jobs/{job_id}/recruiters", response_model=list[RankedRecruiter])
async def list_recruiters_for_job(job_id: UUID, session: SessionDep) -> list[RankedRecruiter]:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    # Provider only matters for discovery; this is read-only.
    service = RecruiterService(session, provider=None)  # type: ignore[arg-type]
    rows = await service.list_for_job(job_id)

    if not rows:
        return []

    recruiter_ids = [r.id for r, _ in rows]
    contacts_by_recruiter: dict[UUID, list[Contact]] = {rid: [] for rid in recruiter_ids}
    contacts = (
        await session.execute(select(Contact).where(Contact.recruiter_id.in_(recruiter_ids)))
    ).scalars().all()
    for c in contacts:
        contacts_by_recruiter[c.recruiter_id].append(c)

    out: list[RankedRecruiter] = []
    for recruiter, job_recruiter in rows:
        out.append(
            RankedRecruiter(
                id=recruiter.id,
                full_name=recruiter.full_name,
                title=recruiter.title,
                linkedin_url=recruiter.linkedin_url,
                location=recruiter.location,
                source=recruiter.source,
                score=float(job_recruiter.score or 0.0),
                rationale=job_recruiter.rationale or "",
                enriched_at=recruiter.enriched_at,
                last_seen_at=recruiter.last_seen_at,
                contacts=[_to_contact(c) for c in contacts_by_recruiter[recruiter.id]],
            )
        )
    return out


@router.post(
    "/recruiters/{recruiter_id}/enrich",
    response_model=EnrichRecruiterResponse,
    status_code=200,
)
async def enrich_recruiter(
    recruiter_id: UUID, session: SessionDep
) -> EnrichRecruiterResponse:
    """Explicit user action: look up contact info for one recruiter.

    Provider chosen by CONTACT_PROVIDER env var; default mock. Burns one credit
    per call when set to contactout.
    """
    service = ContactService(session, provider=get_contact_provider())
    recruiter, contacts = await service.enrich_recruiter(recruiter_id)
    return EnrichRecruiterResponse(
        recruiter_id=recruiter.id,
        enriched_at=recruiter.enriched_at,
        contacts=[_to_contact(c) for c in contacts],
    )


def _to_contact(c: Contact) -> RecruiterContact:
    return RecruiterContact(
        kind=c.kind,
        value=c.value,
        verified=bool(c.verified),
        source=c.source,
        confidence=float(c.confidence) if c.confidence is not None else None,
    )
