from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI, RateLimitError, APIError

from app.config import get_settings
from app.core.errors import UpstreamError
from app.core.retry import default_retry


class OpenAILLM:
    """OpenAI implementation of LLMClient. Uses structured outputs (strict JSON schema)."""

    def __init__(self, *, default_model: str | None = None) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._default_model = default_model or settings.openai_model_extract

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any],
        schema_name: str,
        model: str | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        model = model or self._default_model
        try:
            async for attempt in default_retry(
                attempts=3, retry_on=(RateLimitError, APIError)
            ):
                with attempt:
                    resp = await self._client.chat.completions.create(
                        model=model,
                        temperature=temperature,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        response_format={
                            "type": "json_schema",
                            "json_schema": {
                                "name": schema_name,
                                "strict": True,
                                "schema": schema,
                            },
                        },
                    )
        except (RateLimitError, APIError) as e:
            raise UpstreamError(f"openai call failed: {e}") from e

        content = resp.choices[0].message.content or "{}"
        return json.loads(content)
