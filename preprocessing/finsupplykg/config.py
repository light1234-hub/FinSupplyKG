"""Corpus and preprocessing configuration for FinSupplyKG."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("FSKG_DATA_DIR", ROOT / "data"))

# Companies currently included in the project.
# US issuers use 10-K, 10-Q and 8-K.
# Foreign private issuers use 20-F and 6-K.

COMPANIES = {
    # Chip designers
    "NVDA": {
        "name": "NVIDIA Corporation",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "AMD": {
        "name": "Advanced Micro Devices, Inc.",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "INTC": {
        "name": "Intel Corporation",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "AVGO": {
        "name": "Broadcom Inc.",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "QCOM": {
        "name": "QUALCOMM Incorporated",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "TXN": {
        "name": "Texas Instruments Incorporated",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "NXPI": {
        "name": "NXP Semiconductors N.V.",
        "forms": ["10-K", "10-Q", "8-K"],
    },

    "MU": {
        "name": "Micron Technology, Inc.",
        "forms": ["10-K", "10-Q", "8-K"],
    },

    # Chip equipment and design software
    "AMAT": {
        "name": "Applied Materials, Inc.",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "LRCX": {
        "name": "Lam Research Corporation",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "KLAC": {
        "name": "KLA Corporation",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "TER": {
        "name": "Teradyne, Inc.",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "SNPS": {
        "name": "Synopsys, Inc.",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "CDNS": {
        "name": "Cadence Design Systems, Inc.",
        "forms": ["10-K", "10-Q", "8-K"],
    },

    # Storage
    "WDC": {
        "name": "Western Digital Corporation",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "STX": {
        "name": "Seagate Technology Holdings plc",
        "forms": ["10-K", "10-Q", "8-K"],
    },

    # Networking and components
    "ANET": {
        "name": "Arista Networks, Inc.",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "CSCO": {
        "name": "Cisco Systems, Inc.",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "APH": {
        "name": "Amphenol Corporation",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "GLW": {
        "name": "Corning Incorporated",
        "forms": ["10-K", "10-Q", "8-K"],
    },

    # Servers
    "DELL": {
        "name": "Dell Technologies Inc.",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "SMCI": {
        "name": "Super Micro Computer, Inc.",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "HPE": {
        "name": "Hewlett Packard Enterprise Company",
        "forms": ["10-K", "10-Q", "8-K"],
    },

    # Big buyers
    "MSFT": {
        "name": "Microsoft Corporation",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "AMZN": {
        "name": "Amazon.com, Inc.",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "GOOGL": {
        "name": "Alphabet Inc.",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "META": {
        "name": "Meta Platforms, Inc.",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "ORCL": {
        "name": "Oracle Corporation",
        "forms": ["10-K", "10-Q", "8-K"],
    },
    "AAPL": {
        "name": "Apple Inc.",
        "forms": ["10-K", "10-Q", "8-K"],
    },

    # Automotive
    "TSLA": {
        "name": "Tesla, Inc.",
        "forms": ["10-K", "10-Q", "8-K"],
    },
}



TICKERS = list(COMPANIES.keys())


def forms_for(ticker: str) -> list[str]:
    """Return all SEC filing types monitored for a company."""
    return COMPANIES[ticker]["forms"]


@dataclass(frozen=True)
class SectionSpec:
    key: str                 # our canonical key
    item: str                # item number as printed in the filing ("1A", "4")
    datamule_title: str | None = None      # datamule standardized_title
    edgar_attr: str | None = None          # edgartools TenK / TwentyF property
    title_patterns: tuple[str, ...] = ()  # heading regexes for filings without "Item N" headings
    edgar_item: str | None = None

# Sections that carry supplier / customer / dependency disclosures.
SECTIONS_10K = [
    SectionSpec(
        "business",
        "1",
        "item1",
        "business",
        (
            r"business",
            r"our business",
            r"fundamentals of our business",
        ),
    ),
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
    SectionSpec(
        "operating_review",
        "5",
        "item5",
        "management_discussion",
        (
            r"operating and financial reviews? and prospects",
            r"financial\s+performance",
            r"message from our (?:executive vice president\s+and\s+)?chief financial officer",
        ),
    ),
]

SECTIONS_10Q = [
    SectionSpec(
        key="mdna",
        item="2",
        title_patterns=(
            r"management'?s discussion and analysis"
            r"(?: of financial condition and results of operations)?",
        ),
        edgar_item="Part I, Item 2",
    ),

    SectionSpec(
        key="risk_factors",
        item="1A",
        title_patterns=(
            r"risk factors",
        ),
        edgar_item="Part II, Item 1A",
    ),
]

SECTIONS_8K = [
    SectionSpec(
        key="material_agreement",
        item="1.01",
        title_patterns=(
            r"entry into a material definitive agreement",
        ),
        edgar_item="Item 1.01",
    ),

    SectionSpec(
        key="agreement_termination",
        item="1.02",
        title_patterns=(
            r"termination of a material definitive agreement",
        ),
        edgar_item="Item 1.02",
    ),

    SectionSpec(
        key="cybersecurity_incident",
        item="1.05",
        title_patterns=(
            r"material cybersecurity incidents?",
        ),
        edgar_item="Item 1.05",
    ),

    SectionSpec(
        key="acquisition_disposition",
        item="2.01",
        title_patterns=(
            r"completion of acquisition or disposition of assets",
        ),
        edgar_item="Item 2.01",
    ),

    SectionSpec(
        key="results_operations",
        item="2.02",
        title_patterns=(
            r"results of operations and financial condition",
        ),
        edgar_item="Item 2.02",
    ),

    SectionSpec(
        key="financial_obligation",
        item="2.03",
        title_patterns=(
            r"creation of a direct financial obligation",
        ),
        edgar_item="Item 2.03",
    ),

    SectionSpec(
        key="exit_disposal",
        item="2.05",
        title_patterns=(
            r"costs associated with exit or disposal activities",
        ),
        edgar_item="Item 2.05",
    ),

    SectionSpec(
        key="material_impairment",
        item="2.06",
        title_patterns=(
            r"material impairments?",
        ),
        edgar_item="Item 2.06",
    ),

    SectionSpec(
        key="equity_sales",
        item="3.02",
        title_patterns=(
            r"unregistered sales of equity securities",
        ),
        edgar_item="Item 3.02",
    ),

    SectionSpec(
        key="management_changes",
        item="5.02",
        title_patterns=(
            r"departure of directors or certain officers.*",
            r"election of directors.*",
            r"appointment of certain officers.*",
            r"compensatory arrangements of certain officers.*",
        ),
        edgar_item="Item 5.02",
    ),

    SectionSpec(
        key="regulation_fd",
        item="7.01",
        title_patterns=(
            r"regulation fd disclosure",
        ),
        edgar_item="Item 7.01",
    ),

    SectionSpec(
        key="other_events",
        item="8.01",
        title_patterns=(
            r"other events",
        ),
        edgar_item="Item 8.01",
    ),
]




def sections_for(form: str) -> list[SectionSpec]:
    if form == "10-K":
        return SECTIONS_10K

    if form == "10-Q":
        return SECTIONS_10Q

    if form == "8-K":
        return SECTIONS_8K

    if form == "20-F":
        return SECTIONS_20F

    if form == "6-K":
        return []

    raise ValueError(f"Unsupported filing form: {form}")


@dataclass
class PipelineConfig:
    filing_start: str | None = None
    filing_end: str | None = None
    filings_per_ticker: int = 5          # most recent N original (non-amended) filings in window
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
