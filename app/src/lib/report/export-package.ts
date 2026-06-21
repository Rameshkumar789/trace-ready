import type { StoredAudit } from "@/lib/audit/stored-audit";
import { findingsToRows } from "./export-audit-xlsx";

function buildReadinessSummaryRows(audit: StoredAudit) {
  const counts = audit.findings.reduce<Record<string, number>>((acc, finding) => {
    acc[finding.status] = (acc[finding.status] ?? 0) + 1;
    return acc;
  }, {});
  return [
    { metric: "audit_id", value: audit.auditId },
    { metric: "file_name", value: audit.fileName },
    { metric: "created_at", value: audit.createdAt },
    { metric: "readiness_gate", value: audit.readinessGate.passed ? "passed" : "blocked" },
    { metric: "findings", value: String(audit.findings.length) },
    ...Object.entries(counts).map(([status, count]) => ({ metric: `findings_${status}`, value: String(count) }))
  ];
}

function buildSortableExportCheckRows(audit: StoredAudit) {
  return audit.dataset.events.map((event) => ({
    event_id: event.eventId,
    cte_type: event.eventType,
    event_datetime: event.eventDatetime ?? "",
    actor_location_id: event.actorLocationId ?? "",
    reference_record_type: event.referenceRecordType ?? "",
    reference_record_no: event.referenceRecordNo ?? "",
    has_source_document: audit.dataset.sourceDocuments.some(
      (doc) => doc.eventId === event.eventId && doc.evidenceStatus === "available"
    )
      ? "yes"
      : "no"
  }));
}

export function buildAuditExportPackage(audit: StoredAudit) {
  return {
    "11_Bellwether_Findings": findingsToRows(audit.findings),
    "12_Readiness_Summary": buildReadinessSummaryRows(audit),
    "13_FDA_Sortable_Export_Check": buildSortableExportCheckRows(audit)
  };
}
