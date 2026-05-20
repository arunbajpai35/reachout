"""Fixtures for prompt tuning. Five JD archetypes the user wants to test against.

Edit freely. Add new archetypes by adding a key to JOBS. The tuning runner picks
them up automatically.
"""
from __future__ import annotations


CANDIDATE: dict = {
    "summary": (
        "Backend engineer at an Indian fintech building payments infra. "
        "Focused on distributed systems correctness and operational reliability."
    ),
    "years_experience": 5,
    "target_role": "Senior Backend Engineer (Platform / Payments / Infra)",
    "skills": [
        "python", "go", "postgres", "kafka", "redis", "kubernetes", "grpc", "aws",
    ],
    "notable_projects": [
        {
            "name": "Idempotent payment retry",
            "description": (
                "Built exactly-once retry across three PSPs; cut double-charges "
                "from ~0.4% to under 0.01%."
            ),
            "stack": ["go", "postgres", "kafka"],
        },
        {
            "name": "Daily settlement reconciliation",
            "description": (
                "Owned the 8M-row daily reconciliation between PSP files and "
                "the internal ledger; resolved a chronic 30k-row drift."
            ),
            "stack": ["python", "postgres"],
        },
    ],
}


RECRUITERS: dict[str, dict] = {
    "tech_blr": {
        "full_name": "Priya Sharma",
        "title": "Senior Technical Recruiter",
        "location": "Bengaluru, India",
    },
    "tech_hyd": {
        "full_name": "Aarav Mehta",
        "title": "Engineering Recruiter",
        "location": "Hyderabad, India",
    },
    "general_blr": {
        "full_name": "Neha Kapoor",
        "title": "Talent Acquisition Partner",
        "location": "Bengaluru, India",
    },
}


JOBS: dict[str, dict] = {
    "startup": {
        "title": "Founding Backend Engineer",
        "seniority": "senior",
        "yoe_min": 4,
        "yoe_max": 8,
        "location": "Bengaluru, India",
        "work_mode": "hybrid",
        "employment_type": "fulltime",
        "skills": ["go", "postgres", "redis"],
        "tech_stack": ["go", "postgres", "redis", "aws"],
        "responsibilities": [
            "Own backend architecture from day one",
            "Ship the first version of the API and ingestion pipeline",
            "Help shape early eng culture and hire the next 3 backend engineers",
        ],
        "compensation": "INR 50-70L plus meaningful equity",
        "company_name": "Loopwise",
        "team": "Engineering",
    },
    "infra": {
        "title": "Senior Platform Engineer",
        "seniority": "senior",
        "yoe_min": 5,
        "yoe_max": 10,
        "location": "Bengaluru, India",
        "work_mode": "hybrid",
        "employment_type": "fulltime",
        "skills": ["kubernetes", "go", "terraform"],
        "tech_stack": ["kubernetes", "go", "terraform", "argocd", "prometheus", "aws"],
        "responsibilities": [
            "Run a multi-region Kubernetes platform for 200+ engineers",
            "Improve developer experience and self-serve workflows",
            "Drive cost reductions on the AWS bill",
        ],
        "compensation": None,
        "company_name": "Atlas Cloud",
        "team": "Platform",
    },
    "ai": {
        "title": "Backend Engineer, AI Infrastructure",
        "seniority": "mid",
        "yoe_min": 3,
        "yoe_max": 6,
        "location": "Bengaluru, India",
        "work_mode": "onsite",
        "employment_type": "fulltime",
        "skills": ["python", "ray", "postgres"],
        "tech_stack": ["python", "ray", "postgres", "kafka", "kubernetes"],
        "responsibilities": [
            "Build the inference orchestration layer",
            "Manage GPU scheduling across clusters",
            "Cut p99 inference latency for production endpoints",
        ],
        "compensation": None,
        "company_name": "Polaris AI",
        "team": "AI Infra",
    },
    "fintech": {
        "title": "Senior Backend Engineer, Payments",
        "seniority": "senior",
        "yoe_min": 5,
        "yoe_max": 9,
        "location": "Bengaluru, India",
        "work_mode": "hybrid",
        "employment_type": "fulltime",
        "skills": ["go", "postgres", "kafka"],
        "tech_stack": ["go", "postgres", "kafka", "grpc"],
        "responsibilities": [
            "Own the payment retry and settlement domains",
            "Improve idempotency guarantees across multi-PSP routing",
            "Drive p99 latency below 200ms",
        ],
        "compensation": "INR 60-90L",
        "company_name": "Cleartap Payments",
        "team": "Money Movement",
    },
    "enterprise": {
        "title": "Lead Backend Engineer",
        "seniority": "lead",
        "yoe_min": 7,
        "yoe_max": 12,
        "location": "Pune, India",
        "work_mode": "onsite",
        "employment_type": "fulltime",
        "skills": ["java", "spring", "oracle"],
        "tech_stack": ["java", "spring boot", "oracle", "kafka", "kubernetes"],
        "responsibilities": [
            "Lead modernization of a 15-year-old billing platform",
            "Mentor a team of 6 backend engineers",
            "Drive migration from on-prem to AWS over 18 months",
        ],
        "compensation": None,
        "company_name": "GlobalTrust Financial",
        "team": "Billing Platform",
    },
}
