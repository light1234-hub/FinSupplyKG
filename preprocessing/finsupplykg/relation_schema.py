from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any


EDGE_TYPES = {
    "SUPPLIES",
    "COMPETES_WITH",
    "MAKES",
    "PARENT_OF",
}

DEPENDENCY_VALUES = {
    "sole",
    "primary",
    "minor",
}

INTENSITY_VALUES = {
    "direct",
    "partial",
    "adjacent",
}

BASIS_VALUES = {
    "stated",
    "inferred",
}

MAKE_ROLES = {
    "designs",
    "manufactures",
    "both",
}

STATUS_VALUES = {
    "active",
    "announced",
    "ended",
}

EDGE_SPECIFIC_FIELDS = {
    "SUPPLIES": {
        "product_name",
        "dependency",
        "dependency_basis",
    },
    "COMPETES_WITH": {
        "market",
        "intensity",
        "intensity_basis",
    },
    "MAKES": {
        "role",
        "production_location",
    },
    "PARENT_OF": {
        "ownership_pct",
        "effect",
    },
}


ALL_EDGE_SPECIFIC_FIELDS = set().union(
    *EDGE_SPECIFIC_FIELDS.values()
)


def _validate_field_scope(
    claim: RelationClaim,
    errors: list[str],
) -> None:
    allowed = EDGE_SPECIFIC_FIELDS.get(
        claim.edge_type
    )

    if allowed is None:
        return

    forbidden = (
        ALL_EDGE_SPECIFIC_FIELDS
        - allowed
    )

    for field_name in sorted(forbidden):
        if getattr(claim, field_name) is not None:
            errors.append(
                f"{field_name} is not valid "
                f"for {claim.edge_type}"
            )

@dataclass
class RelationClaim:
    edge_type: str

    # Raw names exactly as understood from the evidence.
    # Canonical IDs are assigned later.
    from_name: str
    to_name: str

    # Evidence
    quote: str
    context: str | None = None

    # SUPPLIES
    product_name: str | None = None
    dependency: str | None = None
    dependency_basis: str | None = None

    # COMPETES_WITH
    market: str | None = None
    intensity: str | None = None
    intensity_basis: str | None = None

    # MAKES
    role: str | None = None
    production_location: str | None = None

    # PARENT_OF
    ownership_pct: float | None = None
    effect: str | None = None

    # Shared relationship facts that may be explicitly stated.
    status: str | None = None
    valid_until: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractionResult:
    chunk_id: str
    claims: list[RelationClaim]
    model: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_claim(
    claim: RelationClaim,
    chunk_text: str,
) -> list[str]:
    errors = []

    if claim.edge_type not in EDGE_TYPES:
        errors.append(
            f"unsupported edge type: {claim.edge_type}"
        )

    _validate_field_scope(
        claim,
        errors,
    )

    if not claim.from_name.strip():
        errors.append("from_name is required")

    if not claim.to_name.strip():
        errors.append("to_name is required")

    quote = claim.quote.strip()

    if not quote:
        errors.append("quote is required")

    elif quote not in chunk_text:
        errors.append(
            "quote is not an exact source sentence"
        )

    elif quote[-1] not in ".!?":
        errors.append(
            "quote is not an exact source sentence"
        )

    if (
        claim.edge_type
        in {"SUPPLIES", "COMPETES_WITH", "PARENT_OF"}
        and claim.from_name.strip().lower()
        == claim.to_name.strip().lower()
    ):
        errors.append(
            f"{claim.edge_type} cannot connect an entity to itself"
        )

    if claim.edge_type == "SUPPLIES":
        _validate_supplies(claim, errors)

    elif claim.edge_type == "COMPETES_WITH":
        _validate_competition(claim, errors)

    elif claim.edge_type == "MAKES":
        _validate_makes(claim, errors)

    elif claim.edge_type == "PARENT_OF":
        _validate_parent(claim, errors)

    if claim.status is not None:
        if claim.status not in STATUS_VALUES:
            errors.append(
                f"invalid status: {claim.status}"
            )

    if claim.valid_until is not None:
        try:
            date.fromisoformat(claim.valid_until)
        except ValueError:
            errors.append(
                "valid_until must be YYYY-MM-DD"
            )

    return errors


def _validate_supplies(
    claim: RelationClaim,
    errors: list[str],
) -> None:

    if claim.dependency is not None:
        if claim.dependency not in DEPENDENCY_VALUES:
            errors.append(
                f"invalid dependency: {claim.dependency}"
            )

        if claim.dependency_basis is None:
            errors.append(
                "dependency_basis is required when dependency is set"
            )

    if claim.dependency_basis is not None:
        if claim.dependency_basis not in BASIS_VALUES:
            errors.append(
                f"invalid dependency_basis: "
                f"{claim.dependency_basis}"
            )

        if claim.dependency is None:
            errors.append(
                "dependency is required when "
                "dependency_basis is set"
            )


def _validate_competition(
    claim: RelationClaim,
    errors: list[str],
) -> None:

    if not claim.market:
        errors.append(
            "market is required for COMPETES_WITH"
        )

    if claim.intensity is not None:
        if claim.intensity not in INTENSITY_VALUES:
            errors.append(
                f"invalid intensity: {claim.intensity}"
            )

        if claim.intensity_basis is None:
            errors.append(
                "intensity_basis is required when intensity is set"
            )

    if claim.intensity_basis is not None:
        if claim.intensity_basis not in BASIS_VALUES:
            errors.append(
                f"invalid intensity_basis: "
                f"{claim.intensity_basis}"
            )

        if claim.intensity is None:
            errors.append(
                "intensity is required when "
                "intensity_basis is set"
            )


def _validate_makes(
    claim: RelationClaim,
    errors: list[str],
) -> None:

    if claim.role is not None:
        if claim.role not in MAKE_ROLES:
            errors.append(
                f"invalid MAKES role: {claim.role}"
            )


def _validate_parent(
    claim: RelationClaim,
    errors: list[str],
) -> None:

    if claim.ownership_pct is not None:
        if not 0 <= claim.ownership_pct <= 100:
            errors.append(
                "ownership_pct must be between 0 and 100"
            )