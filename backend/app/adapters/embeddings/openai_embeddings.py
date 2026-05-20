from __future__ import annotations

from openai import APIError, AsyncOpenAI, RateLimitError

from app.config import get_settings
from app.core.errors import UpstreamError
from app.core.retry import default_retry


class OpenAIEmbeddings:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_embed_model

    async def embed(self, text: str) -> list[float]:
        try:
            async for attempt in default_retry(retry_on=(RateLimitError, APIError)):
                with attempt:
                    resp = await self._client.embeddings.create(model=self._model, input=text)
        except (RateLimitError, APIError) as e:
            raise UpstreamError(f"openai embeddings failed: {e}") from e
        return resp.data[0].embedding
