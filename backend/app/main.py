from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.embeddings.openai_embeddings import OpenAIEmbeddings
from app.adapters.llm.openai_client import OpenAILLM
from app.adapters.recruiter_providers.router import get_recruiter_provider
from app.adapters.scrapers.router import ScraperRouter
from app.api.v1 import candidate, jobs, outreach, recruiters
from app.config import get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging, log


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    # Shared adapters live on app.state so BackgroundTasks can reuse them
    # without per-request construction.
    app.state.llm = OpenAILLM()
    app.state.embeddings = OpenAIEmbeddings()
    app.state.scraper_router = ScraperRouter()
    app.state.recruiter_provider = get_recruiter_provider()
    log.info(
        "app.start",
        env=settings.app_env,
        recruiter_provider=app.state.recruiter_provider.name,
    )
    yield
    log.info("app.stop")


def _cors_origins() -> list[str]:
    """Origins allowed by CORS. Local dev plus any extra hosts passed via env
    (comma-separated CORS_ORIGINS) so deployed frontends can be added without
    a code change."""
    settings = get_settings()
    defaults = ["http://localhost:5173", "http://localhost:3000"]
    extra = (settings.cors_origins or "").strip()
    if not extra:
        return defaults
    return defaults + [o.strip() for o in extra.split(",") if o.strip()]


def create_app() -> FastAPI:
    app = FastAPI(
        title="ReachOut API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(jobs.router, prefix="/api/v1")
    app.include_router(recruiters.router, prefix="/api/v1")
    app.include_router(candidate.router, prefix="/api/v1")
    app.include_router(outreach.router, prefix="/api/v1")

    @app.exception_handler(AppError)
    async def _app_error_handler(_, exc: AppError):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    return app


app = create_app()
