"""Deterministic PDF text extraction.

Uses pdfplumber (MIT-licensed). No OCR. If the PDF is image-only the extracted text
will be empty or near-empty -- callers detect that and surface a clear error rather
than silently degrading.
"""
from __future__ import annotations

import io
import re

import pdfplumber

from app.core.errors import ValidationError

# Heuristic: anything under this many chars is almost certainly a scanned PDF or
# a malformed file. Real resumes are always 1k+ characters of text.
MIN_USEFUL_TEXT = 400


def extract_pdf_text(data: bytes) -> str:
    """Return cleaned text from a PDF byte payload.

    Raises ValidationError with a user-friendly message if the PDF appears
    image-only or unreadable.
    """
    if not data:
        raise ValidationError("uploaded file is empty")

    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages: list[str] = []
            for page in pdf.pages:
                txt = page.extract_text() or ""
                pages.append(txt)
    except Exception as e:  # pdfplumber raises a wide range; normalize.
        raise ValidationError(f"could not read PDF: {e}") from e

    text = "\n\n".join(p.strip() for p in pages if p and p.strip())
    text = _normalize_whitespace(text)

    if len(text) < MIN_USEFUL_TEXT:
        raise ValidationError(
            "This PDF appears to be a scanned image (no embedded text). "
            "Please re-export from your source (Word/Docs/LaTeX) as a text-based PDF."
        )
    return text


def _normalize_whitespace(text: str) -> str:
    # Collapse runs of spaces, strip trailing whitespace per line, drop empty lines that pile up.
    text = re.sub(r"[ \t]+", " ", text)
    lines = [ln.rstrip() for ln in text.splitlines()]
    out: list[str] = []
    blank_run = 0
    for ln in lines:
        if not ln:
            blank_run += 1
            if blank_run <= 1:
                out.append("")
        else:
            blank_run = 0
            out.append(ln)
    return "\n".join(out).strip()
