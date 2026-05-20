# ReachOut

AI reverse job hunting copilot for Indian engineers.

Paste a job URL + upload your resume → ReachOut finds the right Indian recruiters at that company, enriches their contact info, and drafts personalized outreach.

## Layout

```
reachout/
├── backend/      FastAPI + Postgres (pgvector) + Redis (Arq workers)
└── frontend/     React + TS + Tailwind + Vite + TanStack Query
```

## Frontend quickstart

```powershell
cd frontend
npm install
npm run dev          # http://localhost:5173, proxies /api to localhost:8000
```

Backend must be running at `localhost:8000` (the Vite dev server proxies `/api` to it).

## Backend quickstart

```powershell
cd backend
docker compose up -d
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
copy .env.example .env          # fill in OPENAI_API_KEY at minimum
python scripts/bootstrap_db.py

# Two processes:
uvicorn app.main:app --reload                       # API
arq app.workers.arq_app.WorkerSettings              # worker
```

Health check: `GET http://localhost:8000/healthz`.

### Try the pipeline

```bash
# 1. Submit (URL or pasted text)
curl -X POST localhost:8000/api/v1/jobs -H 'content-type: application/json' \
  -d '{"url": "https://boards.greenhouse.io/airbnb/jobs/6500000"}'
# -> { id, status: "pending", ... }

# 2. Poll until status == "extracted"
curl localhost:8000/api/v1/jobs/<id>
# Response now includes `company_slug_suggestion: "airbnb"`.

# 3. Confirm/correct the LinkedIn slug. This is what authorizes recruiter discovery.
curl -X PATCH localhost:8000/api/v1/jobs/<id>/company \
  -H 'content-type: application/json' \
  -d '{"linkedin_slug": "airbnb"}'
# -> status flips to "recruiters_pending"; worker enqueued.

# 4. Poll until status == "recruiters_found"
curl localhost:8000/api/v1/jobs/<id>/recruiters
# -> ranked list with `score` + `rationale` for each.

# 5. (Once) set candidate profile -- the context used for outreach generation
curl -X PUT localhost:8000/api/v1/candidate \
  -H 'content-type: application/json' \
  -d '{
    "summary": "Backend engineer building payment infra at a fintech.",
    "years_experience": 4,
    "target_role": "Senior Backend Engineer (Platform / Payments)",
    "skills": ["python", "go", "postgres", "kafka", "redis"],
    "notable_projects": [
      {"name": "Idempotent payments", "description": "Built exactly-once payment retry across 3 PSPs.",
       "stack": ["go", "postgres", "kafka"]}
    ]
  }'

# 6. Generate drafts for a top-ranked recruiter
curl -X POST localhost:8000/api/v1/outreach \
  -H 'content-type: application/json' \
  -d '{"job_id":"<id>", "recruiter_id":"<rid>"}'
# -> 3 drafts: recruiter_email (with subject), linkedin_dm, networking_intro

# 7. Regenerate one variant
curl -X POST localhost:8000/api/v1/outreach/<outreach_id>/regenerate
```

### Status state machine

```
pending  ──extract worker──▶  extracted  ──user confirms company──▶  recruiters_pending
                                                                         │
                                                                         ▼
                                                                 recruiters_found  ──user generates──▶  outreach drafts
       (any step can transition to: failed, with .error populated)
```

## Supported sources (v0)

| Source | Status | Path |
|---|---|---|
| Greenhouse `boards.greenhouse.io`, `job-boards.greenhouse.io` | supported | public JSON API |
| Lever `jobs.lever.co` | supported | public JSON API |
| Raw pasted JD text | supported | first-class input |
| LinkedIn | unsupported in v0 | returns 422 asking user to paste text |
| Naukri / others | not yet | returns 422 |

Adding a new URL-based source = drop one file in `app/adapters/scrapers/` and add it to the router list.

## Status

- [x] Phase 1 — Slice 1: project skeleton, DB schema, `/jobs` endpoints
- [x] Phase 1 — Slice 2: scrapers (Greenhouse, Lever, raw text), LLM extraction worker
- [x] Phase 1 — Slice 3: company-confirm flow, recruiter discovery + ranking (mock + ContactOut)
- [x] Phase 1 — Slice 4: candidate profile + outreach generation (email / DM / intro)
- [x] Phase 1 — Slice 5: frontend shell (Vite + React + TS + Tailwind)
- [x] Phase 1 — Slice 6: outreach quality calibration (tone presets + evaluator + tuning CLI)
- [x] Phase 1 — Slice 6.1: **baseline frozen at `outreach-v2.1`** — subject realism,
       killed chat/discuss/connect, removed flattery, tightened sentence length to 22 words,
       expanded corporate-filler & over-politeness bans
- [x] Phase 1 — Slice 7: resume upload + parsing (pdfplumber → GPT-4o → review-and-merge UI)

## Outreach prompt tuning

Drafts must "sound like a real engineer reaching out," not "AI-generated automation."
We iterate on this deterministically:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
# All 5 fixtures × 4 tones × 3 channels = 20 LLM calls, ~$0.10 / run
python scripts/tune_outreach.py
# Or narrow scope while iterating:
python scripts/tune_outreach.py --fixtures fintech --tones concise,technical
```

Reports land in `backend/tuning-reports/<version>-<timestamp>.md`. Diff reports across
prompt versions to see what changed. Workflow:

1. Edit `app/adapters/llm/prompts.py` (`OUTREACH_BASE_SYSTEM` or tone overlays).
2. Bump `OUTREACH_PROMPT_VERSION` so old vs new drafts are distinguishable.
3. Re-run the script. Score column in the summary table jumps up = win.
4. Mirror new forbidden phrases into `app/domain/outreach/quality.py` so the evaluator
   catches future regressions.

The quality evaluator (`app/domain/outreach/quality.py`) is **pure rules, no LLM**:
forbidden openers / phrases / closers, punctuation, sentence-length stats, word-count
targets. Frontend draft cards show the quality chip + any violations inline.
