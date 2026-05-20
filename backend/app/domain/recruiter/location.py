"""Location-based scoring for Indian-market priority.

Tiered weights, transparent and editable. Each lookup returns a score AND
the matched signal so ranking rationale stays inspectable.
"""
from __future__ import annotations

# Lowercased substring matches. India-first per MVP target.
_TIER1_INDIA = {"bengaluru", "bangalore", "bangaluru"}
_TIER2_INDIA = {
    "hyderabad",
    "mumbai",
    "pune",
    "delhi",
    "new delhi",
    "gurgaon",
    "gurugram",
    "noida",
    "chennai",
}
_GENERIC_INDIA = {"india"}
_REMOTE = {"remote", "anywhere", "work from home", "wfh"}

# Score weights. 1.0 = perfect location signal.
_W_TIER1 = 1.0
_W_TIER2 = 0.85
_W_INDIA_GENERIC = 0.6
_W_REMOTE = 0.4
_W_UNKNOWN = 0.1
_W_OTHER = 0.0  # explicitly elsewhere e.g. "San Francisco"


def location_score(location: str | None) -> tuple[float, str]:
    """Return (score in [0, 1], rationale token).

    Rationale token shape: "tier1:bengaluru" | "tier2:pune" | "india_generic" |
    "remote" | "unknown" | "other:san_francisco".
    """
    if not location:
        return _W_UNKNOWN, "unknown"
    loc = location.lower()

    for city in _TIER1_INDIA:
        if city in loc:
            return _W_TIER1, f"tier1:{city}"
    for city in _TIER2_INDIA:
        if city in loc:
            return _W_TIER2, f"tier2:{city}"
    for sig in _GENERIC_INDIA:
        if sig in loc:
            return _W_INDIA_GENERIC, "india_generic"
    for sig in _REMOTE:
        if sig in loc:
            return _W_REMOTE, "remote"

    # Known to be elsewhere. Compact rationale for debugging.
    return _W_OTHER, f"other:{loc[:40].replace(' ', '_')}"
