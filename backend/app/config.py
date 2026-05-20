from functools import lru_cache
from uuid import UUID

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # DB
    database_url: str

    # Redis
    redis_url: str

    # OpenAI (direct) -- optional if Azure is configured.
    openai_api_key: str | None = None
    openai_model_extract: str = "gpt-4o-2024-11-20"
    openai_model_outreach: str = "gpt-4o-2024-11-20"
    openai_embed_model: str = "text-embedding-3-small"

    # Azure OpenAI -- if these are set, they take precedence over direct OpenAI.
    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_api_version: str = "2025-01-01-preview"
    azure_openai_deployment_chat: str | None = None
    azure_openai_deployment_embed: str | None = None

    @property
    def use_azure(self) -> bool:
        return bool(
            self.azure_openai_api_key
            and self.azure_openai_endpoint
            and self.azure_openai_deployment_chat
        )

    # Vendors
    apify_token: str | None = None
    contactout_api_key: str | None = None
    hunter_api_key: str | None = None

    # Discovery provider switch: "mock" (default, free) | "contactout" (paid) | "apify" (paid)
    recruiter_provider: str = "mock"
    recruiter_limit: int = 25
    # Optional override for which Apify actor to use; default is set in the adapter.
    apify_recruiter_actor: str | None = None

    # Contact-enrichment provider: "mock" (default, free) | "contactout" (paid, 1 credit/call)
    contact_provider: str = "mock"

    # Dev user (single-user MVP)
    dev_user_id: UUID
    dev_user_email: str

    # App
    app_env: str = "dev"
    log_level: str = "INFO"
    # Comma-separated extra origins allowed by CORS (e.g. "https://reachout.vercel.app")
    cors_origins: str | None = None
    # When True, the API uses FastAPI BackgroundTasks instead of Arq for in-process
    # async work. Default True so single-service deploys (Render free tier) work
    # without a separate worker process. Set False to use the Arq worker.
    use_background_tasks: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
