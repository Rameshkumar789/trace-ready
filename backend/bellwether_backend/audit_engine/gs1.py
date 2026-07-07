"""GS1 identifier validation (GTIN-8/12/13/14, GLN) + retailer overlay rules.

FDA does not mandate GS1 identifiers, so under `fda_rule` an invalid check digit is at most
a review item (an unreliable identifier undermines the product-description KDE). Big
retailers DO mandate GS1 (Walmart, Kroger, Albertsons supplier instructions) - those rules
ship as overlay cards (data, not code) and produce findings with
requirement_source="customer_requirement".
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictGs1Model(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, str_strip_whitespace=True)


class Gs1Check(StrictGs1Model):
    check_id: str
    entity_type: str  # product | location
    entity_id: str
    entity_name: str | None = None
    identifier: str
    id_kind: str  # gtin8 | gtin12 | gtin13 | gtin14 | gln
    valid_check_digit: bool
    requirement_source: str = "fda_rule"  # fda_rule | customer_requirement
    overlay_id: str | None = None
    retailer: str | None = None
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)


RETAILER_OVERLAYS_DIR = Path(__file__).resolve().parent / "bundled_rules" / "retailer-overlays"


@lru_cache(maxsize=4)
def load_retailer_overlays(directory: Path | None = None) -> tuple[dict[str, Any], ...]:
    overlay_dir = directory or RETAILER_OVERLAYS_DIR
    overlays: list[dict[str, Any]] = []
    if overlay_dir.is_dir():
        for path in sorted(overlay_dir.glob("*.json")):
            try:
                overlays.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
    return tuple(overlays)


def gs1_check_digit_valid(digits: str) -> bool:
    """Standard GS1 mod-10 check digit (weights 3/1 from the right, excluding check digit)."""
    if not digits.isdigit() or len(digits) < 8:
        return False
    body, check = digits[:-1], int(digits[-1])
    total = 0
    for position, char in enumerate(reversed(body)):
        weight = 3 if position % 2 == 0 else 1
        total += int(char) * weight
    return (10 - total % 10) % 10 == check


def looks_like_gs1(value: str | None) -> str | None:
    """Return the GS1 id kind a value could be, else None. Never guesses on non-digits."""
    if not value:
        return None
    text = re.sub(r"[\s-]", "", str(value))
    if not text.isdigit():
        return None
    return {8: "gtin8", 12: "gtin12", 13: "gtin13", 14: "gtin14"}.get(len(text))


def check_gs1_identifiers(*, entity_graph: Any, overlays: tuple[dict[str, Any], ...] | None = None) -> list[Gs1Check]:
    overlays = load_retailer_overlays() if overlays is None else overlays
    checks: list[Gs1Check] = []

    def _add(**kwargs: Any) -> None:
        checks.append(Gs1Check(check_id=f"gs1-check-{len(checks) + 1:04d}", **kwargs))

    def _scan(entities: list[Any], entity_type: str) -> None:
        for entity in entities:
            identifier = re.sub(r"[\s-]", "", str(entity.entity_id))
            kind = looks_like_gs1(identifier)
            if entity_type == "location" and kind == "gtin13":
                kind = "gln"  # a 13-digit location identifier is a GLN candidate
            if kind is None:
                continue
            valid = gs1_check_digit_valid(identifier)
            _add(
                entity_type=entity_type,
                entity_id=str(entity.entity_id),
                entity_name=entity.name,
                identifier=identifier,
                id_kind=kind,
                valid_check_digit=valid,
                requirement_source="fda_rule",
                reason=(
                    f"{kind.upper()} check digit is valid."
                    if valid
                    else f"Identifier {identifier} looks like a {kind.upper()} but its check digit is invalid - "
                    "the identifier may be mistyped or not a real GS1 identifier."
                ),
                evidence_ids=list(getattr(entity, "evidence_ids", []))[:10],
            )
            for overlay in overlays:
                for rule in overlay.get("rules", []):
                    applies_to = rule.get("applies_to")
                    if applies_to == "product_identifier" and entity_type != "product":
                        continue
                    if applies_to == "location_identifier" and entity_type != "location":
                        continue
                    requirement = rule.get("requirement", "")
                    if requirement.startswith("valid_") and not valid:
                        _add(
                            entity_type=entity_type,
                            entity_id=str(entity.entity_id),
                            entity_name=entity.name,
                            identifier=identifier,
                            id_kind=kind,
                            valid_check_digit=valid,
                            requirement_source="customer_requirement",
                            overlay_id=overlay.get("overlay_id"),
                            retailer=overlay.get("retailer"),
                            reason=(
                                f"{overlay.get('retailer', 'A retailer')} requires GS1-conformant "
                                f"{'GTINs' if entity_type == 'product' else 'GLNs'} from supply partners; "
                                f"identifier {identifier} fails GS1 validation."
                            ),
                            evidence_ids=list(getattr(entity, "evidence_ids", []))[:10],
                        )

    _scan(list(getattr(entity_graph, "products", [])), "product")
    _scan(list(getattr(entity_graph, "locations", [])), "location")
    return checks
