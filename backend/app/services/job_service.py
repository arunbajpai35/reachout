from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.embeddings.openai_embeddings import OpenAIEmbeddings
from app.adapters.llm.base import LLMClient
from app.adapters.llm.prompts import (
    EXTRACT_JOB_SCHEMA,
    EXTRACT_JOB_SYSTEM,
    build_extract_user_prompt,
)
from app.adapters.scrapers.base import ScrapeResult, UnsupportedSourceError
from app.adapters.scrapers.router import ScraperRouter
from app.core.errors import AppError, NotFoundError
from app.core.logging import log
from app.db.models import Company, Job


class JobService:
    """Owns the URL/text -> structured job pipeline.

    Single public entry point: `extract(job_id)`. Worker calls this.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        llm: LLMClient,
        embeddings: OpenAIEmbeddings,
        router: ScraperRouter,
    ) -> None:
        self.session = session
        self.llm = llm
        self.embeddings = embeddings
        self.router = router

    async def extract(self, job_id: UUID) -> None:
        job = await self.session.get(Job, job_id)
        if job is None:
            raise NotFoundError(f"job {job_id} not found")

        try:
            scrape = await self._scrape(job)
            parsed = await self._normalize(scrape)
            company = await self._upsert_company(
                name=parsed.get("company_name") or scrape.company_name or "Unknown",
                domain=scrape.company_domain,
            )

            embed_text = _build_embed_text(parsed)
            embedding = await self.embeddings.embed(embed_text)

            job.source = scrape.source
            job.title = parsed.get("title") or scrape.title
            job.raw_html = scrape.raw_payload
            job.parsed = parsed
            job.embedding = embedding
            job.company_id = company.id
            job.status = "extracted"
            job.error = None
            await self.session.commit()
            log.info("job.extracted", job_id=str(job.id), source=scrape.source, title=job.title)

        except UnsupportedSourceError as e:
            job.status = "failed"
            job.error = e.message
            await self.session.commit()
            log.warning("job.unsupported", job_id=str(job.id), reason=e.message)
            raise
        except AppError as e:
            job.status = "failed"
            job.error = e.message
            await self.session.commit()
            log.error("job.failed", job_id=str(job.id), reason=e.message)
            raise
        except Exception as e:
            job.status = "failed"
            job.error = f"unexpected: {e}"
            await self.session.commit()
            log.exception("job.failed_unexpected", job_id=str(job.id))
            raise

    async def _scrape(self, job: Job) -> ScrapeResult:
        # Convention: source_url == "text://" means the body lives in job.raw_html.
        if job.source_url.startswith("text://"):
            return await self.router.for_text().fetch(text=job.raw_html or "")
        scraper = self.router.for_url(job.source_url)
        return await scraper.fetch(url=job.source_url)

    async def _normalize(self, scrape: ScrapeResult) -> dict:
        user_prompt = build_extract_user_prompt(
            hint_title=scrape.title,
            hint_company=scrape.company_name,
            body=scrape.description_text,
        )
        return await self.llm.complete_json(
            system=EXTRACT_JOB_SYSTEM,
            user=user_prompt,
            schema=EXTRACT_JOB_SCHEMA,
            schema_name="extract_job",
        )

    async def _upsert_company(self, *, name: str, domain: str | None) -> Company:
        # Match by lowercased name for MVP. Domain/linkedin_slug filled in later by enrichment.
        stmt = select(Company).where(func.lower(Company.name) == name.lower()).limit(1)
        existing = await self.session.scalar(stmt)
        if existing is not None:
            if domain and not existing.domain:
                existing.domain = domain
            return existing
        company = Company(name=name, domain=domain)
        self.session.add(company)
        await self.session.flush()  # populate id without committing
        return company


def _build_embed_text(parsed: dict) -> str:
    """Build a compact, retrieval-friendly representation of the JD."""
    parts: list[str] = []
    if title := parsed.get("title"):
        parts.append(f"Title: {title}")
    if (sen := parsed.get("seniority")) and sen != "unknown":
        parts.append(f"Seniority: {sen}")
    if (yoe_min := parsed.get("yoe_min")) is not None:
        yoe_max = parsed.get("yoe_max")
        parts.append(f"YoE: {yoe_min}+" if yoe_max is None else f"YoE: {yoe_min}-{yoe_max}")
    if skills := parsed.get("skills"):
        parts.append("Skills: " + ", ".join(skills))
    if stack := parsed.get("tech_stack"):
        parts.append("Stack: " + ", ".join(stack))
    if resp := parsed.get("responsibilities"):
        parts.append("Responsibilities: " + "; ".join(resp))
    return "\n".join(parts)
