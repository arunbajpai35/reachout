"""Deterministic mock provider for dev.

Same slug -> same candidates, always. Lets us exercise ranking + persistence
without paying ContactOut. Mix is intentionally noisy: technical recruiters,
generic TA, unrelated HR roles, and a couple of off-geo profiles so the
ranking layer has real signal to discriminate.
"""
from __future__ import annotations

import hashlib

from app.adapters.recruiter_providers.base import RecruiterCandidate, RecruiterDiscoveryProvider

# Fixture templates. The slug seeds which slice we return so it's stable per company.
_TEMPLATES: list[dict] = [
    {"name": "Priya Sharma",   "title": "Senior Technical Recruiter",                "location": "Bengaluru, India"},
    {"name": "Aarav Mehta",    "title": "Engineering Recruiter",                     "location": "Bengaluru, India"},
    {"name": "Ananya Iyer",    "title": "Talent Acquisition - Engineering",          "location": "Hyderabad, India"},
    {"name": "Rahul Verma",    "title": "Tech Recruiter",                            "location": "Pune, India"},
    {"name": "Neha Kapoor",    "title": "Talent Acquisition Partner",                "location": "Gurgaon, India"},
    {"name": "Vikram Singh",   "title": "Recruiter",                                 "location": "Mumbai, India"},
    {"name": "Riya Patel",     "title": "Sourcer",                                   "location": "Bengaluru, India"},
    {"name": "Karan Joshi",    "title": "Talent Acquisition Group (TAG)",            "location": "Chennai, India"},
    {"name": "Meera Nair",     "title": "HR Business Partner",                       "location": "Bengaluru, India"},
    {"name": "Arjun Reddy",    "title": "Compensation & Benefits Analyst",           "location": "Hyderabad, India"},
    {"name": "Sneha Das",      "title": "Learning & Development Manager",            "location": "Bengaluru, India"},
    {"name": "Jay Patel",      "title": "Design Recruiter",                          "location": "Bengaluru, India"},
    {"name": "Aditi Rao",      "title": "Technical Recruiter",                       "location": "Noida, India"},
    {"name": "Sam O'Brien",    "title": "Senior Technical Recruiter",                "location": "San Francisco, CA"},
    {"name": "Leila Hassan",   "title": "Engineering Recruiter",                     "location": "Remote"},
]


class MockProvider(RecruiterDiscoveryProvider):
    name = "mock"

    async def find_recruiters(
        self,
        *,
        company_linkedin_slug: str,
        company_name: str,
        limit: int = 25,
    ) -> list[RecruiterCandidate]:
        # Deterministic rotation seeded by slug -- same input, same output.
        seed = int(hashlib.sha256(company_linkedin_slug.encode()).hexdigest(), 16)
        rotated = _TEMPLATES[seed % len(_TEMPLATES):] + _TEMPLATES[: seed % len(_TEMPLATES)]
        out: list[RecruiterCandidate] = []
        for i, t in enumerate(rotated[:limit]):
            li_slug = t["name"].lower().replace(" ", "-").replace("'", "")
            out.append(
                RecruiterCandidate(
                    full_name=t["name"],
                    title=t["title"],
                    linkedin_url=f"https://www.linkedin.com/in/{li_slug}-{company_linkedin_slug}-{i}",
                    location=t["location"],
                    company_name=company_name,
                    source=self.name,
                    source_payload={"fixture_index": i},
                )
            )
        return out
