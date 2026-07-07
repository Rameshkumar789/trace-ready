"""FTL three-tier product classification: definite_on | suspicious | definite_off.

The FTL is static; the hard problem is interpreting customer product descriptions ("ham
sandwich" is off-list until someone puts tomato on it). The LLM interprets each product
against the approved FTL cards; every answer is deterministically verified (a claimed match
must name a commodity that exists on the FTL), composite-food forcing is deterministic
post-processing, and verdicts are cached per product so repeat audits are reproducible.
The tier itself never decides compliance - downstream deterministic checks do.
"""

from __future__ import annotations

import json
from typing import Any

from bellwether_backend.intelligence.llm_cache import LLMCache, cache_key
from bellwether_backend.intelligence.llm_perception import PerceptionResult, run_cached_perception

FTL_PROMPT_VERSION = "ftl-v1"

TIERS = ("definite_on", "suspicious", "definite_off")

COMPOSITE_HINT_TOKENS = (
    "salad",
    "sandwich",
    "wrap",
    "kit",
    "mix",
    "mixed",
    "medley",
    "prepared",
    "ready to eat",
    "rte",
    "platter",
    "variety",
    "assorted",
    "combo",
)

_SYSTEM_PROMPT = """You are a food-regulatory analyst classifying products against the FDA \
Food Traceability List (FTL) for FSMA 204 scope.

For EVERY product in the input, return one object:
{
  "product_id": "<exactly as given>",
  "tier": "definite_on" | "suspicious" | "definite_off",
  "matched_commodity": "<the exact 'commodity' string of the matching FTL item, or null>",
  "confidence": 0.0-1.0,
  "reasoning": "<one or two sentences>"
}

Rules:
- Respond with a JSON array only; every input product exactly once.
- definite_on: the description conclusively matches an FTL item (respect its form notes and
  exclusions - e.g. frozen crustaceans are ON the list; hard cheeses are not).
- definite_off: conclusively NOT on the list (cereal, paper goods, canned shelf-stable soup).
- suspicious: cannot be ruled in or out from the description alone - composite foods that may
  contain FTL ingredients (sandwiches, salads, kits), vague names, bare product codes.
- matched_commodity MUST be copied verbatim from an FTL item's "commodity" field when tier is
  definite_on (and when a specific item drives a suspicious call); null otherwise.
- The customer's own declared category is a hint, not truth: they may have misclassified.
- A product named only by a code (no words) is suspicious, never definite_off.
"""


def classify_products(
    products: list[dict[str, Any]],
    ftl_items: list[dict[str, Any]],
    *,
    cache: LLMCache | None = None,
    client: Any | None = None,
) -> dict[str, dict[str, Any]]:
    """Classify products -> {product_id: {tier, matched_commodity, reasoning, method, ...}}.

    Each product: {"product_id", "name", "declared_category" (optional)}.
    Results are cached per product signature; only unseen products hit the model, all in one
    call.
    """
    cache = cache or LLMCache()
    ftl_hash = cache_key("ftl-items", json.dumps(_ftl_digest(ftl_items), sort_keys=True))
    valid_commodities = {str(item.get("commodity")) for item in ftl_items if item.get("commodity")}

    results: dict[str, dict[str, Any]] = {}
    missing: list[dict[str, Any]] = []
    keys: dict[str, str] = {}
    for product in products:
        product_id = str(product.get("product_id"))
        key = cache_key(FTL_PROMPT_VERSION, product_id, _norm(product.get("name")), _norm(product.get("declared_category")), ftl_hash)
        keys[product_id] = key
        cached = cache.get("ftl_tier", key)
        if cached:
            item = cached[0]
            if not _verify_one(item, valid_commodities):
                results[product_id] = {**item, "method": "llm_cached"}
                continue
            cache.delete("ftl_tier", key)
        missing.append(product)

    if missing:
        perception = _classify_batch(missing, ftl_items, valid_commodities, client=client, cache=cache)
        by_id = {str(item.get("product_id")): item for item in perception.items}
        for product in missing:
            product_id = str(product.get("product_id"))
            item = by_id.get(product_id) or _fallback_one(product, ftl_items)
            item = _postprocess(item, product, valid_commodities)
            results[product_id] = {**item, "method": perception.method}
            if perception.method == "llm_live":
                cache.put("ftl_tier", keys[product_id], [item], model=perception.model)

    for product in products:
        product_id = str(product.get("product_id"))
        results[product_id] = _postprocess(results[product_id], product, valid_commodities)
    return results


def _classify_batch(
    products: list[dict[str, Any]],
    ftl_items: list[dict[str, Any]],
    valid_commodities: set[str],
    *,
    client: Any,
    cache: LLMCache,
) -> PerceptionResult:
    payload = {
        "ftl_items": _ftl_digest(ftl_items),
        "products": [
            {
                "product_id": str(product.get("product_id")),
                "name": product.get("name"),
                "declared_category": product.get("declared_category"),
            }
            for product in products
        ],
    }
    call_key = cache_key(FTL_PROMPT_VERSION + "-batch", json.dumps(payload, sort_keys=True, default=str))

    def _verify(items: list[dict[str, Any]]) -> list[str]:
        errors: list[str] = []
        expected = {str(product.get("product_id")) for product in products}
        seen: set[str] = set()
        for item in items:
            product_id = str(item.get("product_id"))
            if product_id not in expected:
                errors.append(f"unknown product_id {product_id!r}")
                continue
            seen.add(product_id)
            error = _verify_one(item, valid_commodities)
            if error:
                errors.append(f"product {product_id}: {error}")
        for product_id in sorted(expected - seen):
            errors.append(f"product {product_id} missing from the answer")
        return errors

    return run_cached_perception(
        namespace="ftl_tier_call",
        cache_key=call_key,
        system=_SYSTEM_PROMPT,
        user_prompt="Classify every product against the FTL items:\n" + json.dumps(payload, ensure_ascii=False, indent=1, default=str),
        verify=_verify,
        fallback=lambda: [_fallback_one(product, ftl_items) for product in products],
        cache=cache,
        client=client,
    )


def _verify_one(item: dict[str, Any], valid_commodities: set[str]) -> str | None:
    """Deterministic per-item verification. Returns an error string or None."""
    tier = item.get("tier")
    if tier not in TIERS:
        return f"tier {tier!r} is not one of {TIERS}"
    matched = item.get("matched_commodity")
    if tier == "definite_on" and (not matched or matched not in valid_commodities):
        return f"definite_on requires matched_commodity verbatim from the FTL items; got {matched!r}"
    if matched is not None and matched not in valid_commodities:
        return f"matched_commodity {matched!r} is not on the FTL"
    return None


def _fallback_one(product: dict[str, Any], ftl_items: list[dict[str, Any]]) -> dict[str, Any]:
    """No-model heuristic: exact term hit -> definite_on; declared category -> suspicious."""
    from bellwether_backend.audit_engine.customer_evidence import _match_ftl_item

    name = _norm(product.get("name"))
    matched = _match_ftl_item(name, ftl_items) if name else None
    if matched:
        commodity = next((str(i.get("commodity")) for i in ftl_items if str(i.get("commodity")) == matched or str(i.get("category")) == matched), None)
        return {
            "product_id": str(product.get("product_id")),
            "tier": "definite_on" if commodity else "suspicious",
            "matched_commodity": commodity,
            "confidence": 0.6,
            "reasoning": f"Deterministic term match against FTL item {matched!r} (no model available).",
        }
    return {
        "product_id": str(product.get("product_id")),
        "tier": "suspicious",
        "matched_commodity": None,
        "confidence": 0.3,
        "reasoning": "Could not be resolved without model perception; requires human review.",
    }


def _postprocess(item: dict[str, Any], product: dict[str, Any], valid_commodities: set[str]) -> dict[str, Any]:
    """Deterministic guards that outrank the model."""
    result = dict(item)
    name = _norm(product.get("name"))
    # Composite foods can hide FTL ingredients: never allow definite_off for them.
    is_composite = any(token in name for token in COMPOSITE_HINT_TOKENS)
    if is_composite and result.get("tier") == "definite_off":
        result["tier"] = "suspicious"
        result["reasoning"] = (result.get("reasoning") or "") + " [Composite-food guard: description suggests a multi-ingredient product; ruled up to suspicious.]"
    result["composite_food"] = is_composite
    # Code-only names can never be conclusively off-list.
    if name and not any(ch.isalpha() for ch in name) and result.get("tier") == "definite_off":
        result["tier"] = "suspicious"
        result["reasoning"] = (result.get("reasoning") or "") + " [Code-only name: cannot be ruled off-list.]"
    # Frozen guard (asymmetric, deterministic - never left to the model alone): freezing
    # removes ONLY cheeses from the FTL; frozen seafood, nut butters, and deli salads
    # frozen prior to retail remain on the list.
    is_frozen = "frozen" in name
    if is_frozen and "cheese" in name and result.get("tier") in {"definite_on", "suspicious"} and "cottage" not in name:
        result["tier"] = "definite_off"
        result["matched_commodity"] = None
        result["reasoning"] = (result.get("reasoning") or "") + " [Frozen-cheese guard: the FTL cheese entries exclude frozen/previously frozen cheese.]"
    # Cottage cheese guard (Feb 2026 exemption): IMS Grade "A" listing cannot be read off a
    # product name, so cottage cheese is never definite_on - it needs the IMS check.
    if "cottage cheese" in name and result.get("tier") == "definite_on":
        result["tier"] = "suspicious"
        result["reasoning"] = (result.get("reasoning") or "") + (
            " [Cottage-cheese guard: IMS-listed Grade \"A\" cottage cheese is exempt from full "
            "Subpart S (Feb 2026); confirm IMS listing before treating as in scope. Source/"
            "recipient records are still required either way.]"
        )
    if result.get("matched_commodity") not in valid_commodities:
        result["matched_commodity"] = None if result.get("tier") != "definite_on" else result.get("matched_commodity")
    declared = _norm(product.get("declared_category"))
    declared_negative = declared in {"", "none", "non-ftl", "not on ftl", "general products", "general", "no", "n/a"}
    result["declared_category"] = product.get("declared_category")
    result["declared_negative"] = declared_negative
    result["mismatch"] = bool(declared_negative and result.get("tier") in {"definite_on", "suspicious"} and declared not in {""})
    return result


def _ftl_digest(ftl_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    digest = []
    for item in ftl_items:
        digest.append(
            {
                "commodity": item.get("commodity"),
                "category": item.get("category"),
                "description": (item.get("description") or "")[:300],
                "included_examples": (item.get("included_examples") or [])[:12],
                "excluded_examples": (item.get("excluded_examples") or [])[:6],
                "form_notes": (item.get("form_notes") or [])[:4],
                "citation": ((item.get("citations") or [{}])[0] or {}).get("citation_anchor"),
            }
        )
    return digest


def _norm(value: Any) -> str:
    return " ".join(str(value or "").lower().split())
