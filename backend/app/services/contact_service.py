"""Contact enrichment orchestration.

One call per recruiter: provider lookup, dedupe, persist, stamp enriched_at.
Explicit user action only -- never auto-enriches during discovery.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.contact_providers.base import ContactEnrichmentProvider
from app.core.errors import NotFoundError
from app.core.logging import log
from app.db.models import Company, Contact, Recruiter


class ContactService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        provider: ContactEnrichmentProvider,
    ) -> None:
        self.session = session
        self.provider = provider

    async def enrich_recruiter(self, recruiter_id: UUID) -> tuple[Recruiter, list[Contact]]:
        recruiter = await self.session.get(Recruiter, recruiter_id)
        if recruiter is None:
            raise NotFoundError(f"recruiter {recruiter_id} not found")

        company = (
            await self.session.get(Company, recruiter.company_id)
            if recruiter.company_id
            else None
        )

        result = await self.provider.enrich(
            linkedin_url=recruiter.linkedin_url,
            full_name=recruiter.full_name,
            company_name=company.name if company else None,
            company_domain=company.domain if company else None,
        )

        # Persist new contacts. Unique constraint (recruiter_id, kind, value) handles dedupe.
        for c in result.contacts:
            stmt = (
                pg_insert(Contact)
                .values(
                    recruiter_id=recruiter.id,
                    kind=c.kind,
                    value=c.value,
                    confidence=c.confidence,
                    verified=c.verified,
                    source=c.source,
                )
                .on_conflict_do_nothing(
                    index_elements=["recruiter_id", "kind", "value"]
                )
            )
            await self.session.execute(stmt)

        # Always stamp enriched_at, even on empty results -- distinguishes "never tried"
        # from "tried, vendor had nothing".
        recruiter.enriched_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(recruiter)

        # Re-read contacts after upsert to return current set.
        rows = (
            await self.session.execute(
                select(Contact).where(Contact.recruiter_id == recruiter.id)
            )
        ).scalars().all()
        log.info(
            "recruiter.enriched",
            recruiter_id=str(recruiter.id),
            provider=self.provider.name,
            new=len(result.contacts),
            total=len(rows),
        )
        return recruiter, list(rows)
