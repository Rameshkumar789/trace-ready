from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from ..versioning.hashing import sha256_text
from .schemas import CanonicalSourceChunk, CanonicalSourceRecord, ChunkHealthIssue, SourceHealthIssue


HUB_MANIFEST = "fda-fsma204-hub-ingestion-manifest.json"
LOCAL_MANIFEST = "local-fda-documents-ingestion-manifest.json"

AUTHORITY_BY_TIER = {
    "binding_rule": "codified_rule",
    "binding_rule_history": "final_rule",
    "core_hub": "support",
    "product_scope": "support",
    "product_scope_support": "support",
    "cte_kde_schema": "support",
    "tlc_support": "support",
    "export_schema": "template",
    "export_schema_sample": "template",
    "guidance": "guidance",
    "guidance_summary": "guidance",
    "scenario": "scenario",
    "traceability_plan_example": "scenario",
    "operator_support": "support",
    "exemption_support": "support",
    "market_impact": "market_impact",
    "product_research": "research",
    "change_monitor": "change_monitor",
    "exemption_change_monitor": "change_monitor",
    "training_support": "training",
    "cross_reference": "cross_reference",
}

AUTHORITY_BY_SOURCE_ID = {
    "ecfr-21-cfr-1-subpart-s": "codified_rule",
    "ecfr-21-cfr-1-subpart-s-pdf": "codified_rule",
    "fr-2022-24417-final-rule": "final_rule",
    "fr-2022-24417-final-rule-pdf": "final_rule",
    "fr-2023-technical-amendment": "federal_register_notice",
    "fr-2025-compliance-date-extension": "change_monitor",
    "fr-2025-compliance-date-extension-pdf": "change_monitor",
    "fr-2026-cottage-cheese-exemption": "change_monitor",
}

SOURCE_DATES = {
    "fr-2022-24417-final-rule": {"effective_date": "2023-01-20"},
    "fr-2022-24417-final-rule-pdf": {"effective_date": "2023-01-20"},
    "ecfr-21-cfr-1-subpart-s": {"effective_date": "2023-01-20"},
    "ecfr-21-cfr-1-subpart-s-pdf": {"effective_date": "2023-01-20"},
    "fr-2025-compliance-date-extension": {"compliance_date": "2028-07-20"},
    "fr-2025-compliance-date-extension-pdf": {"compliance_date": "2028-07-20"},
}

MAX_CANONICAL_CHUNK_CHARS = 18_000
MIN_CANONICAL_CHUNK_CHARS = 40


def build_registry(regulatory_dir: Path) -> dict[str, Any]:
    manifests = _load_manifests(regulatory_dir)
    manifest_items = _manifest_items_by_source_id(manifests)
    normalized_files = sorted(regulatory_dir.glob("*/normalized/*.json"))

    source_records: list[CanonicalSourceRecord] = []
    chunk_records: list[CanonicalSourceChunk] = []
    source_issues: list[SourceHealthIssue] = []
    chunk_issues: list[ChunkHealthIssue] = []
    dropped_chunks: list[dict[str, Any]] = []
    seen_chunk_ids: Counter[str] = Counter()

    for normalized_path in normalized_files:
        data = _read_json(normalized_path)
        source_id = str(data.get("sourceId") or normalized_path.parent.parent.name)
        if not source_id:
            continue

        related_manifest_items = manifest_items.get(source_id, [])
        source_record = _build_source_record(
            regulatory_dir=regulatory_dir,
            normalized_path=normalized_path,
            data=data,
            manifest_items=related_manifest_items,
        )
        source_records.append(source_record)

        chunks = data.get("chunks") or []
        if not chunks:
            source_issues.append(
                SourceHealthIssue(
                    issue_type="empty_chunks",
                    severity="error",
                    source_id=source_id,
                    message="Normalized artifact has no chunks.",
                    artifact_path=str(normalized_path),
                )
            )

        for chunk in chunks:
            canonical_chunk = _build_chunk_record(source_record, chunk)
            drop_reason = _drop_reason(canonical_chunk)
            if drop_reason:
                dropped_chunks.append(
                    {
                        "source_id": canonical_chunk.source_id,
                        "chunk_id": canonical_chunk.chunk_id,
                        "reason": drop_reason,
                        "text_preview": re.sub(r"\s+", " ", canonical_chunk.text).strip()[:160],
                    }
                )
                continue
            for processed_chunk in _split_large_chunk(canonical_chunk):
                chunk_records.append(processed_chunk)
                seen_chunk_ids[processed_chunk.chunk_id] += 1
                chunk_issues.extend(_chunk_health_issues(processed_chunk))

        source_issues.extend(_source_health_issues(source_record, regulatory_dir))

    for chunk_id, count in seen_chunk_ids.items():
        if count > 1:
            for chunk in [item for item in chunk_records if item.chunk_id == chunk_id]:
                chunk_issues.append(
                    ChunkHealthIssue(
                        issue_type="duplicate_chunk_id",
                        severity="error",
                        source_id=chunk.source_id,
                        chunk_id=chunk.chunk_id,
                        message=f"Chunk ID appears {count} times.",
                    )
                )

    duplicate_source_ids = [source_id for source_id, count in Counter(item.source_id for item in source_records).items() if count > 1]
    for source_id in duplicate_source_ids:
        source_issues.append(
            SourceHealthIssue(
                issue_type="duplicate_source_record",
                severity="warning",
                source_id=source_id,
                message="Multiple normalized artifacts produced the same source ID.",
            )
        )

    source_records = sorted(source_records, key=lambda item: item.source_id)
    chunk_records = sorted(chunk_records, key=lambda item: (item.source_id, item.chunk_id))

    triage = _triage_health_issues(source_records=source_records, chunk_records=chunk_records, chunk_issues=chunk_issues)

    return {
        "sources": [item.model_dump() for item in source_records],
        "chunks": [item.model_dump() for item in chunk_records],
        "health": {
            "summary": {
                "sources": len(source_records),
                "chunks": len(chunk_records),
                "sourceIssues": len(source_issues),
                "chunkIssues": len(chunk_issues),
                "errors": sum(1 for item in [*source_issues, *chunk_issues] if item.severity == "error"),
                "warnings": sum(1 for item in [*source_issues, *chunk_issues] if item.severity == "warning"),
                "blockingIssues": len([item for item in triage if item["triageStatus"] == "blocking"]),
                "needsRemediation": len([item for item in triage if item["triageStatus"] == "needs_remediation"]),
                "acceptedNonblocking": len([item for item in triage if item["triageStatus"] == "accepted_nonblocking"]),
                "droppedChunks": len(dropped_chunks),
            },
            "sourceIssues": [item.model_dump() for item in source_issues],
            "chunkIssues": [item.model_dump() for item in chunk_issues],
            "triage": triage,
            "droppedChunks": dropped_chunks,
        },
    }


def write_registry(regulatory_dir: Path, output_dir: Path | None = None) -> dict[str, Any]:
    result = build_registry(regulatory_dir)
    registry_dir = output_dir or regulatory_dir / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    (registry_dir / "sources.json").write_text(json.dumps(result["sources"], indent=2), encoding="utf-8")
    (registry_dir / "source-chunks.json").write_text(json.dumps(result["chunks"], indent=2), encoding="utf-8")
    (registry_dir / "health-report.json").write_text(json.dumps(result["health"], indent=2), encoding="utf-8")
    return result


def _load_manifests(regulatory_dir: Path) -> dict[str, list[dict[str, Any]]]:
    manifests: dict[str, list[dict[str, Any]]] = {}
    for name in [HUB_MANIFEST, LOCAL_MANIFEST]:
        path = regulatory_dir / name
        manifests[name] = _read_json(path) if path.exists() else []
    return manifests


def _manifest_items_by_source_id(manifests: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    items: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for manifest_name, manifest_items in manifests.items():
        for item in manifest_items:
            source_id = item.get("sourceId")
            if source_id:
                items[str(source_id)].append({**item, "_manifest": manifest_name})
    return items


def _build_source_record(
    *,
    regulatory_dir: Path,
    normalized_path: Path,
    data: dict[str, Any],
    manifest_items: list[dict[str, Any]],
) -> CanonicalSourceRecord:
    source_id = str(data.get("sourceId") or normalized_path.parent.parent.name)
    primary_manifest = _select_primary_manifest_item(manifest_items)
    url = str(data.get("url") or primary_manifest.get("url") or "")
    raw_path = _resolve_artifact_path(regulatory_dir, str(data.get("rawArtifact") or primary_manifest.get("rawArtifact") or ""))
    normalized_artifact = _resolve_artifact_path(regulatory_dir, str(normalized_path))
    tier = primary_manifest.get("tier")
    dates = SOURCE_DATES.get(source_id, {})

    duplicate_ids = []
    if len(manifest_items) > 1:
        duplicate_ids = sorted(
            {
                str(item.get("file") or item.get("url") or item.get("normalizedArtifact") or item.get("_manifest"))
                for item in manifest_items[1:]
            }
        )

    return CanonicalSourceRecord(
        source_id=source_id,
        title=_title_for_source(source_id),
        url=url,
        source_type=_source_type(source_id, url, str(data.get("contentType") or primary_manifest.get("contentType") or "")),
        authority_rank=_authority_rank(source_id, str(tier or "")),
        source_status=str(primary_manifest.get("status") or "ingested"),
        source_tier=str(tier) if tier else None,
        source_use=primary_manifest.get("use"),
        content_type=data.get("contentType") or primary_manifest.get("contentType"),
        effective_date=dates.get("effective_date"),
        compliance_date=dates.get("compliance_date"),
        retrieved_at=_retrieved_at_from_chunks(data.get("chunks") or []),
        raw_hash=data.get("rawTextHash"),
        raw_artifact_path=str(raw_path) if raw_path else None,
        normalized_artifact_path=str(normalized_artifact),
        sections_extracted=int(data.get("sectionsExtracted") or primary_manifest.get("sectionsExtracted") or 0),
        chunks_count=len(data.get("chunks") or []),
        rejected_chunks_count=len(data.get("rejectedChunks") or []),
        manifest_sources=sorted({str(item.get("_manifest")) for item in manifest_items if item.get("_manifest")}),
        duplicate_source_ids=duplicate_ids,
        notes=_source_notes(source_id, primary_manifest),
    )


def _build_chunk_record(source: CanonicalSourceRecord, chunk: dict[str, Any]) -> CanonicalSourceChunk:
    anchors = chunk.get("anchors") or []
    first_anchor = anchors[0] if anchors else {}
    page_number = first_anchor.get("page_number") or first_anchor.get("pageNumber")
    return CanonicalSourceChunk(
        chunk_id=str(chunk.get("chunk_id") or chunk.get("chunkId") or f"{source.source_id}-{sha256_text(str(chunk))[:12]}"),
        source_id=source.source_id,
        section_label=str(chunk.get("section_label") or chunk.get("sectionLabel") or chunk.get("section") or "Document"),
        section_ref=str(chunk.get("section") or chunk.get("citation") or "document"),
        page_number=int(page_number) if isinstance(page_number, int | float) or str(page_number).isdigit() else None,
        text=str(chunk.get("text") or ""),
        text_hash=str(chunk.get("text_hash") or chunk.get("textHash") or f"sha256:{sha256_text(str(chunk.get('text') or ''))}"),
        citation_anchor=str(chunk.get("citation") or first_anchor.get("citation") or chunk.get("section") or "document"),
        authority_rank=source.authority_rank,
        source_url=source.url,
        source_type=source.source_type,
        usage_role="extraction",
        quality_flags=[],
        raw_artifact_path=source.raw_artifact_path,
        normalized_artifact_path=source.normalized_artifact_path,
    )


def _source_health_issues(source: CanonicalSourceRecord, regulatory_dir: Path) -> list[SourceHealthIssue]:
    issues: list[SourceHealthIssue] = []
    if not source.url:
        issues.append(SourceHealthIssue(issue_type="missing_url", severity="error", source_id=source.source_id, message="Source URL is missing."))
    if not source.raw_hash:
        issues.append(SourceHealthIssue(issue_type="missing_hash", severity="warning", source_id=source.source_id, message="Raw source hash is missing."))
    for label, path_value in [("raw_artifact", source.raw_artifact_path), ("normalized_artifact", source.normalized_artifact_path)]:
        if not path_value:
            issues.append(SourceHealthIssue(issue_type=f"missing_{label}_path", severity="error", source_id=source.source_id, message=f"{label} path is missing."))
            continue
        path = Path(path_value)
        if not path.exists():
            issues.append(
                SourceHealthIssue(
                    issue_type=f"missing_{label}",
                    severity="error",
                    source_id=source.source_id,
                    message=f"{label} does not exist on disk.",
                    artifact_path=str(path),
                )
            )
    if source.chunks_count == 0:
        issues.append(SourceHealthIssue(issue_type="no_chunks", severity="error", source_id=source.source_id, message="Source has zero chunks."))
    return issues


def _chunk_health_issues(chunk: CanonicalSourceChunk) -> list[ChunkHealthIssue]:
    issues: list[ChunkHealthIssue] = []
    text = chunk.text.strip()
    if not text:
        issues.append(ChunkHealthIssue(issue_type="empty_chunk", severity="error", source_id=chunk.source_id, chunk_id=chunk.chunk_id, message="Chunk text is empty."))
    if text.startswith("%PDF") or "%PDF-" in text[:40]:
        issues.append(ChunkHealthIssue(issue_type="raw_pdf_bytes", severity="error", source_id=chunk.source_id, chunk_id=chunk.chunk_id, message="Chunk appears to contain raw PDF bytes instead of extracted text."))
    if len(text) < MIN_CANONICAL_CHUNK_CHARS and chunk.usage_role != "citation_only":
        issues.append(ChunkHealthIssue(issue_type="short_chunk", severity="warning", source_id=chunk.source_id, chunk_id=chunk.chunk_id, message="Chunk text is very short."))
    if len(text) > MAX_CANONICAL_CHUNK_CHARS:
        issues.append(ChunkHealthIssue(issue_type="large_chunk", severity="warning", source_id=chunk.source_id, chunk_id=chunk.chunk_id, message="Chunk text is large and may need more precise sectioning."))
    if not chunk.citation_anchor:
        issues.append(ChunkHealthIssue(issue_type="missing_citation_anchor", severity="error", source_id=chunk.source_id, chunk_id=chunk.chunk_id, message="Citation anchor is missing."))
    return issues


def _drop_reason(chunk: CanonicalSourceChunk) -> str | None:
    text = re.sub(r"\s+", " ", chunk.text.strip())
    if not text:
        return "empty_text"
    if chunk.authority_rank == "codified_rule":
        return None
    if _is_known_boilerplate_chunk(text):
        return "known_boilerplate_or_page_metadata"
    return None


def _split_large_chunk(chunk: CanonicalSourceChunk) -> list[CanonicalSourceChunk]:
    chunk = _annotate_canonical_chunk(chunk)
    if len(chunk.text) <= MAX_CANONICAL_CHUNK_CHARS:
        return [chunk]

    parts = _split_text_for_citation(chunk.text, max_chars=MAX_CANONICAL_CHUNK_CHARS)
    if len(parts) <= 1:
        return [chunk]

    split_chunks = []
    for index, part in enumerate(parts, start=1):
        suffix = f"part-{index:03d}"
        data = chunk.model_dump()
        data.update(
            {
                "chunk_id": f"{chunk.chunk_id}-{suffix}",
                "section_label": f"{chunk.section_label} ({suffix})",
                "section_ref": f"{chunk.section_ref}#{suffix}",
                "text": part,
                "text_hash": f"sha256:{sha256_text(chunk.text_hash + part)}",
                "citation_anchor": f"{chunk.citation_anchor} {suffix}",
            }
        )
        split_chunks.append(CanonicalSourceChunk(**data))
    return split_chunks


def _annotate_canonical_chunk(chunk: CanonicalSourceChunk) -> CanonicalSourceChunk:
    text = re.sub(r"\s+", " ", chunk.text.strip())
    flags = list(chunk.quality_flags)
    usage_role = chunk.usage_role

    if len(text) < MIN_CANONICAL_CHUNK_CHARS:
        flags.append("short_citation_only")
        usage_role = "citation_only"
    if chunk.source_id.startswith("scenario-") and _is_title_only_scenario_slide(text):
        flags.append("scenario_title_only")
        usage_role = "citation_only"

    if usage_role == chunk.usage_role and sorted(set(flags)) == chunk.quality_flags:
        return chunk

    data = chunk.model_dump()
    data["usage_role"] = usage_role
    data["quality_flags"] = sorted(set(flags))
    return CanonicalSourceChunk(**data)


def _split_text_for_citation(text: str, *, max_chars: int) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
    if len(paragraphs) <= 1:
        paragraphs = [part.strip() for part in re.split(r"(?<=[.;:])\s+(?=[A-Z(§])", text) if part.strip()]
    if len(paragraphs) <= 1:
        return _fixed_width_split(text, max_chars=max_chars)

    parts: list[str] = []
    current: list[str] = []
    current_len = 0
    for paragraph in paragraphs:
        paragraph_parts = _fixed_width_split(paragraph, max_chars=max_chars) if len(paragraph) > max_chars else [paragraph]
        for paragraph_part in paragraph_parts:
            addition = len(paragraph_part) + (2 if current else 0)
            if current and current_len + addition > max_chars:
                parts.append("\n\n".join(current).strip())
                current = []
                current_len = 0
            current.append(paragraph_part)
            current_len += addition
    if current:
        parts.append("\n\n".join(current).strip())
    return [part for part in parts if part.strip()]


def _fixed_width_split(text: str, *, max_chars: int) -> list[str]:
    parts = []
    cursor = 0
    while cursor < len(text):
        end = min(len(text), cursor + max_chars)
        if end < len(text):
            boundary = max(text.rfind("\n", cursor, end), text.rfind(" ", cursor, end))
            if boundary > cursor + max_chars // 2:
                end = boundary
        part = text[cursor:end].strip()
        if part:
            parts.append(part)
        cursor = end
    return parts


def _triage_health_issues(
    *,
    source_records: list[CanonicalSourceRecord],
    chunk_records: list[CanonicalSourceChunk],
    chunk_issues: list[ChunkHealthIssue],
) -> list[dict[str, Any]]:
    source_by_id = {source.source_id: source for source in source_records}
    chunk_by_id = {chunk.chunk_id: chunk for chunk in chunk_records}
    triage = []
    for issue in chunk_issues:
        source = source_by_id.get(issue.source_id)
        chunk = chunk_by_id.get(issue.chunk_id)
        triage.append(
            {
                **issue.model_dump(),
                **_triage_issue(issue=issue, source=source, chunk=chunk),
            }
        )
    return triage


def _triage_issue(
    *,
    issue: ChunkHealthIssue,
    source: CanonicalSourceRecord | None,
    chunk: CanonicalSourceChunk | None,
) -> dict[str, str]:
    authority_rank = source.authority_rank if source else ""
    source_id = issue.source_id
    text = (chunk.text if chunk else "").strip()

    if issue.issue_type == "raw_pdf_bytes":
        return {
            "triageStatus": "blocking",
            "triageReason": "Raw PDF bytes cannot support extraction, citation, or rule drafting.",
            "recommendedAction": "Re-ingest with PDF extraction runtime before using this source.",
        }

    if issue.issue_type in {"empty_chunk", "missing_citation_anchor", "duplicate_chunk_id"}:
        return {
            "triageStatus": "blocking",
            "triageReason": "Chunk cannot safely support cited structured extraction.",
            "recommendedAction": "Fix chunking/citation generation before using this source.",
        }

    if authority_rank == "codified_rule":
        return {
            "triageStatus": "blocking",
            "triageReason": "Primary executable legal source must not have unresolved chunk quality warnings.",
            "recommendedAction": "Fix source chunking before obligation or rule-card extraction.",
        }

    if issue.issue_type == "short_chunk" and _is_known_boilerplate_chunk(text):
        return {
            "triageStatus": "accepted_nonblocking",
            "triageReason": "Known FDA page boilerplate or metadata chunk; exclude from extraction.",
            "recommendedAction": "Do not use this chunk for rule drafting; keep it only for source completeness.",
        }

    if source_id.startswith("scenario-") and issue.issue_type == "short_chunk":
        return {
            "triageStatus": "needs_remediation",
            "triageReason": "Scenario slide text is too thin for benchmark extraction; likely needs transcript pairing or visual/OCR extraction.",
            "recommendedAction": "Use transcript chunks first; revisit slide OCR under scenario benchmark task RI-035.",
        }

    if source_id == "fr-2022-24417-final-rule-pdf" and issue.issue_type == "large_chunk":
        return {
            "triageStatus": "needs_remediation",
            "triageReason": "Final-rule history chunk is readable but too large for precise final-rule rationale extraction.",
            "recommendedAction": "Do not use for executable obligations; split further before extracting final-rule reasoning.",
        }

    if source_id == "fda-faq-food-traceability-rule" and issue.issue_type == "large_chunk":
        return {
            "triageStatus": "needs_remediation",
            "triageReason": "FAQ table was captured as one large chunk; useful for search but weak for precise Q&A extraction.",
            "recommendedAction": "Add FAQ table row extraction before using FAQ records as reviewer support.",
        }

    if source_id == "fda-fish-guidance-chapter-3" and issue.issue_type == "large_chunk":
        return {
            "triageStatus": "accepted_nonblocking",
            "triageReason": "Fish guidance is cross-reference support, not an FSMA 204 executable source.",
            "recommendedAction": "Keep searchable; do not use for initial FTL/CTE/KDE extraction.",
        }

    if issue.issue_type == "large_chunk":
        return {
            "triageStatus": "needs_remediation",
            "triageReason": "Large chunk may reduce citation precision.",
            "recommendedAction": "Split before AI-assisted extraction from this source.",
        }

    return {
        "triageStatus": "needs_remediation",
        "triageReason": "Warning needs explicit source-specific review before extraction.",
        "recommendedAction": "Inspect chunk and either improve extraction or mark as excluded from drafting.",
    }


def _is_known_boilerplate_chunk(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return normalized in {
        "food & beverages",
        "guidance document",
        "small entity compliance guide",
        "may 2023",
        "visit the webpage to learn more.",
        "| | |",
        "modal header some text in the modal.",
    }


def _is_title_only_scenario_slide(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.strip())
    if len(normalized) > 90:
        return False
    if re.search(r"\b(in this scenario|key data elements|kdes?|traceability|receiv|ship|transform)\b", normalized, re.I):
        return False
    return bool(re.fullmatch(r"Supply Chain Example: .+ \d+", normalized))


def _select_primary_manifest_item(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {}
    ingested = [item for item in items if item.get("status") == "ingested"]
    hub = [item for item in ingested if item.get("_manifest") == HUB_MANIFEST]
    return (hub or ingested or items)[0]


def _authority_rank(source_id: str, tier: str) -> str:
    if source_id in AUTHORITY_BY_SOURCE_ID:
        return AUTHORITY_BY_SOURCE_ID[source_id]
    if source_id.startswith("cfr-") or source_id.startswith("ecfr-"):
        return "codified_rule"
    return AUTHORITY_BY_TIER.get(tier, "support")


def _source_type(source_id: str, url: str, content_type: str) -> str:
    lower_url = url.lower()
    lower_content = content_type.lower()
    if source_id.startswith("ecfr-"):
        return "ecfr"
    if source_id.startswith("cfr-"):
        return "cfr"
    if "federalregister.gov" in lower_url or source_id.startswith("fr-"):
        return "federal_register"
    if "spreadsheet" in lower_content or lower_url.endswith((".xlsx", ".xlsm")):
        return "fda_xlsx"
    if "pdf" in lower_content or lower_url.endswith(".pdf") or "/media/" in lower_url:
        return "fda_pdf"
    if "hfpappexternal.fda.gov" in lower_url:
        return "fda_web_app"
    if "fda.gov" in lower_url:
        return "fda_html"
    if lower_url.startswith("local://"):
        return "local_document"
    return "unknown"


def _title_for_source(source_id: str) -> str:
    return " ".join(part.upper() if part in {"fda", "fsma", "cte", "kde", "tlc", "rfe", "cfr"} else part.capitalize() for part in source_id.split("-"))


def _source_notes(source_id: str, manifest_item: dict[str, Any]) -> list[str]:
    notes = []
    if manifest_item.get("status") == "duplicate_skipped":
        notes.append("Duplicate skipped in source manifest.")
    if source_id.startswith("fr-2025"):
        notes.append("Change-monitoring source; do not treat proposed compliance-date extension as executable final rule without reviewer confirmation.")
    if "guidance" in source_id or "faq" in source_id:
        notes.append("Guidance/support source; does not override CFR text.")
    return notes


def _retrieved_at_from_chunks(chunks: list[dict[str, Any]]) -> str | None:
    for chunk in chunks:
        for anchor in chunk.get("anchors") or []:
            retrieved_at = anchor.get("retrieved_at") or anchor.get("retrievedAt")
            if retrieved_at:
                return str(retrieved_at)
    return None


def _resolve_artifact_path(regulatory_dir: Path, value: str) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    if value.startswith("../data/regulatory/"):
        return regulatory_dir / value.removeprefix("../data/regulatory/")
    if "bellwether/data/regulatory/" in value:
        return Path(value)
    if value.startswith("data/regulatory/"):
        return regulatory_dir.parent / value
    return path


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
