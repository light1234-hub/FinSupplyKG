"""Extract structured financial facts from SEC XBRL data."""

from __future__ import annotations

import requests

from edgar import Company

from .fetch import FilingRecord

from datetime import date

import math

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
FILING_FALLBACK_CONCEPTS = {
    "revenue": (
        "us-gaap:Revenues",
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        "us-gaap:SalesRevenueNet",
        "ifrs-full:RevenueFromContractsWithCustomers",
    ),

    "net_income": (
        "us-gaap:NetIncomeLoss",
        "ifrs-full:ProfitLossAttributableToOwnersOfParent",
        "ifrs-full:ProfitLoss",
    ),

    "cash": (
        "us-gaap:CashAndCashEquivalentsAtCarryingValue",
        "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "ifrs-full:CashAndCashEquivalents",
    ),

    "assets": (
        "us-gaap:Assets",
        "ifrs-full:Assets",
    ),

    "inventory": (
        "us-gaap:InventoryNet",
        "ifrs-full:Inventories",
    ),

    "operating_income": (
        "us-gaap:OperatingIncomeLoss",
        "ifrs-full:ProfitLossFromOperatingActivities",
    ),

    "eps": (
        "us-gaap:EarningsPerShareDiluted",
        "ifrs-full:DilutedEarningsLossPerShare",
    ),
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


DURATION_METRICS = {
    "revenue",
    "net_income",
    "operating_income",
    "eps",
}

INSTANT_METRICS = {
    "cash",
    "assets",
    "inventory",
}


def _currency_from_unit(
    unit: str | None
) -> str | None:

    if not unit:
        return None

    if "/" in unit:
        return unit.split("/", 1)[0].upper()

    if len(unit) == 3 and unit.isalpha():
        return unit.upper()

    return None

def fallback_companyfacts_metric(
    rec: FilingRecord,
    sec_identity: str,
    metric: str
) -> dict | None:
    """Recover one missing metric using SEC CompanyFacts."""

    tags = METRIC_TAGS.get(metric)

    if not tags:
        return None

    candidates = extract_metric_candidates(
        rec,
        sec_identity,
        tags
    )

    if not candidates:
        return None

    if metric in INSTANT_METRICS:

        selected = select_instant_fact(
            candidates,
            rec
        )

    elif rec.form == "10-Q":

        selected = select_quarter_fact(
            candidates,
            rec
        )

    elif rec.form == "10-K":

        selected = select_annual_fact(
            candidates,
            rec
        )

    else:
        return None

    if selected is None:
        return None

    unit = selected.get("unit")

    concept = selected.get("concept")

    if concept:
        concept = f"us-gaap_{concept}"

    return {
        "value": selected.get("val"),
        "concept": concept,
        "standard_concept": None,
        "label": None,
        "period": selected.get("end"),
        "unit": unit,
        "currency": _currency_from_unit(unit),
    }

def get_record_currency(
    record: dict
) -> str | None:
    """Infer the reporting currency from existing metrics."""

    counts = {}

    for metric in FINANCIAL_METRICS:

        fact = record.get(metric)

        if not isinstance(fact, dict):
            continue

        currency = fact.get("currency")

        if not currency:
            continue

        counts[currency] = counts.get(
            currency,
            0
        ) + 1

    if not counts:
        return None

    return max(
        counts,
        key=counts.get
    )


def fallback_filing_metric(
    record: dict,
    rec: FilingRecord,
    filing,
    metric: str
) -> dict | None:
    """Recover one missing metric directly from filing-level XBRL."""

    concepts = FILING_FALLBACK_CONCEPTS.get(
        metric,
        ()
    )

    if not concepts:
        return None

    xbrl = filing.xbrl()

    if xbrl is None:
        return None

    preferred_currency = get_record_currency(
        record
    )

    target_date = str(
        rec.period_of_report
    )

    period_type = (
        "instant"
        if metric in INSTANT_METRICS
        else "duration"
    )

    for concept in concepts:

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
            continue

        if period_type == "duration":

            matches = df[
                (df["period_type"] == "duration")
                & (
                    df["period_end"].astype(str)
                    == target_date
                )
            ]

        else:

            matches = df[
                (df["period_type"] == "instant")
                & (
                    df["period_instant"].astype(str)
                    == target_date
                )
            ]

        if matches.empty:
            continue

        if preferred_currency:

            currency_matches = matches[
                matches["currency"]
                == preferred_currency
            ]

            if currency_matches.empty:
                continue

            matches = currency_matches

        else:

            currencies = (
                matches["currency"]
                .dropna()
                .unique()
            )

            if len(currencies) > 1:
                continue

        if (
            period_type == "duration"
            and "fiscal_period" in matches.columns
        ):

            annual = matches[
                matches["fiscal_period"] == "FY"
            ]

            if not annual.empty:
                matches = annual

        if (
            period_type == "duration"
            and "statement_type" in matches.columns
        ):

            statement_matches = matches[
                matches["statement_type"]
                == "IncomeStatement"
            ]

            if not statement_matches.empty:
                matches = statement_matches

        row = matches.iloc[0]

        value = row.get(
            "numeric_value"
        )

        if hasattr(value, "item"):
            value = value.item()

        if (
            isinstance(value, float)
            and value.is_integer()
        ):
            value = int(value)

        return {
            "value": value,
            "concept": row.get("concept"),
            "standard_concept": None,
            "label": row.get("label"),
            "period": target_date,
            "unit": row.get("unit_ref"),
            "currency": row.get("currency"),
        }

    return None

def apply_financial_fallbacks(
    record: dict,
    rec: FilingRecord,
    filing,
    sec_identity: str | None,
    missing: list[str]
) -> dict:
    """Attempt to recover metrics missed by standardized statements."""

    for metric in missing:

        fallback = None

        try:

            if (
                rec.form in {"10-K", "10-Q"}
                and sec_identity
            ):

                fallback = fallback_companyfacts_metric(
                    rec,
                    sec_identity,
                    metric
                )

            if fallback is None:

                fallback = fallback_filing_metric(
                    record,
                    rec,
                    filing,
                    metric
                )

            if fallback is not None:
                record[metric] = fallback

        except Exception:
            continue

    return record

def extract_financial_record(
    rec: FilingRecord,
    filing,
    sec_identity: str | None = None
) -> dict:

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
        record = apply_financial_fallbacks(
            record,
            rec,
            filing,
            sec_identity,
            missing
        )

    missing = [
        metric
        for metric in FINANCIAL_METRICS
        if record.get(metric) is None
    ]

    record["missing_metrics"] = missing
    record["missing_reasons"] = {
        metric: "not_found_after_fallbacks"
        for metric in missing
    }
    record["status"] = (
        "complete"
        if not missing
        else "partial"
    )

    return record