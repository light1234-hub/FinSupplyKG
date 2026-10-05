"""Sentence segmentation (pySBD) and overlapping chunk construction."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

import pysbd

from .parse import Section

_SEGMENTER = pysbd.Segmenter(language="en", clean=False)
_PARAGRAPH = re.compile(r"\n\s*\n")


@dataclass
class Chunk:
    chunk_id: str
    ticker: str
    form: str
    accession: str
    filing_date: str
    section: str
    method: str
    index: int            # position within its section
    text: str             # ticker-prefixed text that gets indexed and embedded
    raw_text: str         # the chunk without the prefix


def split_sentences(text: str) -> list[str]:
    # Segmenting paragraph by paragraph is much faster than one call on a 100k-char
    # section, and stops sentences from running across paragraph breaks.
    sentences = []
    for para in _PARAGRAPH.split(text):
        para = " ".join(para.split())
        if para:
            sentences += [s.strip() for s in _SEGMENTER.segment(para) if s.strip()]
    return sentences

def window_sentences(
    sentences: list[str],
    max_words: int,
    overlap: int,
) -> list[list[str]]:
    """Pack sentences into windows of <= max_words.

    Each window repeats the previous window's last `overlap`
    sentences. A single sentence longer than max_words becomes
    its own window.
    """

    windows = []
    i = 0

    while i < len(sentences):
        window = []
        words = 0
        j = i

        while j < len(sentences):
            n = len(sentences[j].split())

            if window and words + n > max_words:
                break

            window.append(sentences[j])
            words += n
            j += 1

        windows.append(window)

        if j >= len(sentences):
            break

        i = max(j - overlap, i + 1)

    return windows


def chunk_section(sec: Section, max_words: int, overlap: int) -> list[Chunk]:
    chunks = []
    for idx, window in enumerate(window_sentences(split_sentences(sec.text), max_words, overlap)):
        raw = " ".join(window)
        text = f"[{sec.ticker}] {raw}"
        cid = hashlib.sha1(f"{sec.accession}|{sec.section}|{idx}|{raw}".encode()).hexdigest()[:16]
        chunks.append(Chunk(cid, sec.ticker, sec.form, sec.accession, sec.filing_date,
                            sec.section, sec.method, idx, text, raw))
    return chunks
