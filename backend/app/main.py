from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import candidate, jobs, outreach, recruiters
from app.config import get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging, log


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    log.info("app.start", env=settings.app_env)
    yield
    log.info("app.stop")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Reverse Recruit API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
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
