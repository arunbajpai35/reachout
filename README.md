# ReachOut

[![ci](https://github.com/arunbajpai35/reachout/actions/workflows/ci.yml/badge.svg)](https://github.com/arunbajpai35/reachout/actions/workflows/ci.yml)

AI reverse job hunting copilot for Indian engineers. Paste a job URL or JD text, get real recruiters at that company, and draft outreach that doesn't sound like a robot.

**Live demo: https://reachout-two.vercel.app** &nbsp;·&nbsp; **API: https://reachout-hbu8.onrender.com**

> First request after 15 min of idle on the demo can take ~45s — that's Render's free-tier cold start, not the app. Subsequent requests are fast.

## What it does

End-to-end loop, ~30 seconds from URL paste to copyable LinkedIn DM:

1. **Paste a Greenhouse / Lever URL or raw JD text** → the JD is fetched (public board APIs, no scraping where possible) and normalized into structured fields via an LLM with strict JSON schema output.
2. **Confirm the company's LinkedIn slug** → explicit user action; the system never spends recruiter-API credits without your go-ahead.
3. **Real recruiter discovery** → an Apify actor pulls current employees of that company filtered to recruiter / TA / engineering-recruiter titles, India-only by default.
4. **Rule-based ranking** → titles classified (technical / general / unrelated) and locations tiered (Bengaluru first, then tier-2 cities, then "India", then remote). Every score carries a human-readable rationale string.
5. **Upload your resume (PDF)** → structured roles are extracted by the LLM; years-of-experience is computed in plain Python from those roles, not by the LLM (because LLMs are unreliable at multi-step arithmetic).
6. **Generate outreach** → one LLM call produces email + LinkedIn DM + short networking intro. Four tone presets (concise / technical / warm / founder-energy).
7. **Pure-rule quality evaluator** flags AI-sounding language before you send: forbidden phrases, em-dashes, "I hope this finds you well", "chat / discuss / connect" patterns, sentence-length anomalies, clickbait subject lines.

## Architecture

```
                       https://reachout-two.vercel.app
                                  │
                            Frontend (Vercel)
                            Vite + React + TS + Tailwind + TanStack Query
                                  │
                                  │  HTTPS, CORS-allowlisted
                                  ▼
                       https://reachout-hbu8.onrender.com
                                  │
                            Backend (Render free tier)
                            FastAPI + FastAPI BackgroundTasks (single service)
                                  │
                    ┌─────────────┼──────────────┬────────────────────┐
                    ▼             ▼              ▼                    ▼
                 Postgres      LLM            Recruiter            Resume PDF
                 + pgvector    Azure OpenAI   discovery            extraction
                 (Neon SG)     gpt-4.1-mini   Apify actor          pdfplumber
                                              (LinkedIn employees) (in-process)
```

The whole thing runs on free tiers. Total session spend across building + testing on real data: about $0.40.

## Repo layout

```
reachout/
├── backend/                FastAPI service
│   ├── app/
│   │   ├── api/v1/         HTTP handlers (jobs, recruiters, candidate, outreach)
│   │   ├── adapters/       Swappable interfaces: LLM, scrapers, recruiter providers,
│   │   │                   contact providers, PDF, embeddings
│   │   ├── services/       Orchestration: scrape → extract → rank → generate
│   │   ├── domain/         Pure logic: classifier, ranking, quality evaluator
│   │   ├── workers/        Arq tasks (legacy; deploy uses BackgroundTasks instead)
│   │   ├── db/             SQLAlchemy models + session
│   │   └── core/           Logging, retry, error types
│   ├── scripts/
│   │   ├── bootstrap_db.py     create tables + seed dev user (run once)
│   │   └── tune_outreach.py    deterministic prompt-tuning sweep on fixtures
│   ├── tests/fixtures/     5 JD archetypes for outreach calibration
│   └── pyproject.toml
├── frontend/               Vite app
│   ├── src/
│   │   ├── features/       feature-folder organization
│   │   ├── components/     UI primitives (Button, Card, Badge, etc.)
│   │   └── lib/            typed API client
│   └── package.json
├── .github/workflows/ci.yml    lint + import smoke (backend) + tsc/build (frontend)
├── render.yaml                 Render service config
└── frontend/vercel.json        Vercel SPA rewrite
```

Dependencies point inward: `api → services → domain`. Adapters are interface-driven so any provider (Azure OpenAI / direct OpenAI, Apify / ContactOut, Hunter / mock) is one env-var switch.

## Tech stack at a glance

| Layer | Choice | Why |
|---|---|---|
| Backend framework | FastAPI | Native async + strict Pydantic + automatic OpenAPI |
| LLM | Azure OpenAI `gpt-4.1-mini` | Cheaper than 4o, structured outputs work cleanly; provider-agnostic interface so direct OpenAI is a one-line swap |
| DB | Neon Postgres + pgvector | Free tier with pgvector; sub-50ms from Singapore |
| Cache / queue | Upstash Redis | Free tier, TLS, regional |
| Recruiter discovery | Apify `harvestapi/linkedin-company-employees` | Pay-per-result, ~$0.004 per recruiter, no LinkedIn account needed |
| Email enrichment | Pluggable: mock / Hunter / ContactOut | All optional — the demo defaults to mock since most "free" finders gate on work-email signup |
| Frontend | Vite + React 18 + TS + Tailwind + TanStack Query | Sub-second HMR; no global state library; mocked-out data flows correctly through real component tree |
| Deploy | Vercel (frontend) + Render (backend) | Free tiers; the backend uses FastAPI BackgroundTasks so it's a single-service deploy |
| CI | GitHub Actions | Backend lint + import smoke, frontend type check + build |

## Local development

You need cloud Postgres + Redis. Free tiers work end-to-end. Replace local Docker if you'd prefer it (we don't ship a `docker-compose.yml`).

```powershell
# Provision (one-time)
#  - https://neon.tech                  → Postgres URL
#  - https://upstash.com                → Redis URL (rediss://)
#  - https://console.apify.com          → APIFY_TOKEN
#  - Azure OpenAI deployment            → AZURE_OPENAI_* values

# Backend
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env                  # fill in values
python scripts/bootstrap_db.py          # one-time: tables + pgvector + dev user
$env:PYTHONPATH = "."
uvicorn app.main:app --port 8002        # single service, no separate worker needed

# Frontend (new terminal)
cd frontend
npm install
npm run dev                             # http://localhost:5173
```

Open http://localhost:5173, paste a Greenhouse URL, walk through the flow.

## Outreach prompt tuning

Drafts must sound like a real engineer reaching out, not AI-generated automation. The deterministic calibration workflow:

```powershell
cd backend
python scripts/tune_outreach.py --fixtures fintech,infra,ai --tones concise,technical
```

Generates drafts against fixture JDs (startup / infra / AI / fintech / enterprise) across tone presets, runs each through the quality evaluator, writes a markdown report you can diff across prompt versions. The evaluator (`app/domain/outreach/quality.py`) is pure substring + regex rules — no LLM judge, no critique loop, no chain of agents. It's the spec.

Workflow when a draft drifts:
1. Add the offending phrase to `OUTREACH_BASE_SYSTEM` in `app/adapters/llm/prompts.py`
2. Mirror it in the matching list in `quality.py`
3. Bump `OUTREACH_PROMPT_VERSION` so old vs new drafts are distinguishable
4. Re-run the script, diff the new report against the previous one

Current baseline: `outreach-v2.1`. Validated against 36 real drafts (3 fixtures × 4 tones × 3 channels): zero block-severity violations.

## Supported inputs

| Source | Status |
|---|---|
| Greenhouse `boards.greenhouse.io`, `job-boards.greenhouse.io` | ✅ public JSON API |
| Greenhouse-embedded company pages (`?gh_jid=...`) | ✅ token auto-resolved |
| Lever `jobs.lever.co` | ✅ public JSON API |
| Raw pasted JD text | ✅ first-class input |
| LinkedIn job URLs | ❌ placeholder; paste the JD text instead |
| Naukri / others | ❌ not yet |

Adding a new URL-based source = drop one file in `app/adapters/scrapers/` and register it in the router.

## State machine

```
pending  ──extract──▶  extracted  ──user confirms company──▶  recruiters_pending
                                                                    │
                                                                    ▼
                                                              recruiters_found  ──generate──▶  drafts
       (any step can transition to: failed, with .error populated)
```

## Honest caveats

- **Render free tier cold start** is ~45s after 15 min idle. Fine for a demo; not for production.
- **Background tasks run in-process** on the deployed backend (FastAPI BackgroundTasks, not Arq). If the dyno sleeps mid-task, the task dies. Add `--reload` and Arq when this matters.
- **Email enrichment is mock by default** — Hunter.io requires a work email to sign up; ContactOut API requires a paid plan. For real outreach, use the LinkedIn DM variant — it works fine without an email anyway.
- **No auth.** Single-user MVP; a fixed `DEV_USER_ID` keeps schema FK constraints valid. Adding Clerk / Supabase Auth is a Phase 2 task.
- **No reply tracking, no auto-send.** Drafts are copy-paste. Sending introduces deliverability concerns (SPF/DKIM/warmup) that are their own project.

## License

Source-available, no permissive license granted by default. Copyright Arun Bajpai. See `LICENSE` if added, otherwise treat as all-rights-reserved.
