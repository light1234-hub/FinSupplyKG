"""Extract structured financial facts from SEC XBRL data."""

from __future__ import annotations

import requests

from edgar import Company

from .fetch import FilingRecord

from datetime import date

import math

FOREIGN_REPORTING_CURRENCY = {
    "TSM": "TWD",
    "ASML": "EUR",
}
FINANCIAL_METRICS = (
    "revenue",
    "net_income",
    "cash",
    "assets",
    "inventory",
    "operating_income",
    "eps",
)

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

IFRS_METRIC_TAGS = {
    "revenue": "ifrs-full:RevenueFromContractsWithCustomers",
    "net_income": "ifrs-full:ProfitLoss",
    "cash": "ifrs-full:CashAndCashEquivalents",
    "assets": "ifrs-full:Assets",
    "inventory": "ifrs-full:Inventories",
    "operating_income": "ifrs-full:ProfitLossFromOperatingActivities",
    "eps": "ifrs-full:DilutedEarningsLossPerShare",
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

def select_annual_fact(
    candidates: list[dict],
    rec: FilingRecord
) -> dict | None:
    """Select the current annual duration fact."""

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

    return max(
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

def select_ifrs_duration_fact(
    xbrl,
    concept: str,
    rec: FilingRecord
) -> dict | None:
    """Select the consolidated annual IFRS fact in the reporting currency."""

    currency = FOREIGN_REPORTING_CURRENCY.get(
        rec.ticker
    )

    df = (
        xbrl.facts
        .query()
        .by_concept(
            concept,
            exact=True
        )
        .by_dimension(None)
        .to_dataframe()
    )

    if df.empty:
        return None

    target_end = str(rec.period_of_report)

    matches = df[
        (df["period_end"].astype(str) == target_end)
        & (df["period_type"] == "duration")
        & (df["currency"] == currency)
    ]

    if matches.empty:
        return None

    if "fiscal_period" in matches.columns:

        annual = matches[
            matches["fiscal_period"] == "FY"
        ]

        if not annual.empty:
            matches = annual

    if "statement_type" in matches.columns:

        statement_matches = matches[
            matches["statement_type"]
            == "IncomeStatement"
        ]

        if not statement_matches.empty:
            matches = statement_matches

    row = matches.iloc[0]

    value = row.get("numeric_value")

    if hasattr(value, "item"):
        value = value.item()

    if isinstance(value, float) and value.is_integer():
        value = int(value)

    return {
        "value": value,
        "unit": row.get("unit_ref"),
        "currency": row.get("currency"),
        "concept": row.get("concept"),
        "taxonomy": "ifrs-full",
        "start": row.get("period_start"),
        "end": row.get("period_end"),
    }

def select_ifrs_instant_fact(
    xbrl,
    concept: str,
    rec: FilingRecord
) -> dict | None:
    """Select a consolidated IFRS instant fact in the reporting currency."""

    currency = FOREIGN_REPORTING_CURRENCY.get(
        rec.ticker
    )

    df = (
        xbrl.facts
        .query()
        .by_concept(
            concept,
            exact=True
        )
        .by_dimension(None)
        .to_dataframe()
    )

    if df.empty:
        return None

    target_end = str(rec.period_of_report)

    matches = df[
        (df["period_instant"].astype(str) == target_end)
        & (df["period_type"] == "instant")
        & (df["currency"] == currency)
    ]

    if matches.empty:
        return None

    row = matches.iloc[0]

    value = row.get("numeric_value")

    if hasattr(value, "item"):
        value = value.item()

    if isinstance(value, float) and value.is_integer():
        value = int(value)

    return {
        "value": value,
        "unit": row.get("unit_ref"),
        "currency": row.get("currency"),
        "concept": row.get("concept"),
        "taxonomy": "ifrs-full",
        "start": None,
        "end": row.get("period_instant"),
    }
def extract_ifrs_financial_record(
    rec: FilingRecord,
    filing
) -> dict:
    """Extract normalized financial metrics from a 20-F filing."""

    xbrl = filing.xbrl()

    if xbrl is None:
        raise ValueError(
            f"No filing-level XBRL found for {rec.ticker}"
        )

    revenue = select_ifrs_duration_fact(
        xbrl,
        IFRS_METRIC_TAGS["revenue"],
        rec
    )

    net_income = select_ifrs_duration_fact(
        xbrl,
        IFRS_METRIC_TAGS["net_income"],
        rec
    )

    operating_income = select_ifrs_duration_fact(
        xbrl,
        IFRS_METRIC_TAGS["operating_income"],
        rec
    )

    eps = select_ifrs_duration_fact(
        xbrl,
        IFRS_METRIC_TAGS["eps"],
        rec
    )

    cash = select_ifrs_instant_fact(
        xbrl,
        IFRS_METRIC_TAGS["cash"],
        rec
    )

    assets = select_ifrs_instant_fact(
        xbrl,
        IFRS_METRIC_TAGS["assets"],
        rec
    )

    inventory = select_ifrs_instant_fact(
        xbrl,
        IFRS_METRIC_TAGS["inventory"],
        rec
    )

    return {
        "ticker": rec.ticker,
        "form": rec.form,
        "accession": rec.accession,
        "filing_date": rec.filing_date,
        "period_of_report": rec.period_of_report,

        "revenue": revenue,
        "net_income": net_income,
        "cash": cash,
        "assets": assets,
        "inventory": inventory,
        "operating_income": operating_income,
        "eps": eps,
    }
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

def taxonomy_for_filing(
    rec: FilingRecord,
    company_facts: dict
) -> str:
    """Choose the XBRL taxonomy used by the filing."""

    available = company_facts.get("facts", {})

    if rec.form in {"20-F", "6-K"}:
        if "ifrs-full" in available:
            return "ifrs-full"

    if "us-gaap" in available:
        return "us-gaap"

    if "ifrs-full" in available:
        return "ifrs-full"

    raise ValueError(
        f"No supported XBRL taxonomy found for {rec.ticker}"
    )

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
def inspect_filing_xbrl(
    rec: FilingRecord,
    sec_identity: str
) -> None:
    """Print taxonomies and XBRL concepts used by a filing."""

    company_facts = get_company_facts(
        rec.ticker,
        sec_identity
    )

    all_facts = company_facts.get("facts", {})

    print("Available taxonomies:")
    for taxonomy in all_facts:
        print(" -", taxonomy)

    print("\nConcepts for accession:", rec.accession)

    found = 0

    for taxonomy, concepts in all_facts.items():

        for tag, concept in concepts.items():

            matches = facts_for_accession(
                concept,
                rec.accession
            )

            if matches:
                print(
                    taxonomy,
                    tag,
                    "->",
                    len(matches),
                    "fact(s)"
                )

                found += 1

    print("\nTotal concepts found:", found)

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

    taxonomy = taxonomy_for_filing(
        rec,
        company_facts
    )

    facts = company_facts["facts"].get(
        taxonomy,
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
            match["taxonomy"] = taxonomy
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
        "taxonomy": fact.get("taxonomy"),
        "start": fact.get("start"),
        "end": fact.get("end"),
    }

def extract_financial_record(
    rec: FilingRecord,
    filing,
    sec_identity: str
) -> dict:
    """Extract a normalized financial record from a filing."""

    if rec.form == "20-F":
        return extract_ifrs_financial_record(
            rec,
            filing
        )

    if rec.form not in {"10-Q", "10-K"}:
        raise ValueError(
            f"Unsupported form for structured financial extraction: {rec.form}"
        )

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


    if rec.form == "10-K":

        revenue = select_annual_fact(
            revenue_candidates,
            rec
        )

        net_income = select_annual_fact(
            net_income_candidates,
            rec
        )

        operating_income = select_annual_fact(
            operating_income_candidates,
            rec
        )

        eps = select_annual_fact(
            eps_candidates,
            rec
        )

    else:

        revenue = select_quarter_fact(
            revenue_candidates,
            rec
        )

        net_income = select_quarter_fact(
            net_income_candidates,
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
def select_statement_period_column(
    df,
    rec: FilingRecord
) -> str | None:

    target_date = str(rec.period_of_report)

    candidates = [
        column
        for column in df.columns
        if str(column).startswith(target_date)
    ]

    if not candidates:
        return None

    if rec.form == "10-Q":

        quarter_columns = [
            column
            for column in candidates
            if "(Q" in str(column)
            and "(YTD)" not in str(column)
        ]

        if quarter_columns:
            return quarter_columns[0]

    if rec.form in {"10-K", "20-F"}:

        annual_columns = [
            column
            for column in candidates
            if "(FY)" in str(column)
        ]

        if annual_columns:
            return annual_columns[0]

    return candidates[0]

def get_standard_metric(
    df,
    rec: FilingRecord,
    standard_concept: str,
    raw_concepts: tuple[str, ...] = ()
) -> dict | None:
    """Extract a metric from a standardized financial statement."""

    period_column = select_statement_period_column(
        df,
        rec
    )

    if period_column is None:
        return None

    matches = df[
        df["standard_concept"] == standard_concept
    ]

    matches = matches[
        matches["is_breakdown"] != True
    ]

    if matches.empty and raw_concepts:

        def local_concept_name(concept) -> str:
            concept = str(concept)

            if ":" in concept:
                return concept.split(":", 1)[1]

            if "_" in concept:
                return concept.split("_", 1)[1]

            return concept

        local_names = df["concept"].apply(
            local_concept_name
        )

        matches = df[
            local_names.isin(raw_concepts)
        ]

        matches = matches[
            matches["is_breakdown"] != True
        ]

    if matches.empty:
        return None

    for _, row in matches.iterrows():

        value = row.get(period_column)

        if value is None:
            continue

        try:
            if value != value:
                continue
        except TypeError:
            pass

        if hasattr(value, "item"):
            value = value.item()

        if isinstance(value, float) and value.is_integer():
            value = int(value)

        standard = row.get("standard_concept")

        try:
            if standard != standard:
                standard = None
        except TypeError:
            pass

        return {
            "value": value,
            "concept": row.get("concept"),
            "standard_concept": standard,
            "label": row.get("label"),
            "period": period_column,
        }

    return None
def _to_xbrl_concept(concept: str) -> str:
    """Convert statement concept names to XBRL namespace format."""

    if ":" in concept:
        return concept

    if "_" in concept:
        prefix, name = concept.split("_", 1)
        return f"{prefix}:{name}"

    return concept


def _normalise_number(value):

    if hasattr(value, "item"):
        value = value.item()

    if isinstance(value, float) and value.is_integer():
        return int(value)

    return value


def _same_value(left, right) -> bool:

    left = _normalise_number(left)
    right = _normalise_number(right)

    if isinstance(left, int) and isinstance(right, int):
        return left == right

    if isinstance(left, (int, float)) and isinstance(
        right,
        (int, float)
    ):
        return math.isclose(
            float(left),
            float(right),
            rel_tol=1e-9,
            abs_tol=1e-9
        )

    return left == right


def add_fact_metadata(
    xbrl,
    rec: FilingRecord,
    metric: dict | None,
    period_type: str
) -> dict | None:
    """Add unit and currency from the underlying XBRL fact."""

    if metric is None:
        return None

    concept = _to_xbrl_concept(
        metric["concept"]
    )

    df = (
        xbrl.facts
        .query()
        .by_concept(concept, exact=True)
        .by_dimension(None)
        .to_dataframe()
    )

    result = dict(metric)

    if df.empty:
        result["unit"] = None
        result["currency"] = None
        return result

    target_date = str(rec.period_of_report)

    matches = df[
        df["period_type"] == period_type
    ]

    if period_type == "duration":

        matches = matches[
            matches["period_end"].astype(str)
            == target_date
        ]

    elif period_type == "instant":

        matches = matches[
            matches["period_instant"].astype(str)
            == target_date
        ]

    selected = None

    for _, row in matches.iterrows():

        if _same_value(
            row.get("numeric_value"),
            metric["value"]
        ):
            selected = row
            break

    if selected is None:
        result["unit"] = None
        result["currency"] = None
        return result

    result["unit"] = selected.get("unit_ref")
    result["currency"] = selected.get("currency")

    return result
def extract_standardized_financial_record(
    rec: FilingRecord,
    filing
) -> dict:
    """Extract normalized metrics from standardized XBRL statements."""

    xbrl = filing.xbrl()

    if xbrl is None:
        raise ValueError(
            f"No XBRL available for {rec.ticker} {rec.form}"
        )

    income_df = (
        xbrl.statements
        .income_statement()
        .to_dataframe(view="summary")
    )

    balance_df = (
        xbrl.statements
        .balance_sheet()
        .to_dataframe(view="summary")
    )

    revenue = get_standard_metric(
        income_df,
        rec,
        "Revenue",
        raw_concepts=(
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "SalesRevenueNet",
            "RevenueFromContractsWithCustomers",
        )
    )

    net_income = get_standard_metric(
        income_df,
        rec,
        "NetIncome",
        raw_concepts=(
            "NetIncomeLoss",
            "ProfitLossAttributableToOwnersOfParent",
            "ProfitLoss",
        )
    )

    operating_income = get_standard_metric(
        income_df,
        rec,
        "OperatingIncomeLoss",
        raw_concepts=(
            "OperatingIncomeLoss",
            "ProfitLossFromOperatingActivities",
        )
    )

    eps = get_standard_metric(
        income_df,
        rec,
        "EarningsPerShareDiluted",
        raw_concepts=(
            "EarningsPerShareDiluted",
            "DilutedEarningsLossPerShare",
        )
    )

    cash = get_standard_metric(
        balance_df,
        rec,
        "CashAndCashEquivalents",
        raw_concepts=(
            "CashAndCashEquivalentsAtCarryingValue",
            "CashAndCashEquivalents",
            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        )
    )

    assets = get_standard_metric(
        balance_df,
        rec,
        "Assets",
        raw_concepts=(
            "Assets",
        )
    )

    inventory = get_standard_metric(
        balance_df,
        rec,
        "Inventories",
        raw_concepts=(
            "InventoryNet",
            "Inventories",
        )
    )

    revenue = add_fact_metadata(
        xbrl,
        rec,
        revenue,
        "duration"
    )

    net_income = add_fact_metadata(
        xbrl,
        rec,
        net_income,
        "duration"
    )

    operating_income = add_fact_metadata(
        xbrl,
        rec,
        operating_income,
        "duration"
    )

    eps = add_fact_metadata(
        xbrl,
        rec,
        eps,
        "duration"
    )

    cash = add_fact_metadata(
        xbrl,
        rec,
        cash,
        "instant"
    )

    assets = add_fact_metadata(
        xbrl,
        rec,
        assets,
        "instant"
    )

    inventory = add_fact_metadata(
        xbrl,
        rec,
        inventory,
        "instant"
    )

    return {
        "ticker": rec.ticker,
        "form": rec.form,
        "accession": rec.accession,
        "filing_date": rec.filing_date,
        "period_of_report": rec.period_of_report,

        "revenue": revenue,
        "net_income": net_income,
        "cash": cash,
        "assets": assets,
        "inventory": inventory,
        "operating_income": operating_income,
        "eps": eps,
    }
def extract_financial_record(
    rec: FilingRecord,
    filing,
    sec_identity: str | None = None
) -> dict:
    """Extract normalized financial metrics from an SEC filing."""

    record = extract_standardized_financial_record(
        rec,
        filing
    )

    missing = [
        metric
        for metric in FINANCIAL_METRICS
        if record.get(metric) is None
    ]

    if missing:
        record["missing_metrics"] = missing
        record["status"] = "partial"
    else:
        record["missing_metrics"] = []
        record["status"] = "complete"

    return record