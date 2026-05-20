from uuid import UUID

from fastapi import APIRouter

from app.adapters.llm.openai_client import OpenAILLM
from app.api.schemas.outreach import (
    EvaluateOutreachRequest,
    EvaluateOutreachResponse,
    GenerateOutreachRequest,
    GenerateOutreachResponse,
    OutreachDraft,
    QualityReportModel,
)
from app.config import get_settings
from app.db.models import Outreach
from app.deps import SessionDep
from app.domain.outreach.quality import QualityReport, evaluate_draft
from app.services.outreach_service import OutreachService

router = APIRouter(prefix="/outreach", tags=["outreach"])

_llm = OpenAILLM()


def _to_draft(row: Outreach, quality: QualityReport | None = None) -> OutreachDraft:
    if quality is None:
        # On read paths we evaluate on the fly. Cheap (<1ms), no need to persist.
        quality = evaluate_draft(channel=row.channel, subject=row.subject, body=row.body)
    return OutreachDraft(
        id=row.id,
        job_id=row.job_id,
        recruiter_id=row.recruiter_id,
        channel=row.channel,  # type: ignore[arg-type]
        subject=row.subject,
        body=row.body,
        status=row.status,
        model=row.model,
        prompt_version=row.prompt_version,
        tone=row.tone,
        created_at=row.created_at,
        quality=QualityReportModel(**quality.to_dict()),
    )


@router.post("", response_model=GenerateOutreachResponse, status_code=201)
async def generate_outreach(
    payload: GenerateOutreachRequest, session: SessionDep
) -> GenerateOutreachResponse:
    service = OutreachService(session, llm=_llm)
    pairs = await service.generate(
        user_id=get_settings().dev_user_id,
        job_id=payload.job_id,
        recruiter_id=payload.recruiter_id,
        channels=list(payload.channels),
        tone=payload.tone,
    )
    return GenerateOutreachResponse(drafts=[_to_draft(row, q) for row, q in pairs])


@router.get("/{outreach_id}", response_model=OutreachDraft)
async def get_outreach(outreach_id: UUID, session: SessionDep) -> OutreachDraft:
    service = OutreachService(session, llm=_llm)
    return _to_draft(await service.get(outreach_id))


@router.post("/{outreach_id}/regenerate", response_model=GenerateOutreachResponse, status_code=201)
async def regenerate_outreach(
    outreach_id: UUID, session: SessionDep, tone: str | None = None
) -> GenerateOutreachResponse:
    service = OutreachService(session, llm=_llm)
    pairs = await service.regenerate(
        user_id=get_settings().dev_user_id, outreach_id=outreach_id, tone=tone
    )
    return GenerateOutreachResponse(drafts=[_to_draft(row, q) for row, q in pairs])


@router.get(
    "/by-pair/{job_id}/{recruiter_id}",
    response_model=list[OutreachDraft],
)
async def list_drafts_for_pair(
    job_id: UUID, recruiter_id: UUID, session: SessionDep
) -> list[OutreachDraft]:
    service = OutreachService(session, llm=_llm)
    rows = await service.list_for_pair(job_id=job_id, recruiter_id=recruiter_id)
    return [_to_draft(r) for r in rows]


@router.post("/evaluate", response_model=EvaluateOutreachResponse)
async def evaluate_outreach(payload: EvaluateOutreachRequest) -> EvaluateOutreachResponse:
    """Stateless quality evaluation. Used for ad-hoc inspection from the UI."""
    quality = evaluate_draft(channel=payload.channel, subject=payload.subject, body=payload.body)
    return EvaluateOutreachResponse(quality=QualityReportModel(**quality.to_dict()))
