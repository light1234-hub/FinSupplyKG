"""Unicode / whitespace normalization for SEC filing text."""

from __future__ import annotations

import re
import unicodedata


_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿­"), None)
_HYPHENS = {ord(c): "-" for c in "‐-‒–−"}
_QUOTES = {
    ord("‘"): "'",
    ord("’"): "'",
    ord("“"): '"',
    ord("”"): '"',
}

_INLINE_WS = re.compile(r"[^\S\n]+")
_MANY_NEWLINES = re.compile(r"\n\s*\n\s*\n+")
_PAGE_NOISE = re.compile(
    r"(?im)^\s*(?:table of contents|\d{1,3}|page \d+)\s*$"
)
_FILING_PAGE_HEADER = re.compile(
    r"(?i)^"
    r"\s*[^|\n]{2,100}"
    r"\s*\|\s*"
    r"20\d{2}\s+Form\s+"
    r"(?:10-K|10-Q|8-K|20-F|6-K)"
    r"\s*\|\s*\d+"
    r"\s*$"
)


def normalize_text(text: str) -> str:
    """Normalize SEC text without removing semantic information."""

    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)

    text = (
        text.translate(_ZERO_WIDTH)
        .translate(_HYPHENS)
        .translate(_QUOTES)
    )

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _INLINE_WS.sub(" ", text)
    text = _PAGE_NOISE.sub("", text)

    text = "\n".join(
        line
        for line in text.split("\n")
        if not _FILING_PAGE_HEADER.fullmatch(line.strip())
    )

    text = "\n".join(
        _drop_repeated_lines(
            line.strip()
            for line in text.split("\n")
        )
    )

    text = _MANY_NEWLINES.sub("\n\n", text).strip()

    return deduplicate_paragraphs(text)


def deduplicate_paragraphs(text: str) -> str:
    """Remove exact repeated long paragraphs while preserving order."""

    paragraphs = re.split(r"\n\s*\n", text)

    seen = set()
    cleaned = []

    for paragraph in paragraphs:
        paragraph = paragraph.strip()

        if not paragraph:
            continue

        key = " ".join(paragraph.split())

        if len(key) >= 80:
            if key in seen:
                continue

            seen.add(key)

        cleaned.append(paragraph)

    return "\n\n".join(cleaned)


def _drop_repeated_lines(lines):
    """Remove immediately repeated layout lines."""

    prev = None

    for line in lines:
        if line and line == prev:
            continue

        yield line

        if line:
            prev = line
