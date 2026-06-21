from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from bellwether_backend.backend.repositories.supabase_tables import (
    NormalizedBusinessObjectUpsert,
    NormalizedEventEvidenceRefCreate,
    NormalizedEventUpsert,
    NormalizedEvidenceRepository,
    NormalizedKdeValueCreate,
    NormalizedReviewItemCreate,
    TlcLineageLinkCreate,
)
from bellwether_backend.audit_engine.customer_evidence import (
    CustomerEvidenceRecord,
    Phase10CustomerEvidencePackage,
    TraceabilityEntity,
)
from bellwether_backend.versioning.hashing import sha256_text


class NormalizedEvidenceRepositories(Protocol):
    normalized_evidence: NormalizedEvidenceRepository


@dataclass(frozen=True)
class NormalizedEvidencePersistResult:
    audit_project_id: str
    audit_run_id: str | None
    business_object_count: int
    event_count: int
    event_evidence_ref_count: int
    kde_value_count: int
    tlc_lineage_link_count: int
    review_item_count: int


def persist_normalized_customer_evidence(
    *,
    audit_project_id: str,
    audit_run_id: str | None,
    audit_file_id: str | None,
    package: Phase10CustomerEvidencePackage,
    repositories: NormalizedEvidenceRepositories,
) -> NormalizedEvidencePersistResult:
    object_rows, entity_id_to_object_id = _business_object_rows(
        audit_project_id=audit_project_id,
        audit_run_id=audit_run_id,
        package=package,
    )
    event_rows, event_id_to_normalized_id = _event_rows(
        audit_project_id=audit_project_id,
        audit_run_id=audit_run_id,
        audit_file_id=audit_file_id,
        package=package,
        entity_id_to_object_id=entity_id_to_object_id,
    )
    event_refs = _event_evidence_refs(package, event_id_to_normalized_id)
    kde_values = _kde_value_rows(
        audit_project_id=audit_project_id,
        audit_run_id=audit_run_id,
        package=package,
        event_id_to_normalized_id=event_id_to_normalized_id,
    )
    lineage_links = _tlc_lineage_rows(
        audit_project_id=audit_project_id,
        audit_run_id=audit_run_id,
        package=package,
        event_id_to_normalized_id=event_id_to_normalized_id,
    )
    review_items = _review_item_rows(
        audit_project_id=audit_project_id,
        audit_run_id=audit_run_id,
        package=package,
        entity_id_to_object_id=entity_id_to_object_id,
        event_id_to_normalized_id=event_id_to_normalized_id,
    )

    repository = repositories.normalized_evidence
    repository.upsert_business_objects(object_rows)
    repository.upsert_events(event_rows)
    repository.create_event_evidence_refs(event_refs)
    repository.create_kde_values(kde_values)
    repository.create_tlc_lineage_links(lineage_links)
    repository.create_review_items(review_items)

    return NormalizedEvidencePersistResult(
        audit_project_id=audit_project_id,
        audit_run_id=audit_run_id,
        business_object_count=len(object_rows),
        event_count=len(event_rows),
        event_evidence_ref_count=len(event_refs),
        kde_value_count=len(kde_values),
        tlc_lineage_link_count=len(lineage_links),
        review_item_count=len(review_items),
    )


def _business_object_rows(
    *,
    audit_project_id: str,
    audit_run_id: str | None,
    package: Phase10CustomerEvidencePackage,
) -> tuple[list[NormalizedBusinessObjectUpsert], dict[str, str]]:
    rows: list[NormalizedBusinessObjectUpsert] = []
    entity_id_to_object_id: dict[str, str] = {}
    groups = [
        ("product", package.entity_graph.products),
        ("product_form", package.entity_graph.product_forms),
        ("lot", package.entity_graph.lots),
        ("actor", package.entity_graph.actors),
        ("location", package.entity_graph.locations),
        ("counterparty", package.entity_graph.counterparties),
        ("document", package.entity_graph.documents),
    ]
    for object_type, entities in groups:
        for entity in entities:
            row = _business_object_from_entity(
                audit_project_id=audit_project_id,
                audit_run_id=audit_run_id,
                object_type=object_type,
                entity=entity,
            )
            rows.append(row)
            entity_id_to_object_id[entity.entity_id] = row.id

    for profile in package.document_profiles:
        object_key = f"profile:{profile.profile_id}"
        rows.append(
            NormalizedBusinessObjectUpsert(
                id=_stable_id("nbo", audit_project_id, audit_run_id or "", "document_profile", object_key),
                audit_project_id=audit_project_id,
                audit_run_id=audit_run_id,
                object_type="document",
                object_key=object_key,
                name=profile.source_name,
                normalized_name=profile.document_type,
                confidence=profile.confidence,
                review_status="needs_review" if profile.confidence < 0.75 else "unreviewed",
                attributes_json=profile.model_dump(mode="json"),
                evidence_ids_json=profile.evidence_ids,
            )
        )

    for fact in package.inferred_facts:
        if fact.field_key not in {"traceability_plan", "exemption_claim", "exemption", "record_storage_location"}:
            continue
        object_type = "exemption_claim" if "exemption" in fact.field_key else "traceability_plan"
        object_key = f"{fact.source_kind}:{fact.source_name}:{fact.field_key}"
        rows.append(
            NormalizedBusinessObjectUpsert(
                id=_stable_id("nbo", audit_project_id, audit_run_id or "", object_type, object_key),
                audit_project_id=audit_project_id,
                audit_run_id=audit_run_id,
                object_type=object_type,
                object_key=object_key,
                name=fact.raw_value,
                normalized_name=fact.normalized_value,
                confidence=fact.confidence,
                review_status="needs_review" if fact.confidence < 0.8 else "unreviewed",
                attributes_json=fact.model_dump(mode="json"),
                evidence_ids_json=[],
            )
        )

    deduped = {row.id: row for row in rows}
    return list(deduped.values()), entity_id_to_object_id


def _business_object_from_entity(
    *,
    audit_project_id: str,
    audit_run_id: str | None,
    object_type: str,
    entity: TraceabilityEntity,
) -> NormalizedBusinessObjectUpsert:
    return NormalizedBusinessObjectUpsert(
        id=_stable_id("nbo", audit_project_id, audit_run_id or "", object_type, entity.entity_id),
        audit_project_id=audit_project_id,
        audit_run_id=audit_run_id,
        object_type=object_type,
        object_key=entity.entity_id,
        name=entity.name,
        normalized_name=_normalize_name(entity.name),
        confidence=_safe_float(entity.attributes.get("confidence")),
        review_status="unreviewed",
        attributes_json=entity.attributes,
        evidence_ids_json=entity.evidence_ids,
    )


def _event_rows(
    *,
    audit_project_id: str,
    audit_run_id: str | None,
    audit_file_id: str | None,
    package: Phase10CustomerEvidencePackage,
    entity_id_to_object_id: dict[str, str],
) -> tuple[list[NormalizedEventUpsert], dict[str, str]]:
    classification_by_event = {item.event_id: item for item in package.cte_classification_results}
    rows: list[NormalizedEventUpsert] = []
    event_id_to_normalized_id: dict[str, str] = {}
    for event in package.event_graph:
        normalized_event_id = _stable_id("nev", audit_project_id, audit_run_id or "", event.event_id)
        event_id_to_normalized_id[event.event_id] = normalized_event_id
        classification = classification_by_event.get(event.event_id)
        confidence = classification.confidence if classification else None
        review_status = "needs_review" if event.reviewer_questions or (confidence is not None and confidence < 0.75) else "unreviewed"
        rows.append(
            NormalizedEventUpsert(
                id=normalized_event_id,
                audit_project_id=audit_project_id,
                audit_run_id=audit_run_id,
                audit_file_id=audit_file_id,
                source_row_key=event.source_row_key,
                event_type_claim=event.event_type_claim,
                event_datetime=_parse_datetime(event.event_datetime),
                event_datetime_raw=event.event_datetime,
                actor_object_id=_lookup(entity_id_to_object_id, event.actor_id),
                product_object_id=_lookup(entity_id_to_object_id, event.product_id),
                lot_object_id=_lot_object_id(entity_id_to_object_id, event.lot_or_tlc),
                source_lot_object_id=_lot_object_id(entity_id_to_object_id, event.source_lot_or_tlc),
                output_lot_object_id=_lot_object_id(entity_id_to_object_id, event.output_lot_or_tlc),
                from_object_id=_lookup(entity_id_to_object_id, event.from_partner_id),
                to_object_id=_lookup(entity_id_to_object_id, event.to_partner_id),
                destination_type=event.destination_type,
                action_terms_json=event.action_terms,
                classified_ctes_json=event.classified_ctes,
                suppressed_ctes_json=event.suppressed_ctes,
                reviewer_questions_json=event.reviewer_questions,
                confidence=confidence,
                review_status=review_status,
                metadata_json={
                    "sourceEventId": event.event_id,
                    "actorRole": event.actor_role.model_dump(mode="json"),
                    "foodForm": event.food_form.model_dump(mode="json"),
                    "productName": event.product_name,
                    "lotOrTlc": event.lot_or_tlc,
                },
            )
        )
    return rows, event_id_to_normalized_id


def _event_evidence_refs(
    package: Phase10CustomerEvidencePackage,
    event_id_to_normalized_id: dict[str, str],
) -> list[NormalizedEventEvidenceRefCreate]:
    refs: list[NormalizedEventEvidenceRefCreate] = []
    for event in package.event_graph:
        normalized_event_id = event_id_to_normalized_id[event.event_id]
        for evidence_id in event.evidence_ids:
            refs.append(
                NormalizedEventEvidenceRefCreate(
                    normalized_event_id=normalized_event_id,
                    evidence_item_id=evidence_id,
                    role="source_cell",
                )
            )
    return refs


def _kde_value_rows(
    *,
    audit_project_id: str,
    audit_run_id: str | None,
    package: Phase10CustomerEvidencePackage,
    event_id_to_normalized_id: dict[str, str],
) -> list[NormalizedKdeValueCreate]:
    event_by_row_key = {event.source_row_key: event for event in package.event_graph}
    rows: list[NormalizedKdeValueCreate] = []
    for record in package.evidence_records:
        row_key = _record_row_key(record)
        event = event_by_row_key.get(row_key)
        review_status = "needs_review" if record.confidence < 0.75 else "unreviewed"
        rows.append(
            NormalizedKdeValueCreate(
                id=_stable_id("kde", audit_project_id, audit_run_id or "", record.evidence_id, record.field_key),
                audit_project_id=audit_project_id,
                audit_run_id=audit_run_id,
                normalized_event_id=event_id_to_normalized_id.get(event.event_id) if event else None,
                evidence_item_id=record.evidence_id,
                kde_key=record.field_key,
                kde_label=record.column_name,
                raw_value=record.raw_value,
                normalized_value=record.normalized_value,
                confidence=record.confidence,
                review_status=review_status,
                metadata_json={
                    "fieldType": record.field_type,
                    "extractionMethod": record.extraction_method,
                    "sourcePointer": record.source_pointer.model_dump(mode="json"),
                },
            )
        )
    return rows


def _tlc_lineage_rows(
    *,
    audit_project_id: str,
    audit_run_id: str | None,
    package: Phase10CustomerEvidencePackage,
    event_id_to_normalized_id: dict[str, str],
) -> list[TlcLineageLinkCreate]:
    rows: list[TlcLineageLinkCreate] = []
    for event in package.event_graph:
        normalized_event_id = event_id_to_normalized_id[event.event_id]
        if event.source_lot_or_tlc or event.output_lot_or_tlc:
            rows.append(
                TlcLineageLinkCreate(
                    id=_stable_id("tlc", audit_project_id, audit_run_id or "", event.event_id, "input_output"),
                    audit_project_id=audit_project_id,
                    audit_run_id=audit_run_id,
                    normalized_event_id=normalized_event_id,
                    source_tlc=event.source_lot_or_tlc,
                    output_tlc=event.output_lot_or_tlc or event.lot_or_tlc,
                    link_type="input_to_output",
                    confidence=0.85 if event.source_lot_or_tlc and event.output_lot_or_tlc else 0.65,
                    review_status="needs_review" if not (event.source_lot_or_tlc and event.output_lot_or_tlc) else "unreviewed",
                    evidence_ids_json=event.evidence_ids,
                    metadata_json={"sourceEventId": event.event_id},
                )
            )
        elif event.lot_or_tlc:
            rows.append(
                TlcLineageLinkCreate(
                    id=_stable_id("tlc", audit_project_id, audit_run_id or "", event.event_id, "event_lot"),
                    audit_project_id=audit_project_id,
                    audit_run_id=audit_run_id,
                    normalized_event_id=normalized_event_id,
                    source_tlc=event.lot_or_tlc,
                    output_tlc=event.lot_or_tlc,
                    link_type="event_lot",
                    confidence=0.7,
                    review_status="unreviewed",
                    evidence_ids_json=event.evidence_ids,
                    metadata_json={"sourceEventId": event.event_id},
                )
            )
    return rows


def _review_item_rows(
    *,
    audit_project_id: str,
    audit_run_id: str | None,
    package: Phase10CustomerEvidencePackage,
    entity_id_to_object_id: dict[str, str],
    event_id_to_normalized_id: dict[str, str],
) -> list[NormalizedReviewItemCreate]:
    rows: list[NormalizedReviewItemCreate] = []
    for question in package.reviewer_questions:
        event_id = question.get("eventId") or question.get("event_id")
        evidence_ids = question.get("evidenceIds") or question.get("evidence_ids") or []
        rows.append(
            NormalizedReviewItemCreate(
                id=_stable_id("nri", audit_project_id, audit_run_id or "", "package_question", str(question)),
                audit_project_id=audit_project_id,
                audit_run_id=audit_run_id,
                normalized_event_id=event_id_to_normalized_id.get(str(event_id)) if event_id else None,
                review_type="reviewer_question",
                question=str(question.get("question") or question.get("message") or question),
                reason=str(question.get("reason") or "Parser requested reviewer confirmation."),
                severity=str(question.get("severity") or "medium"),
                evidence_ids_json=evidence_ids,
                metadata_json=question,
            )
        )

    for event in package.event_graph:
        normalized_event_id = event_id_to_normalized_id[event.event_id]
        for question in event.reviewer_questions:
            rows.append(
                NormalizedReviewItemCreate(
                    id=_stable_id("nri", audit_project_id, audit_run_id or "", event.event_id, question),
                    audit_project_id=audit_project_id,
                    audit_run_id=audit_run_id,
                    normalized_event_id=normalized_event_id,
                    review_type="event_ambiguity",
                    question=question,
                    reason="Event classification or normalization was ambiguous.",
                    severity="medium",
                    evidence_ids_json=event.evidence_ids,
                    metadata_json={"sourceEventId": event.event_id},
                )
            )
        if event.food_form.review_required:
            rows.append(
                NormalizedReviewItemCreate(
                    id=_stable_id("nri", audit_project_id, audit_run_id or "", event.event_id, "food_form"),
                    audit_project_id=audit_project_id,
                    audit_run_id=audit_run_id,
                    normalized_event_id=normalized_event_id,
                    review_type="food_form_review",
                    question="Confirm whether the product/form remains in scope for FSMA 204.",
                    reason="Food form resolver marked this event for review.",
                    severity="medium",
                    evidence_ids_json=event.evidence_ids,
                    metadata_json=event.food_form.model_dump(mode="json"),
                )
            )
        if event.actor_role.confidence < 0.75:
            rows.append(
                NormalizedReviewItemCreate(
                    id=_stable_id("nri", audit_project_id, audit_run_id or "", event.event_id, "actor_role"),
                    audit_project_id=audit_project_id,
                    audit_run_id=audit_run_id,
                    normalized_event_id=normalized_event_id,
                    business_object_id=_lookup(entity_id_to_object_id, event.actor_id),
                    review_type="actor_role_review",
                    question="Confirm the actor role for this event.",
                    reason="Actor role confidence is below the auto-accept threshold.",
                    severity="medium",
                    evidence_ids_json=event.evidence_ids,
                    metadata_json=event.actor_role.model_dump(mode="json"),
                )
            )

    for conflict in package.evidence_conflicts:
        rows.append(
            NormalizedReviewItemCreate(
                id=_stable_id("nri", audit_project_id, audit_run_id or "", "conflict", conflict.conflict_id),
                audit_project_id=audit_project_id,
                audit_run_id=audit_run_id,
                review_type="evidence_conflict",
                question=f"Resolve conflicting values for {conflict.field_key}.",
                reason=conflict.conflict_type,
                severity=conflict.severity,
                evidence_ids_json=conflict.evidence_ids_by_value,
                metadata_json=conflict.model_dump(mode="json"),
            )
        )

    deduped = {row.id: row for row in rows}
    return list(deduped.values())


def _record_row_key(record: CustomerEvidenceRecord) -> str:
    return f"{record.uploaded_file}:{record.sheet_name}:{record.row_number}"


def _lookup(entity_id_to_object_id: dict[str, str], value: str | None) -> str | None:
    if not value:
        return None
    return entity_id_to_object_id.get(value)


def _lot_object_id(entity_id_to_object_id: dict[str, str], tlc: str | None) -> str | None:
    if not tlc:
        return None
    candidates = [tlc, f"lot:{tlc}", f"tlc:{tlc}"]
    for candidate in candidates:
        if candidate in entity_id_to_object_id:
            return entity_id_to_object_id[candidate]
    return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_name(value: str) -> str:
    return " ".join(value.lower().split())


def _stable_id(prefix: str, *parts: str) -> str:
    digest = sha256_text("|".join(parts))[:24]
    return f"{prefix}_{digest}"
