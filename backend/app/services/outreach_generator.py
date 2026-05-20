"""Pure outreach generation -- no DB, no Arq, no FastAPI.

Takes raw context dicts and an LLMClient, returns the model's variant list.
This is what the tuning script calls directly; the DB-aware OutreachService
wraps this with persistence and evaluation.
"""
from __future__ import annotations

from typing import Any

from app.adapters.llm.base import LLMClient
from app.adapters.llm.prompts import (
    OUTREACH_SCHEMA,
    build_outreach_user_prompt,
    outreach_system_prompt,
)


async def generate_outreach_variants(
    llm: LLMClient,
    *,
    candidate: dict,
    job: dict,
    company_name: str,
    recruiter: dict,
    channels: list[str],
    tone: str,
    model: str | None = None,
    temperature: float = 0.6,
) -> list[dict[str, Any]]:
    """Return the raw `variants` list from the model. Filtered to requested channels."""
    system = outreach_system_prompt(tone)
    user = build_outreach_user_prompt(
        candidate=candidate,
        job=job,
        company_name=company_name,
        recruiter=recruiter,
        channels=channels,
    )
    result = await llm.complete_json(
        system=system,
        user=user,
        schema=OUTREACH_SCHEMA,
        schema_name="outreach_variants",
        model=model,
        temperature=temperature,
    )
    requested = set(channels)
    return [v for v in result.get("variants", []) if v.get("channel") in requested]
