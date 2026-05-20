from uuid import UUID

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel
from sqlalchemy import select

from app.adapters.llm.openai_client import OpenAILLM
from app.api.schemas.candidate import CandidateResponse, CandidateUpsert
from app.config import get_settings
from app.db.models import Candidate, Resume
from app.deps import SessionDep
from app.services.resume_service import ResumeService

router = APIRouter(prefix="/candidate", tags=["candidate"])

# Single shared LLM client (AsyncOpenAI manages its own connection pool).
_llm = OpenAILLM()


@router.get("", response_model=CandidateResponse | None)
async def get_candidate(session: SessionDep) -> CandidateResponse | None:
    user_id = get_settings().dev_user_id
    row = await session.scalar(select(Candidate).where(Candidate.user_id == user_id))
    if row is None:
        return None
    return _to_response(row)


@router.put("", response_model=CandidateResponse)
async def upsert_candidate(payload: CandidateUpsert, session: SessionDep) -> CandidateResponse:
    user_id = get_settings().dev_user_id
    row = await session.scalar(select(Candidate).where(Candidate.user_id == user_id))
    if row is None:
        row = Candidate(user_id=user_id)
        session.add(row)

    if payload.summary is not None:
        row.summary = payload.summary
    if payload.years_experience is not None:
        row.years_experience = payload.years_experience
    if payload.target_role is not None:
        row.target_role = payload.target_role
    if payload.skills is not None:
        row.skills = [s.strip() for s in payload.skills if s.strip()]
    if payload.notable_projects is not None:
        row.notable_projects = [p.model_dump() for p in payload.notable_projects]
    if payload.resume_id is not None:
        row.resume_id = payload.resume_id

    await session.commit()
    await session.refresh(row)
    return _to_response(row)


# ---------- Resume parsing ----------


class ParsedResumeFields(BaseModel):
    summary: str | None
    years_experience: float | None
    target_role: str | None
    skills: list[str]
    notable_projects: list[dict]
    extraction_notes: str


class ResumeParseResponse(BaseModel):
    resume_id: UUID
    filename: str
    raw_text_preview: str
    parsed: ParsedResumeFields


@router.post("/resume", response_model=ResumeParseResponse, status_code=201)
async def upload_resume(
    session: SessionDep,
    file: UploadFile = File(...),
) -> ResumeParseResponse:
    """Upload + parse a PDF resume. Does NOT mutate the candidate row.

    The frontend reviews the parsed fields, then calls PUT /candidate with the
    merged values + resume_id when the user clicks Apply.
    """
    user_id = get_settings().dev_user_id
    pdf_bytes = await file.read()

    service = ResumeService(session, llm=_llm)
    resume = await service.ingest(
        user_id=user_id,
        filename=file.filename or "resume.pdf",
        pdf_bytes=pdf_bytes,
    )
    return _resume_to_response(resume)


@router.get("/resume/{resume_id}", response_model=ResumeParseResponse)
async def get_parsed_resume(resume_id: UUID, session: SessionDep) -> ResumeParseResponse:
    service = ResumeService(session, llm=_llm)
    resume = await service.get(resume_id)
    return _resume_to_response(resume)


# ---------- Helpers ----------


def _to_response(row: Candidate) -> CandidateResponse:
    return CandidateResponse(
        id=row.id,
        summary=row.summary,
        years_experience=float(row.years_experience) if row.years_experience is not None else None,
        target_role=row.target_role,
        skills=row.skills,
        notable_projects=row.notable_projects,
        resume_id=row.resume_id,
        updated_at=row.updated_at,
        created_at=row.created_at,
    )


def _resume_to_response(resume: Resume) -> ResumeParseResponse:
    parsed = resume.parsed or {}
    raw = resume.raw_text or ""
    label = (resume.file_url or "").removeprefix("filename:") or "resume.pdf"
    return ResumeParseResponse(
        resume_id=resume.id,
        filename=label,
        raw_text_preview=raw[:1_000],  # for "show what we read" affordance in UI
        parsed=ParsedResumeFields(
            summary=parsed.get("summary"),
            years_experience=(
                float(parsed["years_experience"])
                if parsed.get("years_experience") is not None
                else None
            ),
            target_role=parsed.get("target_role"),
            skills=parsed.get("skills") or [],
            notable_projects=parsed.get("notable_projects") or [],
            extraction_notes=parsed.get("extraction_notes") or "",
        ),
    )
