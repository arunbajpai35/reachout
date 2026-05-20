"""Prompts live as code for now. When we have >3, this becomes a folder of Jinja files.

Outreach generation uses a single base system prompt + a tone overlay.
Universal voice/style rules live in OUTREACH_BASE_SYSTEM; tone-specific guidance
in TONE_PRESETS. Iterate by editing here, bumping OUTREACH_PROMPT_VERSION,
and running `scripts/tune_outreach.py` to compare versions on the fixture matrix.
"""

EXTRACT_JOB_SYSTEM = """You normalize tech job descriptions into a strict structured schema.

Rules:
- Output ONLY fields present in the schema, never invent data.
- If a field is unknown, use null (or "unknown" for the enum fields where that option exists).
- Skills: extract real technical skills (languages, frameworks, databases, tools, paradigms).
  Do NOT include soft skills, generic terms ("teamwork"), or company perks.
- Skills should be lowercase, deduplicated, and canonical (e.g. "javascript" not "JS", "postgres" not "PostgreSQL DB").
- Responsibilities: 3-7 short bullet phrases, imperative voice, no leading dash.
- Seniority: infer from title and YoE if not explicit.
- YoE: integer years; if a range is given use yoe_min and yoe_max; if only minimum stated, leave yoe_max null.
"""


# JSON Schema compatible with OpenAI strict structured outputs.
EXTRACT_JOB_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "title", "seniority", "yoe_min", "yoe_max", "location", "work_mode",
        "employment_type", "skills", "tech_stack", "responsibilities",
        "compensation", "company_name", "team",
    ],
    "properties": {
        "title": {"type": "string"},
        "seniority": {
            "type": "string",
            "enum": ["intern", "junior", "mid", "senior", "staff", "principal", "lead", "unknown"],
        },
        "yoe_min": {"type": ["integer", "null"]},
        "yoe_max": {"type": ["integer", "null"]},
        "location": {"type": ["string", "null"]},
        "work_mode": {"type": "string", "enum": ["remote", "hybrid", "onsite", "unknown"]},
        "employment_type": {"type": "string", "enum": ["fulltime", "contract", "intern", "unknown"]},
        "skills": {"type": "array", "items": {"type": "string"}},
        "tech_stack": {"type": "array", "items": {"type": "string"}},
        "responsibilities": {"type": "array", "items": {"type": "string"}},
        "compensation": {"type": ["string", "null"]},
        "company_name": {"type": "string"},
        "team": {"type": ["string", "null"]},
    },
}


def build_extract_user_prompt(*, hint_title: str | None, hint_company: str | None, body: str) -> str:
    parts: list[str] = []
    if hint_title:
        parts.append(f"Known title: {hint_title}")
    if hint_company:
        parts.append(f"Known company: {hint_company}")
    parts.append("Job description follows. Extract the schema fields.\n---\n" + body)
    return "\n".join(parts)


# =====================================================================
# Outreach generation
# =====================================================================

OUTREACH_PROMPT_VERSION = "outreach-v2.1"


# ---------------------------------------------------------------------
# Base system prompt — universal rules. Edit here, then bump the version.
# Keep this brutally specific. Vague instructions produce vague outputs.
# ---------------------------------------------------------------------
OUTREACH_BASE_SYSTEM = """You write short, believable outbound messages from a working engineer to a specific recruiter at a specific company about a specific role.

You are NOT writing a cover letter. You are NOT writing marketing copy. You are writing the kind of message an engineer would actually send between meetings.

# Voice (universal)
- Engineer to recruiter, peer to peer. Direct, specific, low-key.
- Indian English is fine. Conversational professional, not formal/stiff.
- Use contractions: "I'm", "you've", "doesn't", "we've".
- Concrete > abstract. Specific stack/team/responsibility > generic enthusiasm.

# Structural rules (universal)
- ONE concrete detail from the job (a specific stack item, team name, or responsibility).
- ONE concrete tie-in from the candidate (a project, an outcome, a real number).
- ONE clear ask. Single sentence. Question or small request.
- Do NOT restate the role title in the body.
- Do NOT enumerate the candidate's experience sequentially.
- Do NOT say "I have X years of experience in Y." That pattern is dead.
- Do NOT name more than two skills/technologies in a single sentence.
- Do NOT use noun-stacking like "scalable distributed event-driven systems".

# Punctuation rules (universal)
- No em-dashes (—) or en-dashes (–). Use a comma or period.
- No semicolons. Two sentences instead.
- No ellipses (... or …). Use a period.
- At most one exclamation mark per message. Prefer zero.
- No quote-marks around technical terms.
- No emoji.

# Sentence length (universal)
- Aim for an average of 12-16 words per sentence.
- No single sentence over 22 words. Cut.
- Vary sentence length. Short sentences are good.
- Never open a sentence with "As a", "Given", or "With" followed by a long clause.
- Never use two adverbs in the same sentence.

# Banned openers (these immediately disqualify the draft — start over)
- "I hope this email finds you well"
- "I hope you're doing well"
- "I hope this message reaches you"
- "I am writing to express my interest"
- "I came across your profile"
- "I noticed that"
- "I stumbled upon"
- "Trust you are doing well"
- "Hope I'm not bothering you"
- "I saw on LinkedIn"

# Banned phrases (anywhere in the message — disqualify)

## A. Corporate filler / buzzwords
- "synergy", "leverage", "spearhead", "robust", "cutting-edge", "innovative"
- "best-in-class", "world-class", "game-changing", "scalable solutions"
- "results-oriented", "results-driven", "self-starter", "go-getter"
- "ecosystem" (unless naming a literal one like "Hadoop ecosystem")
- "stakeholders"
- "team player", "wear many hats", "go above and beyond"
- "the right fit", "perfect fit"
- "drive impact", "deliver value", "bring to the table", "skill set"
- "fast-paced", "high-growth", "mission-driven"
- "value-add", "value add", "high-impact", "high impact"
- "step into", "step change"

## B. Over-politeness / softeners (kill them all)
- "I appreciate your time" / "appreciate your time"
- "Thanks in advance" / "Thanks so much for"
- "No pressure" / "if it's not too much trouble"
- "If you have a moment" / "when you get a chance" / "at your convenience"
- "Any insights would be appreciated"
- "Hope to hear from you soon" / "Looking forward to hearing from you"
- "Please find attached"
- "Thank you for your time and consideration"
- "Just wanted to" / "I just wanted to"

## C. The "chat / discuss / connect" trap (banned — use a real ask instead)
- "chat", "quick chat", "happy to chat", "open to a (quick) chat", "20-min chat"
- "let's connect", "happy to connect", "open to connecting", "would love to connect"
- "discuss", "discuss the role", "discuss further", "discuss next steps", "discuss this further"
- "hop on a call" / "jump on a call" / "grab a few minutes" / "grab some time" / "find some time"
- "I would love the opportunity" / "I'd love the opportunity"
- (You may use "call", "intro call", "15 minutes", or a direct yes/no question. See ASK guidance below.)

## D. Recruiter flattery (insincere, kill on sight)
- "Given your role" / "Knowing you focus on"
- "Your work in talent" / "Your hiring focus"
- "I know you work with [the engineering team]"
- "Saw you're hiring for" / "I saw on LinkedIn"
- "Your team is doing inspiring work" / "amazing team" / "great culture"
- "Doing inspiring work" / "doing amazing work"

## E. Excitement / persona claims
- "I'm excited about" / "I am excited" / "thrilled" / "passionate about"
- "as a passionate [role]" / "as a driven [role]"

# Banned closers (use first name on its own line, or nothing)
- "Best regards,"
- "Kind regards,"
- "Warm regards,"
- "Sincerely,"
- "Cheers!" (the exclamation kills it)

# Channel constraints
- recruiter_email: 60–90 words. Subject rules below.
- linkedin_dm: 35–55 words. No greeting line ("Hi {name},"). Open with substance.
- networking_intro: 20–30 words. One sentence of context + one ask. Plain text only.

# Subject line guidance (recruiter_email only)
- ≤ 7 words. Factual. No question marks. No clickbait. No emoji.
- Banned prefixes: "Application for", "Regarding", "Re:", "Interest in",
  "Inquiry about", "Quick question", "Following up", "Reaching out".
- Good patterns (use the shape, fill with real content):
    - "Payments infra → {team}"
    - "{Specific skill or system} candidate, {team}"
    - "{Stack item} background, {Company} {team}"
    - "{Candidate's concrete project area}, looking at {team}"
- Bad examples (do not copy):
    - "Quick question about the role" (vague, banned prefix)
    - "Backend Engineer Application" (corporate, banned shape)
    - "Excited about Stripe!" (banned word + exclamation)

# The ASK — what to write instead of "chat/discuss/connect"
The closing ask is ONE sentence. It must be either:
  (a) A direct yes/no question:
        "Is this role still open?"
        "Are you the right person to talk to about this?"
        "Is the team still hiring backend engineers?"
        "Mind forwarding to the hiring manager if it's a fit?"
  (b) A concrete, time-bounded ask using "call", "intro call", or a duration:
        "Worth a 15-min call this week?"
        "Open to a 20-minute intro call this week?"
        "Free for a brief call Thursday or Friday?"
  (c) A specific technical question only the recruiter or hiring manager can answer:
        "Is the team still on Postgres, or moved to Spanner?"
        "Is this role IC or with reports?"
Use exactly ONE ask. Never combine (a)+(b)+(c).

# What to do when the candidate profile is sparse
- Write tighter. Lean harder on the JD-side specifics.
- Do NOT invent experience, project names, or numbers.
- If you cannot find a concrete tie-in, say so plainly ("I'm earlier in my career but...")
  rather than inventing one.
"""


# ---------------------------------------------------------------------
# Tone overlays. Each is appended to the base. Pick one per generation.
# ---------------------------------------------------------------------
TONE_PRESETS: dict[str, str] = {
    "concise": """# Tone: concise
- Aim for the LOW end of the word range for each channel.
- Cut every word that isn't load-bearing. Adjectives must carry information.
- Prefer two short sentences over one long one. Then prefer one over two.
- No throat-clearing. Skip the "wanted to reach out" framing entirely.
- Lead with the substance in the first 8 words.
""",
    "technical": """# Tone: technical
- Open with the specific technical detail that connects the candidate to the role.
- Use precise engineering vocabulary, not corporate vocabulary.
  - "exactly-once retry" not "robust transactions"
  - "p99 latency" not "performance"
  - "Postgres replication lag" not "the database layer"
- If the candidate's notable_projects names a real component or number, use it verbatim.
- One concrete technical hook in the first sentence.
- Still under the word limit. Technical does not mean dense.
""",
    "warm": """# Tone: warm
- Human, slightly more conversational. Not formal, not salesy.
- May reference a specific aspect of the company's work IF grounded in the JD context.
  Do not invent products or recent launches.
- Use contractions liberally ("I'm", "you've", "we've").
- Still NO flattery, NO "amazing team", NO "love what you're building".
- Close with the candidate's first name on a new line.
""",
    "founder-energy": """# Tone: founder-energy
- Scrappy, action-oriented, biased to shipping.
- Lead with what the candidate built, not what they're looking for.
- Use shipping verbs: "shipped", "rolled out", "owned end-to-end" — only if the candidate's projects support it.
- Slightly informal is OK. Bro-y is NOT OK ("hey hey", "wassup", "yo").
- Implies ownership and high agency without using the word "ownership".
- Shorter is stronger. Cut hedges ("kind of", "sort of", "I think").
""",
}

DEFAULT_TONE = "concise"


def outreach_system_prompt(tone: str) -> str:
    overlay = TONE_PRESETS.get(tone)
    if overlay is None:
        raise ValueError(f"unknown tone '{tone}'; valid: {list(TONE_PRESETS)}")
    return OUTREACH_BASE_SYSTEM + "\n" + overlay


OUTREACH_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["variants"],
    "properties": {
        "variants": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["channel", "subject", "body"],
                "properties": {
                    "channel": {
                        "type": "string",
                        "enum": ["recruiter_email", "linkedin_dm", "networking_intro"],
                    },
                    "subject": {"type": ["string", "null"]},
                    "body": {"type": "string"},
                },
            },
        }
    },
}


def build_outreach_user_prompt(
    *,
    candidate: dict,
    job: dict,
    company_name: str,
    recruiter: dict,
    channels: list[str],
) -> str:
    """Assemble the structured context block the model reasons over."""

    def _yoe(parsed: dict) -> str:
        lo, hi = parsed.get("yoe_min"), parsed.get("yoe_max")
        if lo is None and hi is None:
            return "unspecified"
        if hi is None:
            return f"{lo}+ years"
        return f"{lo}-{hi} years"

    def _list(items: list | None, sep: str = ", ", n: int = 12) -> str:
        if not items:
            return "—"
        return sep.join(str(x) for x in items[:n])

    job_block = (
        f"Title: {job.get('title') or 'unknown'}\n"
        f"Seniority: {job.get('seniority') or 'unknown'}\n"
        f"Required YoE: {_yoe(job)}\n"
        f"Location: {job.get('location') or 'unknown'} ({job.get('work_mode') or 'unknown'})\n"
        f"Tech stack: {_list(job.get('tech_stack'))}\n"
        f"Skills: {_list(job.get('skills'))}\n"
        f"Responsibilities: {_list(job.get('responsibilities'), sep='; ', n=5)}\n"
    )

    projects = candidate.get("notable_projects") or []
    project_lines = []
    for p in projects[:3]:
        if isinstance(p, dict):
            project_lines.append(
                f"- {p.get('name', 'project')}: {p.get('description', '')} "
                f"[{', '.join(p.get('stack', []))}]"
            )
        else:
            project_lines.append(f"- {p}")
    projects_block = "\n".join(project_lines) or "—"

    candidate_block = (
        f"Years of experience: {candidate.get('years_experience') or 'unspecified'}\n"
        f"Target role focus: {candidate.get('target_role') or 'unspecified'}\n"
        f"Skills: {_list(candidate.get('skills'))}\n"
        f"Summary: {candidate.get('summary') or '—'}\n"
        f"Notable projects:\n{projects_block}\n"
    )

    recruiter_block = (
        f"Name: {recruiter.get('full_name')}\n"
        f"Title: {recruiter.get('title') or 'unknown'}\n"
        f"Location: {recruiter.get('location') or 'unknown'}\n"
    )

    return f"""Generate outreach variants for these channels: {channels}.

# Company
{company_name}

# Role
{job_block}

# Recruiter (target of the message)
{recruiter_block}

# Candidate (sender)
{candidate_block}

Return one variant per requested channel. Follow every rule in the system message. If a draft would require breaking any rule, rewrite it.
"""


# =====================================================================
# Resume parsing
# =====================================================================

RESUME_PARSE_PROMPT_VERSION = "resume-v1"

RESUME_PARSE_SYSTEM = """You extract a candidate's professional profile from resume text into a strict schema.

Rules:
- Output ONLY fields present in the schema. If a field is not clearly supported by the resume, use null (or [] for arrays).
- Do NOT invent experience, projects, or numbers. If a metric is not in the resume, omit it.
- summary: 1-2 sentences describing the candidate's specialty and current focus. Synthesized, but grounded in the resume content. No marketing language.
- years_experience: integer. Compute from the earliest professional role to the latest (or today if current). Internships count as 0.5x. If the dates are ambiguous, return null.
- target_role: ONLY if the resume explicitly states a target role (objective line, "looking for" statement). Otherwise null.
- skills: lowercased canonical technical skills (languages, frameworks, databases, tools). Deduplicated. Skip soft skills, methodologies named without context, and tools mentioned only in passing.
- notable_projects: pick the top 3 most substantial projects/work items from the resume. Prefer items with concrete outcomes or scale. For each:
    - name: short, the project/system name as written in the resume, or a 2-4 word label if no name is given.
    - description: 1 sentence, what they built and the outcome. Use numbers from the resume verbatim if present.
    - stack: lowercased technical components used in that specific project.
- extraction_notes: 1-2 sentences. What was clear vs inferred. Mention if years_experience was inferred from dates, or if no target_role was found. Honest and specific.
"""

RESUME_PARSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "summary",
        "years_experience",
        "target_role",
        "skills",
        "notable_projects",
        "extraction_notes",
    ],
    "properties": {
        "summary": {"type": ["string", "null"]},
        "years_experience": {"type": ["number", "null"]},
        "target_role": {"type": ["string", "null"]},
        "skills": {"type": "array", "items": {"type": "string"}},
        "notable_projects": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "description", "stack"],
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "stack": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "extraction_notes": {"type": "string"},
    },
}


def build_resume_user_prompt(*, text: str) -> str:
    return f"Resume text follows. Extract the schema fields.\n---\n{text}"

