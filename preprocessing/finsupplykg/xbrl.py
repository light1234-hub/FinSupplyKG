"""Extract structured financial facts from SEC XBRL data."""

from __future__ import annotations

import requests

from edgar import Company

from .fetch import FilingRecord

from datetime import date


METRIC_TAGS = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ],

    "net_income": [
        "NetIncomeLoss",
        "ProfitLoss",
    ],

    "cash": [
        "CashAndCashEquivalentsAtCarryingValue",
    ],

    "assets": [
        "Assets",
    ],

    "inventory": [
        "InventoryNet",
    ],

    "operating_income": [
        "OperatingIncomeLoss",
    ],

    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
    ],

    "eps": [
        "EarningsPerShareDiluted",
    ],
}

def select_quarter_fact(
    candidates: list[dict],
    rec: FilingRecord
) -> dict | None:
    """Select the standalone current-quarter XBRL fact."""

    target_end = str(rec.period_of_report)

    current_period = []

    for candidate in candidates:
        start = candidate.get("start")
        end = candidate.get("end")

        if not start or not end:
            continue

        if str(end) != target_end:
            continue

        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)

        duration_days = (end_date - start_date).days

        current_period.append(
            (duration_days, candidate)
        )

    if not current_period:
        return None

    return min(
        current_period,
        key=lambda item: item[0]
    )[1]
def select_instant_fact(
    candidates: list[dict],
    rec: FilingRecord
) -> dict | None:
    """Select an instant XBRL fact for the filing period end date."""

    current_period = [
        candidate
        for candidate in candidates
        if candidate.get("end") == rec.period_of_report
    ]

    if not current_period:
        return None

    return current_period[0]

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

def format_fact(fact: dict | None) -> dict | None:
    """Convert a selected XBRL fact into a normalized record."""

    if fact is None:
        return None

    return {
        "value": fact.get("val"),
        "unit": fact.get("unit"),
        "concept": fact.get("concept"),
        "start": fact.get("start"),
        "end": fact.get("end"),
    }

def extract_financial_record(
    rec: FilingRecord,
    sec_identity: str
) -> dict:
    """Extract a normalized financial record from a filing."""

    revenue_candidates = extract_metric_candidates(
        rec,
        sec_identity,
        METRIC_TAGS["revenue"]
    )

    net_income_candidates = extract_metric_candidates(
        rec,
        sec_identity,
        METRIC_TAGS["net_income"]
    )

    cash_candidates = extract_metric_candidates(
        rec,
        sec_identity,
        METRIC_TAGS["cash"]
    )

    asset_candidates = extract_metric_candidates(
        rec,
        sec_identity,
        METRIC_TAGS["assets"]
    )

    inventory_candidates = extract_metric_candidates(
        rec,
        sec_identity,
        METRIC_TAGS["inventory"]
    )

    operating_income_candidates = extract_metric_candidates(
        rec,
        sec_identity,
        METRIC_TAGS["operating_income"]
    )

    eps_candidates = extract_metric_candidates(
        rec,
        sec_identity,
        METRIC_TAGS["eps"]
    )

    revenue = select_quarter_fact(
        revenue_candidates,
        rec
    )

    net_income = select_quarter_fact(
        net_income_candidates,
        rec
    )

    cash = select_instant_fact(
        cash_candidates,
        rec
    )

    assets = select_instant_fact(
        asset_candidates,
        rec
    )

    inventory = select_instant_fact(
        inventory_candidates,
        rec
    )

    operating_income = select_quarter_fact(
        operating_income_candidates,
        rec
    )

    eps = select_quarter_fact(
        eps_candidates,
        rec
    )


    return {
        "ticker": rec.ticker,
        "form": rec.form,
        "accession": rec.accession,
        "filing_date": rec.filing_date,
        "period_of_report": rec.period_of_report,

        "revenue": format_fact(revenue),
        "net_income": format_fact(net_income),
        "cash": format_fact(cash),
        "assets": format_fact(assets),
        "inventory": format_fact(inventory),
        "operating_income": format_fact(operating_income),
        "eps": format_fact(eps),
    }

