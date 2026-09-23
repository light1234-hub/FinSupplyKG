"""Section extraction with parser fallbacks.

10-K: datamule (AST, iXBRL-aware) -> edgartools property accessors -> regex slicer
20-F: regex slicer -> edgartools property accessors
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from datamule import Document
import warnings
from .config import PipelineConfig, SectionSpec, sections_for
from .fetch import FilingRecord
from .normalize import normalize_text
from .regex_slicer import slice_section

log = logging.getLogger(__name__)


@dataclass
class Section:
    ticker: str
    form: str
    accession: str
    filing_date: str
    section: str
    method: str    # datamule | edgartools | regex | full_text
    text: str


def _datamule_sections(rec: FilingRecord) -> Document | None:
    html = Path(rec.html_path).read_bytes()
    if not html:
        return None
    filename = rec.primary_document if rec.primary_document.endswith((".htm", ".html")) else "primary.htm"
    doc = Document(type=rec.form, content=html, filename=filename,
                   accession=rec.accession, filing_date=rec.filing_date)
    try:
        doc.parse()
    except Exception as e:  # datamule raises a variety of errors on unusual layouts
        log.warning("%s: datamule parse failed: %s", rec.ticker, e)
        return None
    return doc


def _from_datamule(
    doc: Document | None,
    spec: SectionSpec
) -> str:

    if doc is None or not spec.datamule_title:
        return ""

    try:
        parts = doc.get_section(
            title=spec.datamule_title,
            format="text"
        )
    except Exception as e:
        log.debug(
            "datamule get_section(%s) failed: %s",
            spec.datamule_title,
            e
        )
        return ""

    return max(parts, key=len) if parts else ""


def _from_edgartools(obj, spec: SectionSpec) -> str:
    if obj is None:
        return ""

    try:
        if spec.edgar_item:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)

                value = obj[spec.edgar_item]

            return value or ""

        if spec.edgar_attr:
            value = getattr(
                obj,
                spec.edgar_attr,
                None
            )

            return value or ""

    except Exception as e:
        log.debug(
            "edgartools extraction failed for %s: %s",
            spec.key,
            e
        )

    return ""

def minimum_section_chars(
    form: str,
    cfg: PipelineConfig
) -> int:
    if form == "8-K":
        return 500

    if form == "10-Q":
        return 2_000

    return cfg.min_section_chars

def extract_sections(
    rec: FilingRecord,
    filing,
    cfg: PipelineConfig
) -> list[Section]:

    full_text = normalize_text(
        Path(rec.text_path).read_text(
            encoding="utf-8"
        )
    )

    # 6-K filings do not follow the fixed Item structure used
    # by 10-K, 10-Q, 8-K and 20-F filings.
    # Treat the filing text as one narrative section.
    if rec.form == "6-K":
        if not full_text:
            log.warning(
                "%s %s: filing text is empty",
                rec.ticker,
                rec.form,
            )
            return []

        log.info(
            "%s %s: extracted full filing text (%d chars)",
            rec.ticker,
            rec.form,
            len(full_text),
        )

        return [
            Section(
                ticker=rec.ticker,
                form=rec.form,
                accession=rec.accession,
                filing_date=rec.filing_date,
                section="full_report",
                method="full_text",
                text=full_text,
            )
        ]

    specs = sections_for(rec.form)

    # Both are built lazily: datamule parsing and filing.obj() each take several seconds.
    cache: dict[str, object] = {}

    def dm():
        if "dm" not in cache:
            cache["dm"] = _datamule_sections(rec)
        return cache["dm"]

    def ed():
        if "ed" not in cache:
            try:
                cache["ed"] = filing.obj()
            except Exception as e:
                log.warning("%s: edgartools obj() failed: %s", rec.ticker, e)
                cache["ed"] = None
        return cache["ed"]

    strategies = {
        "datamule": lambda s: _from_datamule(dm(), s),
        "edgartools": lambda s: _from_edgartools(ed(), s),
        "regex": lambda s: slice_section(full_text, s, specs, cfg.max_section_chars),
    }
    if rec.form == "10-K":
        order = [
            "datamule",
            "edgartools",
            "regex"
        ]

    elif rec.form == "20-F":
        order = [
            "regex",
            "edgartools"
        ]

    elif rec.form in {"10-Q", "8-K"}:
        order = [
            "edgartools",
            "regex"
        ]

    else:
        order = []

    sections = []
    min_chars = minimum_section_chars(
        rec.form,
        cfg
    )
    for spec in specs:
        for method in order:
            text = normalize_text(strategies[method](spec))
            if min_chars <= len(text) <= cfg.max_section_chars:
                sections.append(Section(rec.ticker, rec.form, rec.accession, rec.filing_date,
                                        spec.key, method, text))
                log.info("%s %s: %s via %s (%d chars)", rec.ticker, rec.form, spec.key, method, len(text))
                break
            if text:
                log.info("%s %s: %s via %s rejected (%d chars)", rec.ticker, rec.form, spec.key, method, len(text))
        else:
            log.warning("%s %s: %s not found by any parser", rec.ticker, rec.form, spec.key)
    return sections
