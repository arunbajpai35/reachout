"""Arq worker settings. Run with:  arq app.workers.arq_app.WorkerSettings"""
from __future__ import annotations

from arq.connections import RedisSettings

from app.adapters.embeddings.openai_embeddings import OpenAIEmbeddings
from app.adapters.llm.openai_client import OpenAILLM
from app.adapters.recruiter_providers.router import get_recruiter_provider
from app.adapters.scrapers.router import ScraperRouter
from app.config import get_settings
from app.core.logging import configure_logging, log
from app.workers.extract_job import extract_job
from app.workers.find_recruiters import find_recruiters


async def startup(ctx: dict) -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    ctx["llm"] = OpenAILLM()
    ctx["embeddings"] = OpenAIEmbeddings()
    ctx["router"] = ScraperRouter()
    ctx["recruiter_provider"] = get_recruiter_provider()
    log.info("worker.start", recruiter_provider=ctx["recruiter_provider"].name)


async def shutdown(ctx: dict) -> None:
    log.info("worker.stop")


class WorkerSettings:
    functions = [extract_job, find_recruiters]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 8
    job_timeout = 120  # seconds; scrape + LLM round-trip should finish well inside this
    keep_result = 3600
