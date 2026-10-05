"""Regex-based section slicer for normalized filing text.

Works on text that has already been through ``normalize_text`` (NFKC turns the thin
spaces in headings like ``ITEM 4.`` into plain spaces). A section heading usually
appears twice: once in the table of contents and once in the body. Every heading
occurrence is tried as a start, and the longest resulting span is kept, which
selects the body copy over the TOC stub.
"""
from __future__ import annotations

import re

from .config import SectionSpec

_ANY_ITEM = re.compile(
    r"(?im)^(?:part\s+[ivx]+\s*[,.\-]?\s*)?"
    r"item\s+(\d{1,2}(?:\.\d{2})?[a-z]?)(?![0-9a-z])"
)

# Headings of other sections. They mark where a section ends in filings whose headings do
# not start with "Item N" (e.g. Intel's FY2024 10-K).
_OTHER_TITLES = [
    r"unresolved staff comments", r"cybersecurity", r"properties", r"legal proceedings",
    r"mine safety disclosures", r"market for (?:the )?registrant'?s common equity.*",
    r"quantitative and qualitative disclosures? about market risks?",
    r"financial statements(?: and supplement\w+ (?:data|details))?", r"controls and procedures",
    r"changes in and disagreements with accountants.*", r"other information",
    r"directors, (?:executive officers|senior management).*", r"executive compensation",
    r"exhibits(?: and financial statement schedules)?", r"major shareholders.*",
    r"financial information", r"the offer and listing", r"additional information",
    r"identity of directors.*", r"offer statistics.*",
    # Top-level sections of integrated annual reports filed as 20-F (ASML).
    r"risk\s+and\s+security",
    r"information security",
    r"corporate conduct",
    r"corporate governance",
    r"sustainability statements?",
]


def _title_line(title: str) -> re.Pattern[str]:
    # The whole line is the heading, with an optional "Item N." prefix and an optional
    # trailing page reference as printed in tables of contents ("Risk Factors 31", "Properties 8, 49").
    # A trailing "." is not allowed: in hard-wrapped text, lines like "our business." are sentence ends.
    return re.compile(
        rf"(?im)^"
        rf"(?:item\s+\d{{1,2}}(?:\.\d{{2}})?[a-z]?\s*[.:\-]?\s*)?"
        rf"{title}"
        rf"\s*:?"
        rf"(?:\s+\d{{1,3}}(?:\s*[-,]\s*\d{{1,3}})*)?"
        rf"\s*$"
    )


def slice_section(text: str, spec: SectionSpec, all_specs: list[SectionSpec], max_chars: int = 250_000) -> str:
    """Return the longest span of ``text`` that starts at a heading for ``spec``.

    Spans longer than ``max_chars`` are discarded: they mean the end boundary was missed
    and the slice has swallowed the rest of the document.
    """
    own_item = spec.item.lower()
    starts = [m.start() for m in _ANY_ITEM.finditer(text) if m.group(1).lower() == own_item]
    for title in spec.title_patterns:
        starts += [m.start() for m in _title_line(title).finditer(text)]

    boundaries = [m.start() for m in _ANY_ITEM.finditer(text) if m.group(1).lower() != own_item]
    other_titles = [t for s in all_specs if s.key != spec.key for t in s.title_patterns] + _OTHER_TITLES
    for title in other_titles:
        boundaries += [m.start() for m in _title_line(title).finditer(text)]
    boundaries.sort()

    best = ""
    for s in sorted(set(starts)):
        end = next((b for b in boundaries if b > s), len(text))
        if len(best) < end - s <= max_chars:
            best = text[s:end]
    return best.strip()
