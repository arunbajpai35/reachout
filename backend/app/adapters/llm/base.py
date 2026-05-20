from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Provider-agnostic LLM interface. Implementations live next to this file."""

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
        """Return a JSON object matching `schema`. Implementations enforce strictness."""
        ...
