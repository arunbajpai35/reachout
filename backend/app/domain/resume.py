"""Pure resume helpers. No I/O, no LLM, no DB."""
from __future__ import annotations

import re
from datetime import date
from typing import Literal

RoleType = Literal["fulltime", "parttime", "contract", "intern", "volunteer"]

# Months contributed per role-type per month of duration.
_WEIGHTS: dict[str, float] = {
    "fulltime": 1.0,
    "parttime": 0.5,
    "contract": 0.5,
    "intern": 0.0,
    "volunteer": 0.0,
}

_YYYY_MM = re.compile(r"^(\d{4})-(\d{1,2})$")


def _parse_month(s: str) -> date | None:
    if not s:
        return None
    m = _YYYY_MM.match(s.strip())
    if not m:
        return None
    year, month = int(m.group(1)), int(m.group(2))
    if not (1 <= month <= 12):
        return None
    return date(year, month, 1)


def _months_between(start: date, end: date) -> int:
    """Whole-month delta. Nov 2025 -> May 2026 = 6. Negative results clamp to 0."""
    months = (end.year - start.year) * 12 + (end.month - start.month)
    return max(0, months)


def compute_years_experience(
    roles: list[dict] | None,
    *,
    today: date | None = None,
) -> float | None:
    """Sum role durations in months, apply role-type weights, divide by 12 at the end.

    Returns None if the input is empty / unusable. Returns 0.0 if all roles are zero-weight
    (e.g. only internships). Otherwise a non-negative float rounded to one decimal place.
    """
    if not roles:
        return None
    today = today or date.today()
    total_months = 0.0
    counted_any = False
    for r in roles:
        rtype = (r.get("type") or "").lower()
        weight = _WEIGHTS.get(rtype)
        if weight is None:
            # Unknown type -> assume full-time so we don't silently zero it out.
            weight = 1.0
        start = _parse_month(r.get("start") or "")
        if start is None:
            continue
        end_raw = (r.get("end") or "").strip().lower()
        if end_raw in {"", "present", "current", "ongoing", "now"}:
            end = today
        else:
            parsed_end = _parse_month(r.get("end") or "")
            if parsed_end is None:
                continue
            end = parsed_end
        months = _months_between(start, end)
        if months > 0:
            counted_any = True
        total_months += months * weight
    if not counted_any:
        return 0.0
    return round(total_months / 12, 1)
