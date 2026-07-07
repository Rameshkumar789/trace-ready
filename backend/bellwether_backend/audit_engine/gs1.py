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


# ---------------------------------------------------------------------------
# GS1-128 / element-string parsing (PTI case labels, SSCC pallets)

# Application Identifiers relevant to FSMA 204 case/pallet labels. Fixed-length AIs have a
# length; variable AIs terminate at FNC1 (rendered as ASCII GS \x1d) or end of string.
_AI_TABLE: dict[str, tuple[str, int | None]] = {
    "00": ("sscc", 18),
    "01": ("gtin", 14),
    "02": ("content_gtin", 14),
    "10": ("lot", None),
    "11": ("production_date", 6),
    "13": ("pack_date", 6),
    "15": ("best_before_date", 6),
    "17": ("expiry_date", 6),
    "21": ("serial", None),
    "37": ("count", None),
    "410": ("ship_to_gln", 13),
    "412": ("purchased_from_gln", 13),
}


def parse_gs1_element_string(value: str | None) -> dict[str, str] | None:
    """Parse a GS1-128 element string like ``(01)00614141123452(10)LOT42(13)250919`` or the
    raw form with FNC1 separators. Returns {field: value} or None if it doesn't parse.

    This is the machinery behind PTI case-label validation and the retailer
    "ASN must match the case/pallet label" checks.
    """
    if not value:
        return None
    text = str(value).strip()
    fields: dict[str, str] = {}
    if "(" in text:
        for ai, data in re.findall(r"\((\d{2,4})\)([^()]*)", text):
            spec = _AI_TABLE.get(ai)
            if spec:
                fields[spec[0]] = data.strip()
        return fields or None
    # raw form: leading FNC1 optional; walk AI by AI
    stream = text.lstrip("\x1d")
    while stream:
        matched = False
        for ai, (name, length) in _AI_TABLE.items():
            if stream.startswith(ai):
                rest = stream[len(ai):]
                if length is not None:
                    fields[name], stream = rest[:length], rest[length:]
                else:
                    end = rest.find("\x1d")
                    fields[name], stream = (rest, "") if end < 0 else (rest[:end], rest[end + 1:])
                matched = True
                break
        if not matched:
            return fields or None
    return fields or None


def validate_gs1_label_fields(fields: dict[str, str]) -> list[str]:
    """Deterministic validation of parsed label fields. Returns problem strings."""
    problems: list[str] = []
    gtin = fields.get("gtin") or fields.get("content_gtin")
    if gtin and not gs1_check_digit_valid(gtin):
        problems.append(f"GTIN {gtin} fails its check digit")
    sscc = fields.get("sscc")
    if sscc and (len(sscc) != 18 or not gs1_check_digit_valid(sscc)):
        problems.append(f"SSCC {sscc} is not a valid 18-digit SSCC")
    for gln_field in ("ship_to_gln", "purchased_from_gln"):
        gln = fields.get(gln_field)
        if gln and not gs1_check_digit_valid(gln):
            problems.append(f"{gln_field} {gln} fails its check digit")
    if "gtin" in fields and not fields.get("lot"):
        problems.append("label carries a GTIN but no (10) lot - PTI/FSMA case labels require the lot")
    for date_field in ("production_date", "pack_date", "expiry_date", "best_before_date"):
        date_value = fields.get(date_field)
        if date_value and not re.fullmatch(r"\d{6}", date_value):
            problems.append(f"{date_field} {date_value!r} is not YYMMDD")
    return problems


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
