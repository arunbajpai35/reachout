"""Rule-based recruiter title classifier.

Why rules and not an LLM:
  - Volume: a single company can return 100+ profiles. LLM per profile is wasteful.
  - Debuggability: when a recruiter is mis-scored, you can read the matched_signals
    and know exactly which keyword fired. With an LLM you cannot.
  - Determinism: identical input -> identical classification, always.

If a signal is wrong, edit the lists in this file. That IS the spec.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class TitleCategory(StrEnum):
    TECHNICAL_RECRUITER = "technical_recruiter"   # tech-specific TA
    GENERAL_RECRUITER = "general_recruiter"        # generic TA, HRBP doing recruiting
    UNRELATED = "unrelated"                        # comp, payroll, L&D, ops, etc.


# Lowercased substring signals. We test each on the lowercased title.
# Order: a title that matches ANY tech signal is TECHNICAL, else any general signal
# makes it GENERAL, else any unrelated signal demotes it to UNRELATED, else GENERAL by default
# is too aggressive — we default UNRELATED if no recruiter-ish word appeared at all.
_TECH_SIGNALS = [
    "technical recruiter",
    "tech recruiter",
    "technical talent",
    "engineering recruiter",
    "engineering talent",
    "software recruiter",
    "technology recruiter",
    "ta - eng",
    "ta-eng",
    "ta engineering",
    "tag - tech",
    "tag tech",
    "tech ta",
    "developer recruiter",
    "platform recruiter",
    "tech hiring",
    "engineering hiring",
    "talent acquisition - engineering",
    "talent acquisition engineering",
    "talent acquisition - tech",
]

_GENERAL_RECRUITER_SIGNALS = [
    "recruiter",
    "talent acquisition",
    "ta partner",
    "talent partner",
    "talent sourcer",
    "sourcer",
    "recruitment",
    "tag",                  # Talent Acquisition Group (common in India)
    "talent specialist",
    "talent associate",
    "hiring partner",
]

# These DEMOTE to UNRELATED even if a general recruiter word appeared,
# because the specialty makes it irrelevant for backend/platform hiring.
_WRONG_SPECIALTY_SIGNALS = [
    "design",
    "marketing",
    "sales recruiter",
    "gtm recruiter",
    "finance recruiter",
    "accounting",
    "non-tech",
    "non technical",
    "blue collar",
]

# Pure UNRELATED — no recruiting at all
_UNRELATED_SIGNALS = [
    "compensation",
    "payroll",
    "learning and development",
    "l&d",
    "l & d",
    "people operations",
    "people ops",
    "hr operations",
    "hr generalist",
    "hr coordinator",
    "hr executive",
    "hr business partner",
    "hrbp",
    "employee experience",
    "employee relations",
    "office manager",
]


@dataclass
class TitleClassification:
    category: TitleCategory
    matched_signals: list[str] = field(default_factory=list)


def classify_title(title: str | None) -> TitleClassification:
    if not title:
        return TitleClassification(TitleCategory.UNRELATED, ["empty_title"])
    t = title.lower()

    tech_hits = [s for s in _TECH_SIGNALS if s in t]
    if tech_hits:
        return TitleClassification(TitleCategory.TECHNICAL_RECRUITER, tech_hits)

    general_hits = [s for s in _GENERAL_RECRUITER_SIGNALS if s in t]
    wrong_specialty = [s for s in _WRONG_SPECIALTY_SIGNALS if s in t]
    unrelated_hits = [s for s in _UNRELATED_SIGNALS if s in t]

    # A general-recruiter signal but with a wrong specialty -> unrelated.
    if general_hits and wrong_specialty:
        return TitleClassification(
            TitleCategory.UNRELATED, general_hits + wrong_specialty
        )

    if general_hits:
        return TitleClassification(TitleCategory.GENERAL_RECRUITER, general_hits)

    if unrelated_hits or wrong_specialty:
        return TitleClassification(
            TitleCategory.UNRELATED, unrelated_hits + wrong_specialty
        )

    # Nothing matched: probably an engineer or unrelated employee.
    return TitleClassification(TitleCategory.UNRELATED, ["no_recruiter_signal"])
