from __future__ import annotations

from openai import APIError, AsyncAzureOpenAI, AsyncOpenAI, RateLimitError

from app.config import get_settings
from app.core.errors import UpstreamError
from app.core.logging import log
from app.core.retry import default_retry


class OpenAIEmbeddings:
    """Optional embeddings client.

    If no embedding deployment / API key is configured, `embed()` returns None
    and callers persist NULL. Embeddings are only used for future semantic
    search; nothing in the MVP pipeline blocks on their absence.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._available = False
        if settings.use_azure:
            if settings.azure_openai_deployment_embed:
                self._client = AsyncAzureOpenAI(
                    api_key=settings.azure_openai_api_key,
                    api_version=settings.azure_openai_api_version,
                    azure_endpoint=settings.azure_openai_endpoint,
                )
                self._model = settings.azure_openai_deployment_embed
                self._available = True
            else:
                log.info("embeddings.disabled", reason="no azure embed deployment configured")
        elif settings.openai_api_key:
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)
            self._model = settings.openai_embed_model
            self._available = True
        else:
            log.info("embeddings.disabled", reason="no llm credentials configured")

    async def embed(self, text: str) -> list[float] | None:
        if not self._available:
            return None
        try:
            async for attempt in default_retry(retry_on=(RateLimitError, APIError)):
                with attempt:
                    resp = await self._client.embeddings.create(model=self._model, input=text)
        except (RateLimitError, APIError) as e:
            raise UpstreamError(f"embeddings call failed: {e}") from e
        return resp.data[0].embedding
