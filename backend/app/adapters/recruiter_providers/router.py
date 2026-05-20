from __future__ import annotations

from app.adapters.recruiter_providers.base import RecruiterDiscoveryProvider
from app.adapters.recruiter_providers.contactout import ContactOutProvider
from app.adapters.recruiter_providers.mock import MockProvider
from app.config import get_settings
from app.core.errors import AppError


def get_recruiter_provider() -> RecruiterDiscoveryProvider:
    """Pick the discovery provider based on settings. Single switch, no surprise."""
    name = get_settings().recruiter_provider.lower()
    if name == "mock":
        return MockProvider()
    if name == "contactout":
        return ContactOutProvider()
    raise AppError(f"unknown recruiter_provider: {name}")
