from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.schemas.recruiter import RankedRecruiter, RecruiterContact
from app.db.models import Contact, Job
from app.deps import SessionDep
from app.services.recruiter_service import RecruiterService

router = APIRouter(tags=["recruiters"])


@router.get("/jobs/{job_id}/recruiters", response_model=list[RankedRecruiter])
async def list_recruiters_for_job(job_id: UUID, session: SessionDep) -> list[RankedRecruiter]:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    # The provider here is irrelevant for read-only listing.
    service = RecruiterService(session, provider=None)  # type: ignore[arg-type]
    rows = await service.list_for_job(job_id)

    if not rows:
        return []

    # Fetch contacts in one query rather than N+1.
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
                last_seen_at=recruiter.last_seen_at,
                contacts=[
                    RecruiterContact(
                        kind=c.kind,
                        value=c.value,
                        verified=bool(c.verified),
                        source=c.source,
                        confidence=float(c.confidence) if c.confidence is not None else None,
                    )
                    for c in contacts_by_recruiter[recruiter.id]
                ],
            )
        )
    return out
