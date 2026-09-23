"""Extract structured financial facts from SEC XBRL data."""

from __future__ import annotations

import requests

from edgar import Company

from .fetch import FilingRecord

from datetime import date


REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
]

NET_INCOME_TAGS = [
    "NetIncomeLoss",
]

CASH_TAGS = [
    "CashAndCashEquivalentsAtCarryingValue",
]

ASSET_TAGS = [
    "Assets",
]

INVENTORY_TAGS = [
    "InventoryNet",
]

def select_quarter_fact(
    candidates: list[dict],
    rec: FilingRecord
) -> dict | None:
    """Select the current standalone quarter from 10-Q XBRL facts."""

    current_period = [
        candidate
        for candidate in candidates
        if candidate.get("end") == rec.period_of_report
        and candidate.get("start")
    ]

    if not current_period:
        return None

    def duration(candidate: dict) -> int:
        start = date.fromisoformat(candidate["start"])
        end = date.fromisoformat(candidate["end"])

        return (end - start).days

    return min(
        current_period,
        key=duration
    )

def get_company_facts(
    ticker: str,
    sec_identity: str
) -> dict:
    """Download CompanyFacts XBRL data for a company."""

    company = Company(ticker)

    cik = str(company.cik).zfill(10)

    url = (
        "https://data.sec.gov/api/xbrl/"
        f"companyfacts/CIK{cik}.json"
    )

    headers = {
        "User-Agent": sec_identity
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def find_concept(
    company_facts: dict,
    possible_tags: list[str],
    taxonomy: str = "us-gaap"
) -> tuple[str | None, dict | None]:
    """Return the first matching XBRL concept."""

    facts = company_facts["facts"].get(
        taxonomy,
        {}
    )

    for tag in possible_tags:
        if tag in facts:
            return tag, facts[tag]

    return None, None


def facts_for_accession(
    concept: dict,
    accession: str
) -> list[dict]:
    """Return observations reported in a specific SEC filing."""

    matches = []

    for unit, observations in concept.get(
        "units",
        {}
    ).items():

        for observation in observations:

            if observation.get("accn") == accession:

                matches.append({
                    **observation,
                    "unit": unit,
                })

    return matches


def extract_metric_candidates(
    rec: FilingRecord,
    sec_identity: str,
    tags: list[str]
) -> list[dict]:
    """Extract XBRL observations for a metric from a specific filing."""

    company_facts = get_company_facts(
        rec.ticker,
        sec_identity
    )

    facts = company_facts["facts"].get(
        "us-gaap",
        {}
    )

    candidates = []

    for tag in tags:

        concept = facts.get(tag)

        if concept is None:
            continue

        matches = facts_for_accession(
            concept,
            rec.accession
        )

        for match in matches:
            match["concept"] = tag
            candidates.append(match)

    return candidates