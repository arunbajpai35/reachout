"""One-shot DB bootstrap for MVP: enable pgvector, create tables, seed dev user.

This intentionally uses SQLAlchemy's create_all instead of Alembic.
Alembic gets wired up in Phase 2 once the schema settles.
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select, text

from app.config import get_settings
from app.db.models import Base, User
from app.db.session import SessionLocal, engine


async def main() -> None:
    settings = get_settings()

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        # Slice-4 forward-compat ALTER for tables that existed before columns were added.
        # Idempotent. Alembic will own this once we adopt it.
        await conn.execute(
            text("ALTER TABLE outreach ADD COLUMN IF NOT EXISTS prompt_version TEXT")
        )
        await conn.execute(
            text("ALTER TABLE outreach ADD COLUMN IF NOT EXISTS tone TEXT")
        )
        await conn.execute(
            text("ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ")
        )

    async with SessionLocal() as session:
        existing = await session.scalar(select(User).where(User.id == settings.dev_user_id))
        if existing is None:
            session.add(User(id=settings.dev_user_id, email=settings.dev_user_email))
            await session.commit()
            print(f"seeded dev user {settings.dev_user_email}")
        else:
            print("dev user already present")

    print("bootstrap complete")


if __name__ == "__main__":
    asyncio.run(main())
