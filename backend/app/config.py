from functools import lru_cache
from uuid import UUID

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # DB
    database_url: str

    # Redis
    redis_url: str

    # OpenAI
    openai_api_key: str
    openai_model_extract: str = "gpt-4o-2024-11-20"
    openai_model_outreach: str = "gpt-4o-2024-11-20"
    openai_embed_model: str = "text-embedding-3-small"

    # Vendors
    apify_token: str | None = None
    contactout_api_key: str | None = None

    # Discovery provider switch: "mock" (default, free) | "contactout" (paid)
    recruiter_provider: str = "mock"
    recruiter_limit: int = 25

    # Dev user (single-user MVP)
    dev_user_id: UUID
    dev_user_email: str

    # App
    app_env: str = "dev"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
