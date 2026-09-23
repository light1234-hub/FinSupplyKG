"""Corpus and preprocessing configuration for FinSupplyKG."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("FSKG_DATA_DIR", ROOT / "data"))

# US-domiciled issuers file 10-K; foreign private issuers file 20-F.
TICKERS_10K = ["NVDA", "INTC", "AMD", "AVGO", "QCOM", "TXN", "MU", "AMAT", "LRCX", "MRVL", "WDC"]
TICKERS_20F = ["TSM", "ASML"]
TICKERS = TICKERS_10K + TICKERS_20F


def form_for(ticker: str) -> str:
    return "20-F" if ticker in TICKERS_20F else "10-K"


@dataclass(frozen=True)
class SectionSpec:
    key: str                 # our canonical key
    item: str                # item number as printed in the filing ("1A", "4")
    datamule_title: str      # datamule standardized_title
    edgar_attr: str          # edgartools TenK / TwentyF property
    title_patterns: tuple[str, ...] = ()  # heading regexes for filings without "Item N" headings


# Sections that carry supplier / customer / dependency disclosures.
SECTIONS_10K = [
    SectionSpec("business", "1", "item1", "business", (r"business", r"fundamentals of our business")),
    SectionSpec("risk_factors", "1A", "item1a", "risk_factors", (r"risk factors",)),
    SectionSpec("mdna", "7", "item7", "management_discussion",
                (r"management'?s discussion and analysis(?: of financial condition and results of operations)?",)),
]
# Title alternatives after the first cover integrated annual reports filed as 20-F (ASML),
# whose body has no "Item N" headings.
SECTIONS_20F = [
    SectionSpec("key_information", "3", "item3", "risk_factors", (r"key information", r"risk factors")),
    SectionSpec("business", "4", "item4", "business",
                (r"information on the company", r"our business", r"our business model")),
    SectionSpec("operating_review", "5", "item5", "management_discussion",
                (r"operating and financial reviews? and prospects", r"financial performance")),
]


def sections_for(form: str) -> list[SectionSpec]:
    return SECTIONS_20F if form == "20-F" else SECTIONS_10K


@dataclass
class PipelineConfig:
    filing_start: str = "2024-01-01"
    filing_end: str = "2025-12-31"
    filings_per_ticker: int = 1          # most recent N original (non-amended) filings in window
    overlap_sentences: int = 7
    max_words_per_chunk: int = 800
    # Parser results outside this range are treated as misses: below it is a stub
    # (edgartools returns ~2k chars for Intel's Item 1), above it is most of the document.
    min_section_chars: int = 5_000
    max_section_chars: int = 250_000
    embedding_model: str = os.getenv("FSKG_EMBED_MODEL", "models/gemini-embedding-2")
    embedding_dim: int = 3072
    embed_batch_size: int = 32
    sec_identity: str = field(default_factory=lambda: os.getenv("SEC_IDENTITY", ""))
    tickers: list[str] = field(default_factory=lambda: list(TICKERS))
