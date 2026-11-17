from __future__ import annotations

from typing import Any

from .relation_schema import (
    ExtractionResult,
    RelationClaim,
    validate_claim,
)


SYSTEM_PROMPT = """
You extract supply-chain knowledge from SEC filing text.

Only extract relationships supported by the supplied text.

Allowed edge types:

SUPPLIES
- Company -> Company
- supplier -> customer
- product_name may be null if the product is not stated
- dependency may only be: sole, primary, minor
- dependency_basis may only be: stated, inferred

COMPETES_WITH
- Company -> Company
- market is required
- intensity may only be: direct, partial, adjacent
- intensity_basis may only be: stated, inferred

MAKES
- Company -> Product
- role may only be: designs, manufactures, both
- production_location may be included if stated

PARENT_OF
- Company -> Company
- parent -> subsidiary
- ownership_pct may be included if stated
- effect may be included if stated

Important rules:

1. Do not invent relationships from outside knowledge.
2. Do not infer a named company when the filing only says
   "a supplier", "a customer", or similar unnamed entity.
3. quote must be copied exactly as one complete sentence from the supplied text.
4. Do not paraphrase, shorten, combine, or rewrite the quote.
5. If one complete sentence supports multiple claims, reuse that same complete
   sentence for each claim.
6. Return no claim when the relationship is not supported.
7. Do not create IN_SECTOR relationships.
8. Do not create edge IDs.
9. Do not create first_seen, last_seen, disclosed_by or summaries.
10. Use null for fields not supported by the text.
11. "we", "our", "us", and "the Company" may be resolved to the filing company
    identified by the ticker metadata. Do not resolve generic phrases such as
    "a supplier", "a customer", or "a manufacturer" to a named company.
12. Extract every distinct supported relationship. If the same company supplies
    different products, create a separate SUPPLIES claim for each product.
13. A single sentence may support more than one edge type when the text explicitly
    supports each relationship.

14. The quote itself must directly support the relationship and its attributes.
    Do not use information from another sentence to assign a role or relationship.

15. MAKES requires explicit evidence that the company designs, manufactures,
    or both designs and manufactures the Product.

16. Do not create MAKES merely because a company discusses, develops, delivers,
    uses, licenses, enhances, researches, or depends on something.

17. role="designs" requires the supporting quote itself to explicitly indicate
    that the company designs the Product.

18. role="manufactures" requires the supporting quote itself to explicitly
    indicate that the company manufactures or produces the Product.

19. For a non-filing company, from_name and to_name must be explicitly mentioned
    in the supporting quote.

20. The filing company is the only exception. "we", "our", "us", and
    "the Company" may resolve to the company identified by ticker metadata.

21. Do not move a company mentioned in surrounding context into a relationship
    unless the supporting quote itself identifies that company as participating
    in the relationship.

22. For SUPPLIES, product_name is the actual good or service transferred from
    the supplier to the customer.

23. Do not use the customer's downstream product as product_name merely because
    the supplied item is used to manufacture that product.

Example:
"TSMC produces wafers for our HPC, FPGA and adaptive SoC products"

Correct:
supplier = TSMC
customer = filing company
product_name = wafers

Incorrect product_name:
HPC products
FPGA products
adaptive SoC products

24. context must be null. The pipeline computes evidence context
    deterministically from the source document after extraction

25. status must be null unless the supporting quote explicitly states
    that the relationship is announced, not yet effective, or ended.

26. Do not set status="active" merely because a present-tense relationship
    is described. Active status is determined later from accumulated evidence.

27. Fields are edge-specific. Never populate fields belonging to another
    edge type.

    SUPPLIES may use only:
    product_name, dependency, dependency_basis

    COMPETES_WITH may use only:
    market, intensity, intensity_basis

    MAKES may use only:
    role, production_location

    PARENT_OF may use only:
    ownership_pct, effect

    All other edge-specific fields must be null.

28. MAKES is always Company -> Product.
    from_name must contain exactly one company.
    to_name must contain the product.
    Never create MAKES as Company -> Company.

29. If several companies manufacture the same product, create one separate
    MAKES claim per company.

30. For MAKES, do not put the product in product_name.
    The Product belongs in to_name.

31. context must always be null. It is computed later by the pipeline.


"""


def build_extraction_prompt(
    chunk_id: str,
    ticker: str,
    form: str,
    section: str,
    text: str,
) -> str:
    return f"""
{SYSTEM_PROMPT}

SOURCE METADATA

chunk_id: {chunk_id}
ticker: {ticker}
form: {form}
section: {section}

SOURCE TEXT

{text}
""".strip()


def parse_extraction_response(
    chunk_id: str,
    chunk_text: str,
    payload: dict[str, Any],
    model_name: str | None = None,
) -> tuple[ExtractionResult, list[dict[str, Any]]]:

    accepted = []
    rejected = []

    raw_claims = payload.get("claims", [])

    if not isinstance(raw_claims, list):
        raise ValueError("claims must be a list")

    for raw_claim in raw_claims:
        try:
            claim = RelationClaim(
                edge_type=raw_claim["edge_type"],
                from_name=raw_claim["from_name"],
                to_name=raw_claim["to_name"],
                quote=raw_claim["quote"],
                context=None,
                product_name=raw_claim.get("product_name"),
                dependency=raw_claim.get("dependency"),
                dependency_basis=raw_claim.get(
                    "dependency_basis"
                ),
                market=raw_claim.get("market"),
                intensity=raw_claim.get("intensity"),
                intensity_basis=raw_claim.get(
                    "intensity_basis"
                ),
                role=raw_claim.get("role"),
                production_location=raw_claim.get(
                    "production_location"
                ),
                ownership_pct=raw_claim.get(
                    "ownership_pct"
                ),
                effect=raw_claim.get("effect"),
                status=raw_claim.get("status"),
                valid_until=raw_claim.get(
                    "valid_until"
                ),
            )

        except (KeyError, TypeError, ValueError) as exc:
            rejected.append(
                {
                    "claim": raw_claim,
                    "errors": [
                        f"invalid claim structure: {exc}"
                    ],
                }
            )
            continue

        errors = validate_claim(
            claim,
            chunk_text,
        )

        if errors:
            rejected.append(
                {
                    "claim": raw_claim,
                    "errors": errors,
                }
            )
            continue

        accepted.append(claim)

    return (
        ExtractionResult(
            chunk_id=chunk_id,
            claims=accepted,
            model=model_name,
        ),
        rejected,
    )