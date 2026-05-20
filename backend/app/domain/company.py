"""Pure helpers for company resolution. No I/O.

The LinkedIn slug suggestion is intentionally a transparent function of the company name.
Anything more (domain heuristics, search APIs) requires a paid vendor call and
should be explicit, not silent.
"""
from __future__ import annotations

import re

# Common legal suffixes to strip before slugifying. Order matters; longer first.
_LEGAL_SUFFIXES = [
    "private limited",
    "pvt. ltd.",
    "pvt ltd",
    "p. ltd.",
    "incorporated",
    "limited",
    "corporation",
    "holdings",
    "labs",
    "inc.",
    "inc",
    "llc",
    "ltd.",
    "ltd",
    "co.",
]


def suggest_linkedin_slug(name: str) -> str:
    """Convert a company name to a plausible linkedin company slug.

    Examples:
        "Razorpay" -> "razorpay"
        "Razorpay Software Private Limited" -> "razorpay-software"
        "Stripe, Inc." -> "stripe"
        "Project & Co." -> "project"

    This is a suggestion only. The user MUST confirm before recruiter discovery runs.
    """
    n = name.strip().lower()
    for suf in _LEGAL_SUFFIXES:
        if n.endswith(" " + suf):
            n = n[: -(len(suf) + 1)].rstrip(" ,.")
    # Replace non-alphanumeric with hyphens, collapse runs, trim.
    n = re.sub(r"[^a-z0-9]+", "-", n).strip("-")
    return n or name.lower().replace(" ", "-")
