from __future__ import annotations

from app.adapters.contact_providers.base import ContactEnrichmentProvider
from app.adapters.contact_providers.contactout import ContactOutEnrichmentProvider
from app.adapters.contact_providers.hunter import HunterIoProvider
from app.adapters.contact_providers.mock import MockEnrichmentProvider
from app.config import get_settings
from app.core.errors import AppError


def get_contact_provider() -> ContactEnrichmentProvider:
    name = get_settings().contact_provider.lower()
    if name == "mock":
        return MockEnrichmentProvider()
    if name == "contactout":
        return ContactOutEnrichmentProvider()
    if name == "hunter":
        return HunterIoProvider()
    raise AppError(f"unknown contact_provider: {name}")
