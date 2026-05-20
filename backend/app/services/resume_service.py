"""Resume ingestion: PDF bytes -> text -> structured candidate fields.

The parsed result is staged on a Resume row but NOT merged into the Candidate
automatically. The frontend shows the parsed fields side-by-side with the
current Candidate row; the user clicks Apply to merge (via the existing
PUT /candidate endpoint).
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.llm.base import LLMClient
from app.adapters.llm.prompts import (
    RESUME_PARSE_PROMPT_VERSION,
    RESUME_PARSE_SCHEMA,
    RESUME_PARSE_SYSTEM,
    build_resume_user_prompt,
)
from app.adapters.pdf.pdf_extractor import extract_pdf_text
from app.core.errors import NotFoundError, ValidationError
from app.core.logging import log
from app.db.models import Resume
from app.domain.resume import compute_years_experience

# Cap on the text we send to the LLM. Resumes longer than this are rare and the
# tail is usually education/references. Saves tokens and avoids context-window
# games for now.
MAX_TEXT_CHARS = 20_000


class ResumeService:
    def __init__(self, session: AsyncSession, *, llm: LLMClient) -> None:
        self.session = session
        self.llm = llm

    async def ingest(
        self,
        *,
        user_id: UUID,
        filename: str,
        pdf_bytes: bytes,
    ) -> Resume:
        if not filename.lower().endswith(".pdf"):
            raise ValidationError("only PDF uploads are supported")
        if len(pdf_bytes) > 10 * 1024 * 1024:
            raise ValidationError("PDF exceeds 10 MB limit")

        text = extract_pdf_text(pdf_bytes)
        # Truncate from the end; resumes lead with the most important content.
        truncated = text[:MAX_TEXT_CHARS]

        parsed = await self.llm.complete_json(
            system=RESUME_PARSE_SYSTEM,
            user=build_resume_user_prompt(text=truncated),
            schema=RESUME_PARSE_SCHEMA,
            schema_name="resume_parse",
            temperature=0.0,
        )

        # Years of experience is computed in code from the structured `roles`
        # array, not extracted by the LLM. The model is bad at multi-step
        # arithmetic and reliably over- or under-counted on test resumes.
        years_experience = compute_years_experience(parsed.get("roles") or [])
        parsed["years_experience"] = years_experience

        resume = Resume(
            user_id=user_id,
            # We don't persist the file. file_url stores the original filename as a label.
            file_url=f"filename:{filename}",
            raw_text=truncated,
            parsed={**parsed, "_prompt_version": RESUME_PARSE_PROMPT_VERSION},
        )
        self.session.add(resume)
        await self.session.commit()
        await self.session.refresh(resume)
        log.info(
            "resume.parsed",
            resume_id=str(resume.id),
            filename=filename,
            text_chars=len(truncated),
            skills_count=len(parsed.get("skills") or []),
            projects_count=len(parsed.get("notable_projects") or []),
        )
        return resume

    async def get(self, resume_id: UUID) -> Resume:
        row = await self.session.get(Resume, resume_id)
        if row is None:
            raise NotFoundError(f"resume {resume_id} not found")
        return row
