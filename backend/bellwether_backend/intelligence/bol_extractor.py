"""BOL / paper-document extraction: PDF text -> canonical shipment-line facts via cached LLM.

Paper bills of lading carry KDEs that never get digitized. The LLM reads the extracted text
and returns canonical facts per shipment line; verification rejects invented slugs and any
extracted value that does not literally appear in the document text (anti-hallucination),
and a regex fallback covers the no-key case. Scanned PDFs with no text layer come back as an
explicit "unreadable_document" issue instead of a crash.
"""

from __future__ import annotations

import json
import re
from typing import Any

from bellwether_backend.audit_engine.canonical_fields import canonical_field_registry
from bellwether_backend.extractors.pdf_extractor import extract_pdf_pages
from bellwether_backend.intelligence.llm_cache import LLMCache, cache_key
from bellwether_backend.intelligence.llm_perception import run_cached_perception

BOL_PROMPT_VERSION = "bol-v1"

_EXTRACT_SLUGS = (
    "traceability_lot_code",
    "product_name",
    "product_id",
    "quantity",
    "unit",
    "date_you_shipped_the_food",
    "received_date",
    "source_location_name",
    "source_location_id",
    "destination_location_name",
    "destination_location_id",
    "partner_name",
    "reference_record_type",
    "reference_record_no",
    "phone_number",
    "email",
)

_SYSTEM_PROMPT = """You extract FSMA 204 traceability data from the text of a shipping \
document (bill of lading, packing slip, invoice, landing ticket).

Return a JSON array of line objects, one per shipped product line:
{"line_number": <int>, "facts": {"<canonical_slug>": ["<value>", ...], ...}}

Rules:
- Use ONLY the allowed canonical slugs given in the user message.
- Every extracted value must be copied VERBATIM from the document text (you may trim
  surrounding whitespace/punctuation). Never normalize, infer, or invent values.
- Document-level facts (BOL number, ship date, ship-from/ship-to, carrier phone) repeat on
  every line's facts.
- If the document has no discernible product lines, return a single line with the
  document-level facts you can find.
- Dates: copy them as written; do not reformat.
"""


def extract_bol_lines(
    data: bytes,
    *,
    file_name: str = "document.pdf",
    cache: LLMCache | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    """-> {"lines": [{"line_number", "facts"}], "method": ..., "issues": [...]}"""
    pages = extract_pdf_pages(data, source_id=file_name)
    text = "\n".join(page.get("text", "") for page in pages).strip()
    if len(text) < 40:
        # No text layer -> a scan. Read it multimodally (Claude vision over the PDF pages)
        # instead of giving up; degrade to the explicit unreadable verdict only when no
        # model is available or vision extraction fails verification.
        vision = _extract_scanned(data, file_name=file_name, cache=cache, client=client)
        if vision is not None:
            return vision
        return {
            "lines": [],
            "method": "unreadable",
            "issues": [
                "unreadable_document: the PDF has no usable text layer (likely a scan) and no "
                "vision model is available; OCR or the original digital document is needed"
            ],
        }
    text = text[:20000]
    registry = canonical_field_registry()
    allowed = [slug for slug in _EXTRACT_SLUGS if slug in registry]

    def _verify(items: list[dict[str, Any]]) -> list[str]:
        errors: list[str] = []
        if not items:
            return ["no lines extracted; return at least one line with document-level facts"]
        haystack = re.sub(r"\s+", " ", text.lower())
        for item in items:
            facts = item.get("facts")
            if not isinstance(facts, dict):
                errors.append("every line needs a 'facts' object")
                continue
            for slug, values in facts.items():
                if slug not in allowed:
                    errors.append(f"slug {slug!r} is not in the allowed list")
                    continue
                if not isinstance(values, list):
                    errors.append(f"facts[{slug!r}] must be a list of strings")
                    continue
                for value in values:
                    needle = re.sub(r"\s+", " ", str(value).strip().lower())
                    if needle and needle not in haystack:
                        errors.append(f"value {str(value)[:40]!r} for {slug} does not appear in the document text")
        return errors[:15]

    result = run_cached_perception(
        namespace="bol_extract",
        cache_key=cache_key(BOL_PROMPT_VERSION, text),
        system=_SYSTEM_PROMPT,
        user_prompt=(
            "Allowed canonical slugs (with meanings):\n"
            + json.dumps({slug: registry[slug].description for slug in allowed}, indent=1)
            + "\n\nDocument text:\n" + text
        ),
        verify=_verify,
        fallback=lambda: _regex_fallback(text),
        cache=cache,
        client=client,
    )
    lines = []
    for position, item in enumerate(result.items, start=1):
        facts = {slug: [str(v) for v in values] for slug, values in (item.get("facts") or {}).items() if slug in allowed}
        lines.append({"line_number": item.get("line_number") or position, "facts": facts})
    return {"lines": lines, "method": result.method, "issues": result.errors if result.method == "deterministic_fallback" else []}


def _extract_scanned(
    data: bytes,
    *,
    file_name: str,
    cache: LLMCache | None,
    client: Any | None,
) -> dict[str, Any] | None:
    """Vision extraction for scans: send the PDF itself; verify slugs (values cannot be
    text-anchored without a text layer, so provenance is weaker - flagged in the result)."""
    import hashlib

    from bellwether_backend.intelligence.llm_perception import build_default_client

    cache = cache or LLMCache()
    key = cache_key(BOL_PROMPT_VERSION + "-vision", hashlib.sha256(data).hexdigest())
    registry = canonical_field_registry()
    allowed = [slug for slug in _EXTRACT_SLUGS if slug in registry]

    def _verify(items: list[dict[str, Any]]) -> list[str]:
        errors: list[str] = []
        if not items:
            return ["no lines extracted"]
        for item in items:
            facts = item.get("facts")
            if not isinstance(facts, dict):
                errors.append("every line needs a 'facts' object")
                continue
            for slug, values in facts.items():
                if slug not in allowed:
                    errors.append(f"slug {slug!r} is not in the allowed list")
                elif not isinstance(values, list):
                    errors.append(f"facts[{slug!r}] must be a list of strings")
        return errors[:15]

    cached = cache.get("bol_extract_vision", key)
    if cached is not None and not _verify(cached):
        items, method = cached, "llm_cached"
    else:
        resolved_client = client if client is not None else build_default_client()
        if resolved_client is None:
            return None
        prompt = (
            "This is a scanned shipping document (no text layer). Read the pages and extract "
            "shipment lines as a JSON array per the system instructions. Allowed canonical "
            "slugs:\n" + json.dumps({slug: registry[slug].description for slug in allowed}, indent=1)
        )
        try:
            response = resolved_client.complete_json_array_with_document(
                system=_SYSTEM_PROMPT,
                user_prompt=prompt,
                document_bytes=data,
            )
        except Exception:
            return None
        errors = _verify(response.parsed_json)
        if errors:
            return None
        items, method = response.parsed_json, "llm_vision"
        cache.put("bol_extract_vision", key, items, model=response.model, method=method)

    lines = []
    for position, item in enumerate(items, start=1):
        facts = {slug: [str(v) for v in values] for slug, values in (item.get("facts") or {}).items() if slug in allowed}
        lines.append({"line_number": item.get("line_number") or position, "facts": facts})
    return {
        "lines": lines,
        "method": method,
        "issues": [
            "scanned_document: values were read visually from a scan and cannot be text-anchored; "
            "verify against the paper original before relying on them"
        ],
    }


def _regex_fallback(text: str) -> list[dict[str, Any]]:
    """No-model scrape: lot-like tokens, dates, and an overall reference number."""
    facts: dict[str, list[str]] = {}
    # A captured lot token must contain a digit, so header words ("Lot Number") never match.
    lots = re.findall(
        r"\b(?:lot|tlc|batch)\s*(?:#|no\.?|number)?\s*[:\-]?\s*((?=[A-Z0-9\-]*\d)[A-Z0-9][A-Z0-9\-]{3,})",
        text,
        re.IGNORECASE,
    )
    if lots:
        facts["traceability_lot_code"] = list(dict.fromkeys(lots))[:10]
    dates = re.findall(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b", text)
    if dates:
        facts["date_you_shipped_the_food"] = dates[:3]
    bol = re.findall(r"\b(?:bol|bill of lading)\s*(?:#|no\.?|number)?\s*[:\-]?\s*([A-Z0-9\-]{3,})", text, re.IGNORECASE)
    if bol:
        facts["reference_record_no"] = bol[:3]
        facts["reference_record_type"] = ["BOL"]
    return [{"line_number": 1, "facts": facts}]
