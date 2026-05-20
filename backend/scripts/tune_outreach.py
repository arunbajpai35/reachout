"""Outreach prompt tuning runner.

Generates drafts for a (fixture x tone x channel) matrix, runs the deterministic
quality evaluator on each, and emits a markdown report.

Workflow:
    1. Edit prompts in app/adapters/llm/prompts.py
    2. Bump OUTREACH_PROMPT_VERSION
    3. Run: python scripts/tune_outreach.py
    4. Diff the new report against the previous one

Examples:
    # All fixtures, all tones (15 fixtures x 4 tones = 60 LLM calls @ ~$0.005 each)
    python scripts/tune_outreach.py

    # Just two tones
    python scripts/tune_outreach.py --tones concise,technical

    # Just one fixture for fast prompt iteration
    python scripts/tune_outreach.py --fixtures fintech --tones concise

    # Custom output path (default: tuning-reports/<version>-<timestamp>.md)
    python scripts/tune_outreach.py --out my-report.md
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
from pathlib import Path

from app.adapters.llm.openai_client import OpenAILLM
from app.adapters.llm.prompts import OUTREACH_PROMPT_VERSION, TONE_PRESETS
from app.domain.outreach.quality import QualityReport, evaluate_draft
from app.services.outreach_generator import generate_outreach_variants
from tests.fixtures.outreach_fixtures import CANDIDATE, JOBS, RECRUITERS

CHANNELS = ["recruiter_email", "linkedin_dm", "networking_intro"]
DEFAULT_RECRUITER_KEY = "tech_blr"


async def run_one(
    llm: OpenAILLM,
    *,
    job: dict,
    recruiter: dict,
    tone: str,
) -> list[tuple[dict, QualityReport]]:
    variants = await generate_outreach_variants(
        llm,
        candidate=CANDIDATE,
        job=job,
        company_name=job["company_name"],
        recruiter=recruiter,
        channels=CHANNELS,
        tone=tone,
    )
    out: list[tuple[dict, QualityReport]] = []
    for v in variants:
        q = evaluate_draft(channel=v["channel"], subject=v.get("subject"), body=v["body"])
        out.append((v, q))
    return out


def format_quality(q: QualityReport) -> str:
    badges: list[str] = [f"score={q.score}", f"{q.word_count}w", f"avg={q.avg_sentence_words}w/s"]
    blocks = [v for v in q.violations if v.severity == "block"]
    warns = [v for v in q.violations if v.severity == "warn"]
    if blocks:
        badges.append("BLOCK: " + ", ".join(v.rule + ":" + v.detail for v in blocks))
    if warns:
        badges.append("warn: " + ", ".join(v.rule for v in warns))
    return " | ".join(badges)


def render_report(
    *,
    version: str,
    tones: list[str],
    fixtures: list[str],
    recruiter_key: str,
    results: dict,
) -> str:
    now = dt.datetime.now().isoformat(timespec="seconds")
    lines: list[str] = []
    lines.append(f"# Outreach Tuning Report")
    lines.append("")
    lines.append(f"- Prompt version: `{version}`")
    lines.append(f"- Generated: {now}")
    lines.append(f"- Recruiter context: `{recruiter_key}`")
    lines.append(f"- Fixtures: {', '.join(fixtures)}")
    lines.append(f"- Tones: {', '.join(tones)}")
    lines.append("")

    # Summary table
    lines.append("## Quality summary")
    lines.append("")
    header = "| Fixture | Tone | email | DM | intro | blocks | warns |"
    sep = "|---|---|---|---|---|---|---|"
    lines.append(header)
    lines.append(sep)
    for fkey in fixtures:
        for tone in tones:
            cell = results.get((fkey, tone), [])
            by_ch = {q.channel: q for _, q in cell}
            email = by_ch.get("recruiter_email")
            dm = by_ch.get("linkedin_dm")
            intro = by_ch.get("networking_intro")
            blocks = sum(
                1 for _, q in cell for v in q.violations if v.severity == "block"
            )
            warns = sum(
                1 for _, q in cell for v in q.violations if v.severity == "warn"
            )
            lines.append(
                "| {f} | {t} | {e} | {d} | {i} | {b} | {w} |".format(
                    f=fkey,
                    t=tone,
                    e=email.score if email else "-",
                    d=dm.score if dm else "-",
                    i=intro.score if intro else "-",
                    b=blocks,
                    w=warns,
                )
            )
    lines.append("")

    # Detail per (fixture, tone)
    lines.append("## Drafts")
    lines.append("")
    for fkey in fixtures:
        job = JOBS[fkey]
        lines.append(f"### {fkey} — {job['company_name']} · {job['title']}")
        lines.append("")
        for tone in tones:
            lines.append(f"#### tone: `{tone}`")
            lines.append("")
            for v, q in results.get((fkey, tone), []):
                ch = v["channel"]
                lines.append(f"**{ch}** — {format_quality(q)}")
                if v.get("subject"):
                    lines.append(f"> Subject: {v['subject']}")
                lines.append("")
                lines.append("```")
                lines.append(v["body"].strip())
                lines.append("```")
                lines.append("")
            lines.append("")
    return "\n".join(lines)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tones", default=",".join(TONE_PRESETS.keys()))
    ap.add_argument("--fixtures", default=",".join(JOBS.keys()))
    ap.add_argument("--recruiter", default=DEFAULT_RECRUITER_KEY, choices=list(RECRUITERS))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    tones = [t.strip() for t in args.tones.split(",") if t.strip()]
    fixtures = [f.strip() for f in args.fixtures.split(",") if f.strip()]
    for t in tones:
        if t not in TONE_PRESETS:
            raise SystemExit(f"unknown tone: {t}; valid: {list(TONE_PRESETS)}")
    for f in fixtures:
        if f not in JOBS:
            raise SystemExit(f"unknown fixture: {f}; valid: {list(JOBS)}")

    recruiter = RECRUITERS[args.recruiter]
    llm = OpenAILLM()

    results: dict[tuple[str, str], list[tuple[dict, QualityReport]]] = {}
    total = len(fixtures) * len(tones)
    done = 0
    for fkey in fixtures:
        for tone in tones:
            done += 1
            print(f"[{done}/{total}] {fkey} · {tone} …", flush=True)
            results[(fkey, tone)] = await run_one(
                llm, job=JOBS[fkey], recruiter=recruiter, tone=tone
            )

    report = render_report(
        version=OUTREACH_PROMPT_VERSION,
        tones=tones,
        fixtures=fixtures,
        recruiter_key=args.recruiter,
        results=results,
    )

    if args.out:
        out_path = Path(args.out)
    else:
        out_dir = Path(__file__).resolve().parent.parent / "tuning-reports"
        out_dir.mkdir(exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        out_path = out_dir / f"{OUTREACH_PROMPT_VERSION}-{stamp}.md"

    out_path.write_text(report, encoding="utf-8")
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
