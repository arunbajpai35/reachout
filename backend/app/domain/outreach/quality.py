"""Deterministic quality evaluator for outreach drafts.

Pure functions, no LLM. Each rule is a substring or regex match -- inspectable,
debuggable, fast (< 1ms per draft).

Add a rule by editing the lists or `_run_rules`. The evaluator is the spec.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Literal

Severity = Literal["block", "warn"]


@dataclass
class Violation:
    rule: str
    detail: str
    severity: Severity

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class QualityReport:
    channel: str
    word_count: int
    sentence_count: int
    avg_sentence_words: float
    max_sentence_words: int
    violations: list[Violation]
    score: float  # 0..1, 1.0 == no violations

    def to_dict(self) -> dict:
        return {
            "channel": self.channel,
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "avg_sentence_words": self.avg_sentence_words,
            "max_sentence_words": self.max_sentence_words,
            "violations": [v.to_dict() for v in self.violations],
            "score": self.score,
        }


# Mirror of the banned lists in OUTREACH_BASE_SYSTEM. If you edit the prompt,
# edit these too. They are the safety net.
FORBIDDEN_OPENERS = [
    "i hope this email finds you well",
    "i hope you're doing well",
    "i hope you are doing well",
    "i hope this message reaches you",
    "i am writing to express my interest",
    "i came across your profile",
    "i noticed that",
    "i stumbled upon",
    "hope i'm not bothering you",
    "trust you are doing well",
    "i saw on linkedin",
    "i saw your profile on linkedin",
]

# Banned phrases — kept in named groups so violation output identifies the category.
# Mirror of the lists in OUTREACH_BASE_SYSTEM. Update both when you tighten.

_BANNED_CORPORATE_FILLER = [
    "synergy", "leverage", "spearhead", "robust", "cutting-edge", "innovative",
    "best-in-class", "world-class", "game-changing", "scalable solutions",
    "results-oriented", "results-driven", "self-starter", "go-getter",
    "stakeholders",
    "team player", "wear many hats", "go above and beyond",
    "the right fit", "perfect fit",
    "drive impact", "deliver value", "bring to the table", "skill set",
    "fast-paced", "high-growth", "mission-driven",
    "value-add", "value add", "high-impact", "high impact",
    "step into", "step change",
]

_BANNED_OVER_POLITENESS = [
    "appreciate your time",
    "thanks in advance", "thanks so much for",
    "no pressure",
    "if it's not too much trouble",
    "if you have a moment", "when you get a chance", "at your convenience",
    "any insights would be appreciated",
    "hope to hear from you soon", "looking forward to hearing from you",
    "please find attached",
    "thank you for your time and consideration",
    "just wanted to", "i just wanted to",
]

_BANNED_CHAT_DISCUSS_CONNECT = [
    "quick chat", "happy to chat", "open to a chat", "open to a quick chat",
    "20-min chat", "20 min chat", "15-min chat", "15 min chat",
    "let's connect", "happy to connect", "open to connecting", "would love to connect",
    "discuss the role", "discuss further", "discuss next steps", "discuss this further",
    "hop on a call", "jump on a call",
    "grab a few minutes", "grab some time", "find some time", "find time to",
    "i would love the opportunity", "i'd love the opportunity",
    "happy to share more",
    # bare "chat" is intentionally a separate word-boundary rule below
]

_BANNED_RECRUITER_FLATTERY = [
    "given your role",
    "knowing you focus on",
    "your work in talent",
    "your hiring focus",
    "i know you work with",
    "saw you're hiring", "saw you are hiring",
    "i saw on linkedin", "saw your profile on linkedin",
    "amazing team", "great culture",
    "doing inspiring work", "doing amazing work",
    "your team is doing",
]

_BANNED_EXCITEMENT = [
    "i'm excited about", "i am excited about", "i am excited to",
    "thrilled to", "thrilled about",
    "passionate about",
    "as a passionate", "as a driven",
]

# Flat list (group, phrase) so the violation output names the category.
FORBIDDEN_PHRASE_GROUPS: list[tuple[str, list[str]]] = [
    ("corporate_filler", _BANNED_CORPORATE_FILLER),
    ("over_politeness", _BANNED_OVER_POLITENESS),
    ("chat_discuss_connect", _BANNED_CHAT_DISCUSS_CONNECT),
    ("recruiter_flattery", _BANNED_RECRUITER_FLATTERY),
    ("excitement", _BANNED_EXCITEMENT),
]

# Backwards-compat flat list (some callers / tests may import this).
FORBIDDEN_PHRASES: list[str] = [p for _, lst in FORBIDDEN_PHRASE_GROUPS for p in lst]

FORBIDDEN_CLOSERS = [
    "best regards",
    "kind regards",
    "warm regards",
    "sincerely",
]

CLICKBAIT_SUBJECT_PREFIXES = [
    "application for",
    "regarding",
    "interest in",
    "re:",
    "inquiry about",
    "quick question",
    "following up",
    "reaching out",
]

WORD_TARGETS: dict[str, tuple[int, int]] = {
    "recruiter_email": (60, 90),
    "linkedin_dm": (35, 55),
    "networking_intro": (20, 30),
}

MAX_SENTENCE_WORDS = 22
SUBJECT_MAX_WORDS = 7


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def _count_words(s: str) -> int:
    return len(re.findall(r"\b\w+\b", s))


def _last_nonblank_line(text: str) -> str:
    for line in reversed(text.strip().splitlines()):
        if line.strip():
            return line.strip()
    return ""


def evaluate_draft(*, channel: str, subject: str | None, body: str) -> QualityReport:
    violations: list[Violation] = []
    low = body.lower()
    head = low.lstrip()[:120]

    # Opener
    for opener in FORBIDDEN_OPENERS:
        if head.startswith(opener):
            violations.append(Violation("forbidden_opener", opener, "block"))
            break  # one is enough

    # Forbidden phrases (grouped so violation output identifies the category).
    for group, phrases in FORBIDDEN_PHRASE_GROUPS:
        for phrase in phrases:
            if phrase in low:
                violations.append(Violation(group, phrase, "block"))

    # Bare-word "chat" as a noun referencing a meeting -- catches "open to a chat",
    # "a chat", "any chat", and "chat with" without flagging unrelated uses.
    if re.search(r"\b(a|any|quick|brief)\s+chat\b", low) or re.search(r"\bchat\s+with\b", low):
        violations.append(Violation("chat_discuss_connect", "bare 'chat'", "block"))
    # Same for "to discuss" as an ask suffix.
    if re.search(r"\b(would like|want|hoping|looking)\s+to\s+discuss\b", low):
        violations.append(Violation("chat_discuss_connect", "to discuss (as ask)", "block"))

    # Closer
    last = _last_nonblank_line(body).lower().rstrip(",.").strip()
    for closer in FORBIDDEN_CLOSERS:
        if last == closer or last.startswith(closer + ","):
            violations.append(Violation("forbidden_closer", closer, "block"))
            break

    # Punctuation
    if "—" in body or "–" in body:
        violations.append(Violation("em_dash", "em/en dash present", "block"))
    bang_count = body.count("!")
    if bang_count > 1:
        violations.append(
            Violation("excess_exclamation", f"{bang_count} exclamation marks", "warn")
        )
    if ";" in body:
        violations.append(Violation("semicolon", "semicolon present", "warn"))
    if "..." in body or "…" in body:
        violations.append(Violation("ellipsis", "ellipsis present", "warn"))

    # Sentence-length stats
    sentences = _split_sentences(body)
    if sentences:
        lens = [_count_words(s) for s in sentences]
        avg = round(sum(lens) / len(lens), 1)
        mx = max(lens)
        if mx > MAX_SENTENCE_WORDS:
            violations.append(
                Violation("sentence_too_long", f"{mx} words in one sentence", "warn")
            )
    else:
        avg, mx = 0.0, 0

    # Word-count target
    wc = _count_words(body)
    lo, hi = WORD_TARGETS.get(channel, (0, 9999))
    if wc < lo:
        violations.append(Violation("under_word_target", f"{wc} < {lo}", "warn"))
    elif wc > hi:
        violations.append(Violation("over_word_target", f"{wc} > {hi}", "warn"))

    # Subject sanity (email only)
    if channel == "recruiter_email" and subject:
        sub_low = subject.lower().strip()
        for bad in CLICKBAIT_SUBJECT_PREFIXES:
            if sub_low.startswith(bad):
                violations.append(Violation("clickbait_subject", subject, "block"))
                break
        if _count_words(subject) > SUBJECT_MAX_WORDS:
            violations.append(
                Violation("subject_too_long", f"{_count_words(subject)} words", "warn")
            )
        if "?" in subject:
            violations.append(Violation("subject_question_mark", subject, "block"))
        if "!" in subject:
            violations.append(Violation("subject_exclamation", subject, "block"))

    # Score: -0.15 per block, -0.05 per warn, floored at 0.
    score = 1.0
    for v in violations:
        score -= 0.15 if v.severity == "block" else 0.05
    score = max(0.0, round(score, 2))

    return QualityReport(
        channel=channel,
        word_count=wc,
        sentence_count=len(sentences),
        avg_sentence_words=avg,
        max_sentence_words=mx,
        violations=violations,
        score=score,
    )
