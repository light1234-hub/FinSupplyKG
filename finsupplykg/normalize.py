"""Unicode / whitespace normalization for SEC filing text."""
from __future__ import annotations

import re
import unicodedata

# Characters NFKC leaves alone but which break tokenization / sentence splitting.
_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿­"), None)
_HYPHENS = {ord(c): "-" for c in "‐‑‒–−"}
_QUOTES = {ord("‘"): "'", ord("’"): "'", ord("“"): '"', ord("”"): '"'}

_INLINE_WS = re.compile(r"[^\S\n]+")
_MANY_NEWLINES = re.compile(r"\n\s*\n\s*\n+")
_PAGE_NOISE = re.compile(r"(?im)^\s*(?:table of contents|\d{1,3}|page \d+)\s*$")


def normalize_text(text: str) -> str:
    """NFKC-normalize, strip zero-width chars, unify hyphens/quotes, and tidy whitespace."""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_ZERO_WIDTH).translate(_HYPHENS).translate(_QUOTES)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _INLINE_WS.sub(" ", text)
    text = _PAGE_NOISE.sub("", text)
    text = "\n".join(_drop_repeated_lines(line.strip() for line in text.split("\n")))
    return _MANY_NEWLINES.sub("\n\n", text).strip()


def _drop_repeated_lines(lines):
    # Some HTML-to-text conversions (e.g. ASML's integrated annual report) emit each
    # layout line two or three times in a row.
    prev = None
    for line in lines:
        if line and line == prev:
            continue
        yield line
        prev = line if line else prev
