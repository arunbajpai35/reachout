from __future__ import annotations

import json
from typing import Any

from openai import APIError, AsyncAzureOpenAI, AsyncOpenAI, RateLimitError

from app.config import get_settings
from app.core.errors import UpstreamError
from app.core.retry import default_retry


class OpenAILLM:
    """LLMClient implementation. Backs onto Azure OpenAI if AZURE_* env vars are
    configured; falls back to direct OpenAI otherwise.

    In Azure mode the `model` parameter passed by callers is overridden with the
    configured deployment name -- Azure routes by deployment, not by model id.
    """

    def __init__(self, *, default_model: str | None = None) -> None:
        settings = get_settings()
        if settings.use_azure:
            self._client = AsyncAzureOpenAI(
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
                azure_endpoint=settings.azure_openai_endpoint,
            )
            self._azure_deployment = settings.azure_openai_deployment_chat
            self._default_model = self._azure_deployment
        else:
            if not settings.openai_api_key:
                raise UpstreamError(
                    "No LLM credentials configured. Set OPENAI_API_KEY, "
                    "or the AZURE_OPENAI_* vars."
                )
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)
            self._azure_deployment = None
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
        # Azure routes by deployment; the caller's model preference is ignored.
        target = self._azure_deployment or (model or self._default_model)
        try:
            async for attempt in default_retry(
                attempts=3, retry_on=(RateLimitError, APIError)
            ):
                with attempt:
                    resp = await self._client.chat.completions.create(
                        model=target,
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
            raise UpstreamError(f"llm call failed: {e}") from e

        content = resp.choices[0].message.content or "{}"
        return json.loads(content)
