"""Recruiter ranking.

Score formula (additive, transparent):

    base       = title_weight * 0.6 + location_score * 0.4
    final      = base * role_relevance_multiplier

  - title_weight  : 1.0 technical, 0.6 general, 0.0 unrelated
  - location_score: 0..1 from domain.recruiter.location
  - role_relevance_multiplier: 1.0 for engineering JDs (default for MVP),
                               could downweight when targeting non-tech roles later

UNRELATED titles return score 0 -- they are persisted but not linked to the job.

The rationale string is the source of truth. If a score surprises you, read the rationale.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.domain.recruiter.classifier import TitleCategory, TitleClassification, classify_title
from app.domain.recruiter.location import location_score

_TITLE_WEIGHT = {
    TitleCategory.TECHNICAL_RECRUITER: 1.0,
    TitleCategory.GENERAL_RECRUITER: 0.6,
    TitleCategory.UNRELATED: 0.0,
}

# Engineering signals in the JD's skills/tech_stack. If present, we treat the role
# as engineering -- the default assumption for MVP. Kept explicit so future role
# types (design, sales) can flip the multiplier.
_ENG_SIGNALS = {
    "python", "go", "golang", "java", "rust", "kotlin", "scala", "c++", "node",
    "typescript", "javascript", "ruby", "elixir",
    "backend", "platform", "infrastructure", "devops", "sre", "distributed systems",
    "postgres", "mysql", "kafka", "redis", "elasticsearch",
    "react", "frontend", "ios", "android",
}


@dataclass
class RankedCandidate:
    score: float
    rationale: str
    title_category: TitleCategory


def is_engineering_role(job_parsed: dict | None) -> bool:
    if not job_parsed:
        return True  # default: assume engineering, our MVP audience
    bag: set[str] = set()
    for key in ("skills", "tech_stack"):
        for item in job_parsed.get(key) or []:
            bag.add(str(item).lower())
    return bool(bag & _ENG_SIGNALS) or len(bag) == 0


def rank(
    *,
    title: str | None,
    location: str | None,
    job_parsed: dict | None,
) -> RankedCandidate:
    cls = classify_title(title)
    title_w = _TITLE_WEIGHT[cls.category]
    loc_score, loc_token = location_score(location)

    base = title_w * 0.6 + loc_score * 0.4
    multiplier = 1.0 if is_engineering_role(job_parsed) else 0.7
    final = round(base * multiplier, 4)

    if cls.category == TitleCategory.UNRELATED:
        final = 0.0

    rationale = _format_rationale(cls, title_w, loc_token, loc_score, multiplier, final)
    return RankedCandidate(score=final, rationale=rationale, title_category=cls.category)


def _format_rationale(
    cls: TitleClassification,
    title_w: float,
    loc_token: str,
    loc_score: float,
    multiplier: float,
    final: float,
) -> str:
    signals = ",".join(cls.matched_signals) or "none"
    return (
        f"title={cls.category.value}({signals}|w={title_w}); "
        f"location={loc_token}({loc_score}); "
        f"mult={multiplier}; final={final}"
    )


def sort_descending(items: Iterable) -> list:
    return sorted(items, key=lambda x: x.score, reverse=True)
